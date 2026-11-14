"""Dependency-free deterministic core for Jarvis for Freshers.

This module is NOT an LLM agent and NOT a verified ATS scorer. Every tailoring
decision is a transparent rule over facts that already exist in a resume;
nothing is invented, and every claim keeps its provenance.
"""
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Original public API (behaviour preserved)
# ---------------------------------------------------------------------------

def terms(text):
    return set(re.findall(r"[a-z0-9+#]+", text.lower()))

def rank_jobs(resume, interests, jobs):
    profile = terms(resume)
    interests = terms(" ".join(interests))
    ranked = []
    for job in jobs:
        target = terms(job["title"] + " " + job.get("description", "")
                       + " " + " ".join(job.get("requirements", {}).get("required", []))
                       + " " + " ".join(job.get("requirements", {}).get("preferred", [])))
        resume_hits = sorted(profile & target)
        interest_hits = sorted(interests & target)
        ranked.append({**job, "baseline_score": len(resume_hits) + 2*len(interest_hits),
                       "resume_hits": resume_hits, "interest_hits": interest_hits})
    return sorted(ranked, key=lambda j: j["baseline_score"], reverse=True)

def suggest_email_status(subject, body):
    """A suggestion only. Caller must resolve the application and review evidence."""
    text = (subject + " " + body).lower()
    phrases = {"interview": ["schedule an interview", "interview invitation"],
               "rejected": ["not moving forward", "regret to inform"],
               "received": ["application received", "thank you for applying"]}
    hits = [(status, phrase) for status, values in phrases.items() for phrase in values if phrase in text]
    statuses = {status for status, _ in hits}
    if len(statuses) != 1:
        return {"status": "needs_review", "evidence": [p for _, p in hits]}
    return {"status": hits[0][0], "evidence": [p for _, p in hits]}

def daily_digest(events, day):
    """Filter event timestamps by Asia/Kolkata day, supplied as YYYY-MM-DD."""
    from zoneinfo import ZoneInfo
    selected = [e for e in events if datetime.fromisoformat(e["occurred_at"]).astimezone(
        ZoneInfo("Asia/Kolkata")).date().isoformat() == day]
    if not selected:
        return f"{day}: No application updates recorded."
    lines = [f"{day}: {len(selected)} application update(s)"]
    for e in selected:
        action = " - check the original invitation for next steps" if e["status"] == "interview" else ""
        lines.append(f"- {e['company']} / {e['role']}: {e['status']}{action}")
    return "\n".join(lines)


# --- Structured resume rewriting (truthful, provenance-backed) ---

def _split_sentences(text):
    """A minimal sentence splitter preserving original sentences. Not an NLTK replacement.
    Does not break after single-letter initials (e.g. 'Sir M. Visvesvaraya')."""
    text = re.sub(r'\b([A-Z])\.\s+', lambda m: m.group(1) + '\x00 ', text.strip())
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.replace('\x00', '.').strip() for p in parts if p.strip()]


def extract_profile_terms(resume_text):
    """Return a set of normalized terms present in the resume_text."""
    return terms(resume_text)


def rewrite_resume_structured(resume_text, interests=None):
    """Produce a structured, ATS-friendly one-column resume rewrite grounded only in
    facts present in the supplied resume_text.

    Output format (dict):
      {"name":..., "sections": [{"heading":..., "claims": [{"text":..., "provenance": [sentence_idx,...]}]}],
       "approval_preview": "...plain text preview..."}

    Rules enforced:
    - Do not invent employers, dates, metrics or skills not present in the resume.
    - Claims are short rephrasings of source sentences; provenance is indexes into the
      sentence list returned by _split_sentences.
    - interests (optional) are highlighted in a small Interests section if provided.

    This is a deterministic, rule-based transformation. For richer natural rewrites
    integrate an LLM with a reviewer-in-the-loop and keep provenance checks.
    """
    sentences = _split_sentences(resume_text)
    profile = extract_profile_terms(resume_text)
    sections = []

    edu_kw = {'university','college','bachelor','master','phd','degree','education','graduat'}
    proj_kw = {'project','built','developed','created','implemented'}
    skills = []
    experiences = []
    education = []
    others = []

    for idx, s in enumerate(sentences):
        s_terms = terms(s)
        if s_terms & edu_kw:
            education.append((idx, s))
        elif s_terms & proj_kw:
            experiences.append((idx, s))
        else:
            if len(s.split()) < 8 and (',' in s or len(s_terms & profile) > 0):
                skills.append((idx, s))
            else:
                others.append((idx, s))

    if experiences:
        sections.append({"heading": "Experience / Projects",
                         "claims": [{"text": ex[1], "provenance": [ex[0]]} for ex in experiences]})
    if education:
        sections.append({"heading": "Education",
                         "claims": [{"text": ed[1], "provenance": [ed[0]]} for ed in education]})
    if skills:
        sections.append({"heading": "Skills",
                         "claims": [{"text": sk[1], "provenance": [sk[0]]} for sk in skills]})
    if others:
        sections.append({"heading": "Other",
                         "claims": [{"text": o[1], "provenance": [o[0]]} for o in others]})

    if interests:
        sections.insert(0, {"heading": "Interests", "claims": [{"text": i, "provenance": []} for i in interests]})

    preview_lines = []
    for sec in sections:
        preview_lines.append(sec['heading'])
        for c in sec['claims']:
            preview_lines.append(f"- {c['text']}  (source sentences: {c['provenance']})")
    approval_preview = "\n".join(preview_lines)

    return {"sentences": sentences, "sections": sections, "approval_preview": approval_preview}


# ---------------------------------------------------------------------------
# Skill vocabulary: canonical skills with surface forms
# ---------------------------------------------------------------------------
# Matching is deliberately conservative: a requirement is "supported" only when
# a resume fact actually evidences the same canonical skill. Surface forms are
# distinctive phrases (word-boundary matched), never single generic words.

