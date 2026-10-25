import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from backend.evidence import inspect_image, near_duplicate, transition
from backend.main import app
from backend.store import database, all_reports, save


def picture(seed=1, exif=False):
    array = np.random.default_rng(seed).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    out = io.BytesIO()
    image = Image.fromarray(array)
    metadata = Image.Exif()
    if exif:
        metadata[306] = "2026:10:20 12:00:00"
    image.save(out, format="JPEG", exif=metadata)
    return out.getvalue()


class EvidenceTests(unittest.TestCase):
    def test_decoding_and_metadata_privacy(self):
        clean, checks = inspect_image(picture(exif=True), "poor_lighting")
        self.assertTrue(checks["metadata"]["timestamp_present"])
        self.assertFalse(Image.open(io.BytesIO(clean)).getexif())
        self.assertEqual(checks["relevance"]["outcome"], "inconclusive")

    def test_invalid_file_and_oversize(self):
        for raw in [b"<script>alert(1)</script>", b"", b"x" * (8 * 1024 * 1024 + 1)]:
            with self.assertRaises(ValueError):
                inspect_image(raw, "poor_lighting")

    def test_duplicate_and_near_duplicate(self):
        _, first = inspect_image(picture(), "poor_lighting")
        _, same = inspect_image(picture(), "poor_lighting")
        self.assertTrue(near_duplicate(first, same))
        altered = {**same, "sha256": "different", "dhash": f"{int(same['dhash'],16)^3:016x}"}
        self.assertTrue(near_duplicate(first, altered))

    def test_vision_mismatch_is_only_signal(self):
        class Provider:
            def assess(self, image, category):
                return {"outcome": "possible_mismatch", "reason": "Needs review"}
        _, checks = inspect_image(picture(), "poor_lighting", Provider())
        self.assertEqual(checks["relevance"]["outcome"], "possible_mismatch")
        self.assertNotIn("status", checks)

    def test_status_graph_and_verification_gates(self):
        report = {"status": "pending_review", "version": 1, "history": [], "corroboration_candidates": []}
        with self.assertRaises(ValueError):
            transition(report, "verified", "An image passed a classifier.", "reviewer", True, True)
        transition(report, "provisionally_published", "Visible with unverified label.", "reviewer")
        transition(report, "disputed", "Conflicting observation requires investigation.", "reviewer")
        transition(report, "rejected", "Claim cannot meet the evidence policy.", "reviewer")
        transition(report, "pending_review", "Appeal contains new information.", "reviewer")
        self.assertEqual(len(report["history"]), 4)


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {key: os.environ.get(key) for key in ["SAFEPATH_DB", "SAFEPATH_MEDIA", "SAFEPATH_MODERATOR_TOKEN"]}
        os.environ["SAFEPATH_DB"] = str(Path(self.tmp.name) / "reports.db")
        os.environ["SAFEPATH_MEDIA"] = str(Path(self.tmp.name) / "media")
        os.environ["SAFEPATH_MODERATOR_TOKEN"] = "test-moderator-only"
        self.client = TestClient(app)
        self.headers = {"X-Client-ID": "test-device-01", "Idempotency-Key": "test-key-01"}
        self.mod = {"Authorization": "Bearer test-moderator-only"}
        self.fields = {
            "street": "Test observation — not a real incident", "category": "poor_lighting",
            "desc": "Synthetic acceptance-test example.", "observed_at": datetime.now(timezone.utc).isoformat(),
            "latitude": "28.59", "longitude": "77.04", "personally_observed": "true",
            "location_consent": "true", "visibility_consent": "true",
        }

    def tearDown(self):
        self.client.close()
        for key, value in self.env.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        self.tmp.cleanup()

    def submit(self, device=1, image=None):
        headers = {"X-Client-ID": f"test-device-{device:02}", "Idempotency-Key": f"test-key-{device:02}"}
        files = {"file": ("../../escape.jpg", image, "image/jpeg")} if image else None
        response = self.client.post("/api/report", data=self.fields, headers=headers, files=files)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["report"]

    def test_valid_image_and_exif_remain_pending(self):
        report = self.submit(image=picture(exif=True))
        self.assertEqual(report["status"], "pending_review")
        self.assertEqual(self.client.get("/api/reports").json()["reports"], [])
        stored = self.client.get("/api/moderation", headers=self.mod).json()["reports"][0]
        self.assertTrue(stored["checks"]["metadata"]["present"])
        self.assertEqual(stored["status"], "pending_review")
        self.assertTrue((Path(self.tmp.name) / "media" / f"{report['id']}.jpg").exists())

    def test_idempotency_replay_and_conflict(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first["id"], second["id"])
        altered = {**self.fields, "desc": "Changed queued payload."}
        self.assertEqual(self.client.post("/api/report", data=altered, headers=self.headers).status_code, 409)

    def test_role_enforcement_and_image_privacy(self):
        report = self.submit(image=picture())
        self.assertEqual(self.client.get("/api/moderation").status_code, 403)
        self.assertEqual(self.client.get(f"/api/moderation/{report['id']}/image").status_code, 403)
        self.assertEqual(self.client.get(f"/api/moderation/{report['id']}/image", headers=self.mod).status_code, 200)
        os.environ.pop("SAFEPATH_MODERATOR_TOKEN")
        self.assertEqual(self.client.get("/api/moderation", headers=self.mod).status_code, 503)

    def test_no_automated_promotion_or_duplicate_independence(self):
        first = self.submit(1, picture())
        self.submit(2, picture())
        self.submit(3, picture())
        records = self.client.get("/api/moderation", headers=self.mod).json()["reports"]
        self.assertEqual(len(records), 3)  # duplicates retained, not erased
        self.assertTrue(all(len(r["corroboration_candidates"]) == 0 for r in records))
        review = {"status": "verified", "reason": "EXIF alone appears plausible.", "version": 1,
                  "independent_confirmed": True, "privacy_reviewed": True}
        self.assertEqual(self.client.post(f"/api/moderation/{first['id']}", json=review, headers=self.mod).status_code, 422)

    def test_human_review_audit_conflict_and_publication(self):
        first = self.submit(1, picture(1))
        self.submit(2, picture(2))
        self.submit(3, picture(3))
        body = {"status": "verified", "reason": "Reviewed independent observations, times, location and privacy.",
                "version": 1, "independent_confirmed": True, "privacy_reviewed": True}
        result = self.client.post(f"/api/moderation/{first['id']}", headers=self.mod, json=body)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["history"][-1]["role"], "moderator")
        self.assertEqual(self.client.post(f"/api/moderation/{first['id']}", headers=self.mod, json=body).status_code, 409)
        public = self.client.get("/api/reports").json()["reports"][0]
        self.assertNotIn("actor", public)
        self.assertNotIn("checks", public)
        self.assertNotIn("latitude", public)

    def test_training_curation_is_explicit_and_verified_only(self):
        report = self.submit(image=picture(10))
        body = {"eligible": True, "label": "unsafe_location",
                "reason": "Verified report with reviewed evidence and explicit training eligibility."}
        self.assertEqual(self.client.post(f"/api/moderation/{report['id']}/training", headers=self.mod, json=body).status_code, 422)
        review = {"status": "verified", "reason": "Reviewed independent observations, times, location and privacy.",
                  "version": 1, "independent_confirmed": True, "privacy_reviewed": True}
        # No corroboration candidates exist in this isolated submission, so verification remains blocked.
        self.assertEqual(self.client.post(f"/api/moderation/{report['id']}", headers=self.mod, json=review).status_code, 422)
        dataset = self.client.get("/api/moderation/training-dataset", headers=self.mod).json()
        self.assertEqual(dataset["records"], [])

    def test_correction_appeal_and_expiration(self):
        report = self.submit()
        correction = {"kind": "correction", "reason": "The observation time should be corrected."}
        self.assertEqual(self.client.post(f"/api/reports/{report['id']}/review", headers=self.headers, json=correction).status_code, 200)
        self.assertEqual(self.client.post(f"/api/reports/{report['id']}/review", headers={"X-Client-ID": "other-device"}, json=correction).status_code, 404)
        with database() as conn:
            row = all_reports(conn)[0]
            row["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            save(conn, row)
        mine = self.client.get("/api/reports?mine=true", headers=self.headers).json()["reports"][0]
        self.assertEqual(mine["status"], "expired")
        reviewed = self.client.get("/api/moderation", headers=self.mod).json()["reports"][0]
        self.assertEqual(len(reviewed["review_requests"]), 1)

    def test_invalid_location_consent_and_future_time(self):
        fields = {**self.fields, "location_consent": "false"}
        self.assertEqual(self.client.post("/api/report", data=fields).status_code, 422)
        fields = {**self.fields, "observed_at": (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
        self.assertEqual(self.client.post("/api/report", data=fields).status_code, 422)

    def test_rate_limit(self):
        for i in range(8):
            response = self.client.post("/api/report", data=self.fields, headers={"X-Client-ID": "same-device", "Idempotency-Key": str(i)})
            self.assertEqual(response.status_code, 200)
        response = self.client.post("/api/report", data=self.fields, headers={"X-Client-ID": "same-device", "Idempotency-Key": "ninth"})
        self.assertEqual(response.status_code, 429)

    def test_route_contract_and_bounds(self):
        body = {"start_lat": 28.583, "start_lon": 77.038, "end_lat": 28.602, "end_lon": 77.054, "alpha": 2, "hour": 20}
        response = self.client.post("/api/route", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["data_origin"], "SYNTHETIC")
        self.assertLessEqual(data["safest"]["metrics"]["distance"], data["fastest"]["metrics"]["distance"] * 1.5)
        self.assertTrue(0 <= data["safest"]["metrics"]["exposure"] <= 1)
        self.assertEqual(self.client.post("/api/route", json={**body, "hour": 30}).status_code, 422)
        self.assertEqual(self.client.post("/api/route", json={**body, "start_lat": 20}).status_code, 422)
        self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
