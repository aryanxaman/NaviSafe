"""SafePath API. Legacy route shapes retained; evidence is separate from model training."""
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import hmac
import json
import math
import os
import secrets
import time
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path

import networkx as nx
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.evidence import inspect_image, near_duplicate, independent_candidates, transition, MAX_BYTES
from backend.store import ROOT, database, all_reports, save
from backend.supabase_store import SupabaseStore, configured as supabase_configured

app = FastAPI(title="SafePath", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("SAFEPATH_ORIGINS", "http://localhost:5173,http://localhost:4173").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Client-ID"])

def durable_store():
    return SupabaseStore() if supabase_configured() else None

@app.middleware("http")
async def secure_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

edges_df = pd.read_csv(ROOT / "synthetic_data/edges_features.csv")
risk_path = Path(os.getenv("SAFEPATH_RISK_TABLE", str(ROOT / "models/delhi-v3-final/risk_table.csv")))
risk_dict = {}
if risk_path.exists():
    risk_dict = {(int(r.edge_id), int(r.bucket)): float(r.p_ml) for r in pd.read_csv(risk_path).itertuples()}
G = nx.Graph()
nodes_coords = {}
for r in edges_df.itertuples():
    G.add_edge(int(r.u), int(r.v), edge_id=int(r.edge_id), length=float(r.length_m), lit=float(r.lit), isolated=float(r.isolated))
    nodes_coords[int(r.u)] = (float(r.lat1), float(r.lon1))
    nodes_coords[int(r.v)] = (float(r.lat2), float(r.lon2))


def metres(lat, lon, other_lat, other_lon):
    dy = math.radians(other_lat - lat)
    dx = math.radians(other_lon - lon)
    a = math.sin(dy/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(other_lat))*math.sin(dx/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(a)))


def get_nearest_node(lat, lon):
    node = min(nodes_coords, key=lambda n: metres(lat, lon, *nodes_coords[n]))
    if metres(lat, lon, *nodes_coords[node]) > 400:
        raise HTTPException(422, "Outside the available Dwarka street network. Choose points inside the marked study area.")
    return node


def risk(d, hour):
    # Explicit contextual fallback; never the synthetic reporting-propensity feature.
    fallback = min(1, .15 + .35*d["isolated"] + (.35*(1-d["lit"]) if hour >= 19 or hour < 6 else 0))
    if not risk_dict:
        return fallback
    bucket = hour // 4
    next_bucket = (bucket + 1) % 6
    fraction = (hour % 4) / 4
    current = risk_dict.get((d["edge_id"], bucket), fallback)
    following = risk_dict.get((d["edge_id"], next_bucket), current)
    return current + (following - current) * fraction


def provenance():
    return {"data_origin": "SYNTHETIC", "model_version": "delhi-v3" if risk_dict else "context-rules-v1", "data_timestamp": "2026-10-05", "uncertainty": None, "explanation": "Experimental synthetic scenario estimate; not a probability of harm. No verified incident coverage. Street geometry derived from OSM; lighting/activity proxies are synthetic."}

@app.get("/api/health")
def health():
    return {"status": "ok", "moderation_configured": bool(os.getenv("SAFEPATH_MODERATOR_TOKEN")), "automatic_escalation": False, "vision_provider": "unavailable", **provenance()}

@app.get("/api/graph")
def graph(hour: int = 20):
    if not 0 <= hour <= 23: raise HTTPException(422, "Hour must be 0–23")
    return {"type": "FeatureCollection", **provenance(), "features": [{"type": "Feature", "properties": {"edge_id": d["edge_id"], "risk": risk(d, hour), "lit": d.get("lit", 0), "isolated": d.get("isolated", 0), "length_m": d.get("length", 0)}, "geometry": {"type": "LineString", "coordinates": [[nodes_coords[u][1],nodes_coords[u][0]], [nodes_coords[v][1],nodes_coords[v][0]]]}} for u,v,d in G.edges(data=True)]}

