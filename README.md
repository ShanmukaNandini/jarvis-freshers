# Jarvis for Freshers

A job-search companion for first-time job seekers: start with a resume and interests, find relevant openings, prepare a truthful job-specific resume, then track applications and read a daily summary.

**Stage: research + scaffold, 13 November 2026. Not a deployed or completed product.**

## Product scope
1. Base resume + areas of interest, location and eligibility preferences.
2. Real openings with original source links, retrieval timestamps and explainable matches.
3. ATS-friendly tailored resumes grounded only in facts the applicant supplied. No invented skills, employers or metrics; no ATS-pass guarantee.
4. Application tracker, evidence-backed email updates and end-of-day digest.

Stretch: skill-gap suggestions and application email drafts. The applicant sends applications. No auto-apply or automated email sending.

## What runs today
- Dependency-free matching baseline that uses both interest terms and resume terms.
- SQLite application/event store with duplicate-event protection.
- Rule-based email-status *suggestions* with ambiguity held for review.
- A plain-text daily digest from stored events.
- Synthetic CLI smoke demonstration and unit tests.

**Not implemented:** resume upload/PDF export, an LLM/ADK agent, live job-source wiring into a UI, Gmail OAuth ingestion, scheduling, authentication or cloud deployment. The Greenhouse adapter is a read-only starter, not yet exercised against a real employer board. Fixtures are fabricated examples, not live jobs or user emails. Match scores are term counts, not hiring probabilities.

## Run locally
Python 3.11+ recommended. Core scaffold needs no third-party packages.

```sh
python -m unittest discover -s tests -v
python demo.py
```

The smoke demo uses an in-memory database and never connects to an inbox, a model or an employer. The next implementation should add an AgentFoundry-generated Google ADK kit, then a small Streamlit UI. See `docs/BUILD_PLAN.md` and `docs/AGENTFOUNDRY.md`.

## Planned architecture
AgentFoundry IDE → Python/Google ADK orchestration → narrow job-search / resume / tracker tools → authenticated app + persistent database. AgentFoundry is the development IDE, not a mandatory hosting service. Its built-in inference pool is not assumed to fund cloud app inference.

## Configuration and privacy
Copy `.env.example` to a private local config only when connecting a provider. Never commit credentials, OAuth tokens, resumes, email bodies or local databases. The public demo must use synthetic data and isolate visitor sessions. A private inbox connection requires its own explicit consent. Keep raw email content out of prompts when a minimal extracted event suffices.

## Hackathon submission (not yet submitted)
- Event: Code for a Billion; impact area: Tech Employment for Youth; issue-form track: Other.
- Build meaningfully in AgentFoundry and record actual usage; do not claim the local scaffold was generated there.
- Publish an approved open-source repository with setup steps, license, known limits and no private data.
- Deploy a demo to a cloud provider and test a judge-accessible link; record a 2–3 minute backup walkthrough.
- Complete the official GitHub issue form before 15 November 2026. Exact closing time/timezone was not stated on the pages checked. Aim to finish on 14 November IST.
- No field impact or NGO partnership is claimed. Record actual consenting tests rather than invented metrics.

License selection and GitHub publishing await the owner. Official sources and discrepancies: `docs/RESEARCH.md`.
