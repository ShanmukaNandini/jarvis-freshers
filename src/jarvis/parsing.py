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


# --------------------------------------------------------------------------
# Resume-likeness check (deterministic heuristics, no ML)
# --------------------------------------------------------------------------
#
# The profiler turns whatever text it receives into "your facts", so feeding
# it a job posting would silently mix an employer's requirements into the
# user's profile. This check is a HONEST GATE, not a classifier: it counts
# resume-shaped signals (contact info, section headings, degrees, first-
# person action verbs) against job-posting-shaped ones ("Responsibilities",
# "What you'll do", "equal opportunity", second person) and reports both
# sides. The app warns on anything that does not clearly read as a resume
# and lets the user proceed explicitly - it never silently accepts or
# silently rejects.

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_DEGREE_RE = re.compile(
    r"\b(b\.?tech|b\.?e\.?|b\.?sc|m\.?tech|m\.?sc|mba|bachelor|master|"
    r"ph\.?d|diploma|cgpa|gpa)\b", re.IGNORECASE)
_HEADING_RE = re.compile(
    r"^\s*(education|academics?|experience|work experience|employment|skills?|"
    r"technical skills|projects?|summary|objective|certifications?|"
    r"achievements?|awards?|internships?|activities|publications?)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE)
_ACTION_RE = re.compile(
    r"\b(built|developed|designed|implemented|led|created|launched|improved|"
    r"analy[sz]ed|automated|deployed|engineered|mentored|won|published)\b",
    re.IGNORECASE)
_POSTING_PHRASES = [
    "job description", "responsibilities", "requirements", "qualifications",
    "what you'll do", "what you will do", "we're looking for",
    "we are looking for", "about the role", "about this role",
    "equal opportunity", "apply now", "you will", "you'll", "we are hiring",
    "we're hiring", "join our team", "join us", "compensation", "benefits",
    "employment type", "who we are", "our team", "the role", "perks",
]


def resume_likeness(text):
    """Score how resume-like a text is. Returns
    {"verdict": "resume" | "job_posting" | "unclear",
     "resume_score": int, "posting_score": int,
     "signals": [matched resume signals], "concerns": [matched posting phrases]}
    Never raises; short or empty text is simply "unclear"."""
    text = text or ""
    signals, concerns = [], []
    resume_score = 0
    if _EMAIL_RE.search(text):
        resume_score += 2
        signals.append("an email address")
    if _PHONE_RE.search(text):
        resume_score += 1
        signals.append("a phone number")
    headings = _HEADING_RE.findall(text)
    if headings:
        resume_score += min(len(headings), 3)
        signals.append("resume-style section headings ("
                       + ", ".join(sorted({h.strip().title() for h in headings})[:4])
                       + ")")
    if _DEGREE_RE.search(text):
        resume_score += 1
        signals.append("degree / education terms")
    actions = _ACTION_RE.findall(text)
    if actions:
        resume_score += min(len(actions), 3)
        signals.append("first-person achievement verbs (built, developed, ...)")

    lowered = text.lower()
    posting_hits = [phrase for phrase in _POSTING_PHRASES if phrase in lowered]
    posting_score = len(posting_hits)
    concerns = posting_hits

    if posting_score >= 3 and posting_score >= resume_score:
        verdict = "job_posting"
    elif resume_score >= 3 and resume_score > posting_score:
        verdict = "resume"
    elif posting_score >= 2:
        verdict = "job_posting"
    else:
        verdict = "unclear"
    return {"verdict": verdict, "resume_score": resume_score,
            "posting_score": posting_score, "signals": signals,
            "concerns": concerns}
