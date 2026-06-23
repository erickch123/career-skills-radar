"""
Bulk-seed saved jobs from data/raw/companiesTracking1Year.csv via the running backend API.

Usage (from project root):
    python scripts/seed_jobs.py            # skip first 11 (already seeded)
    python scripts/seed_jobs.py --skip 0   # seed everything
    python scripts/seed_jobs.py --skip 20  # skip first 20 rows
"""

import csv
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

API = "http://localhost:8000/api/jobs"
CSV_PATH = Path(__file__).parent.parent / "data" / "raw" / "companiesTracking1Year.csv"

def load_jobs(skip: int) -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "company": r["Company"].strip(),
            "title": r["Title"].strip(),
            "jd_text": r["Job Description"].strip(),
        }
        for r in rows[skip:]
        if r["Company"].strip() and r["Job Description"].strip()
    ]


def seed(skip: int = 11):
    jobs = load_jobs(skip)
    print(f"Seeding {len(jobs)} jobs (skipping first {skip}) to {API}\n")
    success, failed = 0, 0

    for job in jobs:
        payload = json.dumps(job).encode()
        req = urllib.request.Request(
            API,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                print(f"✓ {job['company'][:25]:25}  {job['title'][:40]:40}  {result['skills_found']} skills")
                success += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"✗ {job['company'][:25]:25}  {job['title'][:40]}  HTTP {e.code} — {body[:100]}")
            failed += 1
        except Exception as e:
            print(f"✗ {job['company'][:25]:25}  {job['title'][:40]}  {e}")
            failed += 1

    print(f"\nDone — {success} saved, {failed} failed.")


if __name__ == "__main__":
    skip = 11
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--skip" and i + 2 < len(sys.argv):
            skip = int(sys.argv[i + 2])
    seed(skip)
