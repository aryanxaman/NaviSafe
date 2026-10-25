
"""
SYNTHETIC DATA GENERATOR - women's-safety route-risk prototype
================================================================
Creates STAND-IN data shaped like the three real sources you have requested:

  1. safecity_synthetic.csv      - harassment reports (Safecity-style)
  2. safetipin_synthetic.csv     - point safety audits (Safetipin-style)
  3. ncrb_synthetic.csv          - city-level yearly crime counts (NCRB-style)
  + app_microreports_synthetic.csv - your own crowd form (poor lighting, no shops open...)
  + edges_features.csv           - street segments + static features
  + ground_truth_edge_risk.csv   - the hidden "true" risk used to generate the data
  + graph.graphml                - the street graph, so routing uses the same network

IMPORTANT
  * None of this is real. Every row carries data_origin = "SYNTHETIC".
  * Column layouts are INSPIRED BY the real sources, not copies of their schemas.
    When real data arrives, write a small adapter that maps it to these columns.
  * A model trained on this data learns the rules written in this script.
    Metrics from it prove the PIPELINE works, not that the model predicts real harm.

Usage
  pip install numpy pandas networkx            # always needed
  pip install osmnx                            # optional: real Delhi street network
  python generate_synthetic_safety_data.py --area dwarka --n-reports 6000
  python generate_synthetic_safety_data.py --offline          # no internet: synthetic street grid
"""
import argparse
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# Approximate bounding boxes - check them on a map and adjust.
PRESETS = {
    "dwarka":   dict(north=28.610, south=28.570, east=77.060, west=77.020),
    "hauzkhas": dict(north=28.560, south=28.530, east=77.220, west=77.180),
}

ORIGIN = "SYNTHETIC"
BUCKETS = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]


# ----------------------------------------------------------------- helpers
def vm(h, mu, kappa):
    """Circular (von Mises-shaped) bump on a 24h clock, peak = 1. Wraps past midnight."""
    return np.exp(kappa * (np.cos(2 * np.pi * (np.asarray(h) - mu) / 24.0) - 1.0))


def metres(lat1, lon1, lat2, lon2):
    kx = 111_320 * np.cos(np.radians(lat1))
    return np.hypot((lon2 - lon1) * kx, (lat2 - lat1) * 110_540)


def nearest_dist(lat, lon, pts):
    """Distance (m) from each (lat, lon) to the closest of pts [(lat, lon), ...]."""
    d = np.stack([metres(lat, lon, p[0], p[1]) for p in pts])
    return d.min(axis=0)


# ------------------------------------------------------------------ graph
def fallback_graph(bbox, rng, n=28):
    """Jittered street grid, used when OSM is unavailable."""
    G = nx.Graph()
    lats = np.linspace(bbox["south"], bbox["north"], n)
    lons = np.linspace(bbox["west"], bbox["east"], n)
    dlat, dlon = lats[1] - lats[0], lons[1] - lons[0]
    for i in range(n):
        for j in range(n):
            G.add_node(i * n + j,
                       y=float(lats[i] + rng.normal(0, dlat * 0.12)),
                       x=float(lons[j] + rng.normal(0, dlon * 0.12)))
    for i in range(n):
        for j in range(n):
            for di, dj in ((0, 1), (1, 0)):
                a, b = i + di, j + dj
                if a < n and b < n and rng.random() > 0.12:
                    major = (i % 7 == 0) if di == 0 else (j % 7 == 0)
                    hw = "primary" if major else str(rng.choice(
                        ["residential", "residential", "tertiary", "footway", "service"]))
                    G.add_edge(i * n + j, a * n + b, highway=hw)
    return G