SKILL_ALIASES = {
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite", "dbms"],
    "excel": ["excel", "spreadsheets", "openpyxl"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "machine-learning": ["machine learning", "scikit-learn", "sklearn"],
    "deep-learning": ["deep learning", "neural network", "neural networks",
                      "tensorflow", "pytorch", "keras", "cnn", "lstm"],
    "nlp": ["nlp", "natural language processing"],
    "statistics": ["statistics", "statistical", "probability"],
    "data-visualization": ["data visualization", "data visualisation", "matplotlib",
                           "seaborn", "power bi", "powerbi", "tableau", "dashboards",
                           "dashboard"],
    "rest-api": ["rest api", "rest apis", "restful", "flask", "fastapi", "django"],
    "docker": ["docker", "container", "containers", "containerization", "kubernetes", "k8s"],
    "git": ["git", "github", "version control"],
    "java": ["java"],
    "javascript": ["javascript", "react", "node.js", "nodejs", "typescript",
                   "html", "css", "html/css", "frontend"],
    "c-plus-plus": ["c++", "cpp"],
    "cloud": ["aws", "amazon web services", "azure", "gcp", "google cloud", "cloud"],
    "linux": ["linux", "bash", "shell", "unix"],
    "testing": ["pytest", "unit test", "unit tests", "unit testing", "selenium",
                "testing", "test coverage"],
    "etl": ["etl", "data pipeline", "data pipelines", "airflow"],
    "data-structures": ["data structures", "algorithms", "dsa", "problem solving"],
    "communication": ["communication", "presentation", "presenting", "presented",
                      "teamwork", "collaboration", "storytelling"],
    "ci-cd": ["ci/cd", "ci-cd", "github actions", "jenkins", "ci pipelines"],
}

_HEDGE_WORDS = ("familiarity", "familiar", "exposure", "basic", "basics", "plus",
                "nice-to-have", "nice to have", "preferred", "bonus")

_DEGREE_RE = re.compile(r"\b(bachelor|b\.?tech|b\.?e\.?|degree|master|m\.?tech|phd|mba|"
                        r"computer science|graduat)", re.IGNORECASE)


def canonical_skills(text):
    """Return the set of canonical skills evidenced by a piece of text."""
    lowered = text.lower()
    found = set()
    for canonical, surfaces in SKILL_ALIASES.items():
        for surface in surfaces:
            if re.search(r"(?<![a-z0-9+#])" + re.escape(surface) + r"(?![a-z0-9+#])", lowered):
                found.add(canonical)
                break
    return found


def _requirement_support(requirement, facts):
    """Fact IDs that evidence a job requirement. Deterministic and conservative."""
    req_canon = canonical_skills(requirement)
    supported = []
    for fact in facts:
        fact_skills = set(fact.get("skills", []))
        if req_canon and (req_canon & fact_skills):
            supported.append(fact["id"])
        elif _DEGREE_RE.search(requirement) and fact.get("section") == "education":
            supported.append(fact["id"])
    return supported


# ---------------------------------------------------------------------------
# User-resume structuring (structure-preserving, provenance-backed)
# ---------------------------------------------------------------------------

_KNOWN_HEADINGS = {
    "professional summary": "summary", "summary": "summary", "profile": "summary",
    "objective": "summary", "career objective": "summary",
    "technical skills": "skill", "skills": "skill", "technical competencies": "skill",
    "key skills": "skill", "core competencies": "skill",
    "experience": "experience", "work experience": "experience",
    "professional experience": "experience", "internships": "experience",
    "projects": "project", "personal projects": "project",
    "academic projects": "project", "key projects": "project",
    "education": "education", "education & training": "education",
    "academic background": "education", "academics": "education",
    "achievements": "other", "achievements & leadership": "other",
    "achievements and leadership": "other", "leadership": "other",
    "awards": "other", "certifications": "other", "certificates": "other",
    "activities": "other", "extracurricular": "other", "interests": "other",
}

_BULLET_RE = re.compile(r"^\s*[\u2022\u00b7\-\*\u25aa\u25e6]\s+")

# Tech vocabulary used to split a project title from a tech-stack tail that a
# PDF extractor glued onto the same line.
_TECH_TOKENS = {
    "python", "c", "c++", "sql", "mysql", "sqlite", "postgresql", "mongodb",
    "flask", "django", "fastapi", "react", "react.js", "vue", "angular",
    "node", "node.js", "javascript", "typescript", "html", "css",
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "keras",
    "pytorch", "opencv", "mediapipe", "power bi", "tableau", "excel",
    "postman", "docker", "kubernetes", "git", "github", "aws", "azure",
    "gcp", "langgraph", "langchain", "rag", "llm", "llms", "openai",
    "vector database", "firebase", "supabase", "streamlit", "selenium",
    "tensorflow lite", "rest api", "rest apis",
}


def _split_title_tech(title):
    """PDF extractors often glue a project's tech stack onto its title line
    ('... Dashboard Python, SQL, Pandas, Power BI, Excel'). Split the tail off
    when it is clearly a tech list; returns (title, tech) or (title, '')."""
    parts = [p.strip() for p in title.split(",")]
    for i in range(1, len(parts)):
        tail = [t.strip() for t in parts[i:]]
        hits = sum(1 for t in tail if t.lower() in _TECH_TOKENS)
        if hits < 2:
            continue
        head = [p.strip() for p in parts[:i]]
        # Move trailing tech tokens from the head onto the tail, including a
        # single tech word space-glued to the real title ('... System Python').
        while head:
            last = head[-1]
            if last.lower() in _TECH_TOKENS:
                tail.insert(0, head.pop())
                continue
            words = last.rsplit(" ", 1)
            if len(words) == 2 and words[1].lower().strip("()") in _TECH_TOKENS:
                tail.insert(0, words[1])
                head[-1] = words[0]
                continue
            break
        if head:
            return ", ".join(head).strip(), ", ".join(tail).strip()
    return title, ""
_DATEISH_RE = re.compile(r"\b((19|20)\d{2}|present|expected|jan|feb|mar|apr|may|jun|"
                         r"jul|aug|sep|oct|nov|dec)\b", re.IGNORECASE)
_SENT_END_RE = re.compile(r"[.!?]['\"\)]?$")
_OPEN_END_RE = re.compile(r"(,|;|&|\(|\band\b|\bof\b|\bwith\b|\bthe\b|\bfor\b|\bin\b|\bto\b|-)$",
                          re.IGNORECASE)


def _heading_section(line):
    """Return the internal section key if a raw line is a section heading,
    else None. Heading lines never become resume facts."""
    norm = re.sub(r"\s+", " ", line.strip().strip(":").lower())
    if norm in _KNOWN_HEADINGS:
        return _KNOWN_HEADINGS[norm]
    words = line.split()
    if (1 <= len(words) <= 5 and len(line) <= 45 and not line.endswith(".")
            and line == line.upper() and re.search(r"[A-Z]", line)
            and not re.search(r"@|\d{4}", line)):
        return "other"  # an all-caps heading we do not know: still never a fact
    return None


def _join_two(a, b):
    """Join a wrapped line onto its predecessor, repairing soft hyphens."""
    a = a.rstrip()
    if a.endswith("-") and not a.endswith(" -"):
        return a[:-1] + b.strip()
    return a + " " + b.strip()


def _logical_units(section, lines):
    """Rebuild the section's logical lines: bullets stay whole (wrapped
    continuation lines are joined back), wrapped list/tech lines are rejoined,
    and summary paragraphs are merged so sentence splitting only ever happens
    at real sentence boundaries."""
    units = []
    para = []

    def flush_para():
        if para:
            units.append({"kind": "para", "text": " ".join(para).strip()})
            para.clear()

    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if _BULLET_RE.match(ln):
            flush_para()
            units.append({"kind": "bullet", "text": _BULLET_RE.sub("", ln).strip()})
        elif section == "summary":
            para.append(ln)
        elif units and not para and (
                (units[-1]["kind"] == "bullet" and not _SENT_END_RE.search(units[-1]["text"]))
                or _OPEN_END_RE.search(units[-1]["text"])):
            units[-1]["text"] = _join_two(units[-1]["text"], ln)
        elif para:
            para.append(ln)
        else:
            units.append({"kind": "line", "text": ln})
    flush_para()
    return units


def _group_entries(section, units):
    """Group a section's logical units into entries (title, right-aligned
    location/dates, tech/subtitle line, bullets). Bullets always stay attached
    to the entry they were written under."""
    entries = []
    current = None
    for u in units:
        if u["kind"] == "bullet":
            if current is None:
                current = {"title": "", "subtitle": "", "right": "", "bullets": []}
                entries.append(current)
            current["bullets"].append(u["text"])
        else:
            text = u["text"]
            if current is None or current["bullets"]:
                current = {"title": text, "subtitle": "", "right": "", "bullets": []}
                entries.append(current)
            elif not current["subtitle"] and not current["right"]:
                if _DATEISH_RE.search(text):
                    current["right"] = text
                else:
                    current["subtitle"] = text
            elif current["subtitle"] and not current["right"] and _DATEISH_RE.search(text):
                current["right"] = text
            else:
                current = {"title": text, "subtitle": "", "right": "", "bullets": []}
                entries.append(current)
    return entries


def structure_user_resume(resume_text, name=None):
    """Turn a raw uploaded/pasted resume into the profile shape the tailoring
    code uses, PRESERVING the document's own structure instead of atomizing it.

    - Section headings are detected and never become facts.
    - Wrapped lines are rejoined (with soft-hyphen repair) BEFORE any sentence
      splitting, so no fact is ever a mid-sentence fragment.
    - Bullets stay whole and stay inside their section and their project/job
      entry; tailoring may select, order and trim, never re-mix sentences
      across sections.

    Returns BASE_RESUME-shaped fields plus "entries": grouped project/job
    structure the renderers use, and every fact keeps role + entry provenance.
    """
    raw_lines = [ln.strip() for ln in resume_text.splitlines()]

    email = None
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text)
    if m:
        email = m.group(0)
    phone = None
    m = re.search(r"(\+?\d[\d\s\-()]{7,14}\d)", resume_text)
    if m:
        phone = m.group(0).strip()

    # Split the document into a header block (before the first section
    # heading) and per-section line lists. The first non-empty line is the
    # name by resume convention - it always belongs to the header, even when
    # it is styled in all caps.
    header_lines, sections = [], []
    current = None
    seen_first = False
    for ln in raw_lines:
        if not ln:
            continue
        if not seen_first:
            header_lines.append(ln)
            seen_first = True
            continue
        sec = _heading_section(ln)
        if sec is not None:
            current = {"section": sec, "lines": []}
            sections.append(current)
        elif current is None:
            header_lines.append(ln)
        else:
            current["lines"].append(ln)

    if not sections:
        # No headings at all: fall back to flat sentence structuring.
        return _structure_flat(resume_text, name=name)

    # Contact metadata comes only from the header block, never from facts.
    location, links = "", []
    for ln in header_lines:
        if re.search(r"(linkedin|github|portfolio)", ln, re.I) and \
           not ((email and email in ln) or (phone and phone in ln) or "|" in ln):
            links.append(ln.strip())  # a wrapped line holding just a link
            continue
        if (email and email in ln) or (phone and phone in ln) or \
           ("|" in ln and re.search(r"\d{5,}", ln)):
            for part in ln.split("|"):
                part = part.strip()
                if not part or (email and email in part) or (phone and phone in part):
                    continue
                if re.search(r"(linkedin|github|portfolio|\.com|\.in|\.dev|\.io)", part, re.I):
                    links.append(part)
                elif not location and not re.search(r"\d{5,}", part):
                    location = part

    detected_name = name
    if not detected_name and header_lines:
        first = header_lines[0].strip()
        # The header's first line is the name by resume convention, even when
        # it is styled in all caps (heading detection does not apply here).
        if first and len(first.split()) <= 6 and "@" not in first and not first[0].isdigit():
            detected_name = first.title() if first.isupper() else first

    facts, entries, sentences = [], [], []
    entry_no = 0
    for sec in sections:
        section = sec["section"]
        units = _logical_units(section, sec["lines"])
        grouped = _group_entries(section, units) if section in ("experience", "project", "education") else []
        # Extraction artifact: a wrapped tech line can appear AFTER its own
        # continuation ('Python, OpenCV, ..., TensorFlow Lite,' / 'Flask,
        # SQLite' extracted in the wrong order). Reattach it to the previous
        # entry's tech line instead of inventing a new project.
        if section == "project":
            merged = []
            for entry in grouped:
                if (merged and entry["title"].rstrip().endswith(",")
                        and not entry["subtitle"] and not entry["right"]
                        and merged[-1]["subtitle"] and not merged[-1]["bullets"]):
                    merged[-1]["subtitle"] = _join_two(entry["title"],
                                                       merged[-1]["subtitle"])
                    merged[-1]["bullets"].extend(entry["bullets"])
                else:
                    merged.append(entry)
            grouped = merged
        for entry in grouped:
            if section == "project" and entry["title"] and not entry["subtitle"]:
                title, tech = _split_title_tech(entry["title"])
                entry["title"], entry["subtitle"] = title, tech
            # Extractors can glue the right-aligned location/dates onto the
            # title line ('... (BEL) Bangalore, India | Nov 2026 – Present').
            if entry["title"] and not entry["right"]:
                m = re.search(r"\|([^|]*\d{4}[^|]*)$", entry["title"])
                if m:
                    entry["right"] = m.group(1).strip()
                    entry["title"] = entry["title"][:m.start()].rstrip(" |").strip()
                else:
                    m2 = re.search(r"\s+(Expected\s+(?:19|20)\d{2})$", entry["title"])
                    if m2:
                        entry["right"] = m2.group(1)
                        entry["title"] = entry["title"][:m2.start()].strip()
        entry_of_bullet = {}
        for entry in grouped:
            entry_no += 1
            entry["id"] = f"E{entry_no}"
            entry["section"] = section
            for b in entry["bullets"]:
                entry_of_bullet[b] = entry["id"]
        for entry in grouped:
            entries.append({"id": entry["id"], "section": section,
                            "title": entry["title"], "subtitle": entry["subtitle"],
                            "right": entry["right"], "bullets": list(entry["bullets"])})
        for u in units:
            if u["kind"] == "para":
                for sent in _split_sentences(u["text"]):
                    sentences.append(sent)
                    facts.append({"id": f"U{len(facts) + 1:02d}", "section": section,
                                  "role": "summary", "entry": None, "text": sent,
                                  "skills": sorted(canonical_skills(sent)),
                                  "provenance": [len(sentences) - 1]})
            else:
                sentences.append(u["text"])
                if u["kind"] == "bullet":
                    role, entry_id = "bullet", entry_of_bullet.get(u["text"])
                elif section in ("experience", "project", "education"):
                    entry_id = None
                    for e in entries:
                        if e["section"] != section:
                            continue
                        if e["title"] == u["text"]:
                            role, entry_id = "title", e["id"]
                            break
                        if e["subtitle"] == u["text"]:
                            role, entry_id = "subtitle", e["id"]
                            break
                        if e["right"] == u["text"]:
                            role, entry_id = "right", e["id"]
                            break
                    else:
                        role = "line"
                else:
                    role, entry_id = "line", None
                facts.append({"id": f"U{len(facts) + 1:02d}", "section": section,
                              "role": role, "entry": entry_id, "text": u["text"],
                              "skills": sorted(canonical_skills(u["text"])),
                              "provenance": [len(sentences) - 1]})

    if not facts:
        raise ValueError("Could not find any resume content in the provided text.")

    return {"source": "user",
            "name": detected_name or "Candidate (from uploaded resume)",
            "email": email or "", "phone": phone or "", "location": location,
            "links": links,
            "sentences": sentences,
            "facts": facts,
            "entries": entries}