class RouteReq(BaseModel):
    start_lat: float = Field(ge=-90, le=90)
    start_lon: float = Field(ge=-180, le=180)
    end_lat: float = Field(ge=-90, le=90)
    end_lon: float = Field(ge=-180, le=180)
    alpha: float = Field(default=2, ge=0, le=8)
    hour: int = Field(default=20, ge=0, le=23)
    detour_cap: float = Field(default=1.5, ge=1, le=2)

@app.post("/api/route")
def route(req: RouteReq):
    a,b = get_nearest_node(req.start_lat,req.start_lon),get_nearest_node(req.end_lat,req.end_lon)
    if a == b: raise HTTPException(422, "Choose two distinct points on the network.")
    def build(p):
        pairs = list(zip(p,p[1:]))
        distance = sum(G[u][v]["length"] for u,v in pairs)
        return {"geometry": [[nodes_coords[n][1],nodes_coords[n][0]] for n in p], "metrics": {"distance": distance, "exposure": sum(G[u][v]["length"]*risk(G[u][v],req.hour) for u,v in pairs)/distance}}
    try:
        fast = build(nx.shortest_path(G,a,b,weight="length"))
        def weighted(alpha):
            return build(nx.shortest_path(G,a,b,weight=lambda u,v,d:d["length"]*(1+alpha*risk(d,req.hour))))
        safer, balanced = weighted(req.alpha), weighted(req.alpha/2)
        capped = safer["metrics"]["distance"] > fast["metrics"]["distance"]*req.detour_cap
        if capped: safer = fast
        if balanced["metrics"]["distance"] > fast["metrics"]["distance"]*req.detour_cap: balanced = fast
        return {"safest": safer, "fastest": fast, "balanced": balanced, "detour_capped": capped, "generated_at": datetime.now(timezone.utc).isoformat(), **provenance()}
    except nx.NetworkXNoPath:
        raise HTTPException(422, "No connected walking route is available. Try different points.")

# A device pseudonym is not a verified person. Deployment requires real identity before public-scale corroboration.
def actor(request: Request, x_client_id: str = Header(default=""), authorization: str = Header(default="")):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Sign in is required.")
        try:
            response = httpx.get(f"{supabase_url.rstrip('/')}/auth/v1/user", headers={"apikey": supabase_key, "Authorization": authorization}, timeout=5)
            if response.status_code != 200:
                raise HTTPException(401, "Your session is invalid or expired.")
            user_id = response.json().get("id")
            if not user_id:
                raise HTTPException(401, "Your session is invalid.")
            return "user:" + user_id
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Authentication service is unavailable.") from exc
    value = x_client_id if 8 <= len(x_client_id) <= 100 else (request.client.host if request.client else "local")
    return hashlib.sha256(value.encode()).hexdigest()

def user_id_from_actor(value):
    return value[5:] if value.startswith("user:") else None


def moderator(authorization: str = Header(default="")):
    token = os.getenv("SAFEPATH_MODERATOR_TOKEN", "")
    if not token: raise HTTPException(503, "Moderation is locked: configure a server-side moderator token.")
    if not hmac.compare_digest(authorization, "Bearer " + token): raise HTTPException(403, "Moderator role required.")
    return "moderator:" + hashlib.sha256(token.encode()).hexdigest()[:12]


def public_report(r):
    return {k: r[k] for k in ("id", "street", "category", "description", "observed_at", "submitted_at", "status", "version", "expires_at")}


def expire(conn, records):
    now = datetime.now(timezone.utc)
    for r in records:
        if r["status"] not in {"expired", "rejected"} and datetime.fromisoformat(r["expires_at"]) < now:
            r["history"].append({"from":r["status"],"to":"expired","reason":"Freshness window elapsed; reconfirmation required.","reviewer":"system","role":"system","timestamp":now.isoformat()})
            r["status"] = "expired"
            r["version"] += 1
            save(conn,r)
    return records

