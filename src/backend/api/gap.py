from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import get_db
from models.models import SavedJob, SkillMatchCache
from core.gap_engine import get_gap_engine

router = APIRouter()
USER_ID = 1


@router.get("/api/gap")
def get_gap(
    db: Session = Depends(get_db),
    job_ids: list[int] = Query(default=[]),
):
    cv_matches = db.query(SkillMatchCache).filter_by(source_type="cv", source_id=USER_ID).all()
    cv_skills = [m.canonical_skill_title for m in cv_matches]

    if not cv_skills:
        return {"error": "No CV saved yet. Paste your CV first."}

    q = db.query(SavedJob).filter_by(user_profile_id=USER_ID)
    if job_ids:
        q = q.filter(SavedJob.id.in_(job_ids))
    jobs = q.all()
    if not jobs:
        return {"error": "No job descriptions saved yet. Add a JD first."}

    engine = get_gap_engine()
    analyses = []
    for job in jobs:
        jd_matches = db.query(SkillMatchCache).filter_by(
            source_type="saved_job", source_id=job.id
        ).all()
        jd_skills = [m.canonical_skill_title for m in jd_matches]
        analyses.append(engine.analyze_jd_vs_cv(
            jd_id=job.id,
            title=job.title or "Untitled",
            company=job.company or "",
            jd_skills=jd_skills,
            cv_skills=cv_skills,
        ))

    gaps = engine.rank_action_list(analyses, top_n=12)
    score = engine.readiness_score(analyses)

    return {
        "readiness": score,
        "gaps": [
            {
                "rank": g.rank,
                "skill": g.skill_title,
                "priority": g.priority_score,
                "why": g.why,
                "demand_count": g.demand_count,
                "total_jds": g.total_jds,
                "is_emerging": g.is_emerging,
                "is_casl": g.is_casl,
            }
            for g in gaps
        ],
        "cv_skills_count": len(cv_skills),
        "jobs_count": len(jobs),
    }
