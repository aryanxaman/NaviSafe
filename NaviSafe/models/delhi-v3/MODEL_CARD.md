# SafePath Delhi v3 — experimental model

Selected model: lightgbm. Synthetic data only. No clinical, policing, emergency or real-world individual-safety use.

Target: at least one generated report on a street segment and 4-hour bucket during the next 30 days. Reporting is biased; outcomes are not actual harm. Features include synthetic lighting/activity proxies and pre-snapshot report counts. Compatible Safecity-style and app microreport sources are combined. No `_truth_*`, report propensity, community submissions or ground-truth risk table enters features or filtering.

Evaluation: disjoint 30-day chronological horizons and disjoint coordinate blocks. Preprocessing fits on train only. Class balancing is applied to training folds only; validation and test retain their natural prevalence. Selection by validation average precision, threshold by validation F2. Final test is evaluated after selection. See evaluation.json for PR-AUC, ROC-AUC, precision, recall, F1, confusion matrices, Brier score, calibration bins, group counts and feature associations. No calibrated real-world uncertainty is returned.

Coverage: Dwarka only. Street geometry is OSM-derived; engineered features and reports are synthetic. Other Delhi localities have no validated coverage. This model predicts synthetic report occurrence, not actual harm or personal safety.

Use: local research demonstrations and pipeline testing. A lower score or missing report does not establish safety. The model artifact is fitted only on the train partition; evaluation partitions are not reused for fitting. Prediction probabilities must be displayed as experimental contextual indices. Feature importance is not causal explanation.

Reproduce: `python -m backend.train_model --data synthetic_data --out models/delhi-v3`. Infer: `python -m backend.inference --model models/delhi-v3/model.joblib --features models/delhi-v3/example_features.json`.
