"""Read-only Greenhouse board starter. Employer tokens must be verified first."""
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

def fetch_greenhouse(board_token):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", board_token):
        raise ValueError("Use a verified employer board token, not a URL")
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "JarvisFresherPrototype/0.0.1"})
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    fetched_at = datetime.now(timezone.utc).isoformat()
    return [{"id": str(j["id"]), "title": j["title"],
             "location": j.get("location", {}).get("name", ""),
             "url": j["absolute_url"], "description": j.get("content", ""),
             "source": url, "fetched_at": fetched_at} for j in payload["jobs"]]
