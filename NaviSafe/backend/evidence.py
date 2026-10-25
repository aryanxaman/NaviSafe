"""Evidence signals, never an authenticity or real-world safety classifier."""
import hashlib
import io
import warnings
from datetime import datetime, timezone
from typing import Protocol

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
STATES = {"draft", "pending_review", "provisionally_published", "corroborated",
          "verified", "disputed", "rejected", "expired"}
TRANSITIONS = {
    "draft": {"pending_review"},
    "pending_review": {"pending_review", "provisionally_published", "corroborated", "verified", "disputed", "rejected", "expired"},
    "provisionally_published": {"pending_review", "corroborated", "verified", "disputed", "rejected", "expired"},
    "corroborated": {"pending_review", "verified", "disputed", "rejected", "expired"},
    "verified": {"pending_review", "disputed", "rejected", "expired"},
    "disputed": {"pending_review", "provisionally_published", "corroborated", "verified", "rejected", "expired"},
    "rejected": {"pending_review"},
    "expired": {"pending_review"},
}


class VisionProvider(Protocol):
    def assess(self, image: bytes, category: str) -> dict: ...


class UnavailableVision:
    def assess(self, image: bytes, category: str) -> dict:
        return {"outcome": "inconclusive", "available": False,
                "reason": "No evaluated vision provider configured. Human review required."}


def inspect_image(raw: bytes, category: str, vision: VisionProvider | None = None):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Image must be between 1 byte and 8 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as check:
                if check.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Only decoded JPEG, PNG and WebP images are accepted.")
                check.verify()
            with Image.open(io.BytesIO(raw)) as original:
                exif = original.getexif()
                metadata = {"present": bool(exif), "timestamp_present": bool(exif.get(306) or exif.get(36867)),
                            "gps_present": bool(exif.get(34853)),
                            "reason": "Metadata is untrusted; original metadata is removed and never published."}
                img = ImageOps.exif_transpose(original).convert("RGB")
                img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Image could not be safely decoded.") from exc
    gray = np.asarray(img.resize((128, 128)).convert("L"), dtype=float)
    grad = float(np.var(np.diff(gray, axis=0)) + np.var(np.diff(gray, axis=1)))
    small = np.asarray(img.resize((9, 8)).convert("L"))
    bits = small[:, 1:] > small[:, :-1]
    dhash = f"{sum(int(v) << i for i, v in enumerate(bits.flatten())):016x}"
    signals = []
    if gray.mean() < 45:
        signals.append("dark_image")
    if grad < 25:
        signals.append("low_detail_or_blur")
    if min(img.size) < 240:
        signals.append("low_resolution")
    img.thumbnail((1600, 1600))
    clean = io.BytesIO()
    img.save(clean, format="JPEG", quality=85)  # no original metadata retained
    relevance = (vision or UnavailableVision()).assess(clean.getvalue(), category)
    if relevance.get("outcome") not in {"possibly_relevant", "inconclusive", "possible_mismatch"}:
        relevance = {"outcome": "inconclusive", "reason": "Invalid provider response."}
    return clean.getvalue(), {
        "sha256": hashlib.sha256(raw).hexdigest(), "dhash": dhash,
        "quality": signals, "metadata": metadata, "relevance": relevance,
        "privacy": "Metadata stripped; image private to moderators. Face/plate redaction unavailable.",
        "malware_scan": "unavailable; decoded and re-encoded image only",
        "framing": "obstruction and framing require human review",
    }


def near_duplicate(a: dict, b: dict, threshold: int = 6) -> bool:
    if not a.get("sha256") or not b.get("sha256"):
        return False
    return a["sha256"] == b["sha256"] or (
        int(a["dhash"], 16) ^ int(b["dhash"], 16)).bit_count() <= threshold


def independent_candidates(report: dict, others: list[dict]) -> list[str]:
    """Candidate observations, not confirmed independent people. Identity needs human review."""
    found, evidence_seen, actors = [], [], {report["actor"]}
    if report.get("latitude") is None:
        return found
    for other in others:
        if other["id"] == report["id"] or other["actor"] in actors or other["category"] != report["category"]:
            continue
        if other.get("latitude") is None or other["status"] in {"rejected", "expired", "disputed"}:
            continue
        # Approximate local metres, only for review candidates (not route geometry).
        distance = ((other["latitude"] - report["latitude"]) * 111_000) ** 2 + (
            (other["longitude"] - report["longitude"]) * 97_500) ** 2
        age = abs((datetime.fromisoformat(other["observed_at"]) -
                   datetime.fromisoformat(report["observed_at"])).total_seconds())
        if distance > 250 ** 2 or age > 3 * 3600 or not other["personally_observed"]:
            continue
        if near_duplicate(report["checks"], other["checks"]) or any(
                near_duplicate(other["checks"], previous) for previous in evidence_seen):
            continue
        actors.add(other["actor"])
        evidence_seen.append(other["checks"])
        found.append(other["id"])
    return found


def transition(report: dict, target: str, reason: str, reviewer: str,
               independent_confirmed: bool = False, privacy_reviewed: bool = False):
    if target not in TRANSITIONS.get(report["status"], set()):
        raise ValueError(f"Transition {report['status']} → {target} is not permitted.")
    if len(reason.strip()) < 12:
        raise ValueError("Give a specific review reason (at least 12 characters).")
    if target in {"corroborated", "verified"} and (
        not independent_confirmed or len(report.get("corroboration_candidates", [])) < 2
    ):
        raise ValueError("Two distinct corroboration candidates and reviewer confirmation of independence are required.")
    if target == "verified" and not privacy_reviewed:
        raise ValueError("Verification requires a documented location/time/evidence and privacy review.")
    now = datetime.now(timezone.utc).isoformat()
    report["history"].append({"from": report["status"], "to": target, "reason": reason,
                              "reviewer": reviewer, "role": "moderator", "timestamp": now,
                              "independence_reviewed": independent_confirmed,
                              "evidence_and_privacy_reviewed": privacy_reviewed})
    report["status"] = target
    report["version"] += 1
    return report
