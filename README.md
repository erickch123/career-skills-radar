# Career Radar

Career Radar helps you stay career-ready even when you're not actively applying for jobs. It integrates Singapore's SkillsFuture data with your CV, saved job alerts from your favorite job portals, and work logs to turn scattered signals into one explainable skills-gap view — so if a layoff happens or your goals shift, you already know where you stand and what to learn next.

Built for **PyCon SG 2026 Hackathon — Job & Skills Track**.

---

## Demo video

[Watch on Loom →](https://www.loom.com/share/c4c75719cd724c90837dfbb5bc7458f0)

---

## Diagrams

**User Journey & Features** — problems solved, feature flow, and outcomes:
[Open diagram file →](docs/diagrams/user-journey.excalidraw)

**Tech Stack** — frontend, backend, AI, data connectors, and infrastructure:
[Open diagram file →](docs/diagrams/tech-stack.excalidraw)

---

## What you need

| Requirement | Notes |
|---|---|
| Python 3.12+ | Backend |
| Node 18+ | Frontend |
| Anthropic API key | Powers the chat + seniority classification |
| Supabase project (free tier) | Postgres database |

Everything else (Gmail OAuth, Resend, Apify) is **optional** — the app falls back to demo/mock data automatically when those keys are absent.

---

## Quick start

### 1 — Clone and run the ETL (one-time)

```bash
git clone <repo-url>
cd career-skills-radar
python3 scripts/01_extract.py   # reads data/raw/*.xlsx → writes data/processed/
```

### 2 — Set up the backend

```bash
cd src/backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your keys (see below)
```

Run database migrations:
```bash
alembic upgrade head
```

Start the server:
```bash
fastapi dev main.py             # runs on http://localhost:8000
```

### 3 — Set up the frontend

```bash
cd src/frontend
npm install
npm run dev                     # runs on http://localhost:5173
```

Open **http://localhost:5173** — you should see the Career Radar chat interface.

---

## Environment variables

Edit `src/backend/.env`. Only the first two are required to run the full app:

```env
# ── Required ──────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...          # get from console.anthropic.com

# Supabase → Settings → Database → Session Pooler connection string
# Format: postgresql://postgres.PROJECTREF:PASSWORD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
DATABASE_URL=postgresql://...

# ── Optional: Gmail OAuth (LinkedIn / Indeed job alerts) ───────────
# Without this, Email Alerts shows realistic mock data instead.
# Setup: use Google Cloud OAuth credentials + token.json (see src/backend/.env.example)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback

# ── Optional: Resend (email notifications) ────────────────────────
# Without these, notification features are preview-only.
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=notifications@yourdomain.com

# ── Optional: Apify (job search) ─────────────────────────────────
# Without this, Job Search returns mock results instead of live scraping.
APIFY_API_KEY=apify_api_...

# ── Optional: public deployment ───────────────────────────────────
# Set to your deployed frontend URL so CORS allows it.
FRONTEND_ORIGIN=https://your-app.vercel.app

# Set to true to block all writes — use this for public demos so
# visitors can explore but cannot modify your data.
DEMO_READONLY=true
```

### Getting a Supabase database

1. Go to [supabase.com](https://supabase.com) → New project (free tier, takes ~1 min)
2. Project Settings → Database → **Session Pooler** connection string
3. Replace `[YOUR-PASSWORD]` with your project password
4. Paste as `DATABASE_URL` in `.env`
5. Run `alembic upgrade head` to create the tables

---

## Seed sample jobs (optional but recommended)

The repo includes a CSV of 190 Singapore tech/data/AI job postings:

```bash
# Make sure the backend is running first, then from project root:
python3 scripts/seed_jobs.py            # seeds all 190 jobs
python3 scripts/seed_jobs.py --skip 0  # re-seeds from scratch
```

---

## Demo walkthrough

1. **My CV** → paste your CV text → skills are extracted and mapped to SkillsFuture
2. **Add Job** → paste a job description → required skills are extracted
3. **Analyse Gap** → see your ranked skills gap map with readiness score
4. **Career Radar** → seniority distribution of your target roles + closest SkillsFuture career paths
5. **Job Search with Apify** → search LinkedIn & Indeed live (or mock data if no Apify key), add results to your shortlist
6. **Email Alerts** → LinkedIn / Indeed alert emails parsed from Gmail OAuth (or mock data if Gmail not connected)
7. **Chat** → ask anything, e.g. *"which job am I most ready for?"* — the agent calls real tools to answer

---

## Known limitations & post-hackathon roadmap

These are intentional scope decisions for the hackathon, not bugs. Documented here for future improvement.

### 1 — Single-user only (`USER_ID = 1`)

Every API endpoint hardcodes `USER_ID = 1`. There is no login, no session, and no data isolation. Two people using the app simultaneously will overwrite each other's CV, saved jobs, and work logs.

**Files to change:** All 9 files under `src/backend/api/` replace `USER_ID = 1` with a real session/auth identity. The schema already has `user_profile_id` foreign keys on every table — the DB is multi-user ready, only the API layer needs updating.

**Suggested approach:** Add a lightweight auth layer (e.g. Supabase Auth or FastAPI-Users) and pass `current_user.id` via a `Depends()` injection instead of the hardcoded constant.

---

### 2 — Skill synonym dictionary is tech/ICT-focused

`src/backend/core/matcher.py` has a hand-curated `SYNONYMS` dict that maps tool/framework shorthand (e.g. `"postman"`, `"llm"`, `"mcp"`) to canonical SkillsFuture skill titles. It currently covers only software, cloud, AI, and DevOps terms.

**The underlying data is not the problem.** `data/processed/skills_master.csv` has 2 316 skills and `data/processed/roles.csv` has 2 030 roles across 39 sectors including Accountancy, Financial Services, Engineering Services, Precision Engineering, Healthcare, Legal Services, and more. Exact-phrase and fuzzy matching already work for those sectors without synonyms.

**What's missing:** Synonym mappings for non-tech shorthand — e.g. `"excel modelling"` → `Financial Modelling`, `"solidworks"` → `CAD`, `"bloomberg"` → `Financial Data Analysis`. Add these to the `SYNONYMS` dict to improve extraction for non-tech CVs.

---

### 3 — No real-time streaming from Anthropic (pseudo-chunked)

The chat endpoint (`src/backend/api/chat.py`) calls the Anthropic API in blocking mode and then re-streams the final text in fixed 20-character chunks. It is not true token-by-token streaming.

**Impact:** Slight artificial delay on long responses; no real latency benefit over a regular POST.

**Fix:** Replace `client.messages.create(...)` with `client.messages.stream(...)` and yield each `text_delta` event as it arrives.

---

### 4 — Gmail OAuth credentials are local only

`credentials.json` and `token.json` for Gmail are stored on the local filesystem and excluded from git. A deployed version needs a secrets manager (e.g. Supabase Vault, AWS Secrets Manager) or OAuth token storage in the database.

---

### 5 — Apify actors require login cookies for full results

`src/backend/core/apify_connector.py` uses `curious_coder/linkedin-jobs-scraper` and `valig/indeed-jobs-scraper`. These work without stored login cookies for public listings, but may return fewer results or hit rate limits on heavy usage. For production, use actors that support cookie injection or a residential proxy pool.

---

## Project structure

```
career-skills-radar/
├── data/
│   ├── raw/           SkillsFuture Excel files + job CSV
│   └── processed/     ETL output (generated by scripts/01_extract.py)
├── scripts/
│   ├── 01_extract.py  ETL: Excel → CSVs
│   └── seed_jobs.py   Bulk-seed jobs from CSV via running backend
├── src/
│   ├── backend/       FastAPI app
│   │   ├── api/       Route handlers (chat, gap, jobs, insights, worklog, email_jobs)
│   │   ├── core/      Business logic (matcher, gap_engine, seniority, agent_tools, email_connector)
│   │   └── models/    SQLAlchemy models
│   └── frontend/      React + Vite + TypeScript
│       └── src/
│           └── components/   GapMap, CareerRadar, JobsList, EmailJobsPanel, NotifyPanel,
│                             WorkLogPanel, PastePanel, HistoryPanel, MarkdownMessage
└── docs/              PRD, ERD, Architecture, User Stories
```
