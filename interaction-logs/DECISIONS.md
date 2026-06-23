# Decisions Log

Running log of human-judgment moments during the build — what was delegated to AI vs decided by
the human, kept contemporaneously (not reconstructed after the fact) for the hackathon
submission's interaction-log requirement.

Format: `[Date/session] Decision — Human reasoning — AI's role`

---

### Planning session, pre-build

- **Decision:** Use hybrid keyword/fuzzy matching (not pure-LLM extraction) for the core skill
  matcher.
  **Human reasoning:** explainability matters more for this hackathon's judging criteria than
  raw recall; a black-box LLM match can't show its work the way a literal text match can.
  **AI's role:** proposed the option set; implemented the hybrid pipeline once chosen.

- **Decision:** Scope sector coverage to "all sectors" rather than ICT-only.
  **Human reasoning:** the person's own saved JDs span ICT, Financial Services, and consulting —
  an ICT-only matcher would have silently failed on roughly half the real sample data.
  **AI's role:** flagged the tradeoff; implementation was sector-agnostic by design once decided.

- **Decision:** Caught and corrected an AI error — invented skill names not present in the real
  dataset (e.g. "Blockchain", "Big Data Engineering", "Geographic Information System (GIS)
  Application" as synonym targets that turned out not to exist in `skills_master.csv`).
  **Human reasoning:** N/A — this was the AI's own self-check, prompted by the human's earlier
  insistence on verifying against the real dataset rather than trusting assumed schema/content.
  **AI's role:** ran a programmatic validation step (every synonym target checked against the
  real unique skills list) after the human had already set the expectation, earlier in the
  session, that nothing should be built against guessed structure.

- **Decision:** Tightened fuzzy-matching thresholds after finding real false positives during
  testing (e.g. "change management" matching "Organisational Change Management" at 100% via
  `token_set_ratio`; "worked with" matching an unrelated biosafety skill title).
  **Human reasoning:** N/A — caught via deliberate adversarial testing against real JD text,
  not assumed to work from the first implementation.
  **AI's role:** wrote the test cases that surfaced the failures, diagnosed the scoring-function
  cause, and re-tuned (switched `WRatio`→`token_sort_ratio`, raised threshold 82→94, excluded
  single-word titles from fuzzy matching, required capitalization for single-word exact matches).

- **Decision:** Career Pathfinder ranks by overlap *count*, not overlap *percentage*.
  **Human reasoning:** N/A — discovered as a bug during testing (a 5-skill niche media role
  was outranking genuinely relevant roles like "Back End Developer" purely because having few
  required skills makes percentage easy to game).
  **AI's role:** identified the bias by inspecting the skill-count distribution across all 2,000
  roles, proposed the fix, human did not need to intervene on this one — noted here for
  completeness/transparency on what was purely AI-caught vs human-caught.

- **Decision:** Single-user demo scope, simulated email ingestion (not real IMAP), structured
  notification rules without real cron infrastructure.
  **Human reasoning:** explicit hackathon time-box; chose to demonstrate the *pattern* correctly
  in each case rather than build throwaway infra that wouldn't survive past the demo.
  **AI's role:** proposed the three scoping options for each; human chose.

- **Decision:** Work Log Chat should be free-form on the surface, with structured-output
  extraction underneath, rather than a rigid guided form.
  **Human reasoning:** wanted the experience to feel natural/conversational while keeping the
  backend data clean — explicitly specified this hybrid pattern rather than picking from the
  options initially offered (guided-flow vs free-form).
  **AI's role:** had offered only two options (fully guided vs fully free-form); human proposed
  the actual chosen design, which was a third option not on the original list.

- **Decision:** Adopted the schema-driven notification-rules pattern from PyCon SG 2026 Day 2's
  talk ("Building a Flexible and Scalable Notification System," GyeongSeon Park, Kakaobank) for
  inactivity nudges and emerging-skill alerts.
  **Human reasoning:** attended the talk live; recognized the "rules as schema rows, not
  per-type code" pattern as directly applicable to a feature already planned (notifications),
  rather than the AI inventing a notification architecture from scratch.
  **AI's role:** mapped the talk's specific mechanisms (rule table, dedup via last-fired
  tracking) onto this project's concrete use cases once the human identified the talk as
  relevant.

