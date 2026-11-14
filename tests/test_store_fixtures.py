import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.fixtures import SYNTHETIC_APPLICATIONS, EMAIL_FIXTURES
from jarvis.store import connect, events, applications, process_synthetic_fixtures


class ProcessSyntheticFixtureTests(unittest.TestCase):
    def setUp(self):
        self.db = connect()
        self.result = process_synthetic_fixtures(
            self.db, SYNTHETIC_APPLICATIONS, EMAIL_FIXTURES)

    def test_applications_seeded(self):
        self.assertEqual(len(applications(self.db)), len(SYNTHETIC_APPLICATIONS))

    def test_clean_messages_recorded(self):
        # msg-001, msg-002, msg-003, msg-004, msg-006 are clean -> 5 recorded
        self.assertEqual(self.result["recorded"], 5)
        self.assertEqual(len(events(self.db)), 5)

    def test_ambiguous_held(self):
        held = {h["source_id"]: h["reason"] for h in self.result["held"]}
        self.assertIn("msg-005", held)
        self.assertIn("ambiguous", held["msg-005"])

    def test_out_of_order_held_by_chronology_guard(self):
        held = {h["source_id"]: h["reason"] for h in self.result["held"]}
        self.assertIn("msg-007", held)
        self.assertIn("chronology", held["msg-007"])

    def test_terminal_state_conflict_held(self):
        held = {h["source_id"]: h["reason"] for h in self.result["held"]}
        self.assertIn("msg-008", held)
        self.assertIn("terminal", held["msg-008"])

    def test_statuses_applied(self):
        apps = {a["id"]: a["status"] for a in applications(self.db)}
        self.assertEqual(apps["app-001"], "interview")
        self.assertEqual(apps["app-002"], "rejected")
        self.assertEqual(apps["app-003"], "saved")   # ambiguous msg held, no change
        self.assertEqual(apps["app-004"], "received")

    def test_rerun_is_idempotent(self):
        again = process_synthetic_fixtures(self.db, SYNTHETIC_APPLICATIONS, EMAIL_FIXTURES)
        self.assertEqual(again["recorded"], 0)
        self.assertEqual(again["duplicates"], 5)
        # held messages are re-evaluated and held again, never applied
        self.assertEqual({h["source_id"] for h in again["held"]},
                         {"msg-005", "msg-007", "msg-008"})
        self.assertEqual(len(events(self.db)), 5)


class ConcurrencyTests(unittest.TestCase):
    """The 'database is locked' white-screen: concurrent writers (Streamlit
    reruns, a second app process) must never see an OperationalError."""

    def test_file_connection_uses_wal_and_busy_timeout(self):
        import tempfile, os
        path = tempfile.mktemp(suffix=".db")
        try:
            db = connect(path)
            mode = db.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
            busy = db.execute("PRAGMA busy_timeout").fetchone()[0]
            self.assertGreaterEqual(busy, 10000)
            db.close()
        finally:
            for suffix in ("", "-wal", "-shm"):
                if os.path.exists(path + suffix):
                    os.remove(path + suffix)

    def test_concurrent_writers_never_lock(self):
        import tempfile, threading, os
        path = tempfile.mktemp(suffix=".db")
        errors = []

        def worker(i):
            try:
                db = connect(path)
                for j in range(30):
                    db.execute("INSERT OR IGNORE INTO applications VALUES (?,?,?,?,'saved')",
                               (f"t-{i}-{j}", "Co", "Role", "http://x"))
                    db.commit()
                db.close()
            except Exception as exc:  # noqa: BLE001 - record anything for the assert
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        try:
            self.assertEqual(errors, [])
            db = connect(path)
            self.assertEqual(len(applications(db)), 6 * 30)
            db.close()
        finally:
            for suffix in ("", "-wal", "-shm"):
                if os.path.exists(path + suffix):
                    os.remove(path + suffix)


if __name__ == '__main__':
    unittest.main()
