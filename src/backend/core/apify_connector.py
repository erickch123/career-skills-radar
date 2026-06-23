"""
Apify job scraper connector — cookieless LinkedIn + Indeed actors.

Live mode  — APIFY_API_TOKEN in .env → runs real Apify actors.
Demo mode  — token absent → returns mock jobs instantly.
"""

import os
from dataclasses import dataclass

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")

# Cookieless actors (no LinkedIn login required)
LINKEDIN_ACTOR = "bebity/linkedin-jobs-scraper"
INDEED_ACTOR   = "misceres/indeed-scraper"


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
    """Fetch jobs matching keywords. Live if APIFY_API_TOKEN set, mock otherwise."""
    if not APIFY_TOKEN:
        print("[apify_connector] No APIFY_API_TOKEN — returning mock jobs")
        return _mock_jobs(keywords)

    try:
        return _fetch_via_apify(keywords, location, max_results)
    except Exception as e:
        print(f"[apify_connector] Apify error, falling back to mock: {e}")
        return _mock_jobs(keywords)


def is_connected() -> bool:
    return bool(APIFY_TOKEN)


# ── Live fetch ────────────────────────────────────────────────────────────────

def _fetch_via_apify(keywords: list[str], location: str, max_results: int) -> list[ApifyJob]:
    from apify_client import ApifyClient

    client = ApifyClient(APIFY_TOKEN)
    jobs: list[ApifyJob] = []

    # Build search query from top 3 keywords
    query = " ".join(keywords[:3])

    # LinkedIn
    run = client.actor(LINKEDIN_ACTOR).call(run_input={
        "queries":    [f"{query} {location}"],
        "maxResults": max_results,
    })
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        jobs.append(ApifyJob(
            title=item.get("title", ""),
            company=item.get("company", ""),
            location=item.get("location", location),
            description_snippet=(item.get("description", "")[:300]),
            job_url=item.get("jobUrl", ""),
            posted_at=item.get("publishedAt", ""),
            source="linkedin",
        ))

    # Indeed
    run2 = client.actor(INDEED_ACTOR).call(run_input={
        "queries": [{"query": query, "location": location, "maxItems": max_results}],
    })
    for item in client.dataset(run2["defaultDatasetId"]).iterate_items():
        jobs.append(ApifyJob(
            title=item.get("positionName", ""),
            company=item.get("company", ""),
            location=item.get("location", location),
            description_snippet=(item.get("description", "")[:300]),
            job_url=item.get("url", ""),
            posted_at=item.get("datePosted", ""),
            source="indeed",
        ))

    return jobs[:max_results]


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
