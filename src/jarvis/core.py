"""Dependency-free baselines. Not an LLM agent or a verified ATS scorer."""
import re
from datetime import datetime

def terms(text):
    return set(re.findall(r"[a-z0-9+#]+", text.lower()))

def rank_jobs(resume, interests, jobs):
    profile = terms(resume)
    interests = terms(" ".join(interests))
    ranked = []
    for job in jobs:
        target = terms(job["title"] + " " + job.get("description", ""))
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


# --- New: structured resume rewriting (truthful, provenance-backed) ---

def _split_sentences(text):
    """A minimal sentence splitter preserving original sentences. Not an NLTK replacement."""
    # split on periods, question marks, exclamation; keep abbreviations simple
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


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

    # Heuristics: group sentences mentioning education keywords, project keywords, or otherwise as Experience/Projects
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
            # heuristics: short comma-separated lists likely skills
            if len(s.split()) < 8 and (',' in s or len(s_terms & profile) > 0):
                skills.append((idx, s))
            else:
                others.append((idx, s))

    def claims_from(items):
        return [{"text": " ".join(i[1:].__class__.__name__ and [i[1]]), "provenance": [i[0]]} for i in items]

    # Build sections preserving order of sentences
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

    # Create an approval preview by concatenating claims in order
    preview_lines = []
    for sec in sections:
        preview_lines.append(sec['heading'])
        for c in sec['claims']:
            preview_lines.append(f"- {c['text']}  (source sentences: {c['provenance']})")
    approval_preview = "\n".join(preview_lines)

    return {"sentences": sentences, "sections": sections, "approval_preview": approval_preview}