def _structure_flat(resume_text, name=None):
    """Fallback for resumes with no detectable section headings: the original
    flat sentence structuring, keyword-assigned sections, no entries."""
    raw_lines = [ln.strip() for ln in resume_text.splitlines()]
    units = []
    for ln in raw_lines:
        ln = re.sub(r"^[\u2022\-\*\u00b7\>\d\.\)\s]+", "", ln).strip()
        if not ln:
            continue
        for sent in _split_sentences(ln):
            units.append(sent)

    email = None
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text)
    if m:
        email = m.group(0)
    phone = None
    m = re.search(r"(\+?\d[\d\s\-()]{7,14}\d)", resume_text)
    if m:
        phone = m.group(0).strip()

    location = ""
    links = []
    for ln in raw_lines[:4]:
        if (email and email in ln) or (phone and phone in ln) or \
           ("|" in ln and re.search(r"\d{5,}", ln)):
            for part in ln.split("|"):
                part = part.strip()
                if not part:
                    continue
                if email and email in part:
                    continue
                if phone and phone in part:
                    continue
                if re.search(r"(linkedin|github|portfolio|\.com|\.in|\.dev|\.io)", part, re.I):
                    links.append(part)
                elif not location and not re.search(r"\d{5,}", part):
                    location = part

    edu_kw = {'university', 'college', 'bachelor', 'master', 'phd', 'degree',
              'education', 'b.tech', 'btech', 'school', 'cgpa'}
    achieve_kw = {'prize', 'award', 'hackathon', 'scholarship', 'winner',
                  'achievement', 'medal', 'certificate', 'certification'}
    facts = []
    skipped_content = {email, phone}
    for idx, sent in enumerate(units):
        if sent in skipped_content:
            continue
        s_terms = terms(sent)
        if s_terms & achieve_kw:
            section = "other"
        elif s_terms & edu_kw:
            section = "education"
        elif canonical_skills(sent) and len(sent.split()) <= 25 and "," in sent:
            section = "skill"
        elif s_terms & {'intern', 'internship', 'engineer', 'developer', 'analyst',
                        'worked', 'led', 'organised', 'organized', 'volunteered'}:
            section = "experience"
        elif s_terms & {'project', 'built', 'developed', 'created', 'implemented',
                        'trained', 'deployed', 'automated'}:
            section = "project"
        else:
            section = "project" if canonical_skills(sent) else "other"
        facts.append({"id": f"U{idx + 1:02d}", "section": section, "role": "bullet",
                      "entry": None, "text": sent,
                      "skills": sorted(canonical_skills(sent)),
                      "provenance": [idx]})

    if not facts:
        raise ValueError("Could not find any resume content in the provided text.")

    detected_name = name
    if not detected_name and raw_lines:
        first = raw_lines[0].strip()
        if first and len(first.split()) <= 5 and "@" not in first and not first[0].isdigit():
            detected_name = first
    facts = [f for f in facts
             if f["text"] != detected_name
             and not (email and email in f["text"])
             and not (phone and phone in f["text"])]
    if not facts:
        raise ValueError("Could not find any resume content in the provided text.")
    return {"source": "user",
            "name": detected_name or "Candidate (from uploaded resume)",
            "email": email or "", "phone": phone or "", "location": location,
            "links": links,
            "sentences": units,
            "facts": facts,
            "entries": []}


