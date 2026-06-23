# Product Requirements Document (PRD)

**Project:** Career Radar — Continuous Skills-Gap & Market-Awareness Tool
**Track:** PyCon SG 2026 Hackathon — Job & Skills Track
**Status:** Draft for hackathon build (Day 1 planning)

---

## 1. Problem Statement

The person this is built for is **not actively job hunting**, but wants to avoid ever being caught
flat-footed by a layoff or market shift. Today this is done manually and inconsistently:

- I often save interesting job descriptions ad hocly from LinkedIn job alerts into a spreadsheet.
- I specifically value the recommendation quality LinkedIn's and Indeed's own algorithms already
  provide — their job-alert emails aren't raw search results, they're the output of a
  recommendation system that has already distilled an enormous pool of postings down to what
  it judges relevant to me specifically. Building this tool around those emails means inheriting
  that curation for free, rather than re-implementing a worse version of it myself.
- There is no systematic check of whether the person's actual day-to-day work still maps to
  in-demand skills, or whether their CV reflects what they're actually doing now.
- "Catching up" only happens reactively, right before a job search — which is exactly the
  high-stress moment this tool exists to prevent.

## 2. Goals

1. Turn passively-saved job postings into a structured, queryable signal of where the market
   (and the person's own ambition) is heading.
2. Continuously compare three things against each other, not just two: **CV**, **market demand
   (saved JDs)**, and **actual recent work** (self-reported via chat). Most tools only do
   CV-vs-market; the third leg is this project's main differentiator.
3. Ground every recommendation in the public SkillsFuture Skills Framework dataset, so
   conclusions are explainable and auditable, not black-box AI output.
4. Surface gaps as a short, ranked, actionable list — never an overwhelming dump.
5. Proactively notify the person (inactivity nudges, new emerging-skill matches) rather than
   requiring them to remember to check.
6. **Process every saved job and pasted job description immediately, in the same interaction
   that introduces it** — skill extraction, seniority tagging, and gap analysis happen
   synchronously when a job enters the system (whether via chat-paste, email sync, or Apify
   search), not as a delayed or lazily-triggered batch step. The person should never need to
   "come back later" to see a newly-added job reflected in their Gap Map or Career Radar.
7. **Infer how interested the person actually is in each saved job, not just what skills it
   requires.** Not every saved job carries equal weight — a role passively spotted via an email
   digest and a role whose full description was deliberately pasted and discussed at length
   represent very different levels of genuine interest, and the system should reflect that
   difference rather than treating every `SavedJob` row identically. This is derived
   automatically by default from existing behavioral signals (see ARCHITECTURE.md section 2.13),
   with an explicit, simple way for the person to override the derived value at any time by
   just saying so in conversation.

## 3. Non-Goals (explicitly out of scope for the hackathon build)

- Multi-user auth, accounts, permissions. Built single-user; data model is shaped to extend to
  multi-user later (see ARCHITECTURE.md).
- Real scheduled cron/Airflow infrastructure for notifications. Implemented as an evaluable
  rules table + on-demand evaluation function, following the pattern from the PyCon talk on
  schema-driven notification systems, without standing up real scheduling infra.
- Indeed/Glassdoor/other job board API integration. Named as a future data source in the schema
  (`source` field) but not implemented.
- Full job-description body text from LinkedIn email alerts. Confirmed by direct inspection of
  real inbox data: LinkedIn's job-alert emails contain only title/company/location/link per job,
  never the actual responsibilities/requirements text. Full JD text for skill-gap analysis still
  requires the person to separately paste the posting (see section 6, Email Connector, for the
  precise scope this implies).

## 4. Target User

Primary persona (and the actual person this is built for): a mid-level tech/software/data
professional in Singapore, currently employed, who:
- Casually monitors the job market via LinkedIn alerts out of long-term self-interest, not
  urgency.
- Wants their CV and skills awareness to stay "warm" continuously, so a sudden job search
  wouldn't start from zero.
- Is comfortable with a conversational, AI-assisted tool and wants it to feel personalized to
  their own saved data, not generic market advice.

## 5. Core Differentiators (why this isn't "just another resume matcher")

| Differentiator | Why it matters |
|---|---|
| Grounded in the official SkillsFuture taxonomy, not free-form LLM skill extraction | Every gap/recommendation traces to a real dataset row — satisfies the hackathon's "explain why" judging criterion |
| Three-way comparison (CV vs Market vs Actual Work), not two-way | Catches CV staleness, not just market gaps |
| Seniority/horizon-aware | A "Senior" role saved today isn't a gap to panic about — it's a future-state target. The tool models *time horizon*, not just skill distance |
| Ranked, capped action lists | Directly answers the brief's "actionable pathways instead of overwhelming skill sets" |
| Schema-driven notifications | Adding a new alert type is a data row, not a deploy — applied from a PyCon talk, not invented from scratch |
| Interest-aware, not just skill-aware | Most gap-analysis tools treat every saved job identically; this one weighs gaps differently depending on how genuinely interested the person is in that specific role, inferred from real behavior (how much detail they provided, how much they engaged with it in conversation) rather than a manual rating chore |
| Inherits LinkedIn/Indeed's own recommendation curation rather than re-implementing it | The Email Connector deliberately reads each platform's own job-alert output — already filtered by their own recommendation algorithms — instead of treating those algorithms as something to bypass or replicate. The Apify Connector (raw keyword search, no personalization) exists for a genuinely different purpose: active, on-demand search when the person wants to look beyond what's already been recommended to them |

## 6. Features (high level — see USER_STORIES.md for detail)

1. **Career Radar** — rendered inline in conversation on request (not a separate landing page,
   per the chat-first pivot — see ARCHITECTURE.md section 2.10); two charts (scanning activity
   over time; ambition
   gradient / seniority-vs-current-level distribution).
2. **Gap Map** — ranked, explainable skill gaps; filterable by time horizon; three-way CV /
   Market / Actual-Work comparison.
3. **Profile** — CV input, extracted-skills review/edit, simulated "sync job alerts" action.
4. **The Conversational Interface (agentic, read-only across features, plus JD paste-and-parse)**
   — per the chat-first pivot (ARCHITECTURE.md section 2.10), this is the application's primary
   surface, not a supplementary floating panel. It has three distinct capabilities sharing one
   conversational surface: (a) Work Log extraction — describing recent work creates new
   `WorkLogEntry` rows; (b) read-only agentic Q&A — querying readiness score, ranked gaps,
   Career Pathfinder, saved jobs, CV skills, and notifications via tool calls, answered from the
   same underlying functions any rendered chart or summary draws from; (c) **JD paste-and-parse**
   — pasting a full job description into the chat gets it parsed into a complete `SavedJob`
   record (company, title, seniority tier, extracted skills), with the chat asking for
   confirmation if any expected field (e.g. company name) isn't clearly present in the pasted
   text rather than silently inserting a blank. This
   directly closes the gap left by the Email Connector, which can only ever surface
   title/company/location/date (see feature 6) — pasting the full JD text here is how a
   "spotted" entry becomes a fully analyzable one. When a pasted JD's company+title closely
   matches an existing email-sourced "spotted" entry, the chat offers to attach the new JD text
   to that existing entry rather than creating a duplicate, but only after the person confirms
   — ambiguous or multiple matches are never auto-merged (see ARCHITECTURE.md section 2.5 for
   the full design, including the matching threshold rationale).
5. **Notifications, delivered as real email (not an in-app panel)** — schema-driven rules
   (inactivity nudge, new emerging-skill match, CV staleness alert); rules are data rows,
   evaluated on demand; dedup via `last_fired_at`. Delivery is via Resend (a genuinely free,
   non-expiring transactional email API — confirmed directly rather than assumed; see
   ARCHITECTURE.md section 2.6 for why Clerk and SendGrid were each considered and rejected).
   Sending real emails, rather than items inside the app that the person has to remember to
   open, directly serves this project's core premise: the whole point is to remove the need to
   remember to check something.
6. **Email Connector (real, tested, multi-user OAuth)** — built on a deliberate philosophy, not
   just a technical workaround: LinkedIn's and Indeed's job-alert emails are the output of those
   platforms' own recommendation algorithms, already distilled from a vast pool of postings down
   to what each platform's model judges relevant to the specific person. Reading those emails
   means inheriting that curation quality directly, rather than re-implementing a weaker
   approximation of it. (Separately, this also happens to be the only practical access path,
   since LinkedIn's Developer API cannot expose a user's saved/alerted job details — but that
   constraint is not the primary reason for this design, only a confirming one.) Concretely, this
   is a functional "Connect your Gmail" flow using real OAuth2 (Gmail read-only scope), deployed
   so that **any reviewer can authorize their own Google account** and see the connector run
   against their own real inbox. The underlying search/parse pipeline (filtering to
   LinkedIn/Glassdoor/Indeed job-alert sender addresses, parsing the structured digest format
   into title/company/location/date) was validated during the build against a real inbox (see
   ARCHITECTURE.md section 2.8). The project's own author's personal Gmail is never connected to
   the deployed app at any point — the OAuth flow authenticates each user against their own
   account, not the author's. A synthetic, clearly-labeled sample dataset is shown by default
   before any connection is made, so reviewers who prefer not to connect any account still see
   the feature's output shape.
7. **Apify Job Search Connector (active, on-demand, cost-capped)** — separate from and
   complementary to the Email Connector (feature 6): where the Email Connector is *passive*
   (it surfaces whatever LinkedIn already alerted the person about), this is *active* — the
   person searches on demand ("find me Data Engineer roles in Singapore") across LinkedIn and
   Indeed via Apify actors, funded by the hackathon's provided Apify credit. Cookieless actors
   only, by deliberate choice (cookie-based LinkedIn actors carry real account-ban risk, not
   worth taking for a hackathon demo). Hard-capped to a small number of results per search
   (default 10), with the cap enforced as an actor input parameter at call time — not as a
   post-hoc filter — since several Apify actors bill per search-page (commonly 25-50 results)
   regardless of how many results are kept afterward; capping only the displayed output would
   not actually reduce spend. Results merge into the same `SavedJob` table as both other
   sources, with `source="apify_linkedin"` / `source="apify_indeed"`. Glassdoor is a stretch
   addition, deferred until a cookieless, fairly-priced actor is confirmed (none was verified
   at the time of this writing — see ARCHITECTURE.md section 2.12).

## 7. Success Criteria for the Hackathon Demo

- A judge can see a saved job, click into it, and see *exactly which dataset rows* justify each
  matched/missing skill — no unexplained AI claims.
- The Gap Map's top-ranked item is visibly different from a flat alphabetical or unranked list,
  and the ranking reason is stated in plain language.
- The Work Log chat produces a structured record live, visibly, without the demo needing a
  scripted "happy path" input to avoid breaking.
- At least one notification rule fires during the demo and a real email is visibly sent (e.g.
  shown arriving in an actual inbox, or confirmed via Resend's delivery-status response), since
  notifications are real emails, not items in an in-app panel.
- The Email Connector's OAuth flow works for any reviewer who chooses to connect their own
  Google account, demonstrated live during the demo without ever exposing the project author's
  personal inbox; reviewers who decline to connect anything still see a clearly-labeled
  synthetic sample dataset of LinkedIn/Glassdoor/Indeed-style alerts by default.
- An on-demand Apify search (LinkedIn or Indeed) returns results live during the demo, visibly
  capped at the configured maximum (default 10), with the cap demonstrably enforced at the
  actor-input level rather than only in what's displayed — provable by checking the Apify run's
  actual reported usage/cost against the number of results returned.

## 8. Known Limitations (stated honestly, not hidden)

- Keyword/fuzzy matching has moderate recall on tool/language names not described in
  capability language (mitigated by an LLM fallback layer, lower priority than core build).
- Seniority classification is a heuristic (rule-based + LLM escalation), not a verified fact
  about any real job's actual seniority.
- Derived interest level is a behavioral proxy (how much detail was provided, how much the
  person engaged in conversation about a specific job), not a measurement of actual interest —
  it can be wrong (e.g. someone might paste a full JD purely out of curiosity about a role they
  don't actually want), which is exactly why a simple, always-available manual override exists
  rather than treating the derived value as ground truth.
- "Meaningful, relevant work" in the Work Log chat is operationalized as *skill overlap with CV
  and market demand* — the tool cannot judge impact or quality, only skill-presence signal. This
  is stated explicitly in-product, not implied as a stronger claim than it is.
- The Email Connector reliably extracts title/company/location/timestamp, confirmed against a
  real inbox, but cannot extract full job-description text — none of LinkedIn, Glassdoor, or
  Indeed's alert emails are expected to include it (confirmed directly for LinkedIn; Glassdoor
  and Indeed parsing rules are designed by analogy and should be verified against real samples
  of those alert formats before being trusted to the same degree). This means jobs ingested via
  email start as "spotted" entries with seniority-tier tagging only; full skill-gap analysis
  still requires the person to separately paste the JD body for any specific role they want to
  analyze deeply. This is a deliberate, honestly-scoped product shape (ambient lightweight
  tracking for everything spotted, deep analysis on demand for what's chosen) rather than a
  workaround being presented as more complete than it is.
- The deployed app's Gmail OAuth client will show as "unverified" in Google's consent screen
  (Google's app-verification process was not pursued given the hackathon timeline). This is
  disclosed in-product rather than hidden, with a short note on what scope is being requested
  (read-only Gmail search) so a cautious reviewer can make an informed choice rather than
  guessing.
- Apify actor pricing and exact input-parameter names drift over time and vary actor-to-actor
  (confirmed during research for this feature — pricing models range from pay-per-result to
  pay-per-search-page to flat monthly rental, and "max results" parameters are not named
  consistently). Whichever specific actors are ultimately selected must be verified directly
  against their live Pricing tab and tested with a small (e.g. 1-result) run before being
  trusted in the deployed app — the cap design in feature 7 is correct in principle, but the
  exact actor IDs and their input schemas were not pinned down as of this writing and need
  confirming against the actual $100 hackathon-provided credit balance.
