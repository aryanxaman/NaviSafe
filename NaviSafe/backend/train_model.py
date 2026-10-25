"""Reproducible synthetic report-occurrence experiment. No real-world safety validation."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from pyproj import Transformer
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, balanced_accuracy_score, roc_auc_score, precision_recall_fscore_support, confusion_matrix, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
FEATURES=['length_m','lit','dist_metro_m','dist_police_m','isolated','shops_open_night','liquor_near','police_near','footfall_day','footfall_night','bucket','prior_90d_count']
SEED=42
MODEL_VERSION='delhi-v3'

def snap_reports(edges,reports):
    """Nearest straight graph segment in UTM 43N, bounded to 150 m, no truth access."""
    projection=Transformer.from_crs('EPSG:4326','EPSG:32643',always_xy=True)
    ax,ay=projection.transform(edges.lon1.to_numpy(),edges.lat1.to_numpy())
    bx,by=projection.transform(edges.lon2.to_numpy(),edges.lat2.to_numpy())
    px,py=projection.transform(reports.longitude.to_numpy(),reports.latitude.to_numpy())
    a=np.column_stack([ax,ay]); delta=np.column_stack([bx-ax,by-ay]); denominator=np.sum(delta**2,axis=1)
    matches=[];distances=[]
    for offset in range(0,len(reports),128):
        points=np.column_stack([px[offset:offset+128],py[offset:offset+128]])
        relative=points[:,None,:]-a[None,:,:]
        t=np.clip(np.sum(relative*delta,axis=2)/np.maximum(denominator,1e-8),0,1)
        d2=np.sum((relative-t[:,:,None]*delta)**2,axis=2)
        idx=d2.argmin(axis=1)
        matches.extend(edges.edge_id.to_numpy()[idx]);distances.extend(np.sqrt(d2[np.arange(len(idx)),idx]))
    result=reports.copy();result['edge_id']=matches;result['snap_distance_m']=distances
    return result[result.snap_distance_m<=150].copy()

def spatial_groups(edges):
    # ~500m blocks. No location block or edge occurs in more than one evaluation partition.
    groups=((edges.mid_lat*200).astype(int).astype(str)+'_'+(edges.mid_lon*200).astype(int).astype(str))
    partition=groups.map(lambda s:int(hashlib.sha256(s.encode()).hexdigest()[:8],16)%10)
    return groups,np.where(partition<6,'train',np.where(partition<8,'validation','test'))

def snapshot(edges,reports,at,horizon=30):
    past=reports[(reports.timestamp<at)&(reports.timestamp>=at-pd.Timedelta(days=90))]
    future=reports[(reports.timestamp>=at)&(reports.timestamp<at+pd.Timedelta(days=horizon))]
    prior=past.groupby(['edge_id','bucket']).size(); labels=future.groupby(['edge_id','bucket']).size()
    frame=pd.concat([edges.assign(bucket=b) for b in range(6)],ignore_index=True)
    keys=pd.MultiIndex.from_frame(frame[['edge_id','bucket']])
    frame['prior_90d_count']=prior.reindex(keys,fill_value=0).to_numpy()
    frame['y']=(labels.reindex(keys,fill_value=0).to_numpy()>0).astype(int)
    frame['snapshot']=at.isoformat();frame['label_end']=(at+pd.Timedelta(days=horizon)).isoformat()
    return frame

def metrics(y,p,threshold):
    pred=p>=threshold
    precision,recall,f1,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
    bins=[]
    for lo in np.linspace(0,.9,10):
        mask=(p>=lo)&(p<(lo+.1 if lo<.9 else 1.0001))
        if mask.sum(): bins.append({'lower':float(lo),'count':int(mask.sum()),'mean_prediction':float(p[mask].mean()),'observed_rate':float(np.asarray(y)[mask].mean())})
    return {'n':len(y),'positives':int(np.sum(y)),'accuracy':float(accuracy_score(y,pred)),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),'precision':float(precision),'recall':float(recall),'f1':float(f1),'pr_auc_average_precision':float(average_precision_score(y,p)),'roc_auc':float(roc_auc_score(y,p)) if len(set(y))>1 else None,'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1])),'confusion_matrix_tn_fp_fn_tp':confusion_matrix(y,pred,labels=[0,1]).ravel().tolist(),'threshold':float(threshold),'calibration_bins':bins}

def pipeline(model):
    return Pipeline([('preprocess',ColumnTransformer([('numeric',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),FEATURES)],remainder='drop')),('model',model)])

def load_reports(data):
    sources = [
        ('safecity_synthetic.csv', 'category'),
        ('app_microreports_synthetic.csv', 'report_type'),
    ]
    parts = []
    for filename, category_column in sources:
        path = data / filename
        if not path.exists():
            continue
        raw = pd.read_csv(path)
        required = {'report_id', 'data_origin', 'timestamp', 'latitude', 'longitude', 'reporter_id', category_column}
        missing = required - set(raw.columns)
        if missing:
            raise ValueError(f'{path} is missing required columns: {sorted(missing)}')
        parts.append(raw[['report_id', 'data_origin', 'timestamp', 'latitude', 'longitude', 'reporter_id', category_column]].rename(columns={category_column: 'category'}))
    if not parts:
        raise FileNotFoundError(f'No compatible report sources found in {data}')
    return pd.concat(parts, ignore_index=True)

def run(data,out):
    if out.exists() and any(out.iterdir()): raise SystemExit('Output directory is not empty. Choose a new version; existing artifacts are never overwritten.')
    out.mkdir(parents=True,exist_ok=True)
    edges=pd.read_csv(data/'edges_features.csv')
    raw=load_reports(data)
    # Select allowed columns first. _truth_* and reporting propensity cannot enter training.
    reports=raw.copy()
    reports['timestamp']=pd.to_datetime(reports.timestamp,utc=True)
    reports=reports.drop_duplicates('report_id').drop_duplicates(['timestamp','latitude','longitude','reporter_id','category'])
    reports=snap_reports(edges,reports);reports['bucket']=reports.timestamp.dt.hour//4
    edges['location_group'],edges['geographic_split']=spatial_groups(edges)
    end=reports.timestamp.max().normalize()+pd.Timedelta(days=1)
    windows=pd.date_range(end=end-pd.Timedelta(days=30),periods=12,freq='30D')
    parts=[]
    for i,at in enumerate(windows):
        partition='train' if i<8 else 'validation' if i<10 else 'test'
        frame=snapshot(edges,reports,at);frame=frame[frame.geographic_split==partition].copy();frame['split']=partition;parts.append(frame)
    dataset=pd.concat(parts,ignore_index=True)
    train=dataset[dataset.split=='train'];val=dataset[dataset.split=='validation'];test=dataset[dataset.split=='test']
    assert pd.to_datetime(train.label_end).max()<=pd.to_datetime(val.snapshot).min()
    assert pd.to_datetime(val.label_end).max()<=pd.to_datetime(test.snapshot).min()
    assert not set(train.location_group)&set(val.location_group) and not set(train.location_group)&set(test.location_group) and not set(val.location_group)&set(test.location_group)
    dataset[['edge_id','bucket','location_group','snapshot','label_end','split','y','data_origin']].to_csv(out/'splits.csv',index=False)
    dataset[FEATURES+['y','split','snapshot','data_origin']].to_csv(out/'snapshot_dataset.csv.gz',index=False,compression='gzip')
    models={'prevalence_baseline':DummyClassifier(strategy='prior'),'logistic':LogisticRegression(max_iter=500,random_state=SEED,class_weight='balanced'),'lightgbm':LGBMClassifier(n_estimators=160,max_depth=5,num_leaves=20,min_child_samples=50,learning_rate=.05,random_state=SEED,n_jobs=2,verbosity=-1,class_weight='balanced')}
    fitted={};validation={}
    for name,candidate in models.items():
        print('Training',name,flush=True)
        model=pipeline(candidate).fit(train[FEATURES],train.y);fitted[name]=model
        predictions=model.predict_proba(val[FEATURES])[:,1]
        thresholds=np.unique(np.r_[np.linspace(.001,.2,100),.5,np.quantile(predictions,np.linspace(0,1,50))])
        # F2 favours recall; explicitly exposes resulting false-positive tradeoff.
        def f2(t):
            pr,re,_,_=precision_recall_fscore_support(val.y,predictions>=t,average='binary',zero_division=0)
            return 5*pr*re/(4*pr+re) if 4*pr+re else 0
        threshold=float(max(thresholds,key=f2))
        validation[name]=metrics(val.y,predictions,threshold)
    selected=max(validation,key=lambda n:validation[n]['pr_auc_average_precision'])
    # Final evaluation occurs only after model and threshold decisions above.
    final={name:metrics(test.y,model.predict_proba(test[FEATURES])[:,1],validation[name]['threshold']) for name,model in fitted.items()}
    chosen=fitted[selected]
    joblib.dump({'pipeline':chosen,'features':FEATURES,'model_version':MODEL_VERSION,'threshold':validation[selected]['threshold'],'data_timestamp':reports.timestamp.max().isoformat(),'data_origin':'SYNTHETIC'},out/'model.joblib')
    latest=snapshot(edges,reports,end)
    latest['p_ml']=chosen.predict_proba(latest[FEATURES])[:,1]
    latest[['edge_id','bucket','p_ml']].to_csv(out/'risk_table.csv',index=False)
    # Coefficients / split gain are associations, not causal importance.
    estimator=chosen.named_steps['model']
    weights=getattr(estimator,'feature_importances_',np.abs(getattr(estimator,'coef_',np.zeros((1,len(FEATURES)))))[0] if hasattr(estimator,'coef_') else np.zeros(len(FEATURES)))
    importance=dict(zip(FEATURES,[float(x) for x in weights]))
    subgroups={}
    preds=chosen.predict_proba(test[FEATURES])[:,1]
    for group in sorted(test.location_group.unique()):
        mask=(test.location_group==group).to_numpy();positives=int(test.loc[mask,'y'].sum())
        subgroups[group]=metrics(test.loc[mask,'y'],preds[mask],validation[selected]['threshold']) if positives>=10 else {'n':int(mask.sum()),'positives':positives,'note':'Too few positives for meaningful group metrics.'}
    result={'evaluation_scope':'SYNTHETIC ONLY; no real-world safety validation','selected_model':selected,'selection':'Validation average precision; threshold maximizes validation F2. Test untouched until selection.','split':'Disjoint chronological 30-day label windows AND disjoint 500m coordinate blocks. Same locations never cross partitions.','legacy_baseline':'Legacy trainer used in-sample predictions and truth-based spam filtering; no valid held-out metric exists. Prevalence is the honest evaluation baseline.','snap':{'input':len(raw),'retained':len(reports),'method':'nearest straight segment, EPSG:32643, <=150 metres'},'validation':validation,'test':final,'feature_importance':importance,'geographic_groups':subgroups,'uncertainty':'No calibrated real-world uncertainty; calibration bins describe synthetic test only.'}
    (out/'evaluation.json').write_text(json.dumps(result,indent=2))
    manifest={'version':MODEL_VERSION,'seed':SEED,'origin':'SYNTHETIC','retrieval_date':None,'input_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [data/'edges_features.csv',data/'safecity_synthetic.csv',data/'app_microreports_synthetic.csv'] if p.exists()},'feature_allowlist':FEATURES,'python':platform.python_version(),'coverage':{'name':'Dwarka study network','bounds':[float(edges.mid_lon.min()),float(edges.mid_lat.min()),float(edges.mid_lon.max()),float(edges.mid_lat.max())]},'transformations':['combine compatible synthetic report sources','deduplicate observations','project to UTM 43N','snap to straight segment <=150m','prior 90 day counts strictly before snapshot','next 30 day reported-occurrence target','disjoint time and location splits','class-balanced training only','fit imputer and scaler on training only'],'target':'At least one synthetic reported observation on a segment/time bucket in the next 30 days; includes reporting bias and synthetic spam; not harm.','generation':'Existing scenario generator; original seed/retrieval timestamp not recorded. New runs record full configs separately.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'MODEL_CARD.md').write_text(f'''# SafePath Delhi v3 — experimental model\n\nSelected model: {selected}. Synthetic data only. No clinical, policing, emergency or real-world individual-safety use.\n\nTarget: at least one generated report on a street segment and 4-hour bucket during the next 30 days. Reporting is biased; outcomes are not actual harm. Features include synthetic lighting/activity proxies and pre-snapshot report counts. Compatible Safecity-style and app microreport sources are combined. No `_truth_*`, report propensity, community submissions or ground-truth risk table enters features or filtering.\n\nEvaluation: disjoint 30-day chronological horizons and disjoint coordinate blocks. Preprocessing fits on train only. Class balancing is applied to training folds only; validation and test retain their natural prevalence. Selection by validation average precision, threshold by validation F2. Final test is evaluated after selection. See evaluation.json for PR-AUC, ROC-AUC, precision, recall, F1, confusion matrices, Brier score, calibration bins, group counts and feature associations. No calibrated real-world uncertainty is returned.\n\nCoverage: Dwarka only. Street geometry is OSM-derived; engineered features and reports are synthetic. Other Delhi localities have no validated coverage. This model predicts synthetic report occurrence, not actual harm or personal safety.\n\nUse: local research demonstrations and pipeline testing. A lower score or missing report does not establish safety. The model artifact is fitted only on the train partition; evaluation partitions are not reused for fitting. Prediction probabilities must be displayed as experimental contextual indices. Feature importance is not causal explanation.\n\nReproduce: `python -m backend.train_model --data synthetic_data --out models/delhi-v3`. Infer: `python -m backend.inference --model models/delhi-v3/model.joblib --features models/delhi-v3/example_features.json`.\n''')
    (out/'example_features.json').write_text(latest[FEATURES].iloc[0].to_json())
    print(json.dumps({'selected':selected,'test':final[selected]},indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=ROOT/'synthetic_data');parser.add_argument('--out',type=Path,default=ROOT/'models/delhi-v3');args=parser.parse_args();run(args.data,args.out)