def _display_skill(canonical):
    special = {"sql": "SQL", "nlp": "NLP", "etl": "ETL", "ci-cd": "CI/CD",
               "rest-api": "REST APIs", "c-plus-plus": "C++", "python": "Python",
               "java": "Java", "javascript": "JavaScript", "docker": "Docker",
               "git": "Git", "linux": "Linux", "excel": "Excel",
               "numpy": "NumPy", "cloud": "Cloud (AWS/Azure/GCP)"}
    return special.get(canonical, canonical.replace("-", " "))


def estimate_render_lines(profile, tailored, chars_per_line):
    """Rough rendered line count for one-page font-size decisions."""
    import math
    skill_lines = tailored.get("skill_lines", {})

    def fact_text(f):
        return skill_lines.get(f["id"], f["text"])

    total = 4.0  # name block + contact row
    total += 2.2  # summary section heading
    total += math.ceil(len(tailored["summary"]) / chars_per_line) + 0.5
    skill_facts = [f for f in profile["facts"] if f.get("section") == "skill"]
    if skill_facts:
        total += 2.2
        total += sum(math.ceil(len(fact_text(f)) / chars_per_line) + 0.25 for f in skill_facts)
    if profile.get("entries"):
        entries = tailored.get("entry_view") or profile["entries"]
        sections = {e["section"] for e in entries}
        total += 2.2 * len(sections)
        for e in entries:
            total += 1.3  # entry heading row
            if e.get("subtitle"):
                total += 1.0
            total += sum(math.ceil(len(b) / chars_per_line) + 0.25 for b in e["bullets"])
        other = [f for f in profile["facts"] if f.get("section") == "other"
                 and f.get("role") in ("bullet", "line")]
        if other:
            total += 2.2
            total += sum(math.ceil(len(f["text"]) / chars_per_line) + 0.25 for f in other)
    else:
        for sec in ("experience", "project", "education", "other"):
            facts = [f for f in profile["facts"] if f.get("section") == sec]
            if facts:
                total += 2.2
                total += sum(math.ceil(len(f["text"]) / chars_per_line) + 0.25 for f in facts)
    return total


