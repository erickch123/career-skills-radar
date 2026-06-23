# User Stories

Format: `As a [user], I want [capability], so that [outcome]`, with explicit acceptance
criteria. Stories are grouped by feature area; feature areas map directly to PRD.md section 6
and to ARCHITECTURE.md component boundaries.

---

## Epic A — Profile & Data Ingestion

**A1.** As a user, I want to paste or upload my CV text, so that the system has a baseline of my
current evidenced skills.
- *Acceptance:* CV text is run through the skill matcher; extracted canonical skills are
  displayed back to me with the matching method (exact/synonym/fuzzy) and source text snippet
  for each, before being saved to my profile.

**A2.** As a user, I want to review and correct the skills extracted from my CV, so that the rest
of the tool isn't working from a wrong baseline.
- *Acceptance:* extracted skills list is editable (remove false positives, add missed skills)
  before being committed to `UserProfile`.

**A3.** As a user, I want to simulate syncing my saved LinkedIn job alerts, so that I can see the
intended end-state workflow without manually pasting each job.
- *Acceptance:* a "Sync Job Alerts" action bulk-loads a sample set of JDs tagged
  `source="linkedin_email_simulated"`, each with a generated `date_saved` timestamp, without
  requiring me to paste them individually.

**A4.** As a user, I want each saved job to be automatically tagged with a seniority tier, so
that I don't have to manually classify every posting.
- *Acceptance:* every saved JD has a `seniority_tier` and a `seniority_method` (`rule` or `llm`)
  and, for LLM-classified items, a one-sentence `seniority_reasoning` I can read.

---

## Epic B — Career Radar (rendered inline on request, chat-first per ARCHITECTURE.md §2.10)

**B1.** As a user, I want to see when I've been saving jobs over time, so that I notice if I've
gone quiet on market-scanning.
- *Acceptance:* Chart A renders saved jobs on a timeline (X = `date_saved`, Y = seniority tier);
  gaps of inactivity are visually obvious.

**B2.** As a user, I want to see how far above my current level the jobs I save tend to be, so
that I can validate (or challenge) my own assumption that I save jobs ~2 years ahead of myself.
- *Acceptance:* Chart B shows a distribution of (saved job seniority tier − my current tier)
  across all saved jobs; the chart includes a plain-language summary line, e.g. "Most of your
  saved jobs sit 1–2 tiers above your current level."

**B3.** As a user, I want to click any point on the radar and drill into that specific job's gap
analysis, so that the radar is a navigation surface, not just a static chart.
- *Acceptance:* clicking a point routes to that job's detail view showing the matched/missing
  skill breakdown (reuses Gap Map logic, scoped to one job).

---

## Epic C — Gap Map

**C1.** As a user, I want a ranked, capped list of my top missing skills (not every missing
skill), so that I'm not overwhelmed.
- *Acceptance:* the action list returns at most N items (default 10), each sorted by a stated
  priority score, never an unranked flat dump.

**C2.** As a user, I want to know *why* a skill is ranked where it is, so that I trust the
recommendation instead of treating it as an opaque AI score.
- *Acceptance:* every ranked item displays: how many of my saved JDs demand it, and whether it's
  flagged Emerging/CASL by SkillsFuture — stated in one readable sentence, with the underlying
  numbers visible, not hidden.

