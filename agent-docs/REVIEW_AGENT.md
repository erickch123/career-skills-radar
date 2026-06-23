# Review Agent Instructions

Read `AGENTS.md` first for shared project facts. This file is review-specific.

**You are a second, independent check — not a rubber stamp.** Don't take the coding agent's own
summary of what it did as proof that it did it correctly. Verify directly: run the actual checks
below, read the actual diff, don't just read the commit message or the DECISIONS.md entry the
builder wrote about itself.

## Checklist — derived from mistakes this project already made once during planning

These aren't hypothetical risks. Each one was a real bug found and fixed during this project's
planning phase (see `interaction-logs/DECISIONS.md` for the original incidents). Re-checking for
them is the highest-value thing you can do, because they're proven failure modes, not guesses.

- [ ] **Any new or modified skill-matching code**: does every skill title it references actually
  exist in `skills_master.csv`? Don't trust that it looks plausible — check it programmatically
  (load the CSV, diff against referenced titles).
- [ ] **Any new or modified fuzzy-matching threshold/logic**: does it produce false positives on
  the known trap cases — subset/superset matches (e.g. "change management" matching
  "Organisational Change Management"), near-miss-but-different words ("change" vs "channel"),
  common English words used casually in a sentence ("we do cutting-edge research")? Test it
  against these directly, don't just read the code and assume it's fine.
- [ ] **Any Apify integration code**: is the result cap passed as an actor *input parameter*
  (e.g. `maxItems`), or is it just slicing a larger returned list in Python? The latter doesn't
  save money against page-billed actors and should be rejected.
- [ ] **Any new chat tool**: does it only read, or can it write/modify/delete something? If it
  writes, is it one of the two approved paths (`WorkLogEntry` creation, `SavedJob` creation/merge
  from pasted JD)? A third write path should be flagged, not silently approved.
- [ ] **Any feature touching login/auth**: does it work without login for anything other than
  Gmail connection specifically? If a core feature now silently requires auth, that's a
  regression against the optional-auth model (ARCHITECTURE §2.9) and should be rejected.
- [ ] **Any code assuming LinkedIn email bodies contain JD text**: reject it. Confirmed false by
  direct inspection (ARCHITECTURE §2.8).
- [ ] **Any new ranking/scoring logic** (e.g. changes to `rank_action_list`): is the reasoning
  for the score visible in the output (a `why` field or equivalent), or is it folded into an
  opaque number? This project's explainability requirement means every ranking factor must be
  statable in plain language, not just computed correctly.

## General review questions, beyond the checklist

- Does the implementation match the acceptance criteria in `docs/USER_STORIES.md` for the
  relevant story, or does it do something adjacent-but-different?
- If the builder marked something ✅ in `docs/ARCHITECTURE.md`, did they actually add a test for
  it, or just implement it and assume it works?
- Is there a `docs/PRD.md` "Known Limitations" item this change should update, add to, or
  resolve? If the change fixes a stated limitation, the PRD should be updated to reflect that —
  don't leave the docs claiming a limitation that no longer exists.

## When you find a problem

Don't just fix it silently. Note what was wrong and why in `interaction-logs/DECISIONS.md` —
a review agent catching a real issue is exactly the kind of AI-contribution evidence this
project's hackathon submission needs documented, per the existing entries in that file.

## When you find nothing wrong

Say so explicitly, and say what you actually checked (not just "looks good"). A review that
doesn't show its work is not meaningfully different from no review.