@app.post("/api/report")
async def submit_report(request: Request, street: str = Form(...), category: str = Form(...), desc: str = Form(""), file: UploadFile | None = File(None), observed_at: str = Form(""), latitude: float | None = Form(None), longitude: float | None = Form(None), personally_observed: bool = Form(False), visibility_consent: bool = Form(False), location_consent: bool = Form(False), idempotency_key: str = Header(default="", alias="Idempotency-Key"), who: str = Depends(actor)):
    categories = {"poor_lighting","blocked_footpath","damaged_infrastructure","other","isolated","incident","safe","harassment"}
    if category not in categories or not 2 <= len(street.strip()) <= 120 or len(desc) > 500:
        raise HTTPException(422, "Use a supported category, a 2–120 character area and a description up to 500 characters.")
    if len(idempotency_key)>100: raise HTTPException(422,"Invalid idempotency key")
    now = datetime.now(timezone.utc)
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00")) if observed_at else now
        if observed.tzinfo is None: raise ValueError()
        if observed > now + timedelta(minutes=10) or observed < now - timedelta(days=30): raise ValueError()
    except ValueError: raise HTTPException(422, "Observation time must include a timezone and be within the past 30 days.")
    if (latitude is None) != (longitude is None) or (latitude is not None and (not -90 <= latitude <= 90 or not -180 <= longitude <= 180)):
        raise HTTPException(422,"Invalid coordinate pair")
    if latitude is not None and not location_consent: raise HTTPException(422,"Coordinate storage requires consent")
    # Limit before decoding; reverse proxy additionally bounds the complete multipart request.
    raw = await file.read(MAX_BYTES+1) if file else b""
    clean, checks = None, {"relevance":{"outcome":"inconclusive","available":False,"reason":"No image submitted"}}
    if file:
        try: clean,checks = inspect_image(raw,category)
        except ValueError as exc: raise HTTPException(422,str(exc))
    fingerprint = hashlib.sha256(json.dumps([street,category,desc,observed_at,latitude,longitude,personally_observed,visibility_consent,location_consent,hashlib.sha256(raw).hexdigest()]).encode()).hexdigest()
    durable = durable_store()
    if durable:
        previous = durable.find_by_actor_idem(who, idempotency_key) if idempotency_key else None
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise HTTPException(409, "This queued submission changed. Keep the local draft or submit a new revision with a new key.")
            return {"status": "success", "report": public_report(previous), "replayed": True}
        records = durable.list_reports()
        rid = secrets.token_hex(16)
        r = {"id": rid, "user_id": user_id_from_actor(who), "actor": who, "street": street.strip(), "category": category, "description": desc,
             "observed_at": observed.isoformat(), "submitted_at": now.isoformat(), "latitude": round(latitude, 3) if latitude is not None else None,
             "longitude": round(longitude, 3) if longitude is not None else None, "personally_observed": personally_observed,
             "visibility_consent": visibility_consent, "status": "pending_review", "version": 1,
             "expires_at": (observed + timedelta(hours=int(os.getenv("SAFEPATH_REPORT_TTL_HOURS", "72")))).isoformat(),
             "checks": checks, "history": [{"from": "draft", "to": "pending_review", "reason": "Submitted; automated checks do not establish truth.", "reviewer": who, "role": "reporter", "timestamp": now.isoformat()}]}
        r["duplicate_candidates"] = [o["id"] for o in records if near_duplicate(checks, o.get("checks", {}))]
        r["corroboration_candidates"] = independent_candidates(r, records)
        r["checks"]["location_time"] = "Reported time checked for plausibility. Exact capture location/time cannot be authenticated. Coordinates rounded to approximately 100 m." if latitude is not None else "No coordinates; location consistency requires human review."
        if clean:
            durable.upload_image(rid, clean)
            r["has_image"] = True
        durable.insert_report(r, fingerprint, idempotency_key or rid)
        return {"status": "success", "message": "Saved for review, not used for model training.", "report": public_report(r)}
    with database() as conn:
        previous = conn.execute("SELECT body,fingerprint FROM reports WHERE actor=? AND idem=?",(who,idempotency_key)).fetchone() if idempotency_key else None
        if previous:
            if previous["fingerprint"] != fingerprint: raise HTTPException(409,"This queued submission changed. Keep the local draft or submit a new revision with a new key.")
            return {"status":"success","report":public_report(json.loads(previous["body"])),"replayed":True}
        # Count both device and network requests; no raw IP persisted.
        network = "network:" + hashlib.sha256((request.client.host if request.client else "local").encode()).hexdigest()
        conn.execute("DELETE FROM abuse WHERE timestamp<?",(time.time()-3600,))
        for key in [who,network]:
            if conn.execute("SELECT count(*) FROM abuse WHERE actor=?",(key,)).fetchone()[0] >= (8 if key==who else 40): raise HTTPException(429,"Submission limit reached. Keep a draft and retry later; review/appeal remains available.")
            conn.execute("INSERT INTO abuse VALUES (?,?)",(key,time.time()))
        records = expire(conn,all_reports(conn))
        rid = secrets.token_hex(16)
        r = {"id":rid,"actor":who,"street":street.strip(),"category":category,"description":desc,"observed_at":observed.isoformat(),"submitted_at":now.isoformat(),"latitude":round(latitude,3) if latitude is not None else None,"longitude":round(longitude,3) if longitude is not None else None,"personally_observed":personally_observed,"visibility_consent":visibility_consent,"status":"pending_review","version":1,"expires_at":(observed+timedelta(hours=int(os.getenv("SAFEPATH_REPORT_TTL_HOURS","72")))).isoformat(),"checks":checks,"history":[{"from":"draft","to":"pending_review","reason":"Submitted; automated checks do not establish truth.","reviewer":who,"role":"reporter","timestamp":now.isoformat()}]}
        r["duplicate_candidates"] = [o["id"] for o in records if near_duplicate(checks,o["checks"])]
        r["corroboration_candidates"] = independent_candidates(r,records)
        r["checks"]["location_time"] = "Reported time checked for plausibility. Exact capture location/time cannot be authenticated. Coordinates rounded to approximately 100 m." if latitude is not None else "No coordinates; location consistency requires human review."
        if clean:
            private = Path(os.getenv("SAFEPATH_MEDIA",str(ROOT/"data/private_media")))
            private.mkdir(parents=True,exist_ok=True)
            (private/f"{rid}.jpg").write_bytes(clean)
            r["has_image"] = True
        conn.execute("INSERT INTO reports VALUES (?,?,?,?,?)",(rid,who,idempotency_key or rid,fingerprint,json.dumps(r)))
        return {"status":"success","message":"Saved for review, not used for model training.","report":public_report(r)}

