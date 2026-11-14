import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.fixtures import (BASE_RESUME, JOB_FIXTURES, SYNTHETIC_APPLICATIONS,
                             EMAIL_FIXTURES)


class FixtureTests(unittest.TestCase):
    def test_job_count_is_expanded(self):
        self.assertGreaterEqual(len(JOB_FIXTURES), 8)

    def test_job_ids_unique(self):
        ids = [j["id"] for j in JOB_FIXTURES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_job_has_full_requirements(self):
        for job in JOB_FIXTURES:
            self.assertTrue(job["requirements"]["required"],
                            f"{job['id']} has no required requirements")
            self.assertTrue(job["requirements"]["preferred"],
                            f"{job['id']} has no preferred requirements")
            for field in ("title", "company", "location", "description", "url"):
                self.assertTrue(job.get(field), f"{job['id']} missing {field}")
            self.assertEqual(job.get("source"), "synthetic")

    def test_base_resume_fact_ids_unique(self):
        ids = [f["id"] for f in BASE_RESUME["facts"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(BASE_RESUME["name"])

    def test_email_fixtures_reference_known_applications(self):
        app_ids = {a["id"] for a in SYNTHETIC_APPLICATIONS}
        source_ids = [e["source_id"] for e in EMAIL_FIXTURES]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        for e in EMAIL_FIXTURES:
            self.assertIn(e["application_id"], app_ids)
            # timezone-aware timestamps, required by the store
            from datetime import datetime
            self.assertIsNotNone(datetime.fromisoformat(e["occurred_at"]).tzinfo)


if __name__ == '__main__':
    unittest.main()
