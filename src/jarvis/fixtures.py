"""Synthetic demo fixtures for the public Jarvis for Freshers demo.

Everything in this file is SYNTHETIC. Employers, people, metrics, emails and
URLs are invented so the public demo never exposes a real person's data.
Fixture IDs are stable: tests and saved tracker records refer to them.
"""

# ---------------------------------------------------------------------------
# Synthetic candidate profile
# ---------------------------------------------------------------------------
# A profile is a dict of contact fields plus "facts": atomic, truthful resume
# lines. Each fact has a stable ID, a section, the text itself, and the
# canonical skills the fact evidences (see core.SKILL_ALIASES). Tailoring may
# reorder, select and group facts; it may never invent a fact.

BASE_RESUME = {
    "source": "synthetic",
    "name": "Aarav Sharma (Synthetic Demo Candidate)",
    "email": "aarav.sharma@example.invalid",
    "phone": "+91-90000-00000",
    "location": "Bengaluru, India",
    "facts": [
        {"id": "F01", "section": "education",
         "text": "B.Tech in Computer Science, XYZ Institute of Technology, Bengaluru, expected May 2027, CGPA 8.4/10.",
         "skills": ["data-structures"]},
        {"id": "F02", "section": "experience",
         "text": "Software Engineering Intern at DemoTech Labs (synthetic), May-Jul 2026: built REST APIs in Python using Flask for an internal inventory tool.",
         "skills": ["python", "rest-api", "git"]},
        {"id": "F03", "section": "experience",
         "text": "Wrote unit tests with pytest during the internship, raising coverage of the inventory service from 40% to 85% (synthetic metric).",
         "skills": ["python", "testing"]},
        {"id": "F04", "section": "project",
         "text": "Built a data analysis project cleaning and exploring 100k rows of public transport data with Python, pandas and SQL.",
         "skills": ["python", "pandas", "sql"]},
        {"id": "F05", "section": "project",
         "text": "Created Matplotlib dashboards visualising bus delays, presented at a college fest to 200+ attendees.",
         "skills": ["data-visualization", "communication"]},
        {"id": "F06", "section": "project",
         "text": "Trained a scikit-learn logistic regression classifier to predict bus delays (0.81 F1, synthetic portfolio metric).",
         "skills": ["machine-learning", "statistics", "python"]},
        {"id": "F07", "section": "project",
         "text": "Deployed the delay-prediction model as a Flask API in a Docker container on a free cloud tier.",
         "skills": ["docker", "rest-api"]},
        {"id": "F08", "section": "skill",
         "text": "Languages and tools: Python, SQL, pandas, NumPy, scikit-learn, Flask, Docker, Git, Linux, Excel.",
         "skills": ["python", "sql", "pandas", "numpy", "machine-learning",
                    "rest-api", "docker", "git", "linux", "excel"]},
        {"id": "F09", "section": "education",
         "text": "Relevant coursework: Data Structures and Algorithms, DBMS, Statistics, Machine Learning.",
         "skills": ["data-structures", "sql", "statistics", "machine-learning"]},
        {"id": "F10", "section": "experience",
         "text": "Tech-team lead for the college coding club: organised 4 workshops on Git and Python for 60+ first-year students.",
         "skills": ["git", "python", "communication"]},
        {"id": "F11", "section": "education",
         "text": "Class XII (CBSE), 2023, 92%.",
         "skills": []},
        {"id": "F12", "section": "project",
         "text": "Automated Excel grade reports with Python (openpyxl), saving the placement cell about 6 hours per week (synthetic metric).",
         "skills": ["python", "excel"]},
    ],
}

# ---------------------------------------------------------------------------
# Synthetic job openings (fresher / intern level, India + remote)
# ---------------------------------------------------------------------------
# requirements.required: things the posting says a candidate must have.
# requirements.preferred: nice-to-haves. Tailoring and gap analysis both read
# these lists, so keep them concrete and skill-shaped.