**C3.** As a user, I want to filter the Gap Map by time horizon (e.g. "only show gaps for jobs
2+ seniority tiers above me"), so that I can separate "skills I need now" from "skills I'm
building toward."
- *Acceptance:* a horizon filter control re-runs the aggregation scoped to the filtered subset of
  saved JDs and updates the ranked list and readiness score accordingly.

**C4.** As a user, I want to see a three-way comparison — my CV, the market (saved JDs), and my
actual recent work (Work Log) — so that I can catch CV staleness, not just market gaps.
- *Acceptance:* each skill in the Gap Map view is tagged with which of the three sources
  evidence it (CV / Market / Work Log), and skills present in Work Log but absent from CV are
  visually flagged as "update your CV."

**C5.** As a user, I want an overall readiness score, so that I have one number to track over
time instead of re-reading the full gap list every time.
- *Acceptance:* readiness score = average % of each saved JD's required skills I already
  evidence; displayed with the per-JD breakdown available on demand (not just the aggregate,
  so the number is auditable).

---

## Epic D — Career Pathfinder

**D1.** As a user, I want to see which SkillsFuture job roles most closely match my current
skill set, so that I can discover adjacent roles I hadn't considered.
- *Acceptance:* returns roles ranked by overlap count (not raw percentage, to avoid bias toward
  roles with very few listed required skills — see ARCHITECTURE.md for the scoring rationale),
  each with the specific matched skills shown as evidence and the remaining gap skills listed.

---

## Epic E — Work Log Chat

**E1.** As a user, I want to describe what I've been working on in my own words, so that logging
my recent work doesn't feel like filling out a form.
- *Acceptance:* chat accepts free-form text input at any time, as the application's primary
  interface (see ARCHITECTURE.md §2.10) — not a secondary panel confined to part of the
  experience.

**E2.** As a user, I want the system to tell me what skills it picked up from what I said, so
that I can confirm or correct it in the same conversation.
- *Acceptance:* each turn's structured extraction (skills mentioned, activity summary, confidence
  level) is shown back to me conversationally; low-confidence extractions trigger a clarifying
  follow-up question rather than being silently accepted.

**E3.** As a user, I want to immediately see if what I just described isn't reflected on my CV,
so that I know to update it before I forget.
- *Acceptance:* skills extracted from a Work Log entry that are absent from `UserProfile`'s CV
  skill set are flagged in the same chat turn, with an offer to draft a CV bullet for them.

**E4.** As a user, I want to know if what I'm currently doing still overlaps with what the market
wants, so that I notice if my day-to-day work is drifting away from in-demand skills.
- *Acceptance:* Work Log skills are cross-checked against the aggregate saved-JD demand signal;
  overlaps and non-overlaps are both stated explicitly (the tool does not claim to judge
  "meaningfulness" or impact — only skill-presence overlap, per PRD.md section 8).

**E5.** As a user, I want to ask the chat questions about any part of my data — my readiness
score, my biggest gaps, which saved job I'm closest to being ready for — without leaving the
conversation to go find that page, so the chat feels like one coherent assistant rather than a
narrow logging form.
- *Acceptance:* the chat can call read-only tools wrapping `readiness_score`,
  `rank_action_list`, `find_closest_roles`, and queries over `SavedJob` /
  `UserProfile` / `WorkLogEntry` / `Notification`; answers are composed from the real returned
  values of these calls, not generated independently of them — so an inline chart rendered in
  one conversation and a spoken answer in another never disagree, because both are backed by
  the same function call.

**E6.** As a user, I want to trust that the chat can't accidentally change my data in ways I
didn't ask for while we're just talking, so I don't have to be careful about every word I type.
- *Acceptance:* none of the chat's read-only tools (E5) can create, modify, or delete anything.
  The chat's write capabilities are exactly two, both requiring the person's own explicit
  input to trigger: (a) creating new `WorkLogEntry` rows from described recent work (E1–E3),
  and (b) creating or — only with explicit confirmation — merging into a `SavedJob` row from a
  pasted job description (E7–E9). This boundary is enforced at the tool-definition level (no
  other mutating function is exposed to the chat for general Q&A), not just by prompting the
  model to behave.

**E7.** As a user, I want to paste a full job description into the chat and have it parsed into
my saved jobs automatically, so that I don't have to fill out a separate form for every role I
want to analyze deeply.
- *Acceptance:* pasting JD text into the chat produces a complete `SavedJob` record (company,
  title, seniority tier with reasoning, extracted skills via the same `matcher.py` used
  elsewhere) without the person needing to manually categorize anything; this is how a
  title/company/date-only "spotted" entry (from the Email Connector, Epic G) becomes a fully
  analyzable one, since the email connector itself can never supply the JD body text.

