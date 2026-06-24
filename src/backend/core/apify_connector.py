"""
Apify job scraper connector — LinkedIn + Indeed.

Live mode  — APIFY_API_KEY in .env → runs real Apify actors.
Demo mode  — token absent → returns mock jobs instantly.

Actors used (cheap pay-per-result):
  LinkedIn : curious_coder/linkedin-jobs-scraper  ($0.001/result)
  Indeed   : valig/indeed-jobs-scraper            ($0.0001/result)
"""

import os
import urllib.parse
from dataclasses import dataclass

# Env var name matches what's in src/backend/.env
APIFY_TOKEN = os.getenv("APIFY_API_KEY")

LINKEDIN_ACTOR = "curious_coder/linkedin-jobs-scraper"
INDEED_ACTOR   = "valig/indeed-jobs-scraper"

RESULTS_PER_SOURCE = 5   # 5 from LinkedIn + 5 from Indeed = 10 total


@dataclass
class ApifyJob:
    title: str
    company: str
    location: str
    description_snippet: str
    job_url: str
    posted_at: str
    source: str  # 'linkedin' | 'indeed'


def fetch_jobs(keywords: list[str], location: str = "Singapore", max_results: int = 10) -> list[ApifyJob]:
    """Fetch jobs matching keywords. Live if APIFY_API_KEY set, mock otherwise."""
    if not APIFY_TOKEN:
        print("[apify_connector] No APIFY_API_KEY — returning mock jobs")
        return _mock_jobs(keywords)

    try:
        return _fetch_via_apify(keywords, location)
    except Exception as e:
        print(f"[apify_connector] Apify error, falling back to mock: {e}")
        return _mock_jobs(keywords)


def is_connected() -> bool:
    return bool(APIFY_TOKEN)


# ── Live fetch ────────────────────────────────────────────────────────────────

def _fetch_via_apify(keywords: list[str], location: str) -> list[ApifyJob]:
    from apify_client import ApifyClient

    client = ApifyClient(APIFY_TOKEN)
    query = " ".join(keywords[:3])
    jobs: list[ApifyJob] = []

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    # curious_coder actor takes search page URLs, not raw queries
    linkedin_url = (
        "https://www.linkedin.com/jobs/search/?"
        + urllib.parse.urlencode({"keywords": query, "location": location, "position": 1, "pageNum": 0})
    )
    print(f"[apify_connector] LinkedIn search URL: {linkedin_url}")

    li_run = client.actor(LINKEDIN_ACTOR).call(run_input={
        "urls": [linkedin_url],
        "count": RESULTS_PER_SOURCE,
        "scrapeCompany": False,  # skip extra company page requests for speed
    })
    for item in client.dataset(li_run["defaultDatasetId"]).iterate_items():
        jobs.append(ApifyJob(
            title=item.get("title") or item.get("jobTitle") or "",
            company=item.get("companyName") or item.get("company") or "",
            location=item.get("location") or location,
            description_snippet=(item.get("description") or item.get("descriptionText") or "")[:300],
            job_url=item.get("jobUrl") or item.get("url") or "",
            posted_at=item.get("publishedAt") or item.get("postedDate") or "",
            source="linkedin",
        ))
        if len([j for j in jobs if j.source == "linkedin"]) >= RESULTS_PER_SOURCE:
            break

    # ── Indeed ────────────────────────────────────────────────────────────────
    # valig actor takes keyword + country (ISO 2-letter) + location
    in_run = client.actor(INDEED_ACTOR).call(run_input={
        "title": query,
        "country": "sg",    # Singapore
        "location": location,
        "limit": RESULTS_PER_SOURCE,
    })
    for item in client.dataset(in_run["defaultDatasetId"]).iterate_items():
        jobs.append(ApifyJob(
            title=item.get("title") or item.get("jobTitle") or "",
            company=item.get("companyName") or item.get("company") or "",
            location=item.get("location") or item.get("city") or location,
            description_snippet=(item.get("description") or item.get("summary") or "")[:300],
            job_url=item.get("applyUrl") or item.get("link") or item.get("url") or "",
            posted_at=item.get("datePosted") or item.get("publishedAt") or "",
            source="indeed",
        ))
        if len([j for j in jobs if j.source == "indeed"]) >= RESULTS_PER_SOURCE:
            break

    print(f"[apify_connector] fetched {len(jobs)} jobs total")
    return jobs


# ── Mock data ─────────────────────────────────────────────────────────────────

def _mock_jobs(keywords: list[str]) -> list[ApifyJob]:
    kw = keywords[0] if keywords else "Data"
    return [
        ApifyJob(
            title=f"Senior {kw} Engineer",
            company="GovTech Singapore",
            location="Singapore",
            description_snippet=f"We are looking for a {kw} Engineer with 5+ years experience in Python, SQL, and cloud platforms. You will build scalable data pipelines and work closely with product teams.",
            job_url="https://www.linkedin.com/jobs/view/mock001",
            posted_at="2 days ago",
            source="linkedin",
        ),
        ApifyJob(
            title=f"{kw} Scientist, Risk & Analytics",
            company="DBS Bank",
            location="Singapore",
            description_snippet=f"Join our Risk Analytics team to apply {kw} techniques to credit, fraud, and market risk problems. Strong Python and ML experience required.",
            job_url="https://www.linkedin.com/jobs/view/mock002",
            posted_at="1 day ago",
            source="linkedin",
        ),
        ApifyJob(
            title=f"Lead {kw} Analyst",
            company="Sea Group (Shopee)",
            location="Singapore",
            description_snippet=f"Lead a team of analysts to deliver {kw}-driven insights across our e-commerce platform. Experience with Spark, dbt, and stakeholder management essential.",
            job_url="https://sg.indeed.com/viewjob?jk=mock003",
            posted_at="3 days ago",
            source="indeed",
        ),
        ApifyJob(
            title=f"{kw} Platform Engineer",
            company="Grab",
            location="Singapore",
            description_snippet=f"Build and maintain our {kw} platform serving 100M+ users. You will own infrastructure, tooling, and developer experience for the {kw} org.",
            job_url="https://sg.indeed.com/viewjob?jk=mock004",
            posted_at="5 days ago",
            source="indeed",
        ),
        ApifyJob(
            title=f"AI / {kw} Engineer",
            company="Temasek Holdings",
            location="Singapore",
            description_snippet=f"Work on cutting-edge AI and {kw} applications across Temasek's portfolio companies. LLM experience and financial domain knowledge are a plus.",
            job_url="https://www.linkedin.com/jobs/view/mock005",
            posted_at="Today",
            source="linkedin",
        ),
    ]
