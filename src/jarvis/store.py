"""Local single-user persistence baseline. No production multi-user isolation yet."""
import sqlite3
from datetime import datetime

ALLOWED = {"saved", "applied", "received", "interview", "rejected", "offer", "withdrawn", "needs_review"}

def connect(path=":memory:"):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS applications (
      id TEXT PRIMARY KEY, company TEXT NOT NULL, role TEXT NOT NULL,
      job_url TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'saved');
    CREATE TABLE IF NOT EXISTS events (
      source_id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(id),
      status TEXT NOT NULL, occurred_at TEXT NOT NULL, evidence TEXT NOT NULL);
    """)
    db.execute("PRAGMA foreign_keys=ON")
    return db

def save_application(db, app_id, company, role, url):
    db.execute("INSERT INTO applications(id,company,role,job_url) VALUES (?,?,?,?)",
               (app_id, company, role, url))
    db.commit()

def record_reviewed_event(db, app_id, source_id, status, occurred_at, evidence):
    """Only call after identity, chronology and status review; no email-name guessing."""
    if status not in ALLOWED:
        raise ValueError("Unsupported status")
    ts = datetime.fromisoformat(occurred_at)
    if ts.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    if not evidence.strip():
        raise ValueError("Evidence is required")
    with db:
        cursor = db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)",
                            (source_id, app_id, status, occurred_at, evidence))
        if cursor.rowcount:
            db.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    return bool(cursor.rowcount)

def events(db):
    return [dict(row) for row in db.execute("""
      SELECT e.*, a.company, a.role FROM events e JOIN applications a
      ON a.id=e.application_id ORDER BY e.occurred_at""")]