@app.get("/api/reports")
def reports(mine: bool = False, who: str = Depends(actor)):
    durable = durable_store()
    if durable:
        records = durable.list_reports()
        visible = [r for r in records if (r["actor"] == who if mine else r["visibility_consent"] and r["status"] in {"provisionally_published", "corroborated", "verified", "disputed", "expired"})]
        return {"reports": [public_report(r) for r in visible], "fetched_at": datetime.now(timezone.utc).isoformat()}
    with database() as conn:
        records=expire(conn,all_reports(conn))
        return {"reports":[public_report(r) for r in reversed(records) if (r["actor"]==who if mine else r["visibility_consent"] and r["status"] in {"provisionally_published","corroborated","verified","disputed","expired"})],"fetched_at":datetime.now(timezone.utc).isoformat()}

@app.get("/api/moderation")
def moderation(reviewer: str = Depends(moderator)):
    durable = durable_store()
    if durable:
        records = durable.list_reports()
        for r in records:
            r["corroboration_candidates"] = independent_candidates(r, records)
            r["review_requests"] = durable.reviews_for(r["id"])
            training = next((x for x in durable.training_rows() if x["report_id"] == r["id"]), None)
            r["training_eligibility"] = training or {"eligible": False, "label": None}
        return {"reports": records, "reviewer": reviewer}
    with database() as conn:
        records=expire(conn,all_reports(conn))
        for r in records:
            r["corroboration_candidates"]=independent_candidates(r,records)
            r["review_requests"]=[json.loads(row[0]) for row in conn.execute("SELECT body FROM reviews WHERE report_id=?",(r["id"],))]
            training = conn.execute("SELECT label,eligible,reviewer,timestamp FROM curated_training WHERE report_id=?",(r["id"],)).fetchone()
            r["training_eligibility"] = dict(training) if training else {"eligible": False, "label": None}
        return {"reports":records,"reviewer":reviewer}

