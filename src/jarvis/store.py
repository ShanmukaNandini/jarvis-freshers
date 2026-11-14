"""Local single-user persistence baseline. No production multi-user isolation yet."""
import sqlite3
import time
from datetime import datetime

ALLOWED = {"saved", "applied", "received", "interview", "rejected", "offer", "withdrawn", "needs_review"}

# Statuses after which a different later status is suspicious and held for review.
TERMINAL_STATUSES = {"rejected", "withdrawn", "offer"}


def connect(path=":memory:"):
    """Open a connection that survives concurrent access. Streamlit reruns and
    multiple app processes can hit the same file at once, so file-backed
    databases run in WAL mode (readers never block the writer) with a 30s
    busy timeout instead of failing instantly with 'database is locked'."""
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    if path != ":memory:":
        run_with_retry(lambda: db.execute("PRAGMA journal_mode=WAL"))
    run_with_retry(lambda: db.executescript("""
    CREATE TABLE IF NOT EXISTS applications (
      id TEXT PRIMARY KEY, company TEXT NOT NULL, role TEXT NOT NULL,
      job_url TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'saved');
    CREATE TABLE IF NOT EXISTS events (
      source_id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(id),
      status TEXT NOT NULL, occurred_at TEXT NOT NULL, evidence TEXT NOT NULL);
    """))
    db.execute("PRAGMA foreign_keys=ON")
    return db


def run_with_retry(fn, attempts=4, delay=0.4):
    """Run fn(), retrying briefly on sqlite 'database is locked'. The busy
    timeout makes this rare; the retry keeps a stale lock from another app
    process from ever white-screening the UI. Re-raises the last error."""
    for attempt in range(attempts):
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == attempts - 1:
                raise
            time.sleep(delay)

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

def applications(db):
    return [dict(row) for row in db.execute(
        "SELECT * FROM applications ORDER BY rowid")]


# ---------------------------------------------------------------------------
# Synthetic inbox processing (fixtures only - never a real inbox)
# ---------------------------------------------------------------------------
# Every fixture email is tied to an exact application ID and carries a unique
# source_id. Processing is idempotent (a rerun yields only duplicates) and
# conservative: ambiguous, out-of-order, or terminal-state-conflicting messages
# are HELD for human review instead of being applied.

def _latest_event_time(db, app_id):
    row = db.execute("SELECT MAX(occurred_at) AS latest FROM events WHERE application_id=?",
                     (app_id,)).fetchone()
    return row["latest"] if row and row["latest"] else None

def _application_status(db, app_id):
    row = db.execute("SELECT status FROM applications WHERE id=?", (app_id,)).fetchone()
    return row["status"] if row else None

def process_synthetic_fixtures(db, applications_fixture, email_fixtures):
    """Process synthetic email fixtures into the tracker.

    Returns {"recorded": int, "duplicates": int, "held": [ {source_id, reason} ]}.
    Fixtures are processed in inbox order (list order), as if arriving over time.
    """
    from jarvis.core import suggest_email_status

    result = {"recorded": 0, "duplicates": 0, "held": []}

    for app in applications_fixture:
        db.execute("INSERT OR IGNORE INTO applications(id,company,role,job_url) "
                   "VALUES (?,?,?,?)",
                   (app["id"], app["company"], app["role"], app.get("job_url", "")))
    db.commit()

    known_apps = {a["id"] for a in applications_fixture}

    for fix in email_fixtures:
        source_id = fix["source_id"]
        app_id = fix["application_id"]

        existing = db.execute("SELECT 1 FROM events WHERE source_id=?",
                              (source_id,)).fetchone()
        if existing:
            result["duplicates"] += 1
            continue

        if app_id not in known_apps and _application_status(db, app_id) is None:
            result["held"].append({"source_id": source_id,
                                   "reason": f"unknown application '{app_id}'"})
            continue

        suggestion = suggest_email_status(fix.get("subject", ""), fix.get("body", ""))
        status = suggestion["status"]
        if status == "needs_review":
            result["held"].append({"source_id": source_id,
                                   "reason": "ambiguous or unrecognised message; "
                                             "needs human review"})
            continue

        occurred_at = fix["occurred_at"]
        latest = _latest_event_time(db, app_id)
        if latest and datetime.fromisoformat(occurred_at) < datetime.fromisoformat(latest):
            result["held"].append({"source_id": source_id,
                                   "reason": "out-of-order: older than the application's "
                                             "latest recorded event (chronology guard)"})
            continue

        current = _application_status(db, app_id)
        if current in TERMINAL_STATUSES and status != current:
            result["held"].append({"source_id": source_id,
                                   "reason": f"conflicts with terminal status "
                                             f"'{current}'; held for human review"})
            continue

        evidence = fix.get("evidence", "").strip() or \
            "Matched phrases: " + ", ".join(suggestion.get("evidence", []))
        if record_reviewed_event(db, app_id, source_id, status, occurred_at, evidence):
            result["recorded"] += 1
        else:
            result["duplicates"] += 1

    return result