def choose_font_size(profile, tailored):
    """11pt when the content fits one page, 10pt when it needs the room."""
    return 11 if estimate_render_lines(profile, tailored, 92) <= 50 else 10


# ---------------------------------------------------------------------------
# Visible tailoring helpers
# ---------------------------------------------------------------------------

def _job_skill_signals(job):
    """Canonical skills this job asks for: its requirement list (strong
    signal) plus its whole posting text (weak signal)."""
    reqs = job.get("requirements", {})
    req_text = " ".join(list(reqs.get("required", [])) + list(reqs.get("preferred", [])))
    posting_text = f"{job.get('title', '')} {job.get('description', '')}"
    return canonical_skills(req_text), canonical_skills(posting_text)


def _token_score(token, req_canon, posting_canon):
    canon = canonical_skills(token)
    return (2 if canon & req_canon else 0) + (1 if canon & posting_canon else 0)


def _split_skill_line(text):
    """Split a skill fact into (label, tokens) when it is a comma-separated
    list worth reordering ('Programming: Python, SQL, Git'). Returns
    (None, None) for anything else - prose skill lines are left untouched."""
    label, body = None, text.strip()
    if ": " in body and len(body.split(": ", 1)[0]) <= 40:
        label, body = body.split(": ", 1)
    tokens = [t.strip() for t in body.split(",")]
    tokens = [t for t in tokens if t]
    if len(tokens) < 3:
        return None, None
    return label, tokens


def _reorder_tokens(tokens, req_canon, posting_canon):
    order = sorted(range(len(tokens)),
                   key=lambda i: (-_token_score(tokens[i], req_canon, posting_canon), i))
    return [tokens[i] for i in order]


# ---------------------------------------------------------------------------
# Per-job tailoring (deterministic, truthful, provenance-backed)
# ---------------------------------------------------------------------------

# A zero-overlap project is left out of a tailored resume only when at least
# this many matching projects remain - the Projects section never gets thin.
MIN_VISIBLE_PROJECTS = 3


