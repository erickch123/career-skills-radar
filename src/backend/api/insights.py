"""
Insights endpoints: seniority classification + career pathfinder.
Both consumed by the frontend CareerRadar component.
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.models import SavedJob, SkillMatchCache
from core.seniority import classify_job, TIERS
from core.gap_engine import get_gap_engine

router = APIRouter()
USER_ID = 1

TIER_LABELS = {
    "entry": "Entry",
    "mid": "Mid",
    "senior": "Senior",
    "staff_principal": "Staff / Principal",
    "manager_plus": "Manager+",
}

# In-memory cache — invalidated whenever new jobs get classified
_classify_cache: dict | None = None
_classify_cache_size: int = 0


@router.post("/api/insights/classify")
def classify_all(db: Session = Depends(get_db)):
    """Classify all unclassified jobs; return updated distribution.

    LLM is only called for jobs missing seniority_tier. Results persist in DB
    so subsequent calls are cheap. The in-memory cache makes repeated clicks
    within the same server session instant once everything is classified.
    """
    global _classify_cache, _classify_cache_size

    jobs = db.query(SavedJob).filter_by(user_profile_id=USER_ID).all()
    unclassified = [j for j in jobs if not j.seniority_tier]

    # Return cached result if nothing new to classify and job count unchanged
    if not unclassified and _classify_cache is not None and _classify_cache_size == len(jobs):
        return _classify_cache

    for job in unclassified:
        tier, method, reasoning = classify_job(job.title or "", job.raw_jd_text or "")
        job.seniority_tier = tier
        job.seniority_method = method
        job.seniority_reasoning = reasoning

    if unclassified:
        db.commit()

    counts = Counter(j.seniority_tier or "unknown" for j in jobs)
    distribution = [
        {"tier": t, "label": TIER_LABELS.get(t, t), "count": counts.get(t, 0)}
        for t in TIERS
        if counts.get(t, 0) > 0
    ]
    job_list = [
        {"id": j.id, "title": j.title, "company": j.company, "tier": j.seniority_tier}
        for j in jobs
    ]
    result = {
        "newly_classified": len(unclassified),
        "distribution": distribution,
        "jobs": job_list,
    }

    _classify_cache = result
    _classify_cache_size = len(jobs)
    return result


@router.get("/api/insights/pathfinder")
def pathfinder(db: Session = Depends(get_db)):
    """Return top SkillsFuture roles closest to the user's CV skills."""
    cv_matches = db.query(SkillMatchCache).filter_by(
        source_type="cv", source_id=USER_ID
    ).all()
    cv_skills = [m.canonical_skill_title for m in cv_matches]

    if not cv_skills:
        return {"error": "No CV saved yet. Paste your CV first."}

    engine = get_gap_engine()
    roles = engine.find_closest_roles(cv_skills, top_n=8)

    return {
        "cv_skills_count": len(cv_skills),
        "roles": [
            {
                "job_role": r.job_role,
                "sector": r.sector,
                "overlap_count": r.overlap_count,
                "total_required": r.total_required,
                "match_pct": round(r.overlap_count / r.total_required * 100, 1),
            }
            for r in roles
        ],
    }
