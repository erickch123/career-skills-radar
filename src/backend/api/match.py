from fastapi import APIRouter
from pydantic import BaseModel
from core.matcher import get_matcher

router = APIRouter(prefix="/api", tags=["match"])


class MatchRequest(BaseModel):
    text: str


class MatchResult(BaseModel):
    skill_title: str
    method: str
    confidence: int
    evidence_snippet: str


@router.post("/match", response_model=list[MatchResult])
def match_skills(req: MatchRequest):
    """Extract canonical SkillsFuture skills from free text."""
    matcher = get_matcher()
    return [
        MatchResult(
            skill_title=m.skill_title,
            method=m.method,
            confidence=m.confidence,
            evidence_snippet=m.evidence_snippet,
        )
        for m in matcher.extract_skills(req.text)
    ]
