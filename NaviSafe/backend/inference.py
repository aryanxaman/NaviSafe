"""Stable inference contract; load only trusted, locally generated joblib artifacts."""
import argparse
import json
from pathlib import Path
import joblib
import pandas as pd

def predict(artifact,features):
    missing=set(artifact['features'])-set(features)
    if missing: raise ValueError('Missing features: '+', '.join(sorted(missing)))
    values={k:float(features[k]) for k in artifact['features']}
    if not 0<=values['bucket']<=5: raise ValueError('bucket must be 0–5')
    for name in ['lit','isolated','shops_open_night','liquor_near','police_near','footfall_day','footfall_night']:
        if not 0<=values[name]<=1: raise ValueError(name+' must be 0–1')
    if any(values[n]<0 for n in ['length_m','dist_metro_m','dist_police_m','prior_90d_count']): raise ValueError('Distances and counts must be nonnegative')
    import math
    if not all(math.isfinite(v) for v in values.values()): raise ValueError('Features must be finite')
    score=float(artifact['pipeline'].predict_proba(pd.DataFrame([values]))[0,1])
    return {'score':score,'explanation':'Experimental synthetic report-occurrence estimate, not a probability of harm. Includes lighting, activity proxies, time bucket and pre-snapshot report count.','model_version':artifact['model_version'],'data_timestamp':artifact['data_timestamp'],'data_origin':artifact['data_origin'],'uncertainty':None,'uncertainty_reason':'No calibrated real-world uncertainty available.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--features',type=Path,required=True);a=p.parse_args();print(json.dumps(predict(joblib.load(a.model),json.loads(a.features.read_text())),indent=2))
