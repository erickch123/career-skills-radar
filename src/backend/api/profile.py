from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.models import UserProfile, SkillMatchCache
from core.matcher import get_matcher

router = APIRouter()
USER_ID = 1


class CVRequest(BaseModel):
    cv_text: str


@router.get("/api/profile/cv")
def get_cv(db: Session = Depends(get_db)):
    user = db.get(UserProfile, USER_ID)
    return {"cv_text": user.cv_raw_text if user else ""}


@router.post("/api/profile/cv")
def save_cv(req: CVRequest, db: Session = Depends(get_db)):
    user = db.get(UserProfile, USER_ID)
    if not user:
        user = UserProfile(id=USER_ID)
        db.add(user)
    user.cv_raw_text = req.cv_text
    user.cv_updated_at = datetime.now(timezone.utc)

    db.query(SkillMatchCache).filter_by(source_type="cv", source_id=USER_ID).delete()

    matches = get_matcher().extract_skills(req.cv_text)
    for m in matches:
        db.add(SkillMatchCache(
            source_type="cv",
            source_id=USER_ID,
            canonical_skill_title=m.skill_title,
            match_method=m.method,
            confidence=m.confidence,
            evidence_snippet=m.evidence_snippet,
        ))

    db.commit()
    return {"skills_found": len(matches), "skills": [m.skill_title for m in matches]}
