"""
GET /api/timeline — monthly activity breakdown for the history panel.

Work logs are bucketed by period_covered (when the work happened), not date_logged
(when the entry was added to the database). Falls back to date_logged only if
period_covered is absent or unparseable.
"""

import re
from datetime import datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.models import SavedJob, WorkLogEntry

router = APIRouter()
USER_ID = 1

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
_QUARTER_START = {1: 1, 2: 4, 3: 7, 4: 10}


def _parse_period(period_covered: str | None) -> tuple[int, int] | None:
    """Parse a free-text period string into (year, month).

    Handles:
      "Q1 2025", "2025 Q1"  → first month of the quarter
      "Jun 2025", "June 2025", "Jun-2025"
      "2025"                → January of that year
    Returns None if unparseable.
    """
    if not period_covered:
        return None
    s = period_covered.strip().lower()

    year_m = re.search(r'\b(20\d{2})\b', s)
    if not year_m:
        return None
    year = int(year_m.group(1))

    # Quarter: q1–q4
    q_m = re.search(r'q([1-4])', s)
    if q_m:
        return year, _QUARTER_START[int(q_m.group(1))]

    # Month name (first 3 letters sufficient)
    for abbrev, month_num in _MONTH_MAP.items():
        if abbrev in s:
            return year, month_num

    return year, 1  # year only → January


def _month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%b '%y")


def _worklog_period_key(log: WorkLogEntry) -> str:
    """Return the month key representing WHEN the work happened."""
    parsed = _parse_period(log.period_covered)
    if parsed:
        return _month_key(*parsed)
    # Fallback: when it was logged
    return log.date_logged.strftime("%Y-%m")


def _worklog_period_sort_date(log: WorkLogEntry) -> str:
    """ISO date string for sorting — uses period start date if parseable."""
    parsed = _parse_period(log.period_covered)
    if parsed:
        return f"{parsed[0]}-{parsed[1]:02d}-01T00:00:00+00:00"
    return log.date_logged.isoformat()


@router.get("/api/timeline")
def get_timeline(db: Session = Depends(get_db)):
    jobs = (
        db.query(SavedJob)
        .filter(SavedJob.user_profile_id == USER_ID)
        .order_by(SavedJob.date_saved)
        .all()
    )
    logs = (
        db.query(WorkLogEntry)
        .filter(WorkLogEntry.user_profile_id == USER_ID)
        .all()
    )

    jobs_by_month: dict[str, int] = defaultdict(int)
    logs_by_month: dict[str, int] = defaultdict(int)

    for job in jobs:
        key = job.date_saved.strftime("%Y-%m")
        jobs_by_month[key] += 1

    for log in logs:
        key = _worklog_period_key(log)
        logs_by_month[key] += 1

    all_keys = sorted(set(list(jobs_by_month) + list(logs_by_month)))

    months = []
    for key in all_keys:
        y, m = int(key[:4]), int(key[5:])
        months.append({
            "month": _month_label(y, m),
            "year_month": key,
            "jobs_saved": jobs_by_month.get(key, 0),
            "work_logs": logs_by_month.get(key, 0),
        })

    # Recent activity feed — interleaved, sorted by when things happened
    recent: list[dict] = []
    for job in jobs[-20:]:
        recent.append({
            "type": "job",
            "date": job.date_saved.isoformat(),
            "label": (job.title or "Job") + (f" @ {job.company}" if job.company else ""),
            "meta": job.seniority_tier or "",
        })
    for log in logs:
        recent.append({
            "type": "worklog",
            "date": _worklog_period_sort_date(log),
            "label": log.period_covered or "Work log entry",
            "meta": (log.seniority_signal or "").replace("_", " "),
        })

    recent.sort(key=lambda x: x["date"], reverse=True)

    return {
        "months": months,
        "total_jobs": len(jobs),
        "total_work_logs": len(logs),
        "active_months": len(months),
        "recent": recent[:12],
    }
