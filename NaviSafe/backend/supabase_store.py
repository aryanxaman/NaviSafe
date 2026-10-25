"""Durable report and private-media persistence for Vercel/Supabase deployments."""
import os
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL"))


class SupabaseStore:
    def __init__(self):
        if not configured():
            raise RuntimeError("Supabase persistence is not configured.")
        self.client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
        self.bucket = os.getenv("SUPABASE_MEDIA_BUCKET", "report-media")

    def insert_report(self, report, fingerprint, idem):
        row = {**report, "fingerprint": fingerprint, "idem": idem}
        self.client.table("reports").insert(row).execute()

    def find_by_actor_idem(self, actor, idem):
        result = self.client.table("reports").select("*").eq("actor", actor).eq("idem", idem).limit(1).execute()
        return result.data[0] if result.data else None

    def list_reports(self):
        return self.client.table("reports").select("*").order("submitted_at", desc=True).execute().data

    def get_report(self, rid):
        result = self.client.table("reports").select("*").eq("id", rid).limit(1).execute()
        return result.data[0] if result.data else None

    def update_report(self, report):
        self.client.table("reports").update(report).eq("id", report["id"]).execute()

    def add_review(self, review):
        self.client.table("report_reviews").insert(review).execute()

    def reviews_for(self, rid):
        return self.client.table("report_reviews").select("*").eq("report_id", rid).order("created_at").execute().data

    def set_training(self, row):
        self.client.table("curated_training").upsert(row).execute()

    def training_rows(self):
        return self.client.table("curated_training").select("*").eq("eligible", True).execute().data

    def upload_image(self, rid, content):
        self.client.storage.from_(self.bucket).upload(
            f"{rid}.jpg", content, {"content-type": "image/jpeg", "upsert": "false"}
        )

    def download_image(self, rid):
        return self.client.storage.from_(self.bucket).download(f"{rid}.jpg")
