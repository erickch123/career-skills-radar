# Coding Agent Instructions

Read `AGENTS.md` first for shared project facts. This file is build-specific.

## Commands

`<!-- FILL IN as soon as these exist. Do not guess at framework defaults — a wrong command
wastes a turn and erodes trust in the rest of this file. -->`
- Install: `TBD`
- Run dev server: `TBD`
- Run tests: `TBD`
- Lint: `TBD`
- Run a single test file: `TBD`

## Non-negotiable constraints (don't do these things)

- **Never invent a SkillsFuture skill title.** Every skill name the matcher or synonym
  dictionary uses must be verified against `skills_master.csv` programmatically before shipping
  — write a one-off check script, don't eyeball it. This bit the project once already during
  planning (see `interaction-logs/DECISIONS.md`).
- **Don't assume the LinkedIn email body contains JD text.** Confirmed by direct inspection: it
  never does — title/company/location/date only (ARCHITECTURE §2.8). Any feature needing full
  JD text must go through the chat-paste path, not email parsing.
- **Don't gate core features behind a login wall.** Auth is optional — only "Connect Gmail"
  triggers OAuth. CV input, JD paste, Gap Map, Career Radar, Work Log must all work with zero
  login (ARCHITECTURE §2.9).
- **Don't give the chat a new write-capable tool without flagging it.** Its write access is
  exactly two paths today: new `WorkLogEntry` rows, and new/merged `SavedJob` rows from pasted
  JDs. If a task seems to need a third write path, stop and note it in
  `interaction-logs/DECISIONS.md` rather than quietly adding it — this boundary was a deliberate
  scope decision (USER_STORIES Epic E, story E6), not an oversight.
- **Apify result caps go in the actor's input parameters, never as a post-fetch slice.** Several
  actors bill per search-page regardless of how many results you keep afterward (ARCHITECTURE
  §2.12). A cap that only limits what's *displayed* doesn't save any credit.
- **If you touch `matcher.py`'s fuzzy-matching logic, re-test against the specific failure modes
  already found once during planning** (subset/superset over-matching, near-miss-but-distinct
  words like "change"/"channel", common-English-word skill titles like "Research"/"Cutting",
  substring matches inside unrelated words like "aws" inside "laws"). Concrete test recipes for
  each are in ARCHITECTURE §2.2. Don't assume a refactor preserves behavior without rerunning
  these specific cases.
- **Don't treat a 🔧 ("designed, not built") section of ARCHITECTURE.md as already validated.**
  Several explicitly state what still needs testing once implemented (e.g. the interest-level
  weighting in `rank_action_list`, ARCHITECTURE §2.3/§2.13). Build it, then actually test it —
  don't assume correctness transfers from the design doc.

## Before you start a non-trivial task

1. Check `docs/USER_STORIES.md` for the relevant epic/story and its acceptance criteria — build
   to that, not to your own guess at scope.
2. Check `docs/ARCHITECTURE.md` for the relevant component section — note its ✅/🔧/🔮 tag.
3. If your approach will differ from what's documented, say so and explain why before writing
   code, rather than silently diverging.

## When you're done

- Add a dated entry to `interaction-logs/DECISIONS.md`: what you built, any judgment calls you
  made that weren't explicitly specified, anything you deliberately left for the review agent
  to check.
- If you changed a 🔧 tag to ✅ in ARCHITECTURE.md, make sure you actually tested it, not just
  implemented it — these tags mean something specific in this project's docs (see AGENTS.md).