def tailor_resume_for_job(profile, job):
    """Tailor a structured profile (BASE_RESUME or structure_user_resume output)
    to one job fixture.

    Returns a dict with:
      job_id, job_title, company
      claims: one per profile fact: {"fact_id", "text", "section",
              "matched_requirements": [requirement, ...], "provenance": [...]}
      supported_requirements / missing_required / missing_preferred / clarify
      summary, markdown, plain_text: full-length rendered resume

    Tailoring selects and reorders the profile's own facts. It never invents
    skills, employers, dates or metrics, and it never adds an unmet requirement
    to the resume - unmet requirements are reported as skill gaps instead.
    """
    facts = profile["facts"]
    reqs = job.get("requirements", {})
    required = list(reqs.get("required", []))
    preferred = list(reqs.get("preferred", []))
    all_reqs = required + preferred

    support = {r: _requirement_support(r, facts) for r in all_reqs}

    claims = []
    for fact in facts:
        matched = [r for r in all_reqs if fact["id"] in support[r]]
        claims.append({"fact_id": fact["id"], "text": fact["text"],
                       "section": fact.get("section", "other"),
                       "matched_requirements": matched,
                       "provenance": fact.get("provenance", [])})

    supported = [r for r in all_reqs if support[r]]
    missing_required = [r for r in required if not support[r]]
    missing_preferred = [r for r in preferred if not support[r]]
    clarify = [r for r in supported
               if any(h in r.lower() for h in _HEDGE_WORDS)]

    matched_skills = sorted({s for fact in facts for s in fact.get("skills", [])
                             if any(r for r in all_reqs
                                    if s in canonical_skills(r) and fact["id"] in support[r])})
    summary = (f"Fresher applying to {job['title']} at {job.get('company', 'the company')} "
               f"with resume-backed evidence in "
               f"{', '.join(_display_skill(s) for s in matched_skills[:5]) if matched_skills else 'the areas below'}.")

    # Order entries within each section: best-matching projects/jobs first,
    # original document order kept on ties. Entries are never split or merged.
    matched_ids = {c["fact_id"] for c in claims if c["matched_requirements"]}
    entry_order = []
    entry_view = []
    left_out = []
    bullet_changes = []
    if profile.get("entries"):
        def entry_score(e):
            ids = {f["id"] for f in facts if f.get("entry") == e["id"]}
            return len(ids & matched_ids)
        for sec_key in ("experience", "project", "education"):
            group = [(i, e) for i, e in enumerate(profile["entries"])
                     if e["section"] == sec_key]
            group.sort(key=lambda t: (-entry_score(t[1]), t[0]))
            entry_order.extend(e["id"] for _, e in group)

    # --- Visible tailoring: reorder/select inside the user's own material ---
    # Everything below rearranges the user's own facts. Nothing is added,
    # removed within a fact, or reworded.
    req_canon, posting_canon = _job_skill_signals(job)

    # 1. Skills this job asks for move to the front of each skill line.
    #    Tokens are reordered only - never added, removed or reworded.
    skill_lines = {}
    skill_changes = []
    for fact in facts:
        if fact.get("section") != "skill" or fact.get("role") not in ("line", "bullet"):
            continue
        label, tokens = _split_skill_line(fact["text"])
        if not tokens:
            continue
        new_tokens = _reorder_tokens(tokens, req_canon, posting_canon)
        if new_tokens == tokens:
            continue
        new_text = ((label + ": ") if label else "") + ", ".join(new_tokens)
        skill_lines[fact["id"]] = new_text
        promoted = [t for t in new_tokens
                    if _token_score(t, req_canon, posting_canon) > 0
                    and new_tokens.index(t) < tokens.index(t)]
        skill_changes.append({"fact_id": fact["id"], "before": fact["text"],
                              "after": new_text, "promoted": promoted})

    # 2. Entries: matched bullets first inside each entry (bullets stay
    #    whole), and zero-overlap projects are left out when the section
    #    still shows at least MIN_VISIBLE_PROJECTS matching projects.
    if profile.get("entries"):
        by_id = {e["id"]: e for e in profile["entries"]}
        match_counts = {}
        for sec_key in ("experience", "project", "education"):
            ids_in_sec = [eid for eid in entry_order if by_id[eid]["section"] == sec_key]
            match_counts[sec_key] = (len(ids_in_sec),
                                     sum(1 for eid in ids_in_sec
                                         if entry_score(by_id[eid]) > 0))
        for eid in entry_order:
            entry = by_id[eid]
            sec_key = entry["section"]
            n_total, n_matched = match_counts[sec_key]
            if (sec_key == "project" and entry_score(entry) == 0
                    and n_matched >= MIN_VISIBLE_PROJECTS
                    and n_total > MIN_VISIBLE_PROJECTS):
                left_out.append({"id": eid, "section": sec_key,
                                 "title": entry["title"]})
                continue
            bullets = list(entry["bullets"])
            new_bullets = _reorder_tokens(bullets, req_canon, posting_canon)
            if new_bullets != bullets:
                bullet_changes.append({"entry_id": eid, "title": entry["title"]})
            entry_view.append({"id": eid, "section": sec_key,
                               "title": entry["title"],
                               "subtitle": entry.get("subtitle", ""),
                               "right": entry.get("right", ""),
                               "bullets": new_bullets})

    # 3. A plain-English record of everything tailoring changed, so the user
    #    can SEE that this resume is for THIS job.
    changes = [{"kind": "summary",
                "text": f"Summary points at this role: {job['title']} at "
                        f"{job.get('company', 'the company')}."}]
    for sc in skill_changes:
        shown = ", ".join(sc["promoted"][:6])
        changes.append({"kind": "skills",
                        "text": (f"Skills moved to the front: {shown} - this job asks for them."
                                 if shown else "Skill order adjusted for this job."),
                        "before": sc["before"], "after": sc["after"]})
    if profile.get("entries"):
        dropped_titles = {lo["title"] for lo in left_out}
        original_order = {}
        for e in profile["entries"]:
            original_order.setdefault(e["section"], []).append(e["title"])
        for sec_key in ("experience", "project"):
            before_titles = [t for t in original_order.get(sec_key, [])
                             if t not in dropped_titles]
            after_titles = [e["title"] for e in entry_view if e["section"] == sec_key]
            if before_titles and after_titles and before_titles != after_titles:
                changes.append({"kind": "order",
                                "text": f"{sec_key.title()}s reordered: "
                                        f"'{after_titles[0]}' now leads - it matches "
                                        f"this job best."})
        for lo in left_out:
            changes.append({"kind": "left_out",
                            "text": f"Left out for this job: '{lo['title']}' - no overlap "
                                    f"with its requirements. It stays in your base resume."})
        for bc in bullet_changes:
            changes.append({"kind": "bullets",
                            "text": f"Inside '{bc['title']}', the most relevant points "
                                    f"now come first."})

    result = {
        "job_id": job["id"], "job_title": job["title"],
        "company": job.get("company", ""),
        "claims": claims,
        "supported_requirements": supported,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
        "clarify": clarify,
        "summary": summary,
        "entry_order": entry_order,
        "skill_lines": skill_lines,
        "entry_view": entry_view,
        "left_out": left_out,
        "changes": changes,
    }
    result["markdown"] = render_resume_markdown(profile, result)
    result["plain_text"] = render_resume_plain(profile, result)
    return result