- **Decision:** Adopted Gmail (via MCP connector) as the project's real external integration,
  rather than LinkedIn/Indeed/Glassdoor APIs or a simulated stand-in.
  **Human reasoning:** explicitly wanted at least one real external connector as proof the
  project isn't "just ideation." Recalled that LinkedIn's own Developer API can't expose a
  user's saved job details (known constraint stated earlier), so proposed checking Gmail instead
  since LinkedIn job alerts already arrive there.
  **AI's role:** before committing to this design, ran a live test against the human's actual
  connected Gmail account (real `search_threads`/`get_thread` calls, not a hypothetical) to
  verify the integration was genuinely possible before writing any planning docs around it —
  consistent with the earlier-established norm in this project of verifying real data/schema
  before building on assumptions.

- **Decision:** Scoped the email connector to title/company/location/date extraction only, NOT
  full job-description text, after discovering LinkedIn's alert emails don't contain JD body
  content.
  **Human reasoning:** confirmed this scoping was the right call when presented with the
  finding, rather than asking the AI to find a workaround (e.g. attempting to scrape the
  linked posting page, which would have hit the same login wall as the LinkedIn API).
  **AI's role:** discovered the limitation by directly inspecting real email body content
  (not by assumption), found and fixed a related parsing bug during the same investigation
  (footer/navigation text being misparsed as fake job entries), and proposed the honest scoping
  before the human had to ask for it.

- **Decision:** Built a real, generic OAuth2 "Connect your Gmail" flow into the deployed app
  (rather than a shared demo account or a fully-mocked connector), so any reviewer can
  authorize their own Google account and see the connector run against their own real inbox.
  **Human reasoning:** explicitly did not want to run a separate demo account, and did not want
  to use personal Gmail even just to export one-time sample data. When the AI initially proposed
  "demo account" and "export samples from your own inbox" as the two practical paths, the human
  rejected both and clarified the actual goal was a genuinely functional, reusable feature —
  correctly identifying that the AI had conflated "default view shown to reviewers" with
  "whether a real connect-flow exists at all," which are independent design questions.
  **AI's role:** initially proposed an architecture that implicitly assumed a single
  author-controlled account was the only practical path; corrected this once the human pushed
  back, and redesigned around per-user OAuth (which was the right solution all along, since
  OAuth's entire purpose is per-user authorization — the privacy boundary was never "author's
  Gmail vs. nobody's," it was "author's Gmail vs. each user's own").

- **Decision:** Disclosed the "unverified app" OAuth consent screen explicitly in-product rather
  than leaving a reviewer to encounter it unexplained, and explicitly flagged that Glassdoor/
  Indeed parsing logic is designed by analogy to the validated LinkedIn format, not tested
  against real samples of those providers' actual emails.
  **Human reasoning:** N/A for this specific item — the AI raised both caveats proactively as
  part of stating the design honestly, consistent with the project's established norm (set
  earlier in the session) of not overclaiming validation that wasn't actually performed.
  **AI's role:** named both limitations explicitly in PRD/ARCHITECTURE rather than letting the
  real, tested LinkedIn path implicitly stand in for unverified claims about other providers.

- **Decision:** Made the Work Log Chat a tool-using agent with read-only access across every
  other feature (readiness score, gap rankings, Career Pathfinder, saved jobs, CV skills,
  notifications), explicitly excluding write access to anything except its own Work Log entries.
  **Human reasoning:** wanted the chat to be genuinely "agentic" and aware of the rest of the
  system, not narrowly scoped to logging work activities — explicitly chose the full-read-access
  option over a narrower "Work Log only" scope when offered the choice.
  **AI's role:** proposed the read-vs-write distinction as the key design fork (full agentic
  read+write, read-only across features, or narrowly scoped) before building anything, so the
  human's choice was between clearly-stated tradeoffs rather than an implicit default; once
  chosen, designed the tool surface as thin wrappers around already-existing query functions
  specifically so chat answers stay consistent with what the dashboard pages themselves show,
  rather than becoming a second, independently-reasoned source of truth.

