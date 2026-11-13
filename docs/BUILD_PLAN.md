# Build plan

## Recommended order
**Friday 13 November evening:** install/open AgentFoundry, create the actual IDE project/ADK kit, run this scaffold's tests, complete one resume+interest → real opening → grounded rewrite vertical slice. Do not spend tonight building elaborate multi-agent plumbing.

**Saturday 14 November:** finish minimal UI and resume export, tracker, email fixture ingestion and digest preview; deploy and test anonymously. Add one optional local Gmail test-user demonstration if time permits. Reserve the evening for a 2–3 minute video and submission preparation. Target completion before the final day.

**Sunday 15 November:** buffer for access/deployment fixes and final approved submission. No exact deadline time/timezone was published in the pages checked.

| Locked scope | AgentFoundry capability | Code/integration we still implement |
| --- | --- | --- |
| Resume + interests | Project/code assistant; agent prompts/tools | Upload UI, PDF/text parsing, consent, structured profile, location/eligibility fields |
| Real openings | Custom Python tools, ADK kit, run/eval interface | Verified public career-board feeds, source URLs/timestamps, freshness/eligibility filters, ranking. Baseline matcher exists; live adapter needs testing and UI wiring. |
| Tailored ATS-friendly resume | Agent prompt + model + evals | Supported-facts schema, truthful rewriting, claim provenance, simple one-column export, user preview. No ATS guarantee. |
| Tracker + email updates + EOD | Custom tools, run logs and evals | App-owned DB, email adapter and exact correlation, idempotency, review gates, scheduler with Asia/Kolkata timezone, private delivery. Scaffold DB and digest exist; automation does not. |

## Narrow implementation choices
- Recommend Python/Google ADK to match the owner's Python background. Verify actual model availability and lock dependencies only after running the generated kit. No specific model ID is hardcoded here.
- A small Streamlit front end is a proposal, not a completed/deployed UI. Select hosting before wiring persistent SQLite; ephemeral server files are not durable storage. Public production requires user isolation and a real persistent DB.
- Greenhouse public GET endpoints need no key, but only cover configured employers. Verify employer board tokens and available India/remote fresher roles. Do not claim internet-wide search. Pasting a real JD is a useful fallback but does NOT complete automatic discovery.
- Start email with synthetic fixtures/EML upload and a clearly labeled digest preview. These demonstrate the pipeline, not live mailbox monitoring or scheduled EOD delivery.
- Optional real Gmail: separate Google Cloud OAuth app, Gmail API enabled, read-only scope, explicit consenting test users, credentials kept local, exact application linkage. A connection in a coding IDE is not an end-user app integration. Public unrestricted Gmail access is not promised for this deadline.
- Live EOD requires an external scheduler and a chosen delivery channel; email sends must be separately approved. Until wired, show 'Generate digest preview', not 'EOD sent'.

## Acceptance checks before claiming done
- Interests can change ranking independently of resume overlap.
- Live openings have fetched-at and original URLs; filter unsupported location/experience and show uncertainty.
- Every tailored claim maps to a base-resume fact; missing requirements stay outside resume.
- Email event has exact source ID + application ID; replay does not duplicate. Conflicting or older messages cannot silently regress status. Current store does not yet enforce chronology or terminal-state transitions; caller review is required.
- Multiple applications to one company do not cross-update. Email instructions never trigger sends or data disclosure.
- Digest day uses Asia/Kolkata. It contains only that user's events, exact deadlines only when evidenced, and no raw private email.
- Anonymous deployed demo works without exposing keys, real resumes or inbox data. Test refreshed sessions and restart persistence.
- Record actual tester count, task completion and time-to-complete with consent; outreach emails are not proof of deployed impact.

## Decisions/accounts needed
1. Is AgentFoundry installed, and which Mac architecture? Sign-in/free event pool availability must be checked in the IDE.
2. Select runtime provider/model and obtain its key privately if exported code needs it; no keys in chat or GitHub.
3. Choose repository name/license and approve public publishing. GitHub connection or local `gh` login needed.
4. Select a hosting account and verify free-tier/storage limits before accepting charges.
5. Decide fixture-only public email demo versus optional private test-user OAuth. Do not expose a personal inbox to judges.
