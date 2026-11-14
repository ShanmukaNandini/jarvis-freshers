"""Visible-tailoring and user-addition behaviour.

The hard rule stands: every rendered line is one of the user's own facts.
What this pass adds is that tailoring must be VISIBLE - two different jobs
produce visibly different resumes - and that the user can add new material
to their own profile.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.core import (structure_user_resume, tailor_resume_for_job,
                         add_user_skill, add_user_project, add_user_other,
                         add_user_experience)
from jarvis.jobs import DEFAULT_BOARDS, is_india_remote

# A 4-project resume with one deliberately off-target project (firmware in C)
# and three data/backend projects.
RESUME = (
    "Divya Rao\n"
    "divya.rao@example.com | +91-9812345678 | Bengaluru\n"
    "EDUCATION\n"
    "B.Tech in Computer Science, PES University | Expected 2027\n"
    "CGPA 8.9/10\n"
    "TECHNICAL SKILLS\n"
    "Programming: Python, C, SQL, Java\n"
    "Data & Tools: pandas, Power BI, Excel, Git, Docker\n"
    "PROJECTS\n"
    "Vendor Performance Dashboard | Jan 2026 - Mar 2026\n"
    "Python, SQL, pandas, Power BI, Excel\n"
    "- Built a dashboard tracking 40 vendors' delivery performance with pandas and SQL.\n"
    "- Automated weekly Excel reporting, saving 6 hours per week.\n"
    "Campus Lost-and-Found API | Sep 2025 - Nov 2025\n"
    "Python, Flask, SQLite\n"
    "- Built a REST API in Flask serving 300 students.\n"
    "- Wrote pytest suites covering 85% of endpoints.\n"
    "Bus Delay Predictor | May 2025 - Jul 2025\n"
    "Python, scikit-learn, pandas\n"
    "- Trained a logistic regression model predicting bus delays at 0.81 F1.\n"
    "- Cleaned 100k rows of transport data with pandas.\n"
    "Firmware for Line-Follower Bot | Feb 2025\n"
    "C, Arduino\n"
    "- Programmed AVR firmware in C for sensor polling loops.\n"
    "- Tuned PID constants for stable line tracking.\n"
)

BACKEND_JOB = {
    "id": "job-backend-x", "title": "Software Engineer Intern (Backend)",
    "company": "AcmeCloud", "location": "Bengaluru",
    "description": "Build services in Python. Testing and SQL come up daily.",
    "requirements": {"required": ["Python", "Testing", "SQL"],
                     "preferred": []},
}
DATA_JOB = {
    "id": "job-data-x", "title": "Data Analyst Intern",
    "company": "NumbersCo", "location": "Mumbai",
    "description": "Analyse vendor data with SQL, pandas, Excel and Power BI. "
                   "Dashboards and data visualization for business teams.",
    "requirements": {"required": ["SQL", "pandas", "Excel", "Data visualization"],
                     "preferred": ["Statistics"]},
}


class VisibleTailoringTests(unittest.TestCase):
    def setUp(self):
        self.profile = structure_user_resume(RESUME)

    def test_skill_line_reorders_tokens_without_changing_them(self):
        tailored = tailor_resume_for_job(self.profile, DATA_JOB)
        self.assertTrue(tailored["skill_lines"])
        for fact in self.profile["facts"]:
            if fact["id"] in tailored["skill_lines"]:
                before = tailored["skill_lines"][fact["id"]] and fact["text"]
                after = tailored["skill_lines"][fact["id"]]
                # Same tokens, same multiset - order only.
                strip = lambda s: sorted(t.strip().lower()
                                         for t in s.split(": ", 1)[-1].split(","))
                self.assertEqual(strip(before), strip(after))
        # SQL leads the Programming line for the data job.
        prog = [f for f in self.profile["facts"]
                if f["id"] in tailored["skill_lines"]
                and f["text"].startswith("Programming")][0]
        self.assertTrue(tailored["skill_lines"][prog["id"]].startswith("Programming: SQL"))

    def test_projects_reordered_and_off_target_project_left_out(self):
        tailored = tailor_resume_for_job(self.profile, DATA_JOB)
        view_titles = [e["title"] for e in tailored["entry_view"] if e["section"] == "project"]
        self.assertEqual(view_titles[0], "Vendor Performance Dashboard")
        # 4 projects, 3 match, 1 zero-overlap -> the firmware bot is left out.
        self.assertNotIn("Firmware for Line-Follower Bot", view_titles)
        self.assertEqual([l["title"] for l in tailored["left_out"]],
                         ["Firmware for Line-Follower Bot"])
        self.assertNotIn("Line-Follower", tailored["markdown"])
        # ...but a job matching fewer than 3 projects drops nothing.
        sparse_job = dict(BACKEND_JOB)
        sparse_job["requirements"] = {"required": ["Docker", "Kubernetes"],
                                      "preferred": []}
        tailored_b = tailor_resume_for_job(self.profile, sparse_job)
        self.assertFalse(tailored_b["left_out"])
        self.assertIn("Line-Follower", tailored_b["markdown"])

    def test_bullets_reordered_inside_entries(self):
        tailored = tailor_resume_for_job(self.profile, BACKEND_JOB)
        api = [e for e in tailored["entry_view"] if "Lost-and-Found" in e["title"]][0]
        # Testing is a top requirement here, so the pytest bullet leads.
        self.assertTrue(api["bullets"][0].startswith("Wrote pytest"))
        self.assertTrue(any(c["kind"] == "bullets" for c in tailored["changes"]))

    def test_two_jobs_produce_visibly_different_resumes(self):
        t_data = tailor_resume_for_job(self.profile, DATA_JOB)
        t_back = tailor_resume_for_job(self.profile, BACKEND_JOB)
        self.assertNotEqual(t_data["markdown"], t_back["markdown"])
        self.assertNotEqual(
            [e["title"] for e in t_data["entry_view"] if e["section"] == "project"],
            [e["title"] for e in t_back["entry_view"] if e["section"] == "project"])

    def test_changes_panel_is_plain_english(self):
        tailored = tailor_resume_for_job(self.profile, DATA_JOB)
        kinds = {c["kind"] for c in tailored["changes"]}
        self.assertIn("summary", kinds)
        self.assertIn("skills", kinds)
        self.assertIn("left_out", kinds)
        for c in tailored["changes"]:
            self.assertTrue(c["text"].strip())

    def test_no_invention_still_holds(self):
        job = dict(DATA_JOB)
        job["requirements"] = {"required": ["SQL", "pandas", "Terraform"],
                               "preferred": []}
        tailored = tailor_resume_for_job(self.profile, job)
        # Terraform is nowhere in her facts: it is a gap, never a claim.
        self.assertIn("Terraform", tailored["missing_required"])
        self.assertNotIn("terraform", tailored["markdown"].lower())


class UserAdditionTests(unittest.TestCase):
    def setUp(self):
        self.profile = structure_user_resume(RESUME)

    def test_add_skill_becomes_tailoring_material(self):
        fact = add_user_skill(self.profile, "Kubernetes, Terraform")
        self.assertEqual(fact["added_by"], "user")
        self.assertEqual(fact["section"], "skill")
        self.assertTrue(fact["text"].startswith("Additional Skills:"))
        job = dict(BACKEND_JOB)
        job["requirements"] = {"required": ["Python", "SQL"], "preferred": []}
        tailored = tailor_resume_for_job(self.profile, job)
        self.assertIn("Kubernetes", tailored["markdown"])

    def test_add_project_renders_whole_and_competes(self):
        entry = add_user_project(
            self.profile, "Placement Portal Scraper", "Python, Selenium, SQL",
            ["Scraped 2 years of placement records with Selenium.",
             "Stored and queried results in SQLite with SQL."])
        self.assertEqual(entry["section"], "project")
        self.assertTrue(entry["id"].startswith("E"))
        ids = [e["id"] for e in self.profile["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        tailored = tailor_resume_for_job(self.profile, DATA_JOB)
        self.assertIn("Placement Portal Scraper", tailored["markdown"])
        self.assertIn("Scraped 2 years of placement records", tailored["markdown"])

    def test_add_other_fact(self):
        fact = add_user_other(self.profile, "AWS Certified Cloud Practitioner, 2026")
        self.assertEqual(fact["section"], "other")
        tailored = tailor_resume_for_job(self.profile, BACKEND_JOB)
        self.assertIn("AWS Certified Cloud Practitioner", tailored["markdown"])

    def test_fact_ids_never_collide(self):
        a = add_user_skill(self.profile, "Go")
        b = add_user_other(self.profile, "Hackathon finalist")
        self.assertNotEqual(a["id"], b["id"])
        all_ids = [f["id"] for f in self.profile["facts"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_empty_additions_raise(self):
        self.assertRaises(ValueError, add_user_skill, self.profile, "  ")
        self.assertRaises(ValueError, add_user_project, self.profile, "", "", ["x"])
        self.assertRaises(ValueError, add_user_project, self.profile, "T", "", [])
        self.assertRaises(ValueError, add_user_other, self.profile, "")
        self.assertRaises(ValueError, add_user_experience, self.profile, "", "Co", "", ["x"])
        self.assertRaises(ValueError, add_user_experience, self.profile, "Intern", "", "", [])

    def test_add_experience_renders_and_competes(self):
        entry = add_user_experience(
            self.profile, "Data Analyst Intern", "Acme Insights",
            "Jun 2026 - Aug 2026",
            ["Analysed 20k rows of sales data with SQL and pandas.",
             "Built Power BI dashboards for the weekly business review."])
        self.assertEqual(entry["section"], "experience")
        self.assertEqual(entry["subtitle"], "Acme Insights")
        self.assertEqual(entry["right"], "Jun 2026 - Aug 2026")
        tailored = tailor_resume_for_job(self.profile, DATA_JOB)
        # Renders into the Experience section, bullets whole.
        self.assertIn("Data Analyst Intern", tailored["markdown"])
        self.assertIn("Acme Insights", tailored["markdown"])
        self.assertIn("Analysed 20k rows of sales data", tailored["markdown"])
        # And it competes in per-job ordering: it matches the data job, so it
        # leads the Experience section for it.
        exp_titles = [e["title"] for e in tailored["entry_view"]
                      if e["section"] == "experience"]
        self.assertEqual(exp_titles[0], "Data Analyst Intern")
        all_ids = [f["id"] for f in self.profile["facts"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))


class IndiaBoardTests(unittest.TestCase):
    def test_curated_boards_include_india_heavy_companies(self):
        slugs = {slug for slug, _ in DEFAULT_BOARDS}
        for expected in ("rubrik", "databricks", "okta", "fivetran"):
            self.assertIn(expected, slugs)

    def test_is_india_remote(self):
        self.assertTrue(is_india_remote({"location": "Bengaluru"}))
        self.assertTrue(is_india_remote({"location": "India - Remote"}))
        self.assertTrue(is_india_remote({"location": "Remote - US"}))
        self.assertFalse(is_india_remote({"location": "Dublin"}))
        self.assertFalse(is_india_remote({"location": "New York"}))


if __name__ == '__main__':
    unittest.main()
