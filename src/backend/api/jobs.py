from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.models import UserProfile, SavedJob, SkillMatchCache
from core.matcher import get_matcher

router = APIRouter()
USER_ID = 1


class JDRequest(BaseModel):
    jd_text: str
    company: str | None = None
    title: str | None = None


@router.post("/api/jobs")
def save_job(req: JDRequest, db: Session = Depends(get_db)):
    if not db.get(UserProfile, USER_ID):
        db.add(UserProfile(id=USER_ID))
        db.flush()

    job = SavedJob(
        user_profile_id=USER_ID,
        raw_jd_text=req.jd_text,
        company=req.company,
        title=req.title,
        source="manual_paste_via_chat",
    )
    db.add(job)
    db.flush()

    matches = get_matcher().extract_skills(req.jd_text)
    for m in matches:
        db.add(SkillMatchCache(
            source_type="saved_job",
            source_id=job.id,
            canonical_skill_title=m.skill_title,
            match_method=m.method,
            confidence=m.confidence,
            evidence_snippet=m.evidence_snippet,
        ))

    db.commit()
    return {
        "job_id": job.id,
        "skills_found": len(matches),
        "skills": [m.skill_title for m in matches],
    }


@router.get("/api/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(SavedJob).filter_by(user_profile_id=USER_ID).all()
    result = []
    for j in jobs:
        skills_count = db.query(SkillMatchCache).filter_by(
            source_type="saved_job", source_id=j.id
        ).count()
        result.append({
            "id": j.id,
            "title": j.title or "Untitled",
            "company": j.company or "",
            "skills_count": skills_count,
            "date_saved": j.date_saved.isoformat() if j.date_saved else None,
        })
    return result


@router.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db.query(SkillMatchCache).filter_by(source_type="saved_job", source_id=job_id).delete()
    db.query(SavedJob).filter_by(id=job_id, user_profile_id=USER_ID).delete()
    db.commit()
    return {"deleted": job_id}
