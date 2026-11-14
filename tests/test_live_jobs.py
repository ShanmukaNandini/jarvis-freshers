"""Live-jobs adapter tests: normalization, tiering, aggregation, failure fallback."""
import io
import json
import unittest
from unittest import mock

from jarvis import jobs


def _board_payload(rows):
    return json.dumps({"jobs": rows}).encode()


def _row(job_id, title, location, content=""):
    return {"id": job_id, "title": title,
            "location": {"name": location},
            "absolute_url": f"https://boards.greenhouse.io/acme/jobs/{job_id}",
            "content": content}


class HostileContentTests(unittest.TestCase):
    """Regression: a live posting whose content broke the swipe card with
    React error #137 (double-encoded markup reintroduced as literal tags)."""

    def test_double_encoded_board_content_leaves_no_tags(self):
        # exactly how the MongoDB Dublin posting arrives: every tag encoded
        raw = ("&lt;p&gt;Build things.&lt;br&gt;Ship them.&lt;/p&gt;"
               "&lt;p&gt;Work with Python.&lt;/p&gt;")
        text = jobs._strip_html(raw)
        self.assertNotIn("<", text)
        self.assertNotIn("&lt;", text)
        self.assertIn("Build things.", text)
        self.assertIn("Ship them.", text)

    def test_strip_handles_mixed_and_triple_encoding(self):
        self.assertNotIn("<", jobs._strip_html("<p>plain <b>bold</b></p>"))
        self.assertNotIn("<", jobs._strip_html("&amp;lt;br&amp;gt;triple"))
        self.assertNotIn("<", jobs._strip_html("no markup at all"))

    def test_safe_html_neutralizes_anything(self):
        hostile = '<br><script>alert(1)</script>&"**md** {invariant: 137} <br/>'
        out = jobs.safe_html(hostile)
        self.assertNotIn("<br", out)
        self.assertNotIn("<script", out)
        self.assertIn("&lt;br&gt;", out)
        self.assertIn("{invariant: 137}", out)  # braces pass through as text

    def test_normalization_of_hostile_posting_yields_card_safe_fields(self):
        raw = _row(5, 'Intern <b>&quot;Core&quot;</b> &amp; Ops', 'Dublin',
                   '&lt;p&gt;Do &lt;b&gt;real&lt;/b&gt; work.&lt;br&gt;Python {x}.&lt;/p&gt;')
        with mock.patch("jarvis.jobs.urlopen",
                        return_value=io.BytesIO(_board_payload([raw]))):
            job = jobs.fetch_board_jobs("acme", "Acme")[0]
        self.assertNotIn("<", job["description"])
        for field in (job["title"], job["company"], job["location"],
                      job["description"]):
            escaped = jobs.safe_html(field)
            self.assertNotRegex(escaped, r"<[a-zA-Z/]")


class LiveJobsTests(unittest.TestCase):
    def test_normalization_extracts_skills_and_strips_html(self):
        raw = _row(7, "Software Engineer, Intern", "Bengaluru",
                   "<p>We use <b>Python</b> and SQL daily; Docker a plus.</p>")
        with mock.patch("jarvis.jobs.urlopen",
                        return_value=io.BytesIO(_board_payload([raw]))):
            result = jobs.fetch_board_jobs("acme", "Acme")
        self.assertEqual(len(result), 1)
        job = result[0]
        self.assertEqual(job["id"], "gh-acme-7")
        self.assertEqual(job["source"], "live")
        self.assertEqual(job["company"], "Acme")
        self.assertNotIn("<", job["description"])
        self.assertIn("Python", job["requirements"]["required"])
        self.assertIn("SQL", job["requirements"]["required"])
        self.assertEqual(job["requirements"]["preferred"], [])

    def test_rejects_non_slug_board_tokens(self):
        with self.assertRaises(ValueError):
            jobs.fetch_board_jobs("https://evil.example/x", "Evil")

    def test_select_fresher_jobs_orders_by_tier(self):
        rows = [
            _row(1, "Senior Staff Engineer", "Bengaluru"),
            _row(2, "Software Engineer, Intern", "Bengaluru"),
            _row(3, "Marketing Intern", "Paris, France"),
            _row(4, "Backend Engineer", "Remote, United States"),
            _row(5, "Director of Platform", "New York"),
        ]
        with mock.patch("jarvis.jobs.urlopen",
                        return_value=io.BytesIO(_board_payload(rows))):
            fetched = jobs.fetch_board_jobs("acme", "Acme")
        picked = jobs.select_fresher_jobs(fetched, limit=10)
        ids = [j["id"] for j in picked]
        # tier 1 first, then tier 2, then tier 3 (alphabetical within tier); tier 4 dropped
        self.assertEqual(ids, ["gh-acme-2", "gh-acme-3", "gh-acme-4", "gh-acme-1"])

    def test_fetch_live_jobs_aggregates_and_survives_board_failure(self):
        def fake_urlopen(request, timeout=None):
            if "mongodb" in request.full_url:
                raise OSError("simulated network failure")
            return io.BytesIO(_board_payload(
                [_row(9, "Software Engineer, Intern", "Bengaluru", "Python")]))
        boards = [("stripe", "Stripe"), ("mongodb", "MongoDB")]
        with mock.patch("jarvis.jobs.urlopen", side_effect=fake_urlopen):
            result = jobs.fetch_live_jobs(boards=boards)
        self.assertEqual(result["boards_ok"], ["Stripe"])
        self.assertEqual(result["boards_failed"], ["MongoDB"])
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["jobs"][0]["company"], "Stripe")

    def test_fetch_live_jobs_all_boards_fail_returns_empty(self):
        with mock.patch("jarvis.jobs.urlopen", side_effect=TimeoutError("down")):
            result = jobs.fetch_live_jobs(boards=[("stripe", "Stripe"), ("gitlab", "GitLab")])
        self.assertEqual(result["jobs"], [])
        self.assertEqual(result["boards_ok"], [])
        self.assertEqual(sorted(result["boards_failed"]), ["GitLab", "Stripe"])

    def test_word_boundary_matching_avoids_false_fresher_hits(self):
        # "Internal Systems" must not match the intern keyword
        rows = [_row(1, "Engineering Manager, Internal Systems", "Remote, Canada")]
        with mock.patch("jarvis.jobs.urlopen",
                        return_value=io.BytesIO(_board_payload(rows))):
            fetched = jobs.fetch_board_jobs("acme", "Acme")
        picked = jobs.select_fresher_jobs(fetched)
        self.assertEqual([j["id"] for j in picked], ["gh-acme-1"])  # tier 3 via remote

    def test_legacy_fetch_greenhouse_keeps_token_guard(self):
        with self.assertRaises(ValueError):
            jobs.fetch_greenhouse("https://boards.greenhouse.io/stripe")


if __name__ == "__main__":
    unittest.main()
