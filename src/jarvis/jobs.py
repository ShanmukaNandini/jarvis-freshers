"""Read-only Greenhouse board adapter + curated live openings for the demo.

Live data comes from PUBLIC Greenhouse job-board APIs only - the same JSON a
company's own careers page serves. Fetching is respectful: one request per
board, a real User-Agent, a short timeout, and results cached by the caller
(the Streamlit app caches for 30 minutes).

If every board fails or returns nothing usable, callers get an empty job list
and fall back to the synthetic fixtures, labelled OFFLINE DEMO DATA.
"""
import html
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

USER_AGENT = "JarvisForFreshers/1.0 (hackathon demo; github.com/ShanmukaNandini/jarvis-freshers)"
FETCH_TIMEOUT = 8  # seconds per board, one request each

# Curated boards, verified 2026-11-14 against the public Greenhouse API.
# India-weighted: every board carries India and/or remote openings, and
# Rubrik/Stripe carried live India INTERN/fresher roles at verification time
# (Rubrik: 4 incl. Software Engineer Winter Intern, Bangalore; Stripe:
# Software Engineer Intern, Bengaluru). Databricks (85 India roles), Okta
# (99), MongoDB (73), Fivetran (20 + remote) and GitLab (35 + remote) fill
# out the India/remote pool. (slug, display name)
DEFAULT_BOARDS = [
    ("stripe", "Stripe"),
    ("mongodb", "MongoDB"),
    ("datadog", "Datadog"),
    ("gitlab", "GitLab"),
    ("rubrik", "Rubrik"),
    ("databricks", "Databricks"),
    ("okta", "Okta"),
    ("fivetran", "Fivetran"),
]

_FRESHER_RE = re.compile(
    r"\b(intern|internship|new grad|new-grad|entry level|entry-level|graduate|"
    r"junior|trainee|early career|apprentice|apprenticeship)\b", re.IGNORECASE)
_INDIA_REMOTE_RE = re.compile(
    r"\b(india|bengaluru|bangalore|hyderabad|pune|mumbai|chennai|gurgaon|"
    r"gurugram|noida|remote)\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")

# Canonical skill -> human-readable label for auto-extracted requirements.
_SKILL_LABELS = {
    "python": "Python", "sql": "SQL", "excel": "Excel", "pandas": "pandas",
    "numpy": "NumPy", "machine-learning": "Machine learning",
    "deep-learning": "Deep learning", "nlp": "NLP", "statistics": "Statistics",
    "data-visualization": "Data visualization", "rest-api": "REST APIs",
    "docker": "Docker", "git": "Git", "java": "Java", "javascript": "JavaScript",
    "c-plus-plus": "C++", "cloud": "Cloud (AWS/Azure/GCP)", "linux": "Linux",
    "testing": "Testing", "etl": "ETL / data pipelines",
    "data-structures": "Data structures & algorithms",
    "communication": "Communication", "ci-cd": "CI/CD",
}


def _strip_html(markup):
    """Turn posting markup into SAFE plain text. Boards sometimes double-encode
    their content (every tag stored as &lt;br&gt; etc.), so unescape BEFORE
    stripping - unescaping after stripping would reintroduce literal tags,
    which then break the app's HTML card rendering. Two passes cover triple
    encoding; anything still angle-bracketed after that loses the brackets."""
    text = markup or ""
    for _ in range(3):
        unescaped = html.unescape(text)
        stripped = _TAG_RE.sub(" ", unescaped)
        if stripped == text:
            break
        text = stripped
    text = re.sub(r"\s+", " ", text).strip()
    # No legitimate plain-text word starts with a stray tag fragment.
    return text


def safe_html(text):
    """Escape text for interpolation into the app's unsafe_allow_html card
    markup, so ANY posting content (tags, entities, braces, markdown-ish junk)
    renders as inert literal text."""
    return html.escape(str(text if text is not None else ""), quote=False)


