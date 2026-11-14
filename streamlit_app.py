#!/usr/bin/env python3
"""Jarvis for Freshers - public demo UI (Streamlit).

    pip install -r requirements.txt
    streamlit run streamlit_app.py

Honesty contract:
- Job openings are fetched LIVE from public Greenhouse career boards (one
  request per board, cached 30 minutes) and labelled LIVE. If every board is
  unreachable the app falls back to synthetic fixtures labelled OFFLINE DEMO
  DATA. Requirement lists for live postings are auto-extracted keywords -
  honest hints, not the employer's structured requirements.
- Tailoring is deterministic and truthful: it selects and reorders facts that
  already exist in a resume. It never invents skills, and it is not an ATS
  score or a guarantee.
- No auto-apply: the user always reviews and sends applications themselves.
- The "inbox" is a fixed synthetic fixture set. No real email is connected.
- PDF output is generated in pure Python (fpdf2 + bundled OFL Latin Modern
  fonts) in the same one-page template as the .tex source - no LaTeX
  toolchain needed; the .tex download stays for Overleaf users.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from jarvis.core import (rank_jobs, suggest_email_status, daily_digest,
                         structure_user_resume, tailor_resume_for_job,
                         learning_suggestions,
                         add_user_skill, add_user_project, add_user_other,
                         add_user_experience)
from jarvis.fixtures import (BASE_RESUME, JOB_FIXTURES, SYNTHETIC_APPLICATIONS,
                             EMAIL_FIXTURES)
from jarvis.jobs import fetch_live_jobs, DEFAULT_BOARDS, safe_html, is_india_remote
from jarvis.latex_resume import generate_tex
from jarvis.pdf_resume import generate_pdf
from jarvis.parsing import extract_resume_text, ResumeParseError
from jarvis.store import (connect, save_application, record_reviewed_event,
                          events, applications, process_synthetic_fixtures,
                          run_with_retry)

DB_PATH = "jarvis_demo.db"
IST = ZoneInfo("Asia/Kolkata")

# --------------------------------------------------------------------------
# Page setup + scoped styling (no remote fonts or CDNs; Streamlit only)
# --------------------------------------------------------------------------

st.set_page_config(page_title="Jarvis for Freshers", page_icon="✨",
                   layout="wide", initial_sidebar_state="collapsed")

# Styling note: the app's theme (colors, base=\"light\") lives in
# .streamlit/config.toml, which every Streamlit version honors. The CSS below
# deliberately avoids Streamlit's internal class names and data-testid hooks -
# those change between releases and broke rendering once already. It styles
# only standard elements and our own classes, so it survives upgrades.
st.markdown("""
<style>
  :root { color-scheme: light; }
  .stApp { background-color: #FAF7F2; }
  h1, h2, h3, h4 { color: #0F2A43; }
  .hero {
      background: linear-gradient(135deg, #0F2A43 0%, #14535B 60%, #0E7C7B 100%);
      border-radius: 16px; padding: 2rem 2.2rem; margin-bottom: 1.2rem;
  }
  .hero h1 { color: #FAF7F2 !important; margin-bottom: 0.2rem; }
  .hero p  { color: #D8E6E4 !important; font-size: 1.05rem; margin-bottom: 0; }
  .badge {
      display: inline-block; background: #0E7C7B; color: #FAF7F2 !important;
      border-radius: 999px; padding: 0.15rem 0.7rem; font-size: 0.75rem;
      letter-spacing: 0.06em; text-transform: uppercase; font-weight: 700;
  }
  .badge-live { background: #0E7C7B; }
  .badge-offline { background: #B7791F; }
  .swipecard {
      background: #FFFFFF; border: 2px solid #0E7C7B; border-radius: 18px;
      padding: 1.6rem 1.8rem; margin: 0.6rem 0 0.4rem 0;
      box-shadow: 0 4px 18px rgba(15, 42, 67, 0.10);
  }
  .swipecard h2 { color: #0F2A43 !important; margin: 0.2rem 0 0.3rem 0; }
  .swipemeta { color: #5C6B73 !important; font-size: 1.0rem; margin-bottom: 0.6rem; }
  .swipedesc { color: #22303C !important; font-size: 0.95rem; margin-top: 0.7rem; }
  .swipeprogress { color: #5C6B73 !important; font-size: 0.85rem; text-align: center; }
  .jobcard {
      background: #FFFFFF; border: 1px solid #E4DED3; border-left: 5px solid #0E7C7B;
      border-radius: 12px; padding: 0.9rem 1.1rem; margin-bottom: 0.7rem;
  }
  .jobcard h1, .jobcard h2, .jobcard h3 { color: #0F2A43 !important; margin: 0 0 0.15rem 0; }
  .jobmeta { color: #5C6B73 !important; font-size: 0.9rem; }
  .stephead {
      color: #0F2A43 !important; border-bottom: 2px solid #0E7C7B;
      padding-bottom: 0.25rem; margin-top: 1.6rem;
  }
  .small-note { color: #5C6B73 !important; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <span class="badge">Live openings · honest tailoring</span>
  <h1>✨ Jarvis for Freshers</h1>
  <p>Your truthful job-hunt copilot: match openings, tailor your resume with
     provenance, see your skill gaps, and track every application. You always
     hit send - never the app.</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Step 1 - Your profile (upload .txt/.pdf/.docx, paste, or synthetic demo)
# --------------------------------------------------------------------------

st.markdown('<h2 class="stephead">1 · Your profile</h2>', unsafe_allow_html=True)
st.caption("Upload or paste your real resume, or explore with the synthetic demo "
           "candidate. Uploaded files are parsed in memory for this session only.")

input_method = st.radio(
    "How do you want to provide your resume?",
    ["Upload a file (.txt, .pdf, .docx)", "Paste text", "Use the synthetic demo profile"],
    horizontal=True)

resume_text_draft = ""
uploaded = None
if input_method.startswith("Upload"):
    uploaded = st.file_uploader("Drop your resume here", type=["txt", "pdf", "docx"],
                                help="Parsed locally in this app; nothing is sent to "
                                     "any model or inbox.")
elif input_method.startswith("Paste"):
    resume_text_draft = st.text_area(
        "Paste your resume (plain text)", height=180,
        placeholder="Priya Verma\npriya@example.com | +91-98...\nB.Tech CSE, 2026...\n"
                    "Built a Flask API...\nSkills: Python, SQL, pandas")

interests_raw = st.text_input("Your interests (comma-separated - they steer matching "
                              "and learning tips, never what you claim)",
                              value="data, machine learning, backend")
interests = [i.strip() for i in interests_raw.split(",") if i.strip()]

if st.button("Build my profile", type="primary"):
    try:
        if input_method.startswith("Use"):
            st.session_state["profile"] = BASE_RESUME
            st.session_state["profile_label"] = "Synthetic demo candidate"
        elif input_method.startswith("Upload"):
            if uploaded is None:
                st.warning("Choose a file first.")
                st.stop()
            text = extract_resume_text(uploaded.name, uploaded.getvalue())
            st.session_state["profile"] = structure_user_resume(text)
            st.session_state["profile_label"] = f"Your resume ({uploaded.name})"
        else:
            if not resume_text_draft.strip():
                st.warning("Paste your resume text first.")
                st.stop()
            st.session_state["profile"] = structure_user_resume(resume_text_draft)
            st.session_state["profile_label"] = "Your pasted resume"
    except ResumeParseError as exc:
        st.error(str(exc))
        st.stop()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

profile = st.session_state.get("profile")
if profile:
    st.success(f"Profile ready: {st.session_state.get('profile_label')} - "
               f"{len(profile['facts'])} facts extracted, each with provenance.")
    with st.expander("See the facts Jarvis will work from (nothing else gets claimed)"):
        for fact in profile["facts"]:
            tag = " · added by you" if fact.get("added_by") == "user" else ""
            st.markdown(f"- **{fact['id']}** ({fact['section']}{tag}): {fact['text']}")

    # ---- Add something new to the profile ---------------------------------
    with st.expander("➕ Add something new to your profile "
                     "(a skill, a project, a certification...)"):
        st.caption("You adding a fact IS you supplying a fact - the no-invention "
                   "rule still holds, and anything you add becomes material for "
                   "tailored resumes. Additions live for this browser session "
                   "(demo storage).")
        # The kind selector lives OUTSIDE the form: widget changes inside a
        # st.form do not rerun the script, so the fields would never switch
        # to match the chosen kind (that was the 'internship didn't get
        # added' bug - whatever she typed went in as a skill).
        kind = st.selectbox("What are you adding?",
                            ["A skill", "A project",
                             "An internship or work experience",
                             "A certification, award or activity"],
                            key="add_kind")
        with st.form("add_fact_form", clear_on_submit=True):
            skill_text = proj_title = proj_tech = other_text = ""
            proj_bullets = exp_title = exp_org = exp_dates = exp_bullets = ""
            if kind == "A skill":
                skill_text = st.text_input("Skills (comma-separated)",
                                           placeholder="Docker, Kubernetes")
            elif kind == "A project":
                proj_title = st.text_input("Project title",
                                           placeholder="Campus placements predictor")
                proj_tech = st.text_input("Tech stack (optional, comma-separated)",
                                          placeholder="Python, scikit-learn, Streamlit")
                proj_bullets = st.text_area("Description (one point per line)",
                                            height=110,
                                            placeholder="Trained a classifier on 3 years of placement data\nDeployed it as a Streamlit app used by 50 classmates")
            elif kind == "An internship or work experience":
                exp_title = st.text_input("Role / title",
                                          placeholder="Software Engineering Intern")
                exp_org = st.text_input("Company / organisation",
                                        placeholder="Bharat Electronics Limited (BEL)")
                exp_dates = st.text_input("Dates (optional)",
                                          placeholder="Jun 2026 - Aug 2026")
                exp_bullets = st.text_area("Description (one point per line)",
                                           height=110,
                                           placeholder="Built a Flask API for the internal tools team\nWrote pytest suites that raised coverage to 85%")
            else:
                other_text = st.text_input("Certification / award / activity",
                                           placeholder="AWS Certified Cloud Practitioner, 2026")
            submitted = st.form_submit_button("Add to my profile", type="primary")
        if submitted:
            try:
                if kind == "A skill":
                    fact = add_user_skill(profile, skill_text)
                    st.session_state["added_flash"] = f"Added: {fact['text']}"
                elif kind == "A project":
                    entry = add_user_project(profile, proj_title, proj_tech,
                                             proj_bullets.splitlines())
                    st.session_state["added_flash"] = \
                        f"Added project: {entry['title']} ({len(entry['bullets'])} point(s))"
                elif kind == "An internship or work experience":
                    entry = add_user_experience(profile, exp_title, exp_org,
                                                exp_dates, exp_bullets.splitlines())
                    st.session_state["added_flash"] = \
                        f"Added experience: {entry['title']} - it renders in your " \
                        f"Experience section and competes in per-job ordering."
                else:
                    fact = add_user_other(profile, other_text)
                    st.session_state["added_flash"] = f"Added: {fact['text']}"
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    if st.session_state.pop("added_flash", None):
        st.success("Added to your profile - it will show up in tailored resumes "
                   "from now on. Reopen the facts list above to see it.")

if not profile:
    st.info("Build a profile above to unlock matching, tailoring and skill gaps.")
    st.stop()

# --------------------------------------------------------------------------
# Step 2 - Ranked openings
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Step 2 - Openings: live Greenhouse boards by default, offline fallback
# --------------------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner="Fetching live openings from company career boards...")
def load_openings():
    """One request per curated public Greenhouse board; cached 30 minutes."""
    return fetch_live_jobs()

st.markdown('<h2 class="stephead">2 · Openings for you</h2>', unsafe_allow_html=True)

board_names = ", ".join(name for _, name in DEFAULT_BOARDS)
if st.button("↻ Refresh openings", help="Clears the 30-minute cache and re-fetches "
                                        "the live boards (one polite request each)."):
    load_openings.clear()
    st.rerun()

live = load_openings()
if live["jobs"]:
    jobs_source = live["jobs"]
    source_badge = '<span class="badge badge-live">LIVE</span>'
    source_label = "live"
    st.caption(f"Live openings fetched from public Greenhouse career boards "
               f"({board_names}), fresher-relevant and India/remote-leaning, "
               f"cached for 30 minutes. Requirement lists are auto-extracted "
               f"keywords from each posting - honest hints, not the employer's "
               f"structured requirements.")
    if live["boards_failed"]:
        st.warning("Couldn't reach these boards just now: "
                   + ", ".join(live["boards_failed"])
                   + " - showing what loaded from the rest.")
else:
    jobs_source = JOB_FIXTURES
    source_badge = '<span class="badge badge-offline">OFFLINE DEMO DATA</span>'
    source_label = "offline"
    st.warning("Live boards are unreachable right now, so these are the built-in "
               "synthetic fixtures - **OFFLINE DEMO DATA**, not real openings.",
               icon="⚠️")

profile_text = " ".join(f["text"] for f in profile["facts"])
ranked_all = rank_jobs(profile_text, interests, jobs_source)
india_only = st.checkbox("🇮🇳 India & remote only",
                         help="Narrows the deck to postings located in India "
                              "(Bengaluru, Hyderabad, Pune...) or marked remote.")
ranked = [j for j in ranked_all if is_india_remote(j)] if india_only else ranked_all
if india_only and not ranked:
    st.warning("No India/remote openings in the current fetch - showing the full "
               "shortlist instead. Try Refresh openings.")
    ranked = ranked_all
job_by_id = {j["id"]: j for j in ranked}

# ---- Swipe / List toggle --------------------------------------------------
st.session_state.setdefault("view_mode", "Swipe")
st.session_state.setdefault("skipped_ids", [])
st.session_state.setdefault("saved_ids", [])
view = st.radio("Browse mode", ["Swipe", "List"], horizontal=True, key="view_mode")

if view == "Swipe":
    deck = [j for j in ranked if j["id"] not in st.session_state["skipped_ids"]
            and j["id"] not in st.session_state["saved_ids"]]
    total = len(ranked)
    done = total - len(deck)
    if not deck:
        st.success(f"You've reviewed all {total} openings "
                   f"({len(st.session_state['saved_ids'])} saved, "
                   f"{len(st.session_state['skipped_ids'])} skipped).")
        if st.button("↺ Start the deck over"):
            st.session_state["skipped_ids"] = []
            st.rerun()
    else:
        card = deck[0]
        st.markdown(f'<div class="swipeprogress">Card {done + 1} of {total} · '
                    f'{len(st.session_state["skipped_ids"])} skipped · '
                    f'{len(st.session_state["saved_ids"])} saved</div>',
                    unsafe_allow_html=True)
        reqs = ", ".join(card["requirements"]["required"][:8]) or "see the full posting"
        # Everything dynamic goes through safe_html: postings are arbitrary
        # third-party content and must render as inert text, never markup.
        st.markdown(f"""
        <div class="swipecard">
          {source_badge}
          <h2>{safe_html(card['title'])}</h2>
          <div class="swipemeta">{safe_html(card['company'])} · {safe_html(card.get('location', ''))} ·
            match score {card['baseline_score']}</div>
          <div><b>Key skills:</b> {safe_html(reqs)}</div>
          <div class="swipedesc">{safe_html(card['description'][:280])}...</div>
        </div>
        """, unsafe_allow_html=True)
        col_skip, col_save = st.columns(2)
        with col_skip:
            if st.button("⏭ Skip", use_container_width=True):
                st.session_state["skipped_ids"].append(card["id"])
                st.rerun()
        with col_save:
            if st.button("💾 Save & tailor", type="primary", use_container_width=True):
                st.session_state["saved_ids"].append(card["id"])
                st.session_state["selected_job_id"] = card["id"]
                try:
                    run_with_retry(lambda: save_application(
                        connect(DB_PATH), card["id"], card["company"],
                        card["title"], card.get("url", "")))
                except sqlite3.IntegrityError:
                    pass  # already tracked; the jump to tailoring still happens
                except sqlite3.OperationalError:
                    st.warning("Tracker database was busy - this save did not "
                               "land. Try Save again in a few seconds.")
                st.session_state["just_saved"] = card["id"]
                st.rerun()
        if st.session_state.pop("just_saved", None):
            st.success("Saved to your tracker - your tailored resume for it is "
                       "ready in section 3 below. [Jump straight to it ↓](#tailor)")
        with st.expander("Full posting + apply link"):
            st.write(card["description"])
            st.markdown("**Required:** " + ", ".join(card["requirements"]["required"]))
            if card["requirements"]["preferred"]:
                st.markdown("**Preferred:** " + ", ".join(card["requirements"]["preferred"]))
            if card.get("url"):
                st.markdown(f"[View the posting and apply on the company's site]"
                            f"({card['url']}) - you always hit send yourself.")
else:
    for j in ranked:
        st.markdown(f"""
        <div class="jobcard">
          <h3>{safe_html(j['title'])}</h3>
          <div class="jobmeta">{safe_html(j['company'])} · {safe_html(j.get('location', ''))} ·
            {source_badge} · match score {j['baseline_score']}</div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander(f"Details - {j['title']}"):
            st.write(j["description"])
            st.markdown("**Required:** " + ", ".join(j["requirements"]["required"]))
            if j["requirements"]["preferred"]:
                st.markdown("**Preferred:** " + ", ".join(j["requirements"]["preferred"]))
            if j.get("resume_hits"):
                st.markdown('<span class="small-note">Your matching terms: '
                            + safe_html(", ".join(j["resume_hits"])) + "</span>",
                            unsafe_allow_html=True)
            if j.get("url") and source_label == "live":
                st.markdown(f"[View the posting and apply on the company's site]({j['url']})")

# ---- Tailor target selection (swipe Save jumps here) ----------------------
options = [j["id"] for j in ranked]
if st.session_state.get("selected_job_id") not in options:
    st.session_state["selected_job_id"] = options[0]
selected_id = st.selectbox(
    "Pick an opening to tailor for:",
    options=options,
    format_func=lambda jid: f"{job_by_id[jid]['title']} - {job_by_id[jid]['company']}",
    key="selected_job_id")
job = job_by_id[selected_id]
tailored = tailor_resume_for_job(profile, job)

# --------------------------------------------------------------------------
# Step 3 - Tailored resume (full length, provenance, LaTeX source download)
# --------------------------------------------------------------------------

st.markdown('<a id="tailor"></a>', unsafe_allow_html=True)
st.markdown('<h2 class="stephead">3 · Your tailored resume</h2>', unsafe_allow_html=True)
st.caption(f"Tailored for **{job['title']}** at {job['company']}. Every line is one of "
           "your facts, reordered and selected - nothing invented.")

tab_preview, tab_provenance, tab_downloads = st.tabs(
    ["Resume preview", "Provenance", "Downloads"])

with tab_preview:
    # What changed for THIS job - tailoring you can see.
    changes = tailored.get("changes", [])
    visible = [c for c in changes if c["kind"] != "summary"]
    with st.container(border=True):
        st.markdown("**What changed for this job** "
                    f"({job['company']} · {job['title']})")
        for c in changes:
            st.markdown(f"- {c['text']}")
        if not visible:
            st.caption("Your base order already fit this job - only the summary "
                       "was pointed at it. Try an opening with different "
                       "requirements to see reordering.")
    st.markdown(tailored["markdown"])

with tab_provenance:
    st.write("Every claim links back to a fact in your profile "
             "(and to your original resume sentences for uploaded resumes):")
    for claim in tailored["claims"]:
        matched = ", ".join(claim["matched_requirements"]) or "-"
        prov = ", ".join(str(i) for i in claim["provenance"]) or "-"
        st.markdown(f"- **{claim['fact_id']}** ({claim['section']}) → "
                    f"requirements: {matched} · source lines: {prov}")

with tab_downloads:
    tex_source = generate_tex(profile, tailored)
    safe_job = job["id"]
    pdf_bytes = generate_pdf(profile, tailored)
    st.download_button("Download PDF (.pdf) - ready to send", pdf_bytes,
                       file_name=f"tailored-resume-{safe_job}.pdf",
                       mime="application/pdf", type="primary",
                       help="A finished one-page PDF rendered in the same "
                            "template as the .tex source (Latin Modern fonts, "
                            "your resume's layout). No Overleaf step needed.")
    st.download_button("Download Markdown (.md)", tailored["markdown"],
                       file_name=f"tailored-resume-{safe_job}.md")
    st.download_button("Download plain text (.txt)", tailored["plain_text"],
                       file_name=f"tailored-resume-{safe_job}.txt")
    st.download_button("Download LaTeX source (.tex)", tex_source,
                       file_name=f"tailored-resume-{safe_job}.tex",
                       help="Compile this yourself: Overleaf → New Project → "
                            "Blank Project → paste → Recompile. This app never "
                            "compiles LaTeX server-side.")
    st.info("The PDF is generated in pure Python with the bundled "
            "OFL-licensed Latin Modern fonts - same one-page template as the "
            ".tex, ready to attach to an application. The .tex remains for "
            "anyone who prefers compiling in Overleaf.", icon="ℹ️")

# --------------------------------------------------------------------------
# Step 4 - Skill gaps
# --------------------------------------------------------------------------

st.markdown('<h2 class="stephead">4 · Skill gaps for this opening</h2>',
            unsafe_allow_html=True)
st.caption("Gaps are reported, never papered over. Interests steer what to learn "
           "first; they never count as evidence of a skill.")

supported = [r for r in job["requirements"]["required"]
             if r in tailored["supported_requirements"]]
with st.expander(f"✅ Requirements you already evidence ({len(supported)})",
                 expanded=True):
    for r in supported:
        facts = [c['fact_id'] for c in tailored['claims'] if r in c['matched_requirements']]
        st.markdown(f"- {r} — evidenced by facts: {', '.join(facts)}")

if tailored["missing_required"]:
    with st.expander(f"⚠️ Missing required skills ({len(tailored['missing_required'])})",
                     expanded=True):
        for tip in learning_suggestions(tailored["missing_required"]):
            st.markdown(f"- **{tip['requirement']}** — {tip['suggestion']}")
if tailored["missing_preferred"]:
    with st.expander(f"◻ Preferred, not yet evidenced ({len(tailored['missing_preferred'])})"):
        for tip in learning_suggestions(tailored["missing_preferred"]):
            st.markdown(f"- **{tip['requirement']}** — {tip['suggestion']}")
if tailored["clarify"]:
    with st.expander(f"❓ Worth clarifying in an interview ({len(tailored['clarify'])})"):
        for r in tailored["clarify"]:
            st.markdown(f"- {r} — your evidence may be partial; be ready to describe "
                        "your actual depth honestly.")

# --------------------------------------------------------------------------
# Step 5 - Application tracker + synthetic inbox
# --------------------------------------------------------------------------

st.markdown('<h2 class="stephead">5 · Application tracker</h2>', unsafe_allow_html=True)
st.caption("Local demo database (jarvis_demo.db, wiped whenever this cloud app "
           "restarts). Statuses change only from reviewed evidence - never guessed "
           "from names or senders.")

db = connect(DB_PATH)

col_save, _ = st.columns([2, 3])
with col_save:
    if st.button(f"Save '{job['title']}' to tracker"):
        try:
            run_with_retry(lambda: save_application(
                connect(DB_PATH), job["id"], job["company"], job["title"],
                job.get("url", "")))
            st.success("Saved to the tracker.")
        except sqlite3.IntegrityError:
            st.warning("Already saved in the tracker.")
        except sqlite3.OperationalError:
            st.warning("Tracker database was busy - this save did not land. "
                       "Try again in a few seconds.")

apps = applications(db)
if apps:
    st.subheader("Tracked applications")
    for a in apps:
        st.markdown(f"- **{a['role']}** @ {a['company']} — status: `{a['status']}`")

st.subheader("Synthetic inbox")
st.write("Process the fixed set of synthetic emails against tracked applications. "
         "Run it twice - the second run reports only duplicates, because every "
         "message is tied to an exact application and source ID.")
if st.button("Process synthetic inbox now"):
    try:
        # Short-lived connection + brief lock retry: a locked demo database
        # (two app processes, a stale rerun) can never white-screen the app.
        result = run_with_retry(
            lambda: process_synthetic_fixtures(connect(DB_PATH),
                                               SYNTHETIC_APPLICATIONS, EMAIL_FIXTURES))
        st.success(f"Recorded {result['recorded']} update(s); "
                   f"{result['duplicates']} duplicate(s) skipped.")
        if result["held"]:
            st.warning(f"{len(result['held'])} message(s) held for human review:")
            for held in result["held"]:
                st.markdown(f"- `{held['source_id']}` — {held['reason']}")
    except sqlite3.OperationalError:
        st.warning("The demo database is busy right now (another copy of the app "
                   "may be writing to it). Wait a few seconds and try again - "
                   "your tracked applications are safe.")

with st.expander("Record a reviewed update manually"):
    if apps:
        sel = st.selectbox("Application", options=[a["id"] for a in apps])
        source_id = st.text_input("Source message ID (opaque, required)",
                                  value="manual-1")
        subject = st.text_input("Message subject", value="Application received")
        body_text = st.text_area("Message body",
                                 value="Thank you for applying.")
        suggestion = suggest_email_status(subject, body_text)
        st.write("Suggested status:", suggestion["status"],
                 "(you review before it counts)")
        occurred_at = st.text_input("Occurred at (ISO with timezone)",
                                    value=datetime.now(timezone.utc).isoformat())
        evidence = st.text_area("Evidence summary (required)",
                                value="Copied phrase: 'application received'")
        if st.button("Record reviewed event"):
            try:
                ok = record_reviewed_event(db, sel, source_id,
                                           suggestion["status"], occurred_at, evidence)
                st.success("Event recorded.") if ok else \
                    st.warning("Duplicate source ID - ignored.")
            except Exception as exc:
                st.error(f"Could not record: {exc}")
    else:
        st.info("Save an application first.")

# --------------------------------------------------------------------------
# Step 6 - End-of-day digest preview (Asia/Kolkata)
# --------------------------------------------------------------------------

st.markdown('<h2 class="stephead">6 · End-of-day digest preview</h2>',
            unsafe_allow_html=True)
today_ist = datetime.now(timezone.utc).astimezone(IST).date()
day = st.date_input("Digest day (Asia/Kolkata)", value=today_ist)
st.code(daily_digest(events(db), day.isoformat()), language=None)
st.caption("Preview only - nothing is scheduled or sent. A real digest would "
           "arrive only after you explicitly set it up.")

# --------------------------------------------------------------------------
# Honest limitations
# --------------------------------------------------------------------------

st.markdown('<h2 class="stephead">What this demo does NOT do</h2>', unsafe_allow_html=True)
st.markdown("""
- **Job openings are LIVE by default** - fetched read-only from public
  Greenhouse career boards (one polite request per board, cached 30 minutes).
  Their requirement lists are auto-extracted keywords, so they can be
  incomplete; always read the real posting. If the boards are unreachable the
  app falls back to synthetic fixtures clearly labelled OFFLINE DEMO DATA.
- **Emails and the demo candidate remain synthetic.** No real inbox is
  connected in this public demo.
- **Tailoring is deterministic, not an LLM rewrite and not an ATS score.** It
  reorders and selects your own facts with provenance; it cannot judge how a
  recruiter or an ATS will react.
- **No auto-apply, ever.** Jarvis prepares; you review and you hit send. Apply
  links open the company's own careers page.
- **The inbox is a fixture set.** Real Gmail integration needs OAuth consent,
  restricted-scope verification and private storage - none of that is claimed here.
- **The PDF is rendered in pure Python** (fpdf2 + bundled OFL Latin Modern
  fonts) in the same one-page template as the .tex source. The .tex stays
  available for Overleaf; the app never compiles LaTeX server-side.
- **The tracker database is temporary** - it resets when this cloud app restarts.
""")
st.caption("Built for Code for a Billion · Impact area: Tech Employment for Youth")