**E8.** As a user, if the chat can't clearly tell the company name (or another expected field)
from what I pasted, I want it to ask me rather than guess or leave it blank.
- *Acceptance:* if `company` (or another expected field) isn't clearly present in the parsed
  text, the chat asks a clarifying question before saving the record, rather than silently
  inserting a blank or fabricated value.

**E9.** As a user, if I paste a JD for a role I'd already spotted via email alert, I want the
chat to offer to attach it to that existing entry instead of creating a confusing duplicate —
but I want to confirm that before it happens.
- *Acceptance:* the parsed `(company, title)` is fuzzy-matched against existing email-sourced
  entries that don't yet have full JD text; if exactly one strong match is found, the chat asks
  for explicit confirmation before merging; if multiple or no clear match exists, a new entry is
  created without prompting a merge — ambiguous matches are never auto-resolved.

---

## Epic F — Notifications (schema-driven, per PyCon Day 2 talk pattern; delivered via email)

**F1.** As a user, I want to be nudged if I've gone quiet on scanning the market or logging work,
so that I don't drift into the exact "caught flat-footed" scenario this tool exists to prevent.
- *Acceptance:* an `inactivity` rule fires when no `SavedJob` or `WorkLogEntry` has been created
  in N days (configurable; default 14), sending a real email via Resend to the person's
  `notification_email`, and does not re-fire for the same condition until the condition resets
  (`last_fired_at` dedup, per the talk's lesson on duplicate-send bugs).

**F2.** As a user, I want to be alerted when a skill newly flagged "Emerging" by SkillsFuture
shows up in multiple of my saved jobs, so that I catch rising trends early rather than noticing
them a year later.
- *Acceptance:* a rule evaluates whether any skill crosses a configurable saved-JD-count
  threshold AND is flagged `is_emerging`; firing sends an email naming the specific skill and
  the count of JDs that reference it.

**F3.** As a developer/judge inspecting the system, I want notification rules to be data rows,
not hardcoded per-type logic, so that adding a new alert type doesn't require a code change.
- *Acceptance:* `NotificationRule` table holds trigger type, condition logic reference, and
  schedule metadata; a single evaluator function processes all active rules generically (see
  ARCHITECTURE.md for the schema and evaluator design, adapted from the Kakaobank notification
  system talk).

**F4.** As a user, I want notifications to arrive as real emails rather than as items inside the
application that I have to remember to open and check, so the notification system actually
solves the "remembering to check" problem instead of just relocating it.
- *Acceptance:* `NOTIFICATION` rows represent outbound email sends (recipient, subject,
  delivery status, Resend's own message ID for tracing) rather than a read/unread in-app list;
  delivery is via the Resend API, chosen specifically because it is a genuinely free,
  non-expiring transactional email service (3,000/month, permanent) — Clerk was considered and
  rejected because it is an identity platform with no general-purpose notification-sending API,
  and SendGrid was considered and rejected because its free tier is now a 60-day trial rather
  than permanent (confirmed via direct research, not assumed).

**F5.** As a user who has never connected my Gmail account, I want the system to behave
sensibly rather than fail or send to a wrong address, given that I haven't given it a place to
notify me.
- *Acceptance:* if `USER_PROFILE.notification_email` is null (i.e. Gmail has never been
  connected, per the optional-auth model in ARCHITECTURE.md section 2.9), the notification
  evaluator skips sending for that person without erroring — this is documented as a real,
  accepted limitation of the optional-auth design (notifications are only deliverable to people
  who have connected an account), not silently patched around with an invented address.

---

## Epic G — Email Connector (real external integration, multi-user OAuth)

**G1.** As a reviewer/user, I want to connect my own Gmail account to see the feature work
against my real inbox, so that I can verify this is a genuine integration, not a mockup.
- *Acceptance:* a "Connect your Gmail" action initiates a real OAuth2 authorization-code flow
  requesting `gmail.readonly` scope only; on completion, the connected account's own inbox (not
  the project author's) is what gets searched. The underlying search/parse logic was directly
  tested against a real inbox during the build (201 matching LinkedIn threads found in one test
  query) — proving the mechanism works — though the deployed OAuth wiring itself is a separate
  implementation step from that validated parsing logic.

**G2.** As the project author, I want my own personal Gmail to never be exposed to the deployed
app or to reviewers, so that building this feature doesn't create a privacy risk for me.
- *Acceptance:* the deployed application contains no hardcoded reference to the author's
  account; all email access happens through the generic per-user OAuth flow described in G1;
  the author's own local testing (done during development, documented in
  ARCHITECTURE.md/DECISIONS.md) is not wired into the deployed runtime path.

**G3.** As a reviewer who doesn't want to connect any account, I want to still see what the
feature produces, so that I'm not blocked from evaluating the project.
- *Acceptance:* a clearly-labeled synthetic sample dataset (structurally modeled on the real
  LinkedIn digest format found during testing) is shown by default, before any OAuth connection
  is made, with an explicit "sample data" label distinguishing it from a live connection.

**G4.** As a user, I want each job mentioned in a digest email to become its own entry, so that
a single email containing 5 jobs doesn't collapse into one undifferentiated record.
- *Acceptance:* the parser splits each email body on the provider's fixed separator and produces
  one `{title, company, location}` record per job chunk; verified against real LinkedIn emails
  containing multiple jobs per digest during the build.

**G5.** As a user, I don't want footer/navigation content ("See all jobs on LinkedIn", "View all
jobs", "Expand your search") to be misread as fake job entries.
- *Acceptance:* an explicit filter list excludes chunks whose first line matches known
  navigation/footer markers; this was a real bug found during testing (footer content shares the
  same line-structure as a job chunk) and fixed before being considered done.

**G6.** As a user, I want to know honestly what this connector can and can't give me, so I don't
assume it replaces pasting a full JD when I want deep skill-gap analysis on a specific role.
- *Acceptance:* the product clearly distinguishes "spotted" jobs (title/company/date only, from
  the email connector) from "analyzed" jobs (full skill-gap breakdown, requiring the JD text to
  be pasted into the Work Log Chat per Epic E, stories E7–E9) — this distinction is visible in
  the UI, not just in internal documentation, since LinkedIn's alert emails were confirmed (by
  direct inspection, not assumption) to never include responsibilities/requirements text.