def load_graph(bbox, offline, rng):
    if not offline:
        try:
            import osmnx as ox
            try:  # osmnx >= 2.0: (left, bottom, right, top)
                G = ox.graph_from_bbox(
                    bbox=(bbox["west"], bbox["south"], bbox["east"], bbox["north"]),
                    network_type="walk")
            except TypeError:  # osmnx 1.x
                G = ox.graph_from_bbox(bbox["north"], bbox["south"], bbox["east"],
                                       bbox["west"], network_type="walk")
            return G, "osm"
        except Exception as exc:  # no osmnx / no internet
            print(f"[warn] OSM download failed ({exc}). Using synthetic street grid.")
    return fallback_graph(bbox, rng), "fallback_grid"


def edge_table(G):
    rows, seen = [], set()
    for u, v, d in G.edges(data=True):
        key = (min(u, v), max(u, v))
        if key in seen:
            continue
        seen.add(key)
        hw = d.get("highway", "residential")
        hw = hw[0] if isinstance(hw, list) else hw
        lit_raw = str(d.get("lit", "")).lower()  # osmnx drops 'lit' unless you add it to useful_tags_way
        lit = 1.0 if lit_raw in ("yes", "true", "24/7", "automatic") else 0.0 if lit_raw == "no" else np.nan
        (y1, x1), (y2, x2) = (G.nodes[u]["y"], G.nodes[u]["x"]), (G.nodes[v]["y"], G.nodes[v]["x"])
        length = d.get("length") or float(metres(y1, x1, y2, x2))
        rows.append(dict(u=u, v=v, mid_lat=(y1 + y2) / 2, mid_lon=(x1 + x2) / 2,
                         lat1=y1, lon1=x1, lat2=y2, lon2=x2,
                         length_m=float(length), highway=str(hw), lit=lit))
    df = pd.DataFrame(rows)
    df.insert(0, "edge_id", np.arange(len(df)))
    return df


# --------------------------------------------------------------- features
def add_features(E, rng):
    lat, lon = E.mid_lat.values, E.mid_lon.values
    lo_lat, hi_lat, lo_lon, hi_lon = lat.min(), lat.max(), lon.min(), lon.max()

    def pois(k):  # placeholder POIs - replace with real OSM/Delhi data later
        return [(rng.uniform(lo_lat, hi_lat), rng.uniform(lo_lon, hi_lon)) for _ in range(k)]

    metro, police, market, liquor = pois(3), pois(4), pois(5), pois(8)
    E["dist_metro_m"] = nearest_dist(lat, lon, metro)
    E["dist_police_m"] = nearest_dist(lat, lon, police)
    d_market = nearest_dist(lat, lon, market)
    d_liquor = nearest_dist(lat, lon, liquor)

    activity = np.clip(np.maximum(np.exp(-d_market / 300), np.exp(-E.dist_metro_m / 300)), 0, 1)
    major = E.highway.isin(["primary", "secondary", "trunk", "primary_link"]).values
    minor = E.highway.isin(["tertiary", "unclassified"]).values
    type_iso = np.where(major, 0.3, np.where(minor, 0.5,
                np.where(E.highway.isin(["footway", "path", "service", "track", "steps"]), 1.0, 0.7)))
    lit_p = np.where(major, 0.9, np.where(minor, 0.75, np.where(type_iso == 1.0, 0.35, 0.6)))
    lit_p = np.clip(lit_p + 0.15 * activity, 0, 0.97)
    synth_lit = (rng.random(len(E)) < lit_p).astype(float)
    E["lit"] = E["lit"].fillna(pd.Series(synth_lit, index=E.index))

    E["activity"] = activity
    E["isolated"] = np.clip((1 - activity + rng.normal(0, 0.15, len(E))) * type_iso, 0, 1)
    E["shops_open_night"] = np.clip(activity * 0.8 + rng.normal(0, 0.1, len(E)), 0, 1) * np.where(major | minor, 1, 0.5)
    E["liquor_near"] = np.exp(-d_liquor / 150)
    E["police_near"] = np.exp(-E.dist_police_m / 600)
    E["footfall_day"] = np.clip(0.2 + 0.8 * activity + rng.normal(0, 0.1, len(E)), 0, 1)
    E["footfall_night"] = E.footfall_day * (0.3 + 0.7 * E.shops_open_night)
    E["report_propensity"] = 0.5 + 0.8 * activity  # reporting bias: busy/app-aware areas over-report
    return E


