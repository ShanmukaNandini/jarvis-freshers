import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.core import (structure_user_resume, tailor_resume_for_job,
                         canonical_skills, learning_suggestions)
from jarvis.fixtures import BASE_RESUME, JOB_FIXTURES

JOB = {j["id"]: j for j in JOB_FIXTURES}


class TailoringFromSyntheticProfileTests(unittest.TestCase):
    def setUp(self):
        self.tailored = tailor_resume_for_job(BASE_RESUME, JOB["job-ml-intern-01"])

    def test_claims_reference_only_existing_facts(self):
        fact_ids = {f["id"] for f in BASE_RESUME["facts"]}
        for claim in self.tailored["claims"]:
            self.assertIn(claim["fact_id"], fact_ids)

    def test_no_invented_claims(self):
        fact_texts = {f["id"]: f["text"] for f in BASE_RESUME["facts"]}
        for claim in self.tailored["claims"]:
            self.assertEqual(claim["text"], fact_texts[claim["fact_id"]])

    def test_supported_and_missing_partition_requirements(self):
        job = JOB["job-ml-intern-01"]
        all_reqs = job["requirements"]["required"] + job["requirements"]["preferred"]
        supported = set(self.tailored["supported_requirements"])
        missing = set(self.tailored["missing_required"]) | set(self.tailored["missing_preferred"])
        self.assertEqual(supported | missing, set(all_reqs))
        self.assertFalse(supported & missing)

    def test_expected_support_and_gap(self):
        self.assertIn("Python", self.tailored["supported_requirements"])
        # BASE_RESUME has no deep-learning fact, so it must surface as a gap.
        self.assertIn("deep learning basics", self.tailored["missing_preferred"])
        # ...and must NOT appear anywhere in the tailored resume text.
        self.assertNotIn("deep learning", self.tailored["markdown"].lower())

    def test_every_supported_requirement_has_evidence(self):
        claim_matches = {r for c in self.tailored["claims"] for r in c["matched_requirements"]}
        for r in self.tailored["supported_requirements"]:
            self.assertIn(r, claim_matches)

    def test_full_length_output_has_all_sections(self):
        md = self.tailored["markdown"]
        self.assertIn("# ", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Skills", md)
        self.assertIn("## Experience & Projects", md)
        self.assertIn("## Education", md)
        # full-length: every profile fact appears in the resume
        for fact in BASE_RESUME["facts"]:
            self.assertIn(fact["text"], md)


class TailoringFromUserResumeTests(unittest.TestCase):
    RESUME = (
        "Priya Verma\n"
        "priya.verma@example.com | +91-9812345678 | Hyderabad\n"
        "B.Tech in Computer Science, ABC University, expected 2026.\n"
        "Built a Flask REST API for a campus lost-and-found app using Python.\n"
        "Analysed survey data with SQL and pandas for a final-year project.\n"
        "Skills: Python, SQL, pandas, Git.\n"
    )

    def setUp(self):
        self.profile = structure_user_resume(self.RESUME)

    def test_structuring_preserves_facts_with_provenance(self):
        self.assertTrue(self.profile["facts"])
        for fact in self.profile["facts"]:
            self.assertIn(fact["text"], " ".join(self.profile["sentences"]))
            self.assertTrue(fact["provenance"])
        self.assertEqual(self.profile["name"], "Priya Verma")
        self.assertEqual(self.profile["email"], "priya.verma@example.com")

    def test_tailoring_uses_user_facts(self):
        tailored = tailor_resume_for_job(self.profile, JOB["job-backend-01"])
        self.assertIn("Python", tailored["supported_requirements"])
        self.assertIn("SQL", tailored["supported_requirements"])
        for claim in tailored["claims"]:
            self.assertTrue(claim["fact_id"].startswith("U"))
        self.assertIn("Priya Verma", tailored["markdown"])
        self.assertIn("campus lost-and-found", tailored["markdown"])

    def test_unmet_requirement_never_enters_resume(self):
        tailored = tailor_resume_for_job(self.profile, JOB["job-backend-01"])
        self.assertIn("Docker", tailored["missing_preferred"])
        self.assertNotIn("docker", tailored["markdown"].lower())

    def test_interests_never_establish_skill(self):
        # The profile has no Docker evidence; an interest in docker must not
        # turn it into a supported requirement anywhere in tailoring.
        self.assertNotIn("docker", {s for f in self.profile["facts"]
                                    for s in f["skills"]})

    def test_learning_suggestions_cover_every_gap(self):
        tailored = tailor_resume_for_job(self.profile, JOB["job-backend-01"])
        tips = learning_suggestions(tailored["missing_required"]
                                    + tailored["missing_preferred"])
        self.assertEqual({t["requirement"] for t in tips},
                         set(tailored["missing_required"]
                             + tailored["missing_preferred"]))
        for t in tips:
            self.assertTrue(t["suggestion"])
            self.assertNotIn("http", t["suggestion"])  # no invented links


class CanonicalSkillTests(unittest.TestCase):
    def test_aliases(self):
        self.assertIn("machine-learning", canonical_skills("experience with scikit-learn"))
        self.assertIn("rest-api", canonical_skills("built a Flask service"))
        self.assertIn("data-visualization", canonical_skills("Power BI dashboards"))

    def test_no_false_positives_on_generic_words(self):
        self.assertEqual(canonical_skills("I am a quick learner and team player"),
                         set())


if __name__ == '__main__':
    unittest.main()
