import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jarvis.core import rank_jobs, suggest_email_status, daily_digest
from jarvis.store import connect, save_application, record_reviewed_event, events
from jarvis.jobs import fetch_greenhouse

class CoreTests(unittest.TestCase):
    def test_interest_changes_ranking(self):
        jobs=[{'title':'Python data'}, {'title':'Python frontend'}]
        self.assertEqual(rank_jobs('Python', ['frontend'], jobs)[0]['title'], 'Python frontend')
    def test_ambiguous_email(self):
        self.assertEqual(suggest_email_status('Interview invitation', 'not moving forward')['status'], 'needs_review')
    def test_unknown_email(self):
        self.assertEqual(suggest_email_status('Hello', 'Check our news')['status'], 'needs_review')
    def test_duplicate_event(self):
        db=connect()
        save_application(db,'a','Synthetic','Role','synthetic:job')
        args=(db,'a','mail-1','received','2026-11-13T12:00:00+00:00','fixture')
        self.assertTrue(record_reviewed_event(*args))
        self.assertFalse(record_reviewed_event(*args))
        self.assertEqual(len(events(db)),1)
    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            record_reviewed_event(connect(),'a','x','received','2026-11-13T12:00:00','fixture')
    def test_timezone_boundary(self):
        es=[{'occurred_at':'2026-11-12T20:00:00+00:00','company':'Fixture','role':'Intern','status':'received'}]
        self.assertIn('1 application', daily_digest(es,'2026-11-13'))
        self.assertIn('No application', daily_digest(es,'2026-11-12'))
    def test_board_token_rejects_urls(self):
        with self.assertRaises(ValueError): fetch_greenhouse('https://bad.example/path')

if __name__=='__main__': unittest.main()
