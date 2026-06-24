"""
Backfill historical dates for saved_job and work_log_entry records.

Distributes jobs across Jul 2025 → Jun 2026 with a realistic uneven pattern:
- 2 peak months (high job-hunting activity)
- 2 quiet months (very few saves)
- remaining months at medium volume

Usage:
    cd src/backend && python ../../scripts/backfill_dates.py
"""

import os, random, sys, calendar
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/backend")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../src/backend/.env"))

from db import SessionLocal
from models.models import SavedJob, WorkLogEntry

# Months in order: (year, month)
MONTHS = [
    (2025, 7),  (2025, 8),  (2025, 9),  (2025, 10),
    (2025, 11), (2025, 12), (2026, 1),  (2026, 2),
    (2026, 3),  (2026, 4),  (2026, 5),  (2026, 6),
]

# Relative weights — higher = more jobs that month
# Two peaks: Sep '25 and Feb '26 (post-summer hustle, post-new-year push)
# Two troughs: Dec '25 and May '26 (holiday lull, pre-summer wind-down)
WEIGHTS = {
    (2025, 7):  6,
    (2025, 8):  8,
    (2025, 9):  18,   # peak
    (2025, 10): 9,
    (2025, 11): 7,
    (2025, 12): 2,    # trough
    (2026, 1):  8,
    (2026, 2):  17,   # peak
    (2026, 3):  10,
    (2026, 4):  8,
    (2026, 5):  3,    # trough
    (2026, 6):  4,
}


def _random_datetime_in_month(year: int, month: int) -> datetime:
    days_in_month = calendar.monthrange(year, month)[1]
    day  = random.randint(1, days_in_month)
    hour = random.randint(8, 22)
    minute = random.randint(0, 59)
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _build_month_pool(total: int) -> list[tuple[int, int]]:
    """Return a list of (year, month) of length `total`, weighted by WEIGHTS."""
    total_weight = sum(WEIGHTS.values())
    pool: list[tuple[int, int]] = []
    for ym, w in WEIGHTS.items():
        count = round(total * w / total_weight)
        pool.extend([ym] * count)
    # adjust rounding error
    while len(pool) < total:
        pool.append(max(WEIGHTS, key=WEIGHTS.get))  # type: ignore[arg-type]
    while len(pool) > total:
        pool.pop()
    random.shuffle(pool)
    return pool


def backfill_jobs(session):
    jobs = session.query(SavedJob).order_by(SavedJob.id).all()
    if not jobs:
        print("No saved_job rows found.")
        return
    print(f"Backfilling {len(jobs)} saved_job rows with realistic monthly distribution…")
    pool = _build_month_pool(len(jobs))
    # Sort pool so earlier jobs get earlier months (preserves rough chronology)
    pool.sort()
    counts: dict[str, int] = {}
    for job, (y, m) in zip(jobs, pool):
        job.date_saved = _random_datetime_in_month(y, m)
        key = f"{y}-{m:02d}"
        counts[key] = counts.get(key, 0) + 1
    session.commit()
    print("  Monthly distribution:")
    for ym in MONTHS:
        key = f"{ym[0]}-{ym[1]:02d}"
        dt = datetime(ym[0], ym[1], 1)
        bar = "█" * counts.get(key, 0)
        print(f"    {dt.strftime('%b %Y')}  {counts.get(key, 0):3d}  {bar}")


def backfill_worklogs(session):
    entries = session.query(WorkLogEntry).order_by(WorkLogEntry.id).all()
    if not entries:
        print("No work_log_entry rows found.")
        return
    print(f"Backfilling {len(entries)} work_log_entry rows…")
    pool = _build_month_pool(len(entries))
    pool.sort()
    for entry, (y, m) in zip(entries, pool):
        entry.date_logged = _random_datetime_in_month(y, m)
    session.commit()
    print("  Done.")


if __name__ == "__main__":
    random.seed(42)
    with SessionLocal() as session:
        backfill_jobs(session)
        backfill_worklogs(session)
    print("Backfill complete.")