**G7.** As a cautious reviewer, I want to understand why Google shows an "unverified app"
warning before I decide whether to proceed, so that I can make an informed choice.
- *Acceptance:* the UI states, before the OAuth redirect happens, that the warning is expected
  for a hackathon-scoped project (Google's verification process wasn't pursued given the
  timeline) and names the exact scope being requested (read-only Gmail search).

**G8.** As a user, I want this connector to read jobs that LinkedIn's/Indeed's own
recommendation algorithms have already surfaced to me, rather than re-filtering raw postings
myself, so that I benefit from the curation quality those platforms have already built.
- *Acceptance:* the product's stated rationale for the Email Connector (visible in
  documentation, and reflected in the contrast with the Apify Connector's deliberately
  uncurated, on-demand search — Epic H) is framed around inheriting recommendation-algorithm
  output, not solely around working around the LinkedIn API's lack of saved-job access — the
  API limitation is named as a confirming, secondary fact, not the primary motivation.

---

## Epic H — Apify Job Search Connector (active, on-demand, cost-capped)

**H1.** As a user, I want to actively search for jobs on LinkedIn and Indeed from inside the
dashboard, so that I'm not limited to only what happened to arrive via email alert.
- *Acceptance:* a search action (query + location) triggers a real Apify actor run against
  LinkedIn and/or Indeed and returns results into the dashboard, distinct from and in addition
  to the Email Connector's passive feed.

**H2.** As the project's budget owner, I want every search capped at a small number of results
by default, so that a fixed hackathon credit pool isn't consumed faster than necessary.
- *Acceptance:* the result cap (default 10) is passed as an input parameter to the Apify actor
  call itself, not applied only to what's displayed afterward — verified by checking that the
  actor's reported usage/cost for a capped run is proportionate to the requested count, not to
  a larger uncapped or full-page run.

