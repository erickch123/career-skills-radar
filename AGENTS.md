# AGENTS.md — career-skills-radar

Read this first. For anything not covered here, read the referenced doc — do not guess.

**This project uses two agent roles with separate instructions:**
- Building/implementing code → also read `agent_docs/CODING_AGENT.md`
- Reviewing code (not the same session/agent that wrote it) → also read
  `agent_docs/REVIEW_AGENT.md`
If you don't know which role you're in, ask rather than assuming.

## What this project is

Chat-first (not dashboard) tool that builds an explainable skills-gap map from the SkillsFuture
dataset, a person's CV, saved job postings, and self-reported work logs. Full product framing:
`docs/PRD.md`. Full schema: `docs/ERD.md`. Full feature list with acceptance criteria:
`docs/USER_STORIES.md`. Full system design and rationale for every major choice:
`docs/ARCHITECTURE.md`.

## Tech stack (see `docs/ARCHITECTURE.md` §0 for rationale on every choice)

- Backend: Python, FastAPI
- Frontend: React, chat-first (no dashboard pages — see ARCHITECTURE §2.10)
- DB: PostgreSQL via Supabase (database only, NOT Supabase Auth — see ARCHITECTURE §2.9)
- Fuzzy matching: `rapidfuzz`
- LLM: provider-agnostic. Claude via plain `anthropic` SDK (primary). OpenAI via `openai-agents`
  SDK (deployment alternate). NOT `claude-agent-sdk` (wrong fit — see ARCHITECTURE §2.11). NOT
  OpenAI Agent Builder (deprecated, shuts down Nov 30 2026).
- Auth: self-implemented Google OAuth2 (`google-auth-oauthlib`). Optional — only required to
  connect Gmail. NOT Clerk/Auth0/Supabase Auth (see ARCHITECTURE §2.9 for why).
- Notification delivery: Resend (transactional email). NOT Clerk (no general send API), NOT
  SendGrid (free tier is a 60-day trial, not permanent).

## Where to look before asking

| Need to know... | Read |
|---|---|
| Why a feature exists / what it's for | `docs/PRD.md` |
| Exact acceptance criteria for a feature | `docs/USER_STORIES.md` |
| DB schema, entity relationships | `docs/ERD.md` |
| How a component works, what's tested vs. designed-only (✅/🔧/🔮 tags) | `docs/ARCHITECTURE.md` |
| Why a past decision was made a certain way, what was tried and rejected | `interaction-logs/DECISIONS.md` |

## Status tags used throughout the docs

`✅ Built & tested` · `🔧 Designed, not yet built` · `🔮 Roadmap, out of scope for now`. Don't
treat a 🔧 section as if it were validated — several explicitly say what still needs testing.

## When you make a non-trivial decision

Add a dated entry to `interaction-logs/DECISIONS.md` (what was decided, your reasoning, what
was delegated vs. human-judged). This file is part of the hackathon submission's required
interaction log — treat it as a deliverable, not a nice-to-have. Both coding and review agents
should log here — a review agent rejecting something, or flagging a risk the builder missed,
is exactly the kind of human/AI-judgment trail this file exists to capture.