JOB_FIXTURES = [
    {"id": "job-ml-intern-01", "title": "Machine Learning Intern",
     "company": "SynthWave Analytics (Synthetic)", "location": "Bengaluru",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-ml-intern-01",
     "description": "Join a small applied ML team building demand-forecasting models. "
                    "You will clean data, train baseline models and evaluate them with the team.",
     "requirements": {
         "required": ["Python", "machine learning (scikit-learn)", "statistics", "SQL"],
         "preferred": ["deep learning basics", "Docker", "data visualization"]}},
    {"id": "job-data-analyst-01", "title": "Data Analyst (Fresher)",
     "company": "Nimbus Insights (Synthetic)", "location": "Hyderabad",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-data-analyst-01",
     "description": "Turn messy operational data into weekly dashboards and ad-hoc analyses "
                    "for retail clients.",
     "requirements": {
         "required": ["SQL", "Excel", "data visualization", "communication and presentation"],
         "preferred": ["Python", "pandas", "Power BI or Tableau"]}},
    {"id": "job-backend-01", "title": "Backend Engineer Intern",
     "company": "CloudKart Labs (Synthetic)", "location": "Remote (India)",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-backend-01",
     "description": "Build and test REST APIs for an e-commerce ordering service.",
     "requirements": {
         "required": ["Python", "REST API development (Flask/FastAPI/Django)", "SQL", "Git"],
         "preferred": ["Docker", "AWS or other cloud", "testing with pytest"]}},
    {"id": "job-frontend-01", "title": "Frontend Developer Intern",
     "company": "PixelForge Studio (Synthetic)", "location": "Bengaluru",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-frontend-01",
     "description": "Implement responsive UI components for a design-tooling web app.",
     "requirements": {
         "required": ["JavaScript (React)", "HTML/CSS", "Git"],
         "preferred": ["TypeScript", "testing", "REST APIs"]}},
    {"id": "job-data-eng-01", "title": "Data Engineering Intern",
     "company": "Riverline Data (Synthetic)", "location": "Pune",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-data-eng-01",
     "description": "Help maintain batch data pipelines feeding analytics warehouses.",
     "requirements": {
         "required": ["Python", "SQL", "ETL / data pipelines"],
         "preferred": ["Airflow", "Docker", "Linux"]}},
    {"id": "job-swe-01", "title": "Software Engineer - New Grad",
     "company": "HexaSoft Systems (Synthetic)", "location": "Hyderabad",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-swe-01",
     "description": "Generalist new-grad role rotating across product teams.",
     "requirements": {
         "required": ["data structures and algorithms", "Python, Java or C++", "Git",
                      "Bachelor's degree in Computer Science (2026/2027 batch)"],
         "preferred": ["Linux", "testing", "AWS or other cloud"]}},
    {"id": "job-ml-eng-01", "title": "Junior ML Engineer",
     "company": "Drishti AI (Synthetic)", "location": "Remote (India)",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-ml-eng-01",
     "description": "Productionise computer-vision and text models for document processing.",
     "requirements": {
         "required": ["Python", "machine learning", "deep learning basics", "statistics"],
         "preferred": ["NLP", "Docker", "SQL"]}},
    {"id": "job-business-analyst-01", "title": "Business Analyst Intern",
     "company": "Meridian Consult (Synthetic)", "location": "Mumbai",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-business-analyst-01",
     "description": "Support client engagements with quantitative analysis and slide-ready "
                    "storytelling.",
     "requirements": {
         "required": ["Excel", "SQL", "communication and presentation",
                      "Bachelor's degree (any discipline, 2026/2027 batch)"],
         "preferred": ["Python", "data visualization", "statistics"]}},
    {"id": "job-devops-01", "title": "DevOps Intern",
     "company": "StackHarbor (Synthetic)", "location": "Chennai",
     "source": "synthetic", "url": "https://example.invalid/jobs/job-devops-01",
     "description": "Keep CI pipelines and container builds healthy for a small platform team.",
     "requirements": {
         "required": ["Linux", "Git", "Docker", "scripting (Python or Bash)"],
         "preferred": ["AWS or other cloud", "CI/CD (GitHub Actions)", "testing"]}},
]