def hourly_intensity(E):
    """True (latent) harassment intensity per edge per hour -> array [E, 24]."""
    h = np.arange(24)[None, :]
    night = np.clip(1.2 * (1 - E.lit) + 1.0 * E.isolated + 0.8 * E.liquor_near
                    - 0.8 * E.police_near - 0.7 * E.shops_open_night + 0.2, 0.02, None).values[:, None]
    eve = np.clip(0.9 * E.activity + 0.4 * E.liquor_near + 0.3 * (1 - E.lit)
                  - 0.4 * E.police_near, 0.02, None).values[:, None]
    day = np.clip(0.25 * E.activity + 0.15 * E.isolated - 0.2 * E.police_near, 0.01, None).values[:, None]
    return night * vm(h, 22.5, 1.2) + eve * vm(h, 18.5, 1.8) + day * vm(h, 13, 1.5) + 0.01


# ----------------------------------------------------------- generators
CATS = ["Commenting", "Staring / Ogling", "Catcalling / Whistling", "Stalking / Following",
        "Touching / Groping", "Taking pictures", "Sexual invites"]
CAT_BASE = np.array([.22, .18, .16, .12, .12, .05, .07])
CAT_SEV = np.array([1, 1, 1, 4, 5, 3, 2])


def jitter_points(E, idx, rng):
    """Random point along each edge + GPS/geocoding noise (70% good, 30% rough)."""
    r = E.iloc[idx]
    f = rng.random(len(idx))
    lat = r.lat1.values + f * (r.lat2.values - r.lat1.values)
    lon = r.lon1.values + f * (r.lon2.values - r.lon1.values)
    good = rng.random(len(idx)) < 0.7
    sigma = np.where(good, 15.0, 150.0)
    lat = lat + rng.normal(0, 1, len(idx)) * sigma / 110_540
    lon = lon + rng.normal(0, 1, len(idx)) * sigma / (111_320 * np.cos(np.radians(lat)))
    return lat, lon, np.where(good, "high", "low")


def gen_safecity(E, I, n, months, end, rng):
    prop = E.report_propensity.values[:, None]
    p = (I * prop).ravel()
    p /= p.sum()
    flat = rng.choice(len(p), size=n, p=p)
    e, h = flat // 24, flat % 24
    D = int(months * 30.4)
    w = 0.5 + (1 - np.arange(D) / D)  # days_ago 0 = today; more recent reports (app adoption)
    w /= w.sum()
    days = rng.choice(D, size=n, p=w)
    night = (h >= 20) | (h < 5)
    dow = (end - pd.to_timedelta(days, "D")).dayofweek
    redo = night & ~np.isin(dow, [4, 5]) & (rng.random(n) < 0.3)  # mild Fri/Sat night effect
    days[redo] = rng.choice(D, size=redo.sum(), p=w)

    iso, act = E.isolated.values[e], E.activity.values[e]
    W = np.tile(CAT_BASE, (n, 1))
    nf = night.astype(float)
    crowd = ((h >= 16) & (h < 21)).astype(float)
    W[:, 3] *= 1 + 2.0 * nf * iso
    W[:, 4] *= 1 + 1.5 * nf * iso + 1.0 * crowd * act
    W[:, 0] *= 1 + 0.8 * crowd * act
    cat = (W.cumsum(1) / W.sum(1, keepdims=True) < rng.random(n)[:, None]).sum(1)

    lat, lon, conf = jitter_points(E, e, rng)
    ts = (end - pd.to_timedelta(days, "D")).normalize() + pd.to_timedelta(h * 60 + rng.integers(0, 60, n), "m")
    df = pd.DataFrame(dict(report_id=[f"SC-SYN-{i:06d}" for i in range(n)], timestamp=ts,
                           latitude=lat, longitude=lon, category=np.array(CATS)[cat],
                           severity=CAT_SEV[cat], location_confidence=conf,
                           reporter_id=[f"R{rng.integers(0, 1500):04d}" for _ in range(n)],
                           _truth_edge_id=e, _truth_is_spam=False))
    # spam / revenge-reporting: a few accounts hammer one street in a short window
    spam_rows = []
    for k in range(5):
        se = rng.integers(0, len(E))
        start = rng.integers(0, D - 4)
        m = max(3, int(0.004 * n))
        lat_s, lon_s, conf_s = jitter_points(E, np.full(m, se), rng)
        for j in range(m):
            t = (end - pd.Timedelta(days=int(start - rng.integers(0, 3)))).normalize() \
                + pd.Timedelta(minutes=int(rng.integers(0, 1440)))
            spam_rows.append(dict(report_id=f"SC-SYN-SPAM{k}{j:03d}", timestamp=t, latitude=lat_s[j],
                                  longitude=lon_s[j], category="Stalking / Following", severity=4,
                                  location_confidence=conf_s[j], reporter_id=f"SPAM{k}",
                                  _truth_edge_id=se, _truth_is_spam=True))
    df = pd.concat([df, pd.DataFrame(spam_rows)], ignore_index=True).sort_values("timestamp")
    df.insert(1, "data_origin", ORIGIN)
    return df.reset_index(drop=True)


