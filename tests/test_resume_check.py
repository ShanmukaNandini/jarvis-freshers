"""The profiler turns uploaded text into 'your facts', so a job posting must
never be silently accepted as a resume. These tests pin the deterministic
resume-likeness gate."""
import unittest

from jarvis.parsing import resume_likeness


RESUME_TEXT = """Priya Verma
priya@example.com | +91-98765-43210

Education
B.Tech Computer Science, 2026

Skills
Python, SQL, Flask

Projects
Campus API
Built a Flask API for student records with SQL storage.

Experience
Software Intern, Bharat Electronics
Developed reporting dashboards and implemented pytest suites.
"""

JOB_POSTING_TEXT = """Software Engineer Intern - Pie Infotech
About the role: We are looking for an intern to join our team.
Responsibilities: You will build APIs and you'll write tests.
Requirements: Python, SQL. Qualifications: B.Tech preferred.
Benefits: stipend and mentorship. Equal opportunity employer. Apply now.
"""


class ResumeLikenessTests(unittest.TestCase):
    def test_real_resume_passes(self):
        result = resume_likeness(RESUME_TEXT)
        self.assertEqual(result["verdict"], "resume")
        self.assertGreaterEqual(result["resume_score"], 3)

    def test_job_posting_is_flagged(self):
        result = resume_likeness(JOB_POSTING_TEXT)
        self.assertEqual(result["verdict"], "job_posting")
        self.assertIn("responsibilities", result["concerns"])

    def test_short_junk_is_unclear_not_resume(self):
        self.assertEqual(resume_likeness("hello world")["verdict"], "unclear")

    def test_never_raises_on_empty_or_none(self):
        self.assertEqual(resume_likeness("")["verdict"], "unclear")
        self.assertEqual(resume_likeness(None)["verdict"], "unclear")

    def test_signals_explain_the_decision(self):
        result = resume_likeness(RESUME_TEXT)
        self.assertTrue(any("email" in s for s in result["signals"]))
        self.assertTrue(any("section headings" in s for s in result["signals"]))


if __name__ == "__main__":
    unittest.main()
