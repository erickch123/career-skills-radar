# Execution Plan — Career Radar Prototype

Phased build order from scaffolding to full hackathon demo. Each phase ends at a demo-able checkpoint.

| Phase | Name | Status |
|---|---|---|
| 0 | Project Scaffolding | ✅ Done |
| 1 | Data Foundation | ✅ Done |
| 2 | Database | ⬜ Not started |
| 3 | Chat Shell + LLM Core | ⬜ Not started |
| 4 | CV + JD Paste + Gap Map | ⬜ Not started |
| 5 | Seniority + Career Radar | ⬜ Not started |
| 6 | Full Agentic Work Log Chat | ⬜ Not started |
| 7 | Email Connector (Gmail OAuth) | ⬜ Not started |
| 8 | Apify + Notifications | ⬜ Not started |
| 9 | Polish + Demo Prep | ⬜ Not started |

---

## Phase 0 — Project Scaffolding
**Goal:** Both services run locally and communicate.

- [x] `src/backend/` — FastAPI project (`main.py`, `requirements.txt`)
- [x] `src/frontend/` — React + Vite + TypeScript scaffold (create-vite 9.1.0)
- [x] CORS configured (frontend `localhost:5173` → backend `localhost:8000`)
- [x] `GET /api/health` confirmed reachable — returns `{"status":"ok","service":"career-radar-api"}`
- [x] `CODING_AGENT.md` install/run/test commands filled in
- [x] `.env.example` with required keys documented

---

## Phase 1 — Data Foundation
**Goal:** SkillsFuture data is queryable; matcher and gap engine work against real CSVs.

- [ ] `scripts/01_extract.py` — reads 3 Excels → writes 5 CSVs to `data/processed/`
- [ ] `src/backend/core/matcher.py` — hybrid exact / synonym / fuzzy matching
- [ ] `src/backend/core/gap_engine.py` — `analyze_jd_vs_cv`, `aggregate_demand`, `rank_action_list`, `find_closest_roles`, `readiness_score`
- [ ] Tests against all 5 documented failure modes (ARCHITECTURE §2.2)
- [ ] FastAPI endpoint `POST /api/match` — accepts free text, returns canonical skills

---

## Phase 2 — Database
**Goal:** Supabase Postgres running with full ERD schema.

- [ ] Supabase project created, `DATABASE_URL` in `.env`
- [ ] Migration file covering all 7 tables from ERD.md
- [ ] SQLAlchemy models in `src/backend/models/`
- [ ] Alembic configured; `alembic upgrade head` tested

---

## Phase 3 — Chat Shell + LLM Core  ⭐ first demo checkpoint
**Goal:** A working chat UI that talks to Claude.

- [ ] `src/frontend/` — chat UI: message list + input + streaming
- [ ] `src/backend/core/llm_provider.py` — `extract_structured`, `classify_with_reasoning`, `agent_tool_call` (Claude backend)
- [ ] `src/backend/chat.py` — FastAPI `POST /api/chat` with SSE streaming
- [ ] Milestone: free-text chat works end-to-end

---

## Phase 4 — CV + JD Paste + Gap Map  ⭐ core demo checkpoint
**Goal:** Fundamental value proposition demonstrable.

- [ ] CV paste → matcher → `UserProfile` + `SKILL_MATCH_CACHE` saved
- [ ] JD paste-and-parse via chat (Epics E7–E9): extraction → `SavedJob` + cache
- [ ] Duplicate/merge check with confirmation
- [ ] Gap Map rendered **inline in chat** via Recharts (ranked list + `why` per item)
- [ ] Readiness score displayed

---

## Phase 5 — Seniority + Career Radar  ⭐ second visual checkpoint
**Goal:** Charts work; every saved job has a seniority tier.

- [ ] `src/backend/core/seniority.py` — rule-based Tier 1 + LLM escalation Tier 2
- [ ] Career Radar Chart A (activity timeline) — inline Recharts
- [ ] Career Radar Chart B (seniority distribution) — inline Recharts
- [ ] Career Pathfinder — closest roles by overlap count

---

## Phase 6 — Full Agentic Work Log Chat  ⭐ strongest demo moment
**Goal:** Chat is aware of the whole system.

- [ ] Work Log extraction (E1–E4): free-form → `WorkLogEntry` + skill cache
- [ ] Three-way CV / Market / Work Log comparison in Gap Map (C4)
- [ ] 7 read-only tool wrappers wired to agent
- [ ] Agentic Q&A: "which job am I most ready for?" chains real tool calls

---

## Phase 7 — Email Connector (Gmail OAuth)
**Goal:** Any reviewer can connect their own Gmail.

- [ ] Google Cloud OAuth2 client configured
- [ ] `src/backend/email_connector.py` — parse LinkedIn/Indeed alert emails
- [ ] Synthetic sample dataset shown before any OAuth connection
- [ ] "Unverified app" disclosure in UI

---

## Phase 8 — Apify + Notifications
**Goal:** Active job search works; real notification emails fire.

- [ ] `src/backend/apify_connector.py` — cookieless actors, cap as input param
- [ ] `src/backend/notification_engine.py` — schema-driven rules + Resend delivery
- [ ] At least one notification rule fires and real email lands in inbox

---

## Phase 9 — Polish + Demo Prep
**Goal:** Demo runs without a scripted happy path.

- [ ] Seed script with realistic sample data
- [ ] `interest_level` inference wired into `rank_action_list`
- [ ] Error handling + fallback responses in chat
- [ ] All judgment calls logged to `interaction-logs/DECISIONS.md`
- [ ] Update `CODING_AGENT.md` with final commands