def _ordered_facts(profile, tailored, sections):
    """Profile facts in the given sections, job-matched facts first (reordering
    only - the facts themselves are unchanged)."""
    matched_ids = {c["fact_id"] for c in tailored["claims"] if c["matched_requirements"]}
    facts = [f for f in profile["facts"] if f.get("section") in sections]
    return sorted(facts, key=lambda f: (f["id"] not in matched_ids, f["id"]))


def loose_section_facts(profile, section):
    """Facts in an entry section that belong to no entry (mixed profiles,
    e.g. flat facts from a synthetic profile plus a user-added project).
    A title line whose dates were split off during parsing still starts with
    its entry's title - that IS the entry, not a loose fact."""
    titles = [e["title"] for e in profile.get("entries", [])
              if e["section"] == section and e.get("title")]
    out = []
    for f in profile["facts"]:
        if (f.get("section") != section or f.get("entry") is not None
                or f.get("role") not in ("bullet", "line")):
            continue
        if any(f["text"].startswith(t) for t in titles):
            continue
        out.append(f)
    return out


def _profile_skills(profile, tailored):
    matched_ids = {c["fact_id"] for c in tailored["claims"] if c["matched_requirements"]}
    matched, other = [], []
    for fact in profile["facts"]:
        for s in fact.get("skills", []):
            (matched if fact["id"] in matched_ids else other).append(s)
    seen, ordered = set(), []
    for s in matched + other:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _render_entry_lines_md(entry):
    lines = []
    head = f"**{entry['title']}**"
    if entry.get("right"):
        head += f" — {entry['right']}"
    lines.append(head)
    if entry.get("subtitle"):
        lines.append(f"*{entry['subtitle']}*")
    lines += [f"- {b}" for b in entry["bullets"]]
    return lines


def render_resume_markdown(profile, tailored):
    """Full-length tailored resume as Markdown. Only profile facts. When the
    profile has entries (uploaded resumes), the document structure is
    preserved: entries render whole, bullets stay under their own entry."""
    lines = [f"# {profile.get('name', 'Candidate')}", ""]
    contact = [x for x in (profile.get("email"), profile.get("phone"),
                           profile.get("location")) if x]
    if contact:
        lines += [" | ".join(contact), ""]
    lines += [f"## Summary", "", tailored["summary"], ""]
    skills = _profile_skills(profile, tailored)
    skill_facts = _ordered_facts(profile, tailored, {"skill"})
    skill_lines = tailored.get("skill_lines", {})
    if profile.get("entries"):
        if skills or skill_facts:
            lines += ["## Technical Skills", ""]
            lines += [skill_lines.get(f["id"], f["text"]) for f in skill_facts]
            lines.append("")
    elif skills or skill_facts:
        lines += ["## Skills", ""]
        if skills:
            lines += [", ".join(skills), ""]
        lines += [f"- {f['text']}" for f in skill_facts]
        lines.append("")
    if profile.get("entries"):
        by_id = {e["id"]: e for e in profile["entries"]}
        # The tailored view (reordered bullets, left-out projects) when the
        # tailoring run produced one; otherwise the plain entry order.
        view = tailored.get("entry_view") or \
            [by_id[eid] for eid in tailored.get("entry_order", []) if eid in by_id]
        headings = [("Experience", "experience"), ("Projects", "project"),
                    ("Education", "education")]
        for heading, sec_key in headings:
            group = [e for e in view if e["section"] == sec_key]
            # Facts in this section that belong to no entry (mixed profiles).
            loose = loose_section_facts(profile, sec_key)
            if not group and not loose:
                continue
            lines += [f"## {heading}", ""]
            for entry in group:
                lines += _render_entry_lines_md(entry)
                lines.append("")
            if loose:
                lines += [f"- {f['text']}" for f in loose]
                lines.append("")
        other = [f for f in profile["facts"] if f.get("section") == "other"
                 and f.get("role") in ("bullet", "line")]
        if other:
            lines += ["## Achievements & Leadership", ""]
            lines += [f"- {f['text']}" for f in other]
            lines.append("")
        return "\n".join(lines).strip() + "\n"
    exp = _ordered_facts(profile, tailored, {"experience", "project"})
    if exp:
        lines += ["## Experience & Projects", ""]
        lines += [f"- {f['text']}" for f in exp]
        lines.append("")
    edu = _ordered_facts(profile, tailored, {"education"})
    if edu:
        lines += ["## Education", ""]
        lines += [f"- {f['text']}" for f in edu]
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_resume_plain(profile, tailored):
    """Plain-text variant of the tailored resume (paste-friendly)."""
    md = render_resume_markdown(profile, tailored)
    md = re.sub(r"^#+\s*", "", md, flags=re.MULTILINE)
    return md


