# Data audit and geographic coverage

No verified Delhi safety labels were found. Existing datasets are preserved unchanged. Two legacy user-upload rows are unreviewed, stored separately from all new observations and excluded from model fitting.

| File | Rows | Exact duplicate rows | Provenance |
|---|---:|---:|---|
| app_microreports_synthetic.csv | 2500 | 0 | {'SYNTHETIC': 2500} |
| edges_features.csv | 3769 | 0 | {'SYNTHETIC': 3769} |
| ground_truth_edge_risk.csv | 3769 | 0 | Derived synthetic/evaluation-only artifact |
| ncrb_synthetic.csv | 25 | 0 | {'SYNTHETIC': 25} |
| risk_table.csv | 22614 | 0 | Derived synthetic/evaluation-only artifact |
| safecity_synthetic.csv | 6120 | 0 | {'SYNTHETIC': 6120} |
| safetipin_synthetic.csv | 1200 | 0 | {'SYNTHETIC': 1200} |
| user_reports.csv | 2 | 0 | Unreviewed legacy user input |

The street network covers the Dwarka study area (approximately 28.57–28.61 N, 77.02–77.06 E); source graph may extend slightly beyond the bounding box. Coordinates resemble OSM nodes and the cached graph is retained. Original retrieval date, generator invocation and complete licensing manifest were not recorded; these are unknown rather than reconstructed. Street geometry is derived, while lighting fills, POI distances, activity proxies and incident records are synthetic. Do not describe them as observed municipal infrastructure.

Coverage gaps: no independently reviewed labels in Dwarka; no evaluated real observations in Hauz Khas–Saket or the rest of Delhi. Locality names are not authoritative polygons; evaluation groups use projected-area coordinate blocks, not neighborhood risk labels. No demographic labels support subgroup fairness claims. Numeric distributions, missingness, file hashes, time ranges and category counts are in data_audit.json.

Legacy pipeline risks: in-sample evaluation, truth-based spam filtering, snapping in degrees, reporting-propensity fallback risk. Version 2 excludes all truth columns, uses metric snapping, trains on past-only features, evaluates future windows on disjoint location blocks and separates human reports from training. Sparse positives make subgroup results unstable.

## Documented candidate sources (reviewed 20 October 2026)

- OpenStreetMap street/POI data: https://www.openstreetmap.org/copyright — ODbL attribution and share-alike conditions. The retained graph is the only external geographic input currently used; synthetic proxies must not be relabeled as OSM measurements. Public tile usage also has a separate usage policy; tiles are not bulk downloaded or cached.
- Government Open Data License India: https://data.gov.in/sites/default/files/NDSAP_OpenDataLicense.pdf — check the license on each chosen catalog resource, attribution and access/API requirements. No new official incident dataset was ingested.
- Safetipin methodology: https://safetipin.com/methodology/ — audits provide environmental context. Public methodology does not grant a license to a city-level raw audit dataset; obtain documented access and permitted use.
- NCRB aggregate publications and Safecity access remain candidate inputs, not supplied ground truth. Aggregated city statistics cannot provide precise street incident coordinates or labels.

## Synthetic generation

Existing generator models time, lighting, isolation, activity, reporting bias and spam. It does not create independent real observations. New generation refuses nonempty output directories and saves seed, parameters, source status, hashes and retrieval time where a new OSM request actually succeeds. Offline graphs are explicitly synthetic grids. No original dataset or model is overwritten.
