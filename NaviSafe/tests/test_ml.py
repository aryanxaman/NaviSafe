import json
import unittest
from pathlib import Path

import joblib
import pandas as pd

from backend.inference import predict
from backend.train_model import FEATURES, snapshot

ROOT = Path(__file__).resolve().parents[1]


class MLTests(unittest.TestCase):
    def test_splits_have_no_time_or_location_overlap(self):
        frame = pd.read_csv(ROOT / "models/delhi-v2/splits.csv")
        groups = [frame[frame.split == part] for part in ["train", "validation", "test"]]
        for a, b in zip(groups, groups[1:]):
            self.assertLessEqual(pd.to_datetime(a.label_end).max(), pd.to_datetime(b.snapshot).min())
        for i, a in enumerate(groups):
            for b in groups[i+1:]:
                self.assertFalse(set(a.location_group) & set(b.location_group))
                self.assertFalse(set(a.edge_id) & set(b.edge_id))
        self.assertFalse(frame.duplicated(["edge_id", "bucket", "snapshot"]).any())

    def test_features_exclude_truth_and_reporting_propensity(self):
        self.assertFalse(any(c.startswith("_truth") for c in FEATURES))
        self.assertNotIn("report_propensity", FEATURES)
        self.assertNotIn("y", FEATURES)

    def test_future_reports_do_not_change_past_features(self):
        at = pd.Timestamp("2026-01-01", tz="UTC")
        edges = pd.DataFrame({"edge_id": [1]})
        reports = pd.DataFrame({"edge_id": [1], "bucket": [0], "timestamp": [at-pd.Timedelta(days=1)]})
        first = snapshot(edges, reports, at)
        future = pd.concat([reports, pd.DataFrame({"edge_id": [1], "bucket": [0], "timestamp": [at+pd.Timedelta(days=1)]})])
        second = snapshot(edges, future, at)
        self.assertEqual(first.prior_90d_count.tolist(), second.prior_90d_count.tolist())
        self.assertNotEqual(first.y.tolist(), second.y.tolist())

    def test_inference_contract(self):
        artifact = joblib.load(ROOT / "models/delhi-v2/model.joblib")
        features = json.loads((ROOT / "models/delhi-v2/example_features.json").read_text())
        result = predict(artifact, features)
        self.assertTrue(0 <= result["score"] <= 1)
        self.assertEqual(result["data_origin"], "SYNTHETIC")
        self.assertIsNone(result["uncertainty"])
        with self.assertRaises(ValueError):
            predict(artifact, {**features, "bucket": 24})
        with self.assertRaises(ValueError):
            predict(artifact, {**features, "lit": -1})


if __name__ == "__main__":
    unittest.main()