def gen_safetipin(E, n, months, end, rng):
    idx = rng.choice(len(E), size=n, p=(E.length_m / E.length_m.sum()).values)
    r = E.iloc[idx].reset_index(drop=True)
    night = rng.random(n) < 0.4
    hour = np.where(night, rng.integers(19, 24, n), rng.integers(9, 17, n))

    def sc(x, s=0.12):
        return np.clip(np.rint(3 * np.clip(np.asarray(x) + rng.normal(0, s, n), 0, 1)), 0, 3).astype(int)

    foot = np.where(night, r.footfall_night, r.footfall_day)
    lighting = sc(np.where(night, r.lit * 0.85 + 0.1, 0.85))
    openness = sc(1 - 0.8 * r.isolated)
    visibility = sc(0.5 * (1 - r.isolated) + 0.5 * np.where(night, r.lit, 1.0))
    people = sc(foot)
    security = sc(0.2 + 0.6 * r.police_near + 0.2 * r.shops_open_night)
    type_q = r.highway.map({"primary": .7, "secondary": .7, "tertiary": .6, "residential": .6,
                            "footway": .8, "service": .4}).fillna(.5)
    walk_path = sc(type_q)
    transport = sc(np.exp(-r.dist_metro_m / 700))
    gender_div = sc(0.2 + 0.6 * foot)
    feeling = sc(0.4 * lighting / 3 + 0.3 * people / 3 + 0.2 * security / 3 + 0.1 - 0.3 * r.liquor_near, 0.1)
    parts = np.stack([lighting, openness, visibility, people, security, walk_path, transport, gender_div, feeling])
    lat, lon, _ = jitter_points(E, idx, rng)
    D = int(months * 30.4)
    ts = (end - pd.to_timedelta(rng.integers(0, D, n), "D")).normalize() + pd.to_timedelta(hour * 60, "m")
    return pd.DataFrame(dict(
        audit_id=[f"SP-SYN-{i:05d}" for i in range(n)], data_origin=ORIGIN, timestamp=ts,
        latitude=lat, longitude=lon, lighting=lighting, openness=openness, visibility=visibility,
        people=people, security=security, walk_path=walk_path, public_transport=transport,
        gender_diversity=gender_div, feeling=feeling, safety_score=parts.mean(axis=0).round(2),
        time_of_day=np.where(night, "night", "day"), _truth_edge_id=r.edge_id.values))


