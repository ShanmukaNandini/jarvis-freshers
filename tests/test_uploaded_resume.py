"""Locks the structure-preserving uploaded-resume pipeline against the
mangling bug: no heading strings as facts, no mid-sentence fragments,
correct section membership, all projects whole, one-page output."""
import re
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.core import structure_user_resume, tailor_resume_for_job, choose_font_size
from jarvis.latex_resume import generate_tex
from jarvis.fixtures import JOB_FIXTURES

# The user's real resume as extracted by pypdf in the app (structure from the
# PDF she uploaded; headings, wrapped lines and tech-stack lines preserved).
HER_RESUME = """VALLAPUREDDY SHANMUKA NANDINI
Bangalore, India| +91 9398686408| shanmukavallapureddy@gmail.com| linkedin.com/in/shanmuka-vallapureddy|
github.com/ShanmukaNandini
PROFESSIONAL SUMMARY
Final-year B.Tech Computer Science Engineering student (CGPA 8.58/10) seeking a Trainee System Engineer role in
production and application support. Solid foundation in Python, C, SQL, Operating Systems, Computer Networks
and DBMS, with hands-on experience building and debugging REST APIs and web services and working with relational
databases. Analytical, detail-oriented and a clear communicator with team-based project experience. Eager to contribute
to troubleshooting, system health checks, service request handling, escalation, monitoring, ticketing, SLA/KPI adherence,
shift handover and documentation, while building cloud (AWS/Azure) fundamentals.
TECHNICAL SKILLS
Programming: Python, C, SQL
Core CS: Operating Systems, Computer Networks, DBMS, Data Structures & Algorithms, OOP, SDLC
Web & APIs: REST APIs, Web Services, Flask, React.js, Postman (API testing)
Databases: MySQL, SQLite, relational database design and SQL queries
Cloud (Upskilling): AWS/Azure Fundamentals
Tools: Git, GitHub, VS Code, Pandas, NumPy, Power BI, Excel
Professional Skills: Troubleshooting & Debugging, Analytical & Logical Reasoning, Problem Solving, Communication,
Teamwork, Attention to Detail
EXPERIENCE
Intern, Bharat Electronics Limited (BEL) Bangalore, India | Nov 2026 – Present
• Software engineering intern working on a digital twin project.
• Building a sample digital twin for the team to evaluate and implement in their own system.
PROJECTS
Product Review Sentiment Analyzer Python, Flask, React.js, Scikit-learn, Postman
• Developed Flask REST APIs (/analyze, /analyze-csv) integrated with a React.js frontend to deliver real-time
predictions through a web service.
• Validated API request-response contracts with Postman to verify endpoint behavior and response correctness.
• Built an end-to-end sentiment classification pipeline using structured text preprocessing, TF-IDF vectorization and
Logistic Regression.
Real-Time Driver Drowsiness Detection System (Ongoing) Python, OpenCV, MediaPipe, TensorFlow Lite,
Flask, SQLite
• Developing a low-latency monitoring pipeline over live camera feeds using MediaPipe facial landmarks and Eye/Mouth
Aspect Ratio (EAR/MAR) algorithms to detect microsleep and yawning.
• Integrating a TensorFlow Lite model for on-device detection and real-time alert generation.
• Designing a Flask monitoring dashboard with a SQLite backend to log fatigue incidents and track alertness trends.
Retail Sales & Market Intelligence Dashboard Python, SQL, Pandas, Power BI, Excel
• Analyzed retail sales data using Python and SQL to identify revenue drivers and customer purchasing
patterns.
• Cleaned and transformed data and built interactive Power BI dashboards to track core business KPIs.
Government Scheme Recommendation Assistant Python, LangGraph, RAG, LLMs, Vector Database
• Developed an AI assistant that recommends welfare schemes by eligibility criteria using a RAG pipeline.
• Designed a LangGraph workflow with vector embeddings for semantic, context-aware retrieval across scheme
documents.
EDUCATION
Sir M. Visvesvaraya Institute of Technology, Bangalore, India Expected 2027
B.Tech, Computer Science Engineering | CGPA: 8.58/10
Narayana Junior College: Class XII – 95% | Viswabharathi English Medium High School: Class X – 100%
ACHIEVEMENTS & LEADERSHIP
• Special Jury Prize, Inter-College Hackathon, for the AI Government Scheme Recommendation Assistant (technical
innovation and social impact).
• Lead Coordinator, Decor Club: Planned and executed major college cultural events, managing cross-functional
student teams.
• Member, Welfare Club: Participated in student-led community outreach and social welfare initiatives.
"""

HEADINGS = {"PROFESSIONAL SUMMARY", "TECHNICAL SKILLS", "EXPERIENCE", "PROJECTS",
            "EDUCATION", "ACHIEVEMENTS & LEADERSHIP"}
PROJECTS = ["Product Review Sentiment Analyzer",
            "Real-Time Driver Drowsiness Detection System (Ongoing)",
            "Retail Sales & Market Intelligence Dashboard",
            "Government Scheme Recommendation Assistant"]


