import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from jarvis.parsing import extract_resume_text, ResumeParseError


def _make_minimal_pdf(text):
    """Build a tiny one-page PDF in memory with correct xref offsets."""
    objects = []

    def obj(body):
        objects.append(body)

    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    obj("<< /Type /Catalog /Pages 2 0 R >>")
    obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    obj(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1"))
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
              f"startxref\n{xref_pos}\n%%EOF".encode("latin-1"))
    return out.getvalue()


class TxtParsingTests(unittest.TestCase):
    def test_txt_roundtrip(self):
        text = extract_resume_text("resume.txt", b"Priya Verma\nPython and SQL developer\n")
        self.assertIn("Priya Verma", text)

    def test_empty_file_rejected(self):
        with self.assertRaises(ResumeParseError):
            extract_resume_text("resume.txt", b"")

    def test_unsupported_extension_rejected(self):
        with self.assertRaises(ResumeParseError):
            extract_resume_text("resume.exe", b"MZ" + b"x" * 100)

    def test_legacy_doc_rejected_with_friendly_message(self):
        with self.assertRaises(ResumeParseError) as ctx:
            extract_resume_text("resume.doc", b"\xd0\xcf\x11\xe0" + b"x" * 200)
        self.assertIn(".docx", str(ctx.exception))


class DocxParsingTests(unittest.TestCase):
    def test_docx_roundtrip(self):
        import docx
        buf = io.BytesIO()
        doc = docx.Document()
        doc.add_paragraph("Priya Verma")
        doc.add_paragraph("Built Flask APIs in Python and analysed data with SQL.")
        doc.save(buf)
        text = extract_resume_text("resume.docx", buf.getvalue())
        self.assertIn("Priya Verma", text)
        self.assertIn("Flask", text)

    def test_corrupt_docx_friendly_error(self):
        with self.assertRaises(ResumeParseError):
            extract_resume_text("resume.docx", b"this is not a zip file at all" * 10)


class PdfParsingTests(unittest.TestCase):
    def test_pdf_roundtrip(self):
        pdf = _make_minimal_pdf("Python SQL pandas resume text here")
        text = extract_resume_text("resume.pdf", pdf)
        self.assertIn("Python", text)

    def test_corrupt_pdf_friendly_error(self):
        with self.assertRaises(ResumeParseError) as ctx:
            extract_resume_text("resume.pdf", b"%PDF-1.4 garbage garbage garbage")
        self.assertIn("couldn't read", str(ctx.exception).lower())


if __name__ == '__main__':
    unittest.main()
