"""Synthetic smoke demo. No network, no API key, no user inbox."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from jarvis.core import rank_jobs, suggest_email_status, daily_digest
from jarvis.store import connect, save_application, record_reviewed_event, events

jobs = [{"id":"synthetic-1", "title":"Python Data Intern", "description":"Python SQL data", "synthetic":True}]
print("SYNTHETIC FIXTURE DEMO - not live openings or live email")
print(rank_jobs("Python SQL", ["data"], jobs))
suggestion = suggest_email_status("Interview invitation", "Please schedule an interview.")
print("Review suggestion:", suggestion)
db = connect()
save_application(db, "demo-1", "Synthetic Employer", "Data Intern", "synthetic:not-a-real-job")
record_reviewed_event(db, "demo-1", "synthetic-message-1", "interview", "2026-11-13T17:00:00+05:30", "Synthetic interview invitation")
print(daily_digest(events(db), "2026-11-13"))
