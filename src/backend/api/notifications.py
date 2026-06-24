"""
Notification endpoints.

POST /api/notify/jobs   — Apify scrape → match CV skills → send email
POST /api/notify/gaps   — gap analysis snapshot → send email
GET  /api/notify/status — whether live (Apify + Resend) or demo mode
"""

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models.models import UserProfile, SkillMatchCache, SavedJob
from core.apify_connector import fetch_jobs, is_connected as apify_connected
from core.notification_engine import fire_rule, default_email, RULES

router = APIRouter()
USER_ID = 1


class NotifyRequest(BaseModel):
    to_email: str = ""
    max_results: int = 5


@router.get("/api/apify/search")
def apify_search(keywords: str = "", db: Session = Depends(get_db)):
    """Search LinkedIn + Indeed via Apify. Returns 5 results per source.
    keywords — comma-separated or space-separated terms.
    Falls back to top CV skills if omitted.
    """
    if keywords.strip():
        kw_list = [k.strip() for k in keywords.replace(",", " ").split() if k.strip()]
    else:
        kw_list = [
            s.canonical_skill_title
            for s in db.query(SkillMatchCache)
            .filter_by(source_type="cv", source_id=USER_ID)
            .order_by(SkillMatchCache.confidence.desc())
            .limit(5)
            .all()
        ]

    if not kw_list:
        kw_list = ["software engineer"]

    jobs = fetch_jobs(keywords=kw_list, location="Singapore")

    # Mark already-saved jobs
    saved_keys: set[str] = {
        f"{(j.title or '').lower()}|{(j.company or '').lower()}"
        for j in db.query(SavedJob).filter_by(user_profile_id=USER_ID).all()
    }

    return {
        "jobs": [
            {
                "title":       j.title,
                "company":     j.company,
                "location":    j.location,
                "snippet":     j.description_snippet,
                "job_url":     j.job_url,
                "posted_at":   j.posted_at,
                "source":      j.source,
                "already_saved": f"{j.title.lower()}|{j.company.lower()}" in saved_keys,
            }
            for j in jobs
        ],
        "keywords_used": kw_list,
        "mode": "live" if apify_connected() else "demo",
    }


@router.get("/api/notify/status")
def notify_status():
    return {
        "apify":  "live" if apify_connected() else "demo",
        "resend": "live" if os.getenv("RESEND_API_KEY") else "demo",
        "rules":  list(RULES.keys()),
    }


@router.post("/api/notify/jobs")
def notify_jobs(req: NotifyRequest, db: Session = Depends(get_db)):
    """Scrape fresh jobs via Apify, match against CV skills, email the results."""
    # Get top CV skills
    cv_skills = [
        s.canonical_skill_title
        for s in db.query(SkillMatchCache)
        .filter_by(source_type="cv", source_id=USER_ID)
        .order_by(SkillMatchCache.confidence.desc())
        .limit(10)
        .all()
    ]
    if not cv_skills:
        return {"error": "No CV skills found — paste your CV first."}

    # Fetch jobs from Apify
    jobs = fetch_jobs(keywords=cv_skills[:3], max_results=req.max_results)

    # Simple relevance filter: job description mentions any CV skill
    cv_lower = {s.lower() for s in cv_skills[:15]}
    matched = [
        j for j in jobs
        if any(sk in j.description_snippet.lower() for sk in cv_lower)
    ] or jobs  # if nothing matches, show all anyway

    to_email = req.to_email or default_email()
    if not to_email:
        return {"error": "No email address set. Add NOTIFICATION_EMAIL to .env or pass to_email in request."}

    result = fire_rule("new_job_matches", {
        "count": len(matched),
        "jobs": matched,
        "top_skills": cv_skills[:5],
    }, to_email)

    return {
        "jobs_found": len(jobs),
        "jobs_matched": len(matched),
        "apify_mode": "live" if apify_connected() else "demo",
        "notification": {
            "sent":     result.sent,
            "mode":     result.mode,
            "subject":  result.subject,
            "to_email": result.to_email,
            "error":    result.error,
        },
    }


@router.post("/api/notify/gaps")
def notify_gaps(req: NotifyRequest, db: Session = Depends(get_db)):
    """Send a gap reminder email with the user's top skill gaps."""
    from api.gap import get_gap

    gap_data = get_gap(db=db, job_ids=[])
    if "error" in gap_data:
        return gap_data

    top_gaps = [
        {"skill": g["skill"], "job_count": g["demand_count"]}
        for g in gap_data.get("gaps", [])[:5]
    ]

    to_email = req.to_email or default_email()
    if not to_email:
        return {"error": "No email address. Add NOTIFICATION_EMAIL to .env or pass to_email."}

    result = fire_rule("gap_reminder", {
        "count": len(top_gaps),
        "gaps":  top_gaps,
    }, to_email)

    return {
        "gaps_found": len(top_gaps),
        "notification": {
            "sent":    result.sent,
            "mode":    result.mode,
            "subject": result.subject,
            "error":   result.error,
        },
    }