- **Decision:** Added JD paste-and-parse as a third chat capability (alongside Work Log
  extraction and read-only agentic Q&A), routing through the chat rather than a separate form,
  with a confirmed-merge match against existing email-sourced "spotted" entries rather than
  always creating a new row.
  **Human reasoning:** recognized, after the email connector's scope had already been narrowed
  to title/company/date only (per the earlier finding that LinkedIn alert emails lack JD body
  text), that the dashboard still needed *some* way to get full JD text in for deep analysis —
  and specifically wanted that to go through the chatbot/LLM parsing rather than a plain manual
  form, consistent with the project's existing pattern of routing free-form input through
  structured extraction. Also specifically asked for confirm-before-merge behavior rather than
  silent merging or always-duplicate, when offered the choice.
  **AI's role:** identified that this was the same structured-extraction pattern already used
  for Work Log entries, just with a different schema and a different target table; proposed the
  fuzzy-match-with-confirmation design for linking pasted JDs to existing spotted entries,
  explicitly reusing (but separately re-tuning) the `rapidfuzz` approach already validated in
  the skill matcher, and flagged that company/title matching has its own version of the
  near-miss-but-distinct-meaning trap found earlier in skill matching (e.g. "Software Engineer"
  vs. "Senior Software Engineer" must not be treated as duplicates).

- **Decision:** Made login optional and single-trigger (only required to connect Gmail), rather
  than a precondition for using the app at all; implemented Google OAuth2 directly rather than
  via Clerk/Auth0/Supabase Auth; adopted Supabase for hosted Postgres only, deliberately not its
  auth product.
  **Human reasoning:** explicitly stated that someone should only need to log in if they want to
  connect their email — if not, they shouldn't need OAuth at all. Asked directly whether
  Clerk/Auth0/Supabase could provide both login and Gmail access together, prompting a real
  investigation rather than an assumed answer.
  **AI's role:** clarified a distinction the question's framing risked collapsing — that "login
  via Google" and "Gmail API scope access" are different OAuth grants regardless of which
  identity platform is used, so no platform removes the need to explicitly request
  `gmail.readonly`. Once that was established, proposed the optional/single-trigger auth model
  as the design that matched the human's stated requirement, and recommended against a
  dedicated identity platform on the grounds that it would add a layer (multi-provider identity
  management) the project doesn't need, while keeping Supabase for its actual advantage (managed
  Postgres) once the human confirmed that scope.

- **Decision:** Built a provider-agnostic LLM abstraction layer (Claude as primary/design
  partner, OpenAI as the explicitly-supported deployment alternate), rather than calling either
  SDK directly from each feature module.
  **Human reasoning:** the hackathon's deployment environment requires an OpenAI token, but all
  design and development work in this project was done with Claude — explicitly wanted the
  dashboard to be "robust enough to have Claude or OpenAI" rather than locking into whichever
  provider happened to be used during design.
  **AI's role:** identified that every one of the project's five LLM-touching features already
  shared the same input/output shape (constrained input, structured output), which made a single
  three-function abstraction (`extract_structured`, `classify_with_reasoning`,
  `agent_tool_call`) sufficient to cover all of them without per-feature special-casing;
  proactively flagged the honest limitation that the abstraction guarantees a consistent
  interface but not identical output quality across providers, and recommended explicitly
  re-testing each feature's validated behavior (e.g. the matcher/seniority failure modes found
  earlier in the build) against the OpenAI backend rather than assuming it transfers.

