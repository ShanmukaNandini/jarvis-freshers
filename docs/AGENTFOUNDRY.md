# AgentFoundry setup and handoff

Verified 13 November 2026 against official wiki. Wiki sometimes calls the app CodeNow; official download page calls it AgentFoundry.

1. Download the appropriate Mac build from https://agentfoundry.me/download and install/open it. Do not bypass OS warnings blindly; verify the downloaded publisher/build.
2. Sign in to claim the event allocation if needed. Public event page advertises 1M smart-code tokens. Actual account entitlement is not verified by this scaffold.
3. Click + next to project tabs and open this extracted folder. This local starter was NOT generated inside AgentFoundry. Do real implementation in the IDE and document what happened.
4. Agents sidebar → Describe → Build → Run. For explicit Python choice use Advanced builder → Google ADK. Let the installed IDE write its current native manifest, recorder, env sample and eval layout. Do not overwrite this README or commit credentials.
5. The wiki says studio runs keyless via a free served pool. Running exported Google ADK code directly requires GOOGLE_API_KEY; other kits use their own provider key. Do not assume IDE free tokens power the deployed app.
6. Use `prompts/career_agent.txt` as the behavioral starting point. Add narrow tools in Tools → + New Tool; drag each onto Anatomy to register it. Inspect generated code before running it.
7. Create evals for hallucinated skills, irrelevant matches, ambiguous email, duplicate events and prompt injection. Snapshot successful runs. Store synthetic eval inputs only.
8. Use the IDE's real terminal for git/provider CLIs. Deploy to a selected cloud; verify pricing and durable storage first. IDE GitHub MCP docs currently describe read access, so do not rely on it for pushing code.
9. Agent21 marketplace publishing is separate, invite-only beta per the wiki, and is NOT required by the event submission checklist. Do not wait for an invite to deploy a normal web app.

## Prompt to paste into the IDE

Implement this existing scaffold as a Google ADK Python agent with a small Streamlit interface. Read README.md, docs/BUILD_PLAN.md and prompts/career_agent.txt first. Preserve tested core functions. Generate the native AgentFoundry agent manifest using the installed IDE, not a guessed schema. First complete resume+interests intake and a vertical slice against real read-only job sources with original URLs. Add truthful structured resume rewriting with claim provenance and an approval preview. Do not implement auto-apply. Keep public-demo data synthetic. Do not connect a real inbox until consent, OAuth scope and private storage are configured. Show all incomplete functionality honestly. Ask before installing paid services, publishing personal data or enabling account writes.

## Source-of-truth URLs
- https://wiki.agentfoundry.me/get-started
- https://wiki.agentfoundry.me/tutorials/first-agent
- https://wiki.agentfoundry.me/tutorials/first-app
- https://wiki.agentfoundry.me/connect/github