# ---------------------------------------------------------------------------
# Synthetic tracker applications + inbox fixtures
# ---------------------------------------------------------------------------
# Applications already exist in the tracker; email fixtures then arrive against
# them. Every fixture carries the exact application ID and a unique source_id
# so processing is idempotent (rerun = duplicates, never double-counted).

SYNTHETIC_APPLICATIONS = [
    {"id": "app-001", "company": "SynthWave Analytics (Synthetic)",
     "role": "Machine Learning Intern", "job_url": "https://example.invalid/jobs/job-ml-intern-01"},
    {"id": "app-002", "company": "Nimbus Insights (Synthetic)",
     "role": "Data Analyst (Fresher)", "job_url": "https://example.invalid/jobs/job-data-analyst-01"},
    {"id": "app-003", "company": "CloudKart Labs (Synthetic)",
     "role": "Backend Engineer Intern", "job_url": "https://example.invalid/jobs/job-backend-01"},
    {"id": "app-004", "company": "HexaSoft Systems (Synthetic)",
     "role": "Software Engineer - New Grad", "job_url": "https://example.invalid/jobs/job-swe-01"},
]

# Deliberately includes one ambiguous message (interview + rejection language),
# one out-of-order message (older than the application's latest event) and one
# message that conflicts with a terminal state. Processing must HOLD these for
# human review instead of guessing.
EMAIL_FIXTURES = [
    {"source_id": "msg-001", "application_id": "app-001",
     "subject": "Application received - Machine Learning Intern",
     "body": "Thank you for applying to SynthWave Analytics. Your application received "
             "confirmation means we will review it shortly.",
     "occurred_at": "2026-11-10T09:15:00+05:30",
     "evidence": "Phrase matched: 'application received' / 'thank you for applying'"},
    {"source_id": "msg-002", "application_id": "app-001",
     "subject": "Interview invitation - SynthWave Analytics",
     "body": "We would like to schedule an interview with you next week. Please pick a slot.",
     "occurred_at": "2026-11-12T14:00:00+05:30",
     "evidence": "Phrase matched: 'schedule an interview'"},
    {"source_id": "msg-003", "application_id": "app-002",
     "subject": "Thank you for applying - Data Analyst",
     "body": "Your application received our attention. We will be in touch.",
     "occurred_at": "2026-11-11T10:00:00+05:30",
     "evidence": "Phrase matched: 'thank you for applying'"},
    {"source_id": "msg-004", "application_id": "app-002",
     "subject": "Update on your application",
     "body": "We regret to inform you that we are not moving forward with your application.",
     "occurred_at": "2026-11-13T09:00:00+05:30",
     "evidence": "Phrase matched: 'regret to inform'"},
    {"source_id": "msg-005", "application_id": "app-003",
     "subject": "Interview invitation",
     "body": "Although we are not moving forward with other candidates, we would like to "
             "schedule an interview with you.",
     "occurred_at": "2026-11-12T11:00:00+05:30",
     "evidence": "Conflicting phrases; held for review by design"},
    {"source_id": "msg-006", "application_id": "app-004",
     "subject": "Application received - Software Engineer",
     "body": "Thank you for applying. Your application received a tracking number.",
     "occurred_at": "2026-11-13T18:30:00+05:30",
     "evidence": "Phrase matched: 'application received'"},
    {"source_id": "msg-007", "application_id": "app-004",
     "subject": "Thank you for applying",
     "body": "Thank you for applying to HexaSoft Systems.",
     "occurred_at": "2026-11-10T08:00:00+05:30",
     "evidence": "Out-of-order fixture; held by the chronology guard"},
    {"source_id": "msg-008", "application_id": "app-002",
     "subject": "Interview invitation - Nimbus Insights",
     "body": "We would like to schedule an interview after all.",
     "occurred_at": "2026-11-13T17:00:00+05:30",
     "evidence": "Conflicts with terminal state; held by the terminal-state guard"},
]
