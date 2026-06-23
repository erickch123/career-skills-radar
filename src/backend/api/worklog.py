"""
Work Log endpoints.
POST /api/worklog  — save a free-form entry, extract skills + LLM summary
GET  /api/worklog  — list entries with skill counts
"""

import json
import os

import anthropic
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.models import UserProfile, WorkLogEntry, SkillMatchCache
from core.matcher import get_matcher

router = APIRouter()
USER_ID = 1


class WorkLogRequest(BaseModel):
    raw_text: str
    period_covered: str | None = None


@router.post("/api/worklog")
def save_work_log(req: WorkLogRequest, db: Session = Depends(get_db)):
    # Ensure user profile exists
    user = db.query(UserProfile).filter_by(id=USER_ID).first()
    if not user:
        user = UserProfile(id=USER_ID)
        db.add(user)
        db.flush()

    # LLM: extract activities_summary + seniority_signal
    meta = _extract_meta(req.raw_text)

    entry = WorkLogEntry(
        user_profile_id=USER_ID,
        raw_text=req.raw_text,
        period_covered=req.period_covered,
        activities_summary=meta.get("activities_summary"),
        seniority_signal=meta.get("seniority_signal"),
        extraction_confidence=meta.get("confidence", "medium"),
    )
    db.add(entry)
    db.flush()

    # Skill extraction
    matches = get_matcher().extract_skills(req.raw_text)
    for m in matches:
        db.add(SkillMatchCache(
            source_type="work_log_entry",
            source_id=entry.id,
            canonical_skill_title=m.skill_title,
            match_method=m.method,
            confidence=m.confidence,
            evidence_snippet=m.evidence_snippet,
        ))

    db.commit()
    return {
        "entry_id": entry.id,
        "skills_found": len(matches),
        "skills": [m.skill_title for m in matches],
        "activities_summary": entry.activities_summary,
        "seniority_signal": entry.seniority_signal,
    }


@router.get("/api/worklog")
def list_work_log(db: Session = Depends(get_db)):
    entries = (
        db.query(WorkLogEntry)
        .filter_by(user_profile_id=USER_ID)
        .order_by(WorkLogEntry.date_logged.desc())
        .all()
    )
    result = []
    for entry in entries:
        skills_count = db.query(SkillMatchCache).filter_by(
            source_type="work_log_entry", source_id=entry.id
        ).count()
        result.append({
            "id": entry.id,
            "period_covered": entry.period_covered,
            "date_logged": entry.date_logged.isoformat() if entry.date_logged else None,
            "activities_summary": entry.activities_summary,
            "seniority_signal": entry.seniority_signal,
            "skills_count": skills_count,
            "raw_text_preview": (entry.raw_text or "")[:120] + "…"
            if len(entry.raw_text or "") > 120
            else entry.raw_text,
        })
    return {"entries": result}


# ── LLM meta extraction ───────────────────────────────────────────────────────

def _extract_meta(raw_text: str) -> dict:
    """Extract activities_summary and seniority_signal using Claude Haiku."""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=(
                "You extract structured metadata from work log entries. "
                "Respond with valid JSON only, no prose."
            ),
            messages=[{
                "role": "user",
                "content": (
                    "Extract from this work log:\n"
                    "1. activities_summary: 1 sentence summarising what was done\n"
                    "2. seniority_signal: one of "
                    "individual_contributor | leading_others | strategic | unclear\n"
                    "3. confidence: high | medium | low (how confident you are)\n\n"
                    f"Work log:\n{raw_text[:1500]}\n\n"
                    'Respond with JSON: {"activities_summary": "...", '
                    '"seniority_signal": "...", "confidence": "..."}'
                ),
            }],
        )
        text = resp.content[0].text.strip()
        if "{" in text:
            text = text[text.index("{"):text.rindex("}") + 1]
        return json.loads(text)
    except Exception:
        return {}
