"""
Email job alert endpoints.

GET /api/email/jobs — fetch LinkedIn alert jobs (real or mock), mark already-saved ones.

Adding a job to My Saved Jobs happens via the existing POST /api/jobs endpoint —
the user pastes the full JD there, so no separate import endpoint is needed.
"""

import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.models import SavedJob
from core.email_connector import fetch_job_alerts, is_connected

router = APIRouter()
USER_ID = 1


@router.get("/api/email/jobs")
def get_email_jobs(db: Session = Depends(get_db)):
    """Fetch job alerts and flag ones already saved by title+company match."""
    alerts = fetch_job_alerts(max_per_source=3)

    saved_keys: set[str] = {
        f"{(j.title or '').lower()}|{(j.company or '').lower()}"
        for j in db.query(SavedJob).filter_by(user_profile_id=USER_ID).all()
    }

    result = []
    for i, alert in enumerate(alerts):
        key = f"{alert.title.lower()}|{alert.company.lower()}"
        result.append({
            "index": i,
            "title": alert.title,
            "company": alert.company,
            "location": alert.location,
            "job_url": alert.job_url,
            "email_date": alert.email_date,
            "email_subject": alert.email_subject,
            "source": alert.source,       # 'linkedin' | 'indeed'
            "already_saved": key in saved_keys,
        })

    return {"jobs": result, "mode": "gmail" if is_connected() else "demo"}
