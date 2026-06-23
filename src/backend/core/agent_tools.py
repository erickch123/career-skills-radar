"""
Read-only agent tools — Claude calls these to answer career Q&A.
All tools query the DB or gap engine, never write.
"""

import json
from sqlalchemy.orm import Session

from models.models import SavedJob, SkillMatchCache, WorkLogEntry
from core.gap_engine import get_gap_engine

USER_ID = 1

# ── Tool schemas for Anthropic tool_use ──────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "get_cv_skills",
        "description": (
            "Get the list of skills extracted from the user's CV. "
            "Use this to understand what the user already knows."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_saved_jobs",
        "description": (
            "List all saved jobs with title, company, and seniority tier. "
            "Use this to understand what roles the user is targeting."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_gap_analysis",
        "description": (
            "Run a skills gap analysis between the user's CV and saved jobs. "
            "Returns ranked skill gaps and readiness score. "
            "Optionally filter to specific job IDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Job IDs to restrict analysis to. Omit to analyse all saved jobs.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_career_pathfinder",
        "description": (
            "Find the SkillsFuture job roles that best match the user's CV skills, "
            "ranked by overlap count."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_work_log_summary",
        "description": (
            "Get a summary of the user's work log entries and skills extracted from them. "
            "Use to understand recent work experience."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_job_details",
        "description": "Get the full details and required skill list for a specific saved job by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "integer",
                    "description": "The ID of the saved job to look up.",
                },
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "get_email_job_alerts",
        "description": (
            "Fetch recent LinkedIn job alerts from the user's Gmail inbox. "
            "Returns unimported job postings from alert emails. "
            "Use this when the user asks about new jobs in their email or inbox."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ── Dispatcher ────────────────────────────────────────────────────────────────

def run_tool(name: str, tool_input: dict, db: Session) -> str:
    try:
        match name:
            case "get_cv_skills":        return _get_cv_skills(db)
            case "list_saved_jobs":      return _list_saved_jobs(db)
            case "get_gap_analysis":     return _get_gap_analysis(db, tool_input.get("job_ids"))
            case "get_career_pathfinder":return _get_career_pathfinder(db)
            case "get_work_log_summary": return _get_work_log_summary(db)
            case "get_job_details":        return _get_job_details(db, tool_input.get("job_id"))
            case "get_email_job_alerts":  return _get_email_job_alerts()
            case _:                       return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ── Implementations ───────────────────────────────────────────────────────────

def _get_cv_skills(db: Session) -> str:
    matches = db.query(SkillMatchCache).filter_by(
        source_type="cv", source_id=USER_ID
    ).all()
    skills = [m.canonical_skill_title for m in matches]
    return json.dumps({"skill_count": len(skills), "skills": skills})


def _list_saved_jobs(db: Session) -> str:
    jobs = db.query(SavedJob).filter_by(user_profile_id=USER_ID).all()
    return json.dumps({
        "job_count": len(jobs),
        "jobs": [
            {
                "id": j.id,
                "title": j.title or "Untitled",
                "company": j.company or "",
                "seniority_tier": j.seniority_tier or "unclassified",
                "interest_level": j.interest_level,
            }
            for j in jobs
        ],
    })


def _get_gap_analysis(db: Session, job_ids: list[int] | None) -> str:
    cv_matches = db.query(SkillMatchCache).filter_by(
        source_type="cv", source_id=USER_ID
    ).all()
    cv_skills = [m.canonical_skill_title for m in cv_matches]
    if not cv_skills:
        return json.dumps({"error": "No CV saved yet."})

    q = db.query(SavedJob).filter_by(user_profile_id=USER_ID)
    if job_ids:
        q = q.filter(SavedJob.id.in_(job_ids))
    jobs = q.all()
    if not jobs:
        return json.dumps({"error": "No saved jobs found."})

    engine = get_gap_engine()
    analyses = []
    for job in jobs:
        jd_skills = [
            m.canonical_skill_title
            for m in db.query(SkillMatchCache).filter_by(
                source_type="saved_job", source_id=job.id
            ).all()
        ]
        analyses.append(engine.analyze_jd_vs_cv(
            jd_id=job.id,
            title=job.title or "Untitled",
            company=job.company or "",
            jd_skills=jd_skills,
            cv_skills=cv_skills,
        ))

    gaps = engine.rank_action_list(analyses, top_n=10)
    score = engine.readiness_score(analyses)
    return json.dumps({
        "overall_readiness_pct": score["overall_pct"],
        "jobs_analysed": len(analyses),
        "top_gaps": [
            {"rank": g.rank, "skill": g.skill_title, "why": g.why,
             "demand_count": g.demand_count, "is_emerging": g.is_emerging}
            for g in gaps
        ],
        "per_job_readiness": [
            {"id": p["jd_id"], "title": p["title"], "company": p["company"],
             "coverage_pct": p["coverage_pct"]}
            for p in score["per_jd"]
        ],
    })


def _get_career_pathfinder(db: Session) -> str:
    cv_skills = [
        m.canonical_skill_title
        for m in db.query(SkillMatchCache).filter_by(
            source_type="cv", source_id=USER_ID
        ).all()
    ]
    if not cv_skills:
        return json.dumps({"error": "No CV saved yet."})

    roles = get_gap_engine().find_closest_roles(cv_skills, top_n=8)
    return json.dumps({
        "cv_skills_count": len(cv_skills),
        "closest_roles": [
            {
                "job_role": r.job_role,
                "sector": r.sector,
                "overlap_count": r.overlap_count,
                "total_required": r.total_required,
                "match_pct": round(r.overlap_count / r.total_required * 100, 1),
            }
            for r in roles
        ],
    })


def _get_work_log_summary(db: Session) -> str:
    entries = (
        db.query(WorkLogEntry)
        .filter_by(user_profile_id=USER_ID)
        .order_by(WorkLogEntry.date_logged.desc())
        .all()
    )
    if not entries:
        return json.dumps({"entry_count": 0, "entries": [], "unique_skills": []})

    all_skills: list[str] = []
    entry_summaries = []
    for entry in entries:
        skills = [
            s.canonical_skill_title
            for s in db.query(SkillMatchCache).filter_by(
                source_type="work_log_entry", source_id=entry.id
            ).all()
        ]
        all_skills.extend(skills)
        entry_summaries.append({
            "id": entry.id,
            "period_covered": entry.period_covered,
            "activities_summary": entry.activities_summary,
            "seniority_signal": entry.seniority_signal,
            "skills": skills,
        })

    return json.dumps({
        "entry_count": len(entries),
        "unique_skills": list(set(all_skills)),
        "entries": entry_summaries,
    })


def _get_email_job_alerts() -> str:
    from core.email_connector import fetch_job_alerts
    alerts = fetch_job_alerts(max_emails=10)
    return json.dumps({
        "alert_count": len(alerts),
        "alerts": [
            {
                "title": a.title,
                "company": a.company,
                "location": a.location,
                "date": a.email_date,
            }
            for a in alerts
        ],
    })


def _get_job_details(db: Session, job_id: int | None) -> str:
    if job_id is None:
        return json.dumps({"error": "job_id is required"})
    job = db.query(SavedJob).filter_by(id=job_id, user_profile_id=USER_ID).first()
    if not job:
        return json.dumps({"error": f"Job {job_id} not found"})

    skills = db.query(SkillMatchCache).filter_by(
        source_type="saved_job", source_id=job_id
    ).all()
    preview = (job.raw_jd_text or "")
    if len(preview) > 600:
        preview = preview[:600] + "…"

    return json.dumps({
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "seniority_tier": job.seniority_tier,
        "required_skills": [s.canonical_skill_title for s in skills],
        "jd_preview": preview,
    })
