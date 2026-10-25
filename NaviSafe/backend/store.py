"""Transactional local backend storage. Private media are never statically mounted."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def database():
    path = Path(os.getenv("SAFEPATH_DB", str(ROOT / "data" / "safepath.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, actor TEXT, idem TEXT, fingerprint TEXT, body TEXT, UNIQUE(actor,idem))")
    conn.execute("CREATE TABLE IF NOT EXISTS abuse (actor TEXT, timestamp REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, report_id TEXT, actor TEXT, body TEXT, timestamp TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS curated_training (report_id TEXT PRIMARY KEY, label TEXT NOT NULL, eligible INTEGER NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL)")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def all_reports(conn):
    return [json.loads(row["body"]) for row in conn.execute("SELECT body FROM reports")]


def save(conn, report):
    conn.execute("UPDATE reports SET body=? WHERE id=?", (json.dumps(report), report["id"]))
