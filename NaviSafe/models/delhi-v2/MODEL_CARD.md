# SafePath Delhi v2 — experimental model

Selected model: logistic. Synthetic data only. No clinical, policing, emergency or real-world individual-safety use.

Target: at least one generated report on a street segment and 4-hour bucket during the next 30 days. Reporting is biased; outcomes are not actual harm. Features include synthetic lighting/activity proxies and pre-snapshot report counts. No `_truth_*`, report propensity, community submissions or ground-truth risk table enters features or filtering.

Evaluation: disjoint 30-day chronological horizons and disjoint coordinate blocks. Preprocessing fits on train only. Selection by validation average precision, threshold by validation F2. Final test is evaluated after selection. See evaluation.json for PR-AUC, ROC-AUC, precision, recall, F1, confusion matrices, Brier score, calibration bins, group counts and feature associations. Sparse group performance is withheld. No calibrated real-world uncertainty is returned.

Coverage: Dwarka only. Street geometry is OSM-derived; engineered features and reports are synthetic. Other Delhi localities have no validated coverage. Snapping uses projected straight segments, which approximate curved streets. No demographic safety claims can be assessed.

Use: local research demonstrations and pipeline testing. A lower score or missing report does not establish safety. The model artifact is fitted only on the train partition; evaluation partitions are not reused for fitting. Prediction probabilities must be displayed as experimental contextual indices. Feature importance is not causal explanation.

Reproduce: `python -m backend.train_model --out models/delhi-v3` (new empty output). Infer: `python -m backend.inference --model models/delhi-v2/model.joblib --features models/delhi-v2/example_features.json`.