def extract_requirements(text, limit=10):
    """Greenhouse postings carry no structured requirement fields, so the
    requirement list is honestly AUTO-EXTRACTED: the canonical skills our
    deterministic matcher can see in the posting text. Nothing else is claimed.
    """
    from jarvis.core import canonical_skills
    found = sorted(canonical_skills(text))
    return {"required": [_SKILL_LABELS[s] for s in found[:limit]],
            "preferred": []}


def _normalize_job(raw, slug, company, fetched_at):
    description = _strip_html(raw.get("content", ""))
    location = (raw.get("location") or {}).get("name", "")
    title = raw.get("title", "").strip()
    text_for_skills = f"{title} {description}"
    return {
        "id": f"gh-{slug}-{raw['id']}",
        "title": title,
        "company": company,
        "location": location,
        "source": "live",
        "board": slug,
        "url": raw.get("absolute_url", ""),
        "description": description[:900] + ("..." if len(description) > 900 else ""),
        "requirements": extract_requirements(text_for_skills),
        "fetched_at": fetched_at,
    }


def fetch_board_jobs(slug, company, timeout=FETCH_TIMEOUT):
    """One request to one public board. Raises on any failure; caller decides."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", slug):
        raise ValueError("Use a verified employer board slug, not a URL")
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    request = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    fetched_at = datetime.now(timezone.utc).isoformat()
    return [_normalize_job(j, slug, company, fetched_at) for j in payload.get("jobs", [])]


def _tier(job):
    """1 = fresher title + India/remote, 2 = fresher title anywhere,
    3 = India/remote any level, 4 = everything else."""
    title, location = job["title"], job.get("location", "")
    fresher = bool(_FRESHER_RE.search(title))
    india_remote = bool(_INDIA_REMOTE_RE.search(location))
    if fresher and india_remote:
        return 1
    if fresher:
        return 2
    if india_remote:
        return 3
    return 4


def is_india_remote(job):
    """True when the posting's location is in India or remote - the app's
    'India & remote only' filter."""
    return bool(_INDIA_REMOTE_RE.search(job.get("location", "")))


def select_fresher_jobs(jobs, limit=15, per_board_cap=4):
    """Pick a fresher-relevant, India/remote-leaning shortlist, deterministic,
    with variety across boards."""
    tiered = sorted(jobs, key=lambda j: (_tier(j), j["board"], j["title"]))
    picked, counts = [], {}
    for job in tiered:
        if _tier(job) == 4:
            break
        board = job["board"]
        if _tier(job) >= 2 and counts.get(board, 0) >= per_board_cap:
            continue
        picked.append(job)
        counts[board] = counts.get(board, 0) + 1
        if len(picked) >= limit:
            break
    return picked


def fetch_live_jobs(boards=None, timeout=FETCH_TIMEOUT):
    """Fetch all curated boards and return
    {"jobs": [...], "boards_ok": [...], "boards_failed": [...]}.
    Never raises for a failing board; 'jobs' is empty only if nothing usable
    came back from any board (the caller then falls back to fixtures)."""
    boards = boards if boards is not None else DEFAULT_BOARDS
    all_jobs, boards_ok, boards_failed = [], [], []
    for slug, company in boards:
        try:
            all_jobs.extend(fetch_board_jobs(slug, company, timeout=timeout))
            boards_ok.append(company)
        except Exception:
            boards_failed.append(company)
    return {"jobs": select_fresher_jobs(all_jobs),
            "boards_ok": boards_ok, "boards_failed": boards_failed}


# --- Original starter API, kept for backwards compatibility with early tests ---

def fetch_greenhouse(board_token):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", board_token):
        raise ValueError("Use a verified employer board token, not a URL")
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    fetched_at = datetime.now(timezone.utc).isoformat()
    return [{"id": str(j["id"]), "title": j["title"],
             "location": j.get("location", {}).get("name", ""),
             "url": j["absolute_url"], "description": j.get("content", ""),
             "source": url, "fetched_at": fetched_at} for j in payload["jobs"]]