**H3.** As a user, I want to avoid putting any real LinkedIn account at risk of suspension just
to get richer search results, so that this feature doesn't create a separate problem while
solving the original one.
- *Acceptance:* only cookieless Apify actors (no LinkedIn session cookie input required) are
  used; this is a deliberate scope limit, accepted even though it means somewhat less rich data
  than cookie-based alternatives could provide.

**H4.** As a user, I don't want repeated identical searches during a single session (e.g. a
judge asking to "show that again" mid-demo) to burn additional credit unnecessarily.
- *Acceptance:* results from a given (query, location, provider) combination are cached against
  the local `SavedJob` table; a repeated identical search is served from cache rather than
  triggering a fresh Apify run, within a reasonable freshness window.

**H5.** As a developer/judge inspecting the system, I want it acknowledged that the specific
Apify actors and their exact pricing weren't finalized during planning, so the documentation
doesn't overstate validation that wasn't actually performed.
- *Acceptance:* ARCHITECTURE.md section 2.12 explicitly states that actor selection and a live
  test run against the real credit balance are required implementation steps, distinct from the
  sections of this project that were directly tested against real data (the SkillsFuture
  dataset, the LinkedIn email parsing logic, the skill matcher).

---

## Epic I — Immediate Understanding & Interest Inference

**I1.** As a user, I want a job I just pasted, synced via email, or found via Apify search to be
fully processed (skills extracted, seniority tagged) in that same interaction, so I never have
to come back later to see it reflected anywhere.
- *Acceptance:* skill extraction and seniority tagging run synchronously as part of the same
  conversational turn that introduces a job (chat-paste) or the same sync/search action (email,
  Apify) — there is no separate "processing" step the person has to trigger or wait for
  afterward. A newly-added job's data is immediately available to the Gap Map and Career Radar
  rendering on the very next request.

**I2.** As a user, I want the system to notice how genuinely interested I am in each saved job,
not treat a passively-spotted email alert the same as a role I clearly care about, so my gap
analysis reflects what actually matters to me.
- *Acceptance:* every `SavedJob` row carries a derived `interest_level` (`low` / `medium` /
  `high`), inferred by default from existing behavioral signals — whether the job is
  spotted-only (email/Apify, title+company+date) vs. fully analyzed (full JD pasted), and
  whether the person has asked follow-up questions or used clearly interested/disinterested
  language about that specific job in conversation. No new manual rating step is required for
  this default to exist.

**I3.** As a user, I want to be able to simply tell the chat my actual interest level for a job
and have that override whatever was derived, so I'm never stuck with a wrong inference.
- *Acceptance:* a natural statement like "I'm really interested in that NVIDIA role" or "I'm not
  that serious about the CIX internship, just tracking it" updates `interest_level` directly and
  sets `interest_source = user_stated`, which is never silently overwritten by a future derived
  recalculation — a user-stated value persists until the person changes it again themselves.

**I4.** As a user, I want my interest level to influence how my skill gaps are prioritized, so
that a gap blocking a role I genuinely want ranks above the same gap appearing only in a role I
barely noticed.
- *Acceptance:* `rank_action_list`'s priority score (ARCHITECTURE.md section 2.3) incorporates
  `interest_level` as an additional weighting factor alongside signal strength and the
  emerging/CASL bonus, with the contribution stated in the ranked item's `why` explanation —
  consistent with this project's standing rule that every ranking factor must be visible, not
  folded silently into an opaque score.

**I5.** As a developer/judge inspecting the system, I want it clear that derived interest is a
behavioral proxy, not a verified fact, so the documentation doesn't overstate what's actually
being measured.
- *Acceptance:* PRD.md section 8 states explicitly that derived interest can be wrong (e.g.
  curiosity-driven engagement isn't the same as genuine interest), which is the stated reason a
  manual override exists rather than treating the derived value as ground truth.