@app.get("/api/moderation/{rid}/image")
def image(rid: str, reviewer: str = Depends(moderator)):
    if len(rid)!=32 or any(c not in "0123456789abcdef" for c in rid): raise HTTPException(404)
    durable = durable_store()
    if durable:
        try:
            from fastapi.responses import Response
            return Response(durable.download_image(rid), media_type="image/jpeg")
        except Exception as exc:
            raise HTTPException(404, "Private image not found.") from exc
    path=Path(os.getenv("SAFEPATH_MEDIA",str(ROOT/"data/private_media")))/f"{rid}.jpg"
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path,media_type="image/jpeg")

class Review(BaseModel):
    status: str
    reason: str = Field(min_length=12,max_length=1000)
    version: int
    independent_confirmed: bool = False
    privacy_reviewed: bool = False

class TrainingDecision(BaseModel):
    eligible: bool
    label: str = Field(pattern="^(unsafe_location|safe_location|unresolved)$")
    reason: str = Field(min_length=20, max_length=1000)

@app.post("/api/moderation/{rid}")
def review(rid: str, body: Review, reviewer: str = Depends(moderator)):
    durable = durable_store()
    if durable:
        r = durable.get_report(rid)
        if not r: raise HTTPException(404)
        if r["version"] != body.version: raise HTTPException(409, "Another review changed this report. Reload before deciding.")
        records = durable.list_reports()
        r["corroboration_candidates"] = independent_candidates(r, records)
        try:
            transition(r, body.status, body.reason, reviewer, body.independent_confirmed, body.privacy_reviewed)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        durable.update_report(r)
        return r
    with database() as conn:
        records=expire(conn,all_reports(conn))
        r=next((r for r in records if r["id"]==rid),None)
        if not r: raise HTTPException(404)
        if r["version"]!=body.version: raise HTTPException(409,"Another review changed this report. Reload before deciding.")
        r["corroboration_candidates"]=independent_candidates(r,records)
        try: transition(r,body.status,body.reason,reviewer,body.independent_confirmed,body.privacy_reviewed)
        except ValueError as exc: raise HTTPException(422,str(exc))
        save(conn,r)
        return r

@app.post("/api/moderation/{rid}/training")
def training_decision(rid: str, body: TrainingDecision, reviewer: str = Depends(moderator)):
    """Explicitly curate a reviewed report; uploads never enter training by default."""
    durable = durable_store()
    if durable:
        report = durable.get_report(rid)
        if not report: raise HTTPException(404)
        if body.eligible and (report["status"] != "verified" or not report.get("visibility_consent")):
            raise HTTPException(422, "Only verified reports with visibility consent can enter the curated training set.")
        timestamp = datetime.now(timezone.utc).isoformat()
        durable.set_training({"report_id": rid, "label": body.label, "eligible": body.eligible, "reviewer": reviewer, "reason": body.reason, "timestamp": timestamp})
        return {"status": "curated" if body.eligible else "excluded", "report_id": rid, "label": body.label, "eligible": body.eligible, "timestamp": timestamp}
    with database() as conn:
        row = conn.execute("SELECT body FROM reports WHERE id=?", (rid,)).fetchone()
        if not row:
            raise HTTPException(404)
        report = json.loads(row["body"])
        if body.eligible and (report["status"] != "verified" or not report.get("visibility_consent")):
            raise HTTPException(422, "Only verified reports with visibility consent can enter the curated training set.")
        timestamp = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO curated_training(report_id,label,eligible,reviewer,reason,timestamp) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(report_id) DO UPDATE SET label=excluded.label,eligible=excluded.eligible,reviewer=excluded.reviewer,reason=excluded.reason,timestamp=excluded.timestamp",
            (rid, body.label, int(body.eligible), reviewer, body.reason, timestamp),
        )
        return {"status": "curated" if body.eligible else "excluded", "report_id": rid, "label": body.label, "eligible": body.eligible, "timestamp": timestamp}

