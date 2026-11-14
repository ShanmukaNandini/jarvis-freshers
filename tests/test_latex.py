import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.core import tailor_resume_for_job, structure_user_resume
from jarvis.fixtures import BASE_RESUME, JOB_FIXTURES
from jarvis.latex_resume import escape_latex, generate_tex

JOB = {j["id"]: j for j in JOB_FIXTURES}


class EscapeTests(unittest.TestCase):
    def test_all_specials_escaped(self):
        self.assertEqual(escape_latex("100% & $5 #tag a_b {x} ~ ^ \\"),
                         r"100\% \& \$5 \#tag a\_b \{x\} \textasciitilde{} "
                         r"\textasciicircum{} \textbackslash{}")

    def test_plain_text_untouched(self):
        self.assertEqual(escape_latex("Python developer"), "Python developer")


class GenerateTexTests(unittest.TestCase):
    def setUp(self):
        self.tailored = tailor_resume_for_job(BASE_RESUME, JOB["job-backend-01"])
        self.tex = generate_tex(BASE_RESUME, self.tailored)

    def test_standalone_document(self):
        self.assertIn(r"\documentclass", self.tex)
        self.assertIn(r"\begin{document}", self.tex)
        self.assertIn(r"\end{document}", self.tex)

    def test_her_format_markers(self):
        # small-caps ruled section headings, centered name block, pipe contact row
        self.assertIn(r"\ressection", self.tex)
        self.assertIn(r"\hrule", self.tex)
        self.assertIn(r"\scshape", self.tex)
        self.assertIn(r"\begin{center}", self.tex)
        self.assertIn(r"$|$", self.tex)
        self.assertIn(r"margin=1.9cm", self.tex)
        self.assertIn(r"\pagestyle{empty}", self.tex)

    def test_all_sections_present(self):
        for section in ("Professional Summary", "Technical Skills",
                        "Experience", "Projects", "Education"):
            self.assertIn(r"\ressection{" + section + "}", self.tex)

    def test_full_length(self):
        for fact in BASE_RESUME["facts"]:
            text = fact["text"]
            if ": " in text and len(text.split(": ", 1)[0]) <= 40:
                # skill facts render as a bold label + remainder line
                label, rest = text.split(": ", 1)
                self.assertIn(escape_latex(label), self.tex)
                self.assertIn(escape_latex(rest), self.tex)
            else:
                self.assertIn(escape_latex(text), self.tex)

    def test_skill_label_gets_bold_prefix(self):
        self.assertIn(r"\textbf{Languages and tools:}", self.tex)

    def test_summary_text_present(self):
        self.assertIn(escape_latex(self.tailored["summary"]), self.tex)

    def test_user_content_escaped(self):
        profile = structure_user_resume(
            "Sam & Co Fan\nsam@example.com\n"
            "Cut report time by 50% using Python and SQL.\n"
            "Built a Flask API.\n"
            "B.Tech degree in Computer Science.\n")
        tailored = tailor_resume_for_job(profile, JOB["job-data-analyst-01"])
        tex = generate_tex(profile, tailored)
        self.assertIn(r"Sam \& Co Fan", tex)
        self.assertIn(r"50\%", tex)
        self.assertNotIn("Sam & Co Fan", tex)


if __name__ == '__main__':
    unittest.main()
