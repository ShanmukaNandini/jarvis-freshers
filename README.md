# Jarvis for Freshers

A truthful job-hunt copilot for fresh graduates, built for the **Code for a
Billion** hackathon (impact area: **Tech Employment for Youth**).

**Live demo:** https://jarvis-freshers-jdmeuquh5w8b7dnfzmb9uf.streamlit.app

Jarvis helps a fresher:

1. **Match** - rank openings against their resume and interests. Openings are
   **live by default**, fetched read-only from public Greenhouse career boards
   (Stripe, MongoDB, Datadog, GitLab, Rubrik, Databricks, Okta, Fivetran -
   one polite request per board, cached 30 minutes) and filtered for
   fresher-relevant, India/remote-leaning roles, with an **India & remote
   only** toggle. If every board is unreachable the app falls back to
   built-in synthetic fixtures clearly labelled **OFFLINE DEMO DATA**.
   Browse in **Swipe** mode (one card at a time: Skip or Save & tailor) or
   **List** mode.
2. **Tailor** - produce a one-page, job-specific resume built **only from facts
   already in the candidate's resume**, with per-claim provenance - and
   **visible**: a "What changed for this job" panel lists every adjustment
   (summary pointed at the role, skills reordered to put what this job asks
   for first, projects reordered, off-target projects left out, bullets
   reordered inside projects). Uploaded resumes keep their own structure:
   sections, projects and bullets are preserved whole - tailoring reorders
   and selects, but never splits or re-mixes sentences across sections.
   Export as a **finished one-page PDF** (generated in pure Python with the
   bundled OFL Latin Modern fonts - no Overleaf step), Markdown, plain text,
   or **LaTeX source**.
3. **Grow the profile** - an "Add something new" section lets the candidate
   add skills, projects and certifications to their own profile; user-added
   facts follow the same truthfulness rules and become tailoring material.
4. **See skill gaps** - required/preferred skills the resume does not yet
   evidence, plus practical project suggestions to close them honestly.
5. **Track applications** - a local tracker whose statuses change only from
   reviewed evidence (a synthetic inbox fixture set powers the demo), with an
   end-of-day digest preview in Asia/Kolkata.

## Hard boundaries

- **No auto-apply, ever.** Jarvis prepares; the user reviews and hits send.
- **Nothing invented.** Tailoring reorders and selects the resume's own facts.
  Unmet requirements are reported as skill gaps, never added as skills.
- **Interests steer matching and learning tips; they never count as evidence
  of a skill.**

## Run it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then either upload a resume (.txt / .pdf / .docx), paste text, or explore with
the synthetic demo profile.

## Tests

```bash
python -m unittest discover -s tests -v
```

Current suite: 87 tests covering ranking, email-status suggestion, digest
timezones, fixture integrity, deterministic tailoring (synthetic + uploaded
resumes), visible tailoring (skill-line reordering, project selection and
left-out rules, bullet reordering, per-job change summaries), user-authored
profile additions (skills, projects, internships/experience,
certifications), concurrent-writer database hardening, India/remote filtering, structure-preserving
uploaded-resume parsing (no heading leaks, no mid-sentence fragments, correct
section membership, all projects whole), file parsing, LaTeX
generation/escaping, one-page PDF generation, live-board normalization,
hostile posting sanitization (double-encoded HTML), fresher tiering and
fetch-failure fallback (network fully mocked), and idempotent, guard-railed
inbox processing.

## Compile the LaTeX resume (optional - the app also gives you a finished PDF)

1. The **Download PDF** button gives you a finished one-page PDF straight from
   the app, rendered in pure Python (fpdf2) with the bundled OFL-licensed
   Latin Modern Roman fonts - the same template as the .tex output.
2. Prefer Overleaf? Download the `.tex` file, go to
   [Overleaf](https://www.overleaf.com) (free) → **New Project** →
   **Blank Project** → paste → **Recompile**.
3. The app never compiles LaTeX server-side - there is no LaTeX toolchain on
   Streamlit Cloud; PDF generation needs none.

## Live job data (and the offline fallback)

- Live openings come from the **public Greenhouse board API** - the same JSON
  each company's own careers page serves. No keys, no scraping of logged-in
  pages, no applications submitted.
- Fetching is respectful: **one request per board**, a real User-Agent, an
  8-second timeout, and a **30-minute cache** in the app (the Refresh button
  clears it).
- Postings carry no structured skill fields, so each live job's requirement
  list is **auto-extracted**: the canonical skills our deterministic matcher
  can see in the posting text. Honest hints, never the employer's claims.
- If all boards fail or return nothing usable, the UI switches to the
  synthetic fixtures with a clear **OFFLINE DEMO DATA** label; live postings
  are labelled **LIVE**.

## Honest limitations (public demo)

- **Openings are live from public boards; requirement lists on them are
  auto-extracted keywords** and can be incomplete - always read the real
  posting. **Emails and the demo candidate remain synthetic.**
- **Tailoring is deterministic** (transparent rules, no LLM) and is **not an
  ATS score** or any promise of recruiter outcomes.
- **The inbox is a fixed fixture set.** Ambiguous, out-of-order, or
  terminal-state-conflicting messages are *held for human review*, by design.
  Real Gmail integration would require OAuth consent, restricted-scope
  verification, and private storage - none of which is claimed here.
- **The tracker database (`jarvis_demo.db`) is temporary** and resets when the
  cloud app restarts.

## Project layout

```
streamlit_app.py        the demo UI (Streamlit, scoped CSS only)
src/jarvis/core.py      ranking, status suggestion, digest, truthful tailoring
src/jarvis/fixtures.py  synthetic profile, 9 job openings, inbox fixtures
src/jarvis/store.py     SQLite tracker + guarded synthetic inbox processing
src/jarvis/parsing.py   .txt/.pdf/.docx resume text extraction (defensive)
src/jarvis/latex_resume.py  tailored-resume .tex source generator
src/jarvis/jobs.py      live Greenhouse adapter: curated boards, fresher
                        tiering, auto-extracted requirements, failure-safe
                        aggregation (legacy fetch_greenhouse kept)
src/jarvis/pdf_resume.py  one-page PDF renderer (fpdf2 + bundled Latin Modern)
assets/fonts/           OFL-licensed Latin Modern Roman TTFs + GUST font license
tests/                  unittest suite
docs/                   research + build plan from the hackathon brief
```

## License

For hackathon evaluation. Live job postings come from public company career
boards; all personal/demo data is synthetic. Do not commit real resumes,
inboxes, tokens, or secrets.