@app.get("/api/moderation/training-dataset")
def training_dataset(reviewer: str = Depends(moderator)):
    """Export only explicit, verified curation decisions for offline candidate training."""
    durable = durable_store()
    if durable:
        rows = durable.training_rows()
        records = []
        for curation in rows:
            report = durable.get_report(curation["report_id"])
            if report and report["status"] == "verified":
                records.append({"report_id": report["id"], "category": report["category"], "observed_at": report["observed_at"],
                                "latitude": report["latitude"], "longitude": report["longitude"], "label": curation["label"],
                                "curated_by": curation["reviewer"], "curation_reason": curation["reason"], "curated_at": curation["timestamp"]})
        return {"records": records, "count": len(records), "training_policy": "Explicitly curated verified reports only; export is for offline candidate evaluation and never deploys automatically.", "reviewer": reviewer}
    with database() as conn:
        rows = conn.execute(
            "SELECT r.body, c.label, c.reviewer, c.reason, c.timestamp FROM reports r "
            "JOIN curated_training c ON c.report_id=r.id WHERE c.eligible=1 AND json_extract(r.body, '$.status')='verified'"
        ).fetchall()
        records = []
        for row in rows:
            report = json.loads(row["body"])
            records.append({
                "report_id": report["id"], "category": report["category"], "observed_at": report["observed_at"],
                "latitude": report["latitude"], "longitude": report["longitude"], "label": row["label"],
                "curated_by": row["reviewer"], "curation_reason": row["reason"], "curated_at": row["timestamp"],
            })
        return {"records": records, "count": len(records), "training_policy": "Explicitly curated verified reports only; export is for offline candidate evaluation and never deploys automatically.", "reviewer": reviewer}

class Concern(BaseModel):
    kind: str = Field(pattern="^(inaccurate|resolved|abuse|appeal|correction)$")
    reason: str = Field(min_length=12,max_length=1000)

@app.post("/api/reports/{rid}/review")
def concern(rid: str, body: Concern, who: str = Depends(actor)):
    durable = durable_store()
    if durable:
        r = durable.get_report(rid)
        if not r: raise HTTPException(404)
        if r["actor"] != who and not (r["visibility_consent"] and r["status"] in {"provisionally_published", "corroborated", "verified", "disputed", "expired"}):
            raise HTTPException(404)
        if body.kind in {"appeal", "correction"} and r["actor"] != who:
            raise HTTPException(403, "Only the submitting account can appeal or correct its report.")
        if len(durable.reviews_for(rid)) >= 5:
            raise HTTPException(429, "Review request limit reached for this report.")
        durable.add_review({"report_id": rid, "user_id": user_id_from_actor(who), "kind": body.kind, "reason": body.reason})
        return {"status": "pending_review", "message": "Review requested. The evidence status has not changed automatically."}
    with database() as conn:
        row=conn.execute("SELECT body FROM reports WHERE id=?",(rid,)).fetchone()
        if not row: raise HTTPException(404)
        r=json.loads(row[0])
        if r["actor"]!=who and not (r["visibility_consent"] and r["status"] in {"provisionally_published","corroborated","verified","disputed","expired"}): raise HTTPException(404)
        if body.kind in {"appeal","correction"} and r["actor"]!=who: raise HTTPException(403,"Only the submitting device can appeal or correct its report.")
        if conn.execute("SELECT count(*) FROM reviews WHERE actor=? AND report_id=?",(who,rid)).fetchone()[0]>=5: raise HTTPException(429,"Review request limit reached for this report.")
        entry={"kind":body.kind,"reason":body.reason,"requester":who,"timestamp":datetime.now(timezone.utc).isoformat()}
        conn.execute("INSERT INTO reviews VALUES (?,?,?,?,?)",(secrets.token_hex(16),rid,who,json.dumps(entry),entry["timestamp"]))
        return {"status":"pending_review","message":"Review requested. The report's evidence status has not changed automatically."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SAFEPATH_PORT", "8000"))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port)