def gen_ncrb(end, rng, years=5):
    heads = [("Assault on women with intent to outrage modesty", "IPC 354", 1700),
             ("Insult to modesty of women", "IPC 509", 450),
             ("Stalking", "IPC 354D", 250),
             ("Voyeurism", "IPC 354C", 60),
             ("Rape", "IPC 376", 1350)]  # magnitudes are ARBITRARY placeholders, not real statistics
    rows = []
    for y in range(end.year - years + 1, end.year + 1):
        for name, sec, base in heads:
            trend = 1 + 0.04 * (y - (end.year - years))
            rows.append(dict(city="Delhi (synthetic)", year=y, crime_head=name, section=sec,
                             cases_reported=int(rng.poisson(base * trend)), data_origin=ORIGIN))
    return pd.DataFrame(rows)


def gen_microreports(E, I, n, end, rng):
    """Your own crowd form: short-lived signals that should decay fast."""
    types = ["poor_lighting", "no_shops_open", "harassment_incident", "feels_unsafe", "well_lit_and_busy"]
    rows = []
    for i in range(n):
        t = rng.choice(types, p=[.28, .22, .12, .20, .18])
        h = int(rng.choice([19, 20, 21, 22, 23, 0, 1], p=[.14, .2, .22, .2, .12, .07, .05])) \
            if t in ("poor_lighting", "no_shops_open", "feels_unsafe") else int(rng.integers(8, 23))
        if t == "poor_lighting":
            pe = ((1 - E.lit) + 0.05).values
        elif t == "no_shops_open":
            pe = ((1 - E.shops_open_night) * E.footfall_day + 0.02).values
        elif t == "well_lit_and_busy":
            pe = (E.lit * E.footfall_night + 0.02).values
        else:
            pe = (I[:, h] + 0.01)
        e = rng.choice(len(E), p=pe / pe.sum())
        age_days = float(rng.exponential(25))
        rows.append((t, e, (end - pd.Timedelta(days=age_days)).normalize() + pd.Timedelta(hours=h, minutes=int(rng.integers(0, 60)))))
    e_idx = np.array([r[1] for r in rows])
    lat, lon, _ = jitter_points(E, e_idx, rng)
    return pd.DataFrame(dict(report_id=[f"APP-SYN-{i:05d}" for i in range(n)], data_origin=ORIGIN,
                             timestamp=[r[2] for r in rows], latitude=lat, longitude=lon,
                             report_type=[r[0] for r in rows],
                             reporter_id=[f"U{rng.integers(0, 400):04d}" for _ in range(n)],
                             _truth_edge_id=e_idx)).sort_values("timestamp").reset_index(drop=True)


