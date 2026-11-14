"""PDF renderer tests: valid PDF bytes, one page, both profile kinds."""
import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from pypdf import PdfReader

from jarvis.core import structure_user_resume, tailor_resume_for_job
from jarvis.fixtures import BASE_RESUME, JOB_FIXTURES
from jarvis.pdf_resume import generate_pdf
from tests.test_uploaded_resume import HER_RESUME


class PdfResumeTests(unittest.TestCase):
    def _check(self, profile):
        tailored = tailor_resume_for_job(profile, JOB_FIXTURES[0])
        pdf = generate_pdf(profile, tailored)
        self.assertTrue(pdf.startswith(b"%PDF"), "not a PDF byte stream")
        self.assertGreater(len(pdf), 5000, "PDF suspiciously small (fonts missing?)")
        reader = PdfReader(io.BytesIO(pdf))
        self.assertEqual(len(reader.pages), 1, "tailored resume must be one page")
        text = reader.pages[0].extract_text()
        self.assertIn(profile["name"].split()[0].upper(),
                      text.upper().replace(" ", ""), "name missing from PDF")
        return text

    def test_her_uploaded_resume_pdf_one_page(self):
        text = self._check(structure_user_resume(HER_RESUME))
        # all four projects made it into the rendered page
        for title in ("Drowsiness", "Sentiment", "Market Intelligence", "Scheme"):
            self.assertIn(title, text)

    def test_synthetic_profile_pdf_one_page(self):
        self._check(BASE_RESUME)


if __name__ == "__main__":
    unittest.main()