# ---------------------------------------------------------------------------
# Skill-gap learning suggestions (generic, no invented course links)
# ---------------------------------------------------------------------------

_SUGGESTIONS = {
    "docker": "Containerise one project you already built with Docker and write up the steps in its README.",
    "deep-learning": "Rebuild one of your existing ML projects with a small neural network so you can speak to the basics honestly.",
    "aws-cloud": "Deploy a small project to a free cloud tier and note the services you actually used.",
    "cloud": "Deploy a small project to a free cloud tier and note the services you actually used.",
    "ci-cd": "Add a GitHub Actions workflow that runs your tests on every push to one of your repos.",
    "testing": "Add pytest tests to one existing project and record the before/after coverage.",
    "javascript": "Build one small front-end page that calls an API you already wrote.",
    "java": "Solve a short problem set in Java and publish it, rather than claiming fluency.",
    "etl": "Turn one of your analysis notebooks into a scheduled, re-runnable pipeline script.",
    "nlp": "Do a small text-classification project on a public dataset and write up the results.",
    "linux": "Do your next project entirely from a Linux terminal and note the commands you relied on.",
    "data-visualization": "Turn one dataset you know well into three clear charts with a one-line takeaway each.",
    "excel": "Recreate one analysis you did in Python as an Excel workbook with formulas and a chart.",
    "statistics": "Write up the statistical reasoning behind one project metric you already report.",
}

def learning_suggestions(missing_requirements):
    """Practical project suggestions for missing requirements. Suggestions are
    generic and link-free: no invented course URLs."""
    out = []
    for req in missing_requirements:
        canon = canonical_skills(req)
        tip = next((_SUGGESTIONS[c] for c in sorted(canon) if c in _SUGGESTIONS),
                   f"Build a small, honest portfolio piece that demonstrates: {req} - "
                   f"and add it to your resume only once it is true.")
        out.append({"requirement": req, "suggestion": tip})
    return out


# ---------------------------------------------------------------------------
# User-authored additions (the "add something new to your profile" flow)
# ---------------------------------------------------------------------------
# The no-invention rule is preserved: the user adding a fact IS the user
# supplying a fact. Additions carry added_by="user" and empty provenance
# (they do not come from the uploaded document), and become tailoring
# material exactly like any other fact.

def _next_fact_id(profile):
    nums = [int(f["id"][1:]) for f in profile["facts"]
            if f["id"].startswith("U") and f["id"][1:].isdigit()]
    return f"U{(max(nums) if nums else 0) + 1:02d}"


def _next_entry_id(profile):
    nums = [int(e["id"][1:]) for e in profile.get("entries", [])
            if isinstance(e.get("id"), str) and e["id"].startswith("E")
            and e["id"][1:].isdigit()]
    return f"E{(max(nums) if nums else 0) + 1}"


def _user_fact(profile, section, role, text, entry=None):
    fact = {"id": _next_fact_id(profile), "section": section, "role": role,
            "entry": entry, "text": text.strip(),
            "skills": sorted(canonical_skills(text)),
            "provenance": [], "added_by": "user"}
    profile["facts"].append(fact)
    return fact


def add_user_skill(profile, skills_text):
    """Add user-authored skills as a new skill line ('Docker, Kubernetes' or
    'Cloud: AWS, GCP'). Eligible for the same per-job reordering as any other
    skill line."""
    text = (skills_text or "").strip().strip(",")
    if not text:
        raise ValueError("Type at least one skill first.")
    if ":" not in text:
        text = "Additional Skills: " + text
    return _user_fact(profile, "skill", "line", text)


def add_user_project(profile, title, tech="", bullets=None):
    """Add a user-authored project entry. Bullets stay whole under their own
    entry, exactly like projects parsed from an uploaded resume."""
    title = (title or "").strip()
    tech = (tech or "").strip()
    bullets = [b.strip() for b in (bullets or []) if b and b.strip()]
    if not title:
        raise ValueError("Give the project a title.")
    if not bullets:
        raise ValueError("Add at least one line about what you did.")
    entry_id = _next_entry_id(profile)
    entry = {"id": entry_id, "section": "project", "title": title,
             "subtitle": tech, "right": "", "bullets": bullets}
    profile.setdefault("entries", []).append(entry)
    _user_fact(profile, "project", "title", title, entry=entry_id)
    if tech:
        _user_fact(profile, "project", "subtitle", tech, entry=entry_id)
    for b in bullets:
        _user_fact(profile, "project", "bullet", b, entry=entry_id)
    return entry


def add_user_other(profile, text):
    """Add a user-authored certification / award / activity line."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Type the certification, award or activity first.")
    return _user_fact(profile, "other", "bullet", text)


def add_user_experience(profile, title, organization="", dates="", description=None):
    """Add a user-authored internship / work-experience entry. Renders into
    the Experience section and competes in per-job ordering exactly like a
    project or an experience entry parsed from an uploaded resume."""
    title = (title or "").strip()
    organization = (organization or "").strip()
    dates = (dates or "").strip()
    bullets = [b.strip() for b in (description or []) if b and b.strip()]
    if not title:
        raise ValueError("Give the role a title (e.g. 'Software Engineering Intern').")
    if not bullets:
        raise ValueError("Add at least one line about what you did.")
    entry_id = _next_entry_id(profile)
    entry = {"id": entry_id, "section": "experience", "title": title,
             "subtitle": organization, "right": dates, "bullets": bullets}
    profile.setdefault("entries", []).append(entry)
    _user_fact(profile, "experience", "title", title, entry=entry_id)
    if organization:
        _user_fact(profile, "experience", "subtitle", organization, entry=entry_id)
    if dates:
        _user_fact(profile, "experience", "right", dates, entry=entry_id)
    for b in bullets:
        _user_fact(profile, "experience", "bullet", b, entry=entry_id)
    return entry