class UploadedResumeStructureTests(unittest.TestCase):
    def setUp(self):
        self.profile = structure_user_resume(HER_RESUME)
        self.tailored = tailor_resume_for_job(self.profile, JOB_FIXTURES[0])

    def test_name_and_contact_are_metadata_not_facts(self):
        self.assertEqual(self.profile["name"], "Vallapureddy Shanmuka Nandini")
        self.assertEqual(self.profile["email"], "shanmukavallapureddy@gmail.com")
        self.assertEqual(self.profile["location"], "Bangalore, India")
        self.assertIn("github.com/ShanmukaNandini", self.profile["links"])
        for fact in self.profile["facts"]:
            self.assertNotIn("shanmukavallapureddy@gmail.com", fact["text"])
            self.assertNotEqual(fact["text"].strip(), "github.com/ShanmukaNandini")

    def test_no_section_heading_strings_become_facts(self):
        for fact in self.profile["facts"]:
            self.assertNotIn(fact["text"].strip(), HEADINGS)
            self.assertFalse(fact["text"].strip().isupper(),
                             f"all-caps heading leaked into facts: {fact['text']!r}")

    def test_no_mid_sentence_fragment_facts(self):
        for fact in self.profile["facts"]:
            text = fact["text"].strip()
            if fact["role"] == "bullet":
                # a bullet is a whole sentence: starts uppercase, ends terminal
                self.assertTrue(text[0].isupper() or text[0].isdigit(),
                                f"fragment bullet: {text!r}")
                self.assertRegex(text, r"[.!?]$", f"unterminated bullet: {text!r}")
                self.assertNotIn("\n", text)
        # known mangled fragments from the bug must not exist as facts
        fact_texts = [f["text"] for f in self.profile["facts"]]
        for fragment in ("predic-", "tions through a web service.", "docu-",
                         "ments.", "innovation and social impact).",
                         "to troubleshooting, system health checks, service request handling, escalation, monitoring, ticketing,"):
            self.assertNotIn(fragment, fact_texts)

    def test_correct_section_membership(self):
        by_section = {}
        for fact in self.profile["facts"]:
            by_section.setdefault(fact["section"], []).append(fact["text"])
        self.assertTrue(any("digital twin" in t for t in by_section["experience"]))
        self.assertTrue(any("sentiment classification pipeline" in t
                            for t in by_section["project"]))
        self.assertTrue(any("CGPA: 8.58/10" in t or "Visvesvaraya" in t
                            for t in by_section["education"]))
        self.assertTrue(any("Special Jury Prize" in t for t in by_section["other"]))
        self.assertTrue(any(t.startswith("Programming:") for t in by_section["skill"]))
        # nothing from skills/experience may leak into projects or education
        self.assertFalse(any("github.com" in t for t in by_section["project"]))
        self.assertFalse(any("Lead Coordinator" in t for t in by_section["education"]))

    def test_all_four_projects_present_with_their_bullets(self):
        projects = {e["title"]: e for e in self.profile["entries"]
                    if e["section"] == "project"}
        for title in PROJECTS:
            self.assertIn(title, projects)
            self.assertGreaterEqual(len(projects[title]["bullets"]), 2,
                                    f"{title} lost its description bullets")
            self.assertTrue(projects[title]["subtitle"],
                            f"{title} lost its tech-stack line")
        # bullets are whole and attached to the right project
        drowsy = projects["Real-Time Driver Drowsiness Detection System (Ongoing)"]
        self.assertTrue(any("EAR/MAR" in b for b in drowsy["bullets"]))
        sentiment = projects["Product Review Sentiment Analyzer"]
        self.assertTrue(any("predictions through a web service." in b
                            for b in sentiment["bullets"]))

    def test_bel_entry_keeps_title_dates_and_bullets(self):
        bel = [e for e in self.profile["entries"] if e["section"] == "experience"][0]
        self.assertIn("Bharat Electronics Limited", bel["title"])
        self.assertIn("Nov 2026", bel["right"])
        self.assertEqual(len(bel["bullets"]), 2)

    def test_tailoring_never_remixes_sentences_across_sections(self):
        tex = generate_tex(self.profile, self.tailored)
        # every project bullet appears inside the Projects region of the .tex
        projects_region = tex.split(r"\ressection{Projects}")[1]
        projects_region = projects_region.split(r"\ressection{")[0]
        for fact in self.profile["facts"]:
            if fact["section"] == "project" and fact["role"] == "bullet":
                self.assertIn(fact["text"].replace("&", "\\&").replace("#", "\\#"),
                              projects_region)
        # no project bullet may appear under any other section
        skills_region = tex.split(r"\ressection{Technical Skills}")[1]
        skills_region = skills_region.split(r"\ressection{")[0]
        self.assertNotIn("digital twin", skills_region)
        self.assertNotIn("sentiment", skills_region)

    def test_one_page_layout_for_her_content(self):
        # The deterministic one-page decision must select the compact size for
        # her content volume; the .tex compiles to exactly one page at 10pt
        # (compile-verified separately with pdflatex).
        self.assertEqual(choose_font_size(self.profile, self.tailored), 10)
        tex = generate_tex(self.profile, self.tailored)
        self.assertIn(r"\documentclass[10pt,a4paper]", tex)

    def test_markdown_renders_entries_whole(self):
        md = self.tailored["markdown"]
        for title in PROJECTS:
            self.assertIn(title, md)
        self.assertIn("**Intern, Bharat Electronics Limited", md)
        self.assertIn("Nov 2026", md)


if __name__ == "__main__":
    unittest.main()
