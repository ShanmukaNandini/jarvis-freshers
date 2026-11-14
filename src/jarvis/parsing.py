"""Defensive resume text extraction from uploaded files (.txt / .pdf / .docx).

Extraction is best-effort and honest: a corrupt or unreadable file raises
ResumeParseError with a friendly message, never a raw traceback for the UI.
"""
import io
import re


class ResumeParseError(ValueError):
    """Raised when an uploaded resume cannot be read. Message is user-safe."""


def _clean(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _from_pdf(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ResumeParseError(
            "PDF support is not installed on this deployment (missing pypdf). "
            "Please paste your resume as text instead.")
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError(
            "We couldn't read this PDF - it may be corrupt, password-protected, "
            "or a scanned image. Try a text-based PDF, a DOCX, or paste the text.")
    text = _clean("\n\n".join(pages))
    if len(text) < 20:
        raise ResumeParseError(
            "This PDF yielded almost no text - it is probably a scanned image. "
            "Please paste your resume text or upload a DOCX instead.")
    return text


def _from_docx(data):
    try:
        import docx
    except ImportError:
        raise ResumeParseError(
            "DOCX support is not installed on this deployment (missing python-docx). "
            "Please paste your resume as text instead.")
    try:
        document = docx.Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs if p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                parts.append(" ".join(cell.text.strip() for cell in row.cells
                                      if cell.text.strip()))
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError(
            "We couldn't read this DOCX - it may be corrupt or actually an older "
            ".doc file. Try re-exporting as .docx or PDF, or paste the text.")
    text = _clean("\n".join(parts))
    if len(text) < 20:
        raise ResumeParseError(
            "This DOCX yielded almost no text. Please paste your resume text instead.")
    return text


def extract_resume_text(filename, data):
    """Extract plain text from an uploaded resume file.

    filename: original upload name (extension decides the parser)
    data: raw bytes
    Returns cleaned plain text. Raises ResumeParseError with a friendly message.
    """
    name = (filename or "").strip().lower()
    if not data:
        raise ResumeParseError("That file is empty. Please upload a non-empty resume "
                               "or paste the text.")
    if name.endswith(".pdf"):
        return _from_pdf(data)
    if name.endswith(".doc"):
        raise ResumeParseError(
            "Old-style .doc files aren't supported. Please save it as .docx or PDF, "
            "or paste the text.")
    if name.endswith(".docx"):
        return _from_docx(data)
    if name.endswith(".txt") or name.endswith(".md") or "." not in name:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                text = data.decode(encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            raise ResumeParseError("We couldn't decode that text file. "
                                   "Please paste the text directly.")
        text = _clean(text)
        if len(text) < 20:
            raise ResumeParseError("That file has almost no text. "
                                   "Please paste your resume text instead.")
        return text
    raise ResumeParseError(
        f"Unsupported file type for '{filename}'. Please upload .txt, .pdf or .docx, "
        "or paste the text.")