- **Decision:** Added an Apify-based active job-search connector (LinkedIn + Indeed, cookieless
  actors only), funded by the hackathon-provided $100 Apify credit, designed as complementary to
  rather than a replacement for the existing Email Connector — and specifically required the
  result cap to be enforced as an actor input parameter, not a post-hoc display filter.
  **Human reasoning:** received the Apify credit from the hackathon organizer and wanted to use
  it, but explicitly prioritized minimizing credit consumption — asked for a hard cap (10
  results) on what the dashboard shows.
  **AI's role:** before designing anything, researched actual Apify pricing models for LinkedIn/
  Indeed job actors rather than assuming a simple per-result cost; surfaced a finding that
  directly affected the design — several actors bill per search-page (25-50 results) regardless
  of how many are kept, meaning a display-only cap would not achieve the human's actual cost
  goal. Proposed enforcing the cap as an actor input parameter instead, plus additional
  cost-safety measures (rate limiting, result caching) the human hadn't explicitly asked for but
  that follow directly from the stated goal of minimizing spend. Also recommended cookieless
  actors only after the human, when asked, confirmed avoiding LinkedIn account-suspension risk
  was a priority. Explicitly flagged that no specific actor was selected or live-tested during
  this planning round, consistent with the project's established practice of not documenting
  validation that wasn't actually performed.

- **Decision:** Pivoted from a multi-page dashboard to a chat-first conversational interface as
  the primary product surface, after re-reading the hackathon's published judging criteria
  (Data Integrity, User Focus, Execution, Process & Product) and confirming none of them
  specifically require a dashboard — only "an interactive solution using the datasets."
  **Human reasoning:** explicitly pointed out that the hackathon website's actual criteria
  didn't mention a dashboard requirement, prompting a deliberate re-evaluation rather than
  continuing on the original, unexamined dashboard-first assumption from early planning. When
  presented with three options (agent-first, dashboard-first, hybrid), chose full agent-first.
  **AI's role:** mapped each of the four published criteria against what a chat-first interface
  could plausibly demonstrate versus a dashboard, identified that the backend/data layer
  (sections 2.1–2.9, 2.12) required zero changes since those functions were always
  interface-agnostic, and flagged the one genuinely new design question this pivot raised
  (where does the conversational orchestration actually run) rather than assuming an answer.

- **Decision:** Researched actual current package names before committing to either LLM SDK,
  rather than assuming `claude-agent-sdk` and `openai-agents-sdk` (as initially proposed by the
  human, based on names found online) were both equally well-suited to this project's needs;
  selected the plain `anthropic` SDK for the Claude backend instead, while confirming
  `openai-agents` was a good fit as found. Separately, confirmed via direct search that OpenAI's
  Agent Builder is being deprecated (shutting down November 30, 2026), which the human had heard
  but not yet confirmed.
  **Human reasoning:** asked directly whether both a Claude SDK and an OpenAI SDK could be used
  together, and separately flagged having heard that Agent Builder was deprecating without being
  certain — prompting verification rather than the AI proceeding on an assumption either way.
  **AI's role:** searched for and read the actual OpenAI deprecation notice (confirming the
  human's tip was correct, with a specific shutdown date) before it could affect the build;
  separately investigated `claude-agent-sdk`'s actual documented purpose and found it was built
  around the Claude Code agent loop (bundled CLI, file/bash/web tools) rather than generic custom
  tool-calling, which would have been a heavier and worse-fitting dependency than the plain
  `anthropic` SDK for this project's actual need (a small set of custom domain-function tools).
  Presented this distinction to the human rather than silently picking one, since it changed the
  technical recommendation from what the human had found online.

- **Decision:** Added two previously-implicit-but-undocumented product behaviors as explicit
  goals — synchronous, same-turn processing of every newly-saved job (no deferred batch step),
  and a derived `interest_level` signal per saved job, with a sticky user-stated override.
  **Human reasoning:** asked directly why the PRD and user stories didn't explicitly state that
  the system understands job data immediately and infers user interest — correctly identifying
  that "immediate processing" was only implicit in how the pipeline happened to be described,
  and that "interest" wasn't represented as a concept anywhere in the system at all, despite
  being a real, useful signal. When asked how interest should be captured, chose a hybrid
  (automatic derived default, with a manual override available) rather than either pure
  automation or a mandatory rating step.
  **AI's role:** distinguished the two things bundled in the original question — a
  latency/synchronicity guarantee (already true in spirit, never stated as a deliberate
  promise) versus a genuinely missing signal (interest, which required new schema, not just new
  prose) — and proposed concrete, low-friction derivation signals (spotted-only vs. fully-pasted
  vs. follow-up engagement vs. explicit language) grounded in behavior the system already
  observes, rather than inventing a new manual-input requirement. Explicitly flagged the
  interest-weighted ranking extension as untested and distinct from the already-validated
  `rank_action_list` formula, consistent with the project's standing practice of not implying
  validation that hasn't actually happened.

