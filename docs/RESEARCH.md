# Research notes - 13 November 2026

## Recommendation
Use AgentFoundry as the development IDE and a normal Python app for deployment. The native agent builder can generate an ADK kit; most product features still need application code and external integrations. Do not mistake IDE connectors, runs or Agent21 publishing for an end-user job-tracking service.

## Verified primary sources
1. Event page, Code for India: https://codeforindia.org/hackathon
   Build in AgentFoundry; 1M smart-code tokens advertised; deploy to any cloud by 15 November 2026; public repo and readable README; demo live link or 2–3 minute video; judging equally weighted problem size/severity/solution quality/proven impact. MIT or Apache-2.0 open source to CFI organization described in FAQ. Account entitlement and exact final-hour cutoff unverified.
2. Submission hub README: https://github.com/karlmehta/code-for-a-billion
   Public repository/setup README, working demo, issue submission. Some details stale: dates TBD and different prize figures. Prefer live event date; do not repeat conflicting prizes.
3. Actual form: https://github.com/karlmehta/code-for-a-billion/blob/main/.github/ISSUE_TEMPLATE/submission.yml
   Required project/team, member handles, problem, solution/how AF used, repo/demo URLs, scale/severity, track, contact, three confirmations. Impact data optional in the form but judged. Other is an offered track; Tech Employment for Youth is the event impact area.
4. Rubric: https://github.com/karlmehta/code-for-a-billion/blob/main/JUDGING.md
   Four equal criteria; impact breaks ties. No NGO named in listed eligibility checklist.
5. Wiki overview: https://wiki.agentfoundry.me/
   IDE supports multiple SDKs, project-scoped MCP, runs/evals/replay, deploy tools. Current overview calls IDE free; marketing may vary. No pricing/entitlement guarantee made here.
6. Setup: https://wiki.agentfoundry.me/get-started
   Add a folder via +, Agents sidebar Describe→Build→Run; keyless served pool inside studio; exported kits need provider configuration.
7. Agent tutorial: https://wiki.agentfoundry.me/tutorials/first-agent
   Python/TS Claude, TS Cursor, Python Microsoft, Python ADK kits; prompts/tools/manifest/evals under .codenow/agent-studio; tools need implementations. ADK example uses GOOGLE_API_KEY. Agent21 needs separate beta access and is not mandatory for event submission.
8. App tutorial: https://wiki.agentfoundry.me/tutorials/first-app
   Ordinary framework code and real terminal; deploy using selected provider's CLI, not a mandatory proprietary runtime.
9. GitHub connector: https://wiki.agentfoundry.me/connect/github
   Repo read context via MCP; write access listed as forthcoming. Use an approved git/CLI route for pushing; do not assume the connector publishes repositories.
10. Download: https://agentfoundry.me/download
   Mac Apple Silicon and Intel builds, Windows, Linux. Use this canonical page to choose the architecture.
11. Job source: https://docs.greenhouse.io/job-board.html
   Public board GETs require no auth, `jobs?content=true` supplies descriptions and original URLs. Requires known employer boards; not global job search. No application POST used.
12. Gmail test quickstart: https://developers.google.com/workspace/gmail/api/quickstart/python
   Google Cloud project + enabled Gmail + OAuth client/consent; stores local user tokens. Not production auth guidance.
13. Gmail scopes: https://developers.google.com/workspace/gmail/api/auth/scopes
   gmail.readonly is restricted; request minimum access. Servers storing/transmitting restricted data can require security assessment.
14. OAuth requirements: https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
   Testing apps limited to configured test users can use verification exceptions; unrestricted public deployment is a different project with compliance work. Do not promise completion in two days.

## Unresolved official-source differences
- Public event says deploy to cloud by 15 November; rubric permits a live app or video demo. Safest is deploy AND record backup video.
- Event FAQ describes contribution to the CFI organization, while issue form only requires a public GitHub repository. Publish under owner-approved identity, then clarify contribution/transfer mechanics; do not transfer ownership without permission.
- Organizer registration email asks for a local NGO/partner, while public form/rubric do not make it a submission checkbox. Main has the private correspondence; no message or personal contact data is copied into this public-ready starter. Do not claim NGO involvement is definitely optional or already achieved.
- Deadline clock time/timezone and actual participant free-token balance remain unknown.

All listed pages were fetched and read for the claims above. This is an official platform/requirements question, so primary docs are preferred over unrelated third-party AgentFoundry products. No private email, resume or credentials are included in this project.