# ------------------------------------------------------------------- main
def main():
    import json
    import hashlib
    from datetime import datetime, timezone
    ap = argparse.ArgumentParser(description="Generate SYNTHETIC women's-safety demo data")
    ap.add_argument("--area", choices=list(PRESETS), default="dwarka")
    ap.add_argument("--n-reports", type=int, default=6000, help="Safecity-style reports")
    ap.add_argument("--n-audits", type=int, default=1200, help="Safetipin-style audits")
    ap.add_argument("--n-micro", type=int, default=2500, help="app micro-reports")
    ap.add_argument("--months", type=int, default=24)
    ap.add_argument("--end-date", default="2026-10-05", help="fixed reference date for reproducible generation")
    ap.add_argument("--offline", action="store_true", help="skip OSM, use synthetic street grid")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/scenarios-v2", help="new, empty version directory; existing data is never overwritten")
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    end = pd.Timestamp(a.end_date) if a.end_date else pd.Timestamp.today().normalize()
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        ap.error("Output directory is not empty. Choose a new version with --out; no files were overwritten.")
    if min(a.n_reports, a.n_audits, a.n_micro) < 1 or a.months < 1:
        ap.error("Record counts and months must be positive.")
    out.mkdir(parents=True, exist_ok=True)
    print("=" * 66 + "\n  GENERATING SYNTHETIC DATA - NOT REAL INCIDENTS\n" + "=" * 66)

    G, source = load_graph(PRESETS[a.area], a.offline, rng)
    E = add_features(edge_table(G), rng)
    I = hourly_intensity(E)
    print(f"graph source: {source} | edges: {len(E)} | area: {a.area}")

    # ground truth latent risk per 4-hour bucket, scaled 0-1
    scale = np.percentile(I, 99)
    truth = E[["edge_id"]].copy()
    for lo, hi in BUCKETS:
        truth[f"true_risk_{lo:02d}_{hi:02d}"] = np.clip(I[:, lo:hi].mean(axis=1) / scale, 0, 1).round(4)

    sc = gen_safecity(E, I, a.n_reports, a.months, end, rng)
    sp = gen_safetipin(E, a.n_audits, a.months, end, rng)
    nc = gen_ncrb(end, rng)
    mr = gen_microreports(E, I, a.n_micro, end, rng)

    E.assign(data_origin=ORIGIN).to_csv(out / "edges_features.csv", index=False)
    truth.to_csv(out / "ground_truth_edge_risk.csv", index=False)
    sc.to_csv(out / "safecity_synthetic.csv", index=False)
    sp.to_csv(out / "safetipin_synthetic.csv", index=False)
    nc.to_csv(out / "ncrb_synthetic.csv", index=False)
    mr.to_csv(out / "app_microreports_synthetic.csv", index=False)
    try:
        H = nx.Graph(G) if isinstance(G, nx.Graph) and not G.is_multigraph() else nx.Graph(G.to_undirected())
        for _, _, d in H.edges(data=True):  # GraphML only stores simple types
            for k in [k for k, v in d.items() if not isinstance(v, (str, int, float, bool))]:
                d[k] = str(d[k])
        nx.write_graphml(H, out / "graph.graphml")
    except Exception as exc:
        print(f"[warn] could not save graph.graphml: {exc}")
    (out / "DATA_README.txt").write_text(
        "ALL FILES IN THIS FOLDER ARE SYNTHETIC (data_origin = SYNTHETIC).\n"
        "They were generated by generate_synthetic_safety_data.py as stand-ins for Safecity, "
        "Safetipin and NCRB data, which have been requested but not yet received.\n"
        "Columns starting with _truth_ and ground_truth_edge_risk.csv exist only for pipeline "
        "validation and must never be used as model features.\n"
        "Do not present any result from this data as evidence about real-world safety.\n")

    manifest = {
        "version": "scenario-generator-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": vars(a),
        "seed": a.seed,
        "data_origin": "SYNTHETIC",
        "geographic_coverage": PRESETS[a.area],
        "graph_source": source,
        "source_url": "https://www.openstreetmap.org" if source == "osm" else None,
        "graph_license": "ODbL; © OpenStreetMap contributors" if source == "osm" else "Synthetic grid",
        "retrieval_date": datetime.now(timezone.utc).isoformat() if source == "osm" else None,
        "feature_provenance": "Synthetic POI locations, lighting fills, activity and footfall proxies; not measured Delhi conditions.",
        "label_meaning": "Generated scenarios, never actual crime reports or independently verified observations.",
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.csv")},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"safecity-style reports : {len(sc):>6}  (incl. {int(sc._truth_is_spam.sum())} spam)")
    print(f"safetipin-style audits : {len(sp):>6}")
    print(f"ncrb-style rows        : {len(nc):>6}")
    print(f"app micro-reports      : {len(mr):>6}")
    hrs = sc.timestamp.dt.hour
    print("share of reports 20:00-04:59 =", round(float(((hrs >= 20) | (hrs < 5)).mean()), 2))
    print(f"files written to: {out.resolve()}")


if __name__ == "__main__":
    main()