- **Decision:** Re-stated the Email Connector's primary motivation as deliberately inheriting
  LinkedIn's and Indeed's own recommendation-algorithm curation, rather than leading with the
  mechanical "LinkedIn's API doesn't expose saved jobs" workaround framing that had been the
  documented rationale up to this point.
  **Human reasoning:** explicitly clarified that the real reason for wanting Gmail integration
  was appreciation for the quality of job-portal companies' own recommendation algorithms — the
  email alerts represent an already-distilled, accurate output of systems LinkedIn and Indeed
  have built and tuned, and reading those emails means inheriting that quality rather than
  reimplementing a weaker version of it. The API limitation was always real, but was not the
  actual motivating reason.
  **AI's role:** recognized that this reframing also clarified the relationship between the
  Email Connector and the Apify Connector (section 2.12) — one inherits curation, the other is
  raw uncurated search — and propagated the corrected motivation through every document where
  the Email Connector's rationale was stated (PRD problem statement, PRD feature 6,
  ARCHITECTURE section 2.8's opening framing, and a sharpened contrast in section 2.12), rather
  than treating it as a single isolated sentence to add in one place.

- **Decision:** Notifications are delivered as real outbound emails via Resend, not as items in
  an in-app notification panel; Clerk and SendGrid were each considered and rejected in favor of
  Resend.
  **Human reasoning:** explicitly didn't want notifications inside the dashboard at all — wanted
  them delivered like email — and proposed Clerk first as a free service to use for this.
  **AI's role:** researched Clerk's actual capabilities before accepting the suggestion at face
  value, and found it is an identity/auth platform whose email-sending is built specifically
  around auth-flow templates (verification codes, magic links) with no general-purpose API for
  sending arbitrary application notifications — adopting it would have repeated the same
  category error already corrected once in this project (choosing an identity platform for a
  problem it isn't designed to solve, per section 2.9's earlier reasoning). Presented this
  finding rather than silently substituting a different tool, and proposed transactional email
  alternatives with verified free-tier terms. When the human then asked about SendGrid
  specifically, researched its current pricing directly rather than relying on outdated
  knowledge, and found its free tier was retired in May 2025 in favor of a time-limited 60-day
  trial — a materially different offer than "free" as the human had specified, surfaced before
  committing to it. Recommended Resend as the option whose free tier was confirmed permanent
  rather than time-boxed, and updated every document that had referenced Clerk or an in-app
  notification surface (PRD features and success criteria, USER_STORIES Epic F, ARCHITECTURE
  section 2.6 and the tech stack table, and the ERD's `NOTIFICATION`/`USER_PROFILE` entities)
  once the human confirmed the choice, including the honest edge case that a person who never
  connects Gmail has no notification_email on file and must be skipped rather than guessed at.

---

## Talk notes

### Day 2 — "Building a Flexible and Scalable Notification System"
**Speaker:** GyeongSeon Park, Backend Software Engineer, Kakaobank
**Article:** https://medium.com/p/eef601f22518

Core idea: notification rules live in the schema (a DB row: cron schedule + "what happened"
query + "who cares" query + template ID), not hardcoded per-notification-type code. New
notification type = insert a row, no deploy. Key operational lesson: deduplication logic that
gets copy-pasted into every new job is a recurring source of double-send bugs — centralize dedup
state instead.

**Applied to this project as:** `NotificationRule` + `NotificationRuleState` tables (see
ERD.md), generic evaluator function, `last_fired_at` as the centralized dedup guard. See
ARCHITECTURE.md section 2.6 for the full mapping, including what was simplified for hackathon
scope (no real cron/Airflow; Python-function condition checks instead of stored SQL-as-data,
given the much smaller rule count here).
