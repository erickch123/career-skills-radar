"""
Job alert email connector — LinkedIn + Indeed via Gmail API.

Live mode  — token.json exists in src/backend/ → uses Gmail API (OAuth 2.0).
             Run `python3 scripts/gmail_auth.py` once to create token.json.
Demo mode  — token.json absent → returns hardcoded mock alerts (safe for deployed demo).
"""

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

TOKEN_PATH = Path(__file__).parent.parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

SOURCES = {
    "linkedin": {
        # LinkedIn sends from multiple addresses — cover all known ones
        "query": "from:jobalerts-noreply@linkedin.com OR from:jobs-noreply@linkedin.com OR from:notifications@linkedin.com",
        "job_link_pattern": re.compile(r"linkedin\.com/jobs/view/\d+"),
        "url_clean_pattern": re.compile(r"(https://www\.linkedin\.com/jobs/view/\d+)"),
    },
    "indeed": {
        "query": "from:alert@indeed.com",
        "job_link_pattern": re.compile(r"indeed\.com/(viewjob|rc/clk|pagead/clk)"),
        "url_clean_pattern": re.compile(r"(https://[a-z.]*indeed\.com/(?:viewjob|rc/clk|pagead/clk)[^\s\"'>]+)"),
    },
}


@dataclass
class EmailJobAlert:
    title: str
    company: str
    location: str
    job_url: str
    email_date: str
    email_subject: str
    source: str  # 'linkedin' | 'indeed'


# ── Public entry point ────────────────────────────────────────────────────────

def fetch_job_alerts(max_per_source: int = 2, max_jobs_per_email: int = 6) -> list[EmailJobAlert]:
    """Return job alerts. Uses Gmail API if token.json exists, otherwise mock data."""
    if TOKEN_PATH.exists():
        try:
            return _fetch_via_api(max_per_source, max_jobs_per_email)
        except Exception as e:
            print(f"[email_connector] Gmail API error, falling back to mock: {e}")
    return _mock_alerts()


def is_connected() -> bool:
    return TOKEN_PATH.exists()


# ── Gmail API fetch ───────────────────────────────────────────────────────────

def _fetch_via_api(max_per_source: int, max_jobs_per_email: int = 6) -> list[EmailJobAlert]:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        TOKEN_PATH.write_text(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    all_alerts: list[EmailJobAlert] = []

    for source_key, cfg in SOURCES.items():
        print(f"[email_connector] querying {source_key}: {cfg['query']}")
        results = (
            service.users()
            .messages()
            .list(userId="me", q=cfg["query"], maxResults=max_per_source)
            .execute()
        )
        messages = results.get("messages", [])
        print(f"[email_connector] {source_key}: found {len(messages)} message(s)")

        for msg_meta in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_meta["id"], format="full")
                .execute()
            )
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            print(f"[email_connector] {source_key} msg — From: {headers.get('From')} | Subject: {headers.get('Subject', '')[:60]}")
            alerts = _parse_api_message(msg, source_key, cfg, max_jobs_per_email)
            print(f"[email_connector] {source_key} msg — parsed {len(alerts)} job alert(s)")
            all_alerts.extend(alerts)

    # Deduplicate by stable job key (job ID from URL), then by (title, company) as fallback
    seen_keys: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    unique: list[EmailJobAlert] = []
    for a in all_alerts:
        key = _stable_job_key(a.job_url, a.source)
        pair = (a.title.lower()[:60], a.company.lower()[:40])
        if key in seen_keys or pair in seen_pairs:
            continue
        seen_keys.add(key)
        seen_pairs.add(pair)
        unique.append(a)
    return unique


def _parse_api_message(msg: dict, source_key: str, cfg: dict, max_jobs: int = 6) -> list[EmailJobAlert]:
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("Subject", "")
    date_str = headers.get("Date", "")

    html_body = _extract_html_body(msg.get("payload", {}))
    if not html_body:
        return []

    return _parse_html(html_body, subject, date_str, source_key, cfg, max_jobs)


def _extract_html_body(payload: dict) -> str:
    """Recursively find the text/html part and decode it from base64url."""
    mime = payload.get("mimeType", "")
    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_html_body(part)
        if result:
            return result
    return ""


# ── HTML parsing (shared between API and legacy IMAP paths) ──────────────────

# Text that appears in email cards but is not a company name or location
_CARD_NOISE = re.compile(
    r"^\d+[\.\d]*$"           # standalone ratings like "3.9"
    r"|just posted"
    r"|\d+\s*(day|hour|week|month)s?\s*ago"
    r"|direct apply"
    r"|via indeed|via linkedin"
    r"|apply now"
    r"|new\s*!?"
    r"|promoted",
    re.IGNORECASE,
)


def _extract_title(link_tag) -> str:
    """Return only the job title from an anchor tag, ignoring card body text."""
    # Prefer a heading or strong element (common in Indeed/LinkedIn emails)
    for tag_name in ("h2", "h3", "h4", "strong", "b", "span"):
        el = link_tag.find(tag_name)
        if el:
            t = el.get_text(strip=True)
            if t and len(t) > 3:
                return t
    # Fall back to the first non-empty line of the link text
    lines = [ln.strip() for ln in link_tag.get_text(separator="\n").split("\n") if ln.strip()]
    return lines[0] if lines else ""


def _extract_company_location(link_tag) -> tuple[str, str]:
    """Extract company and location from inside the card anchor or its siblings."""
    # Get all lines of text inside the card, skip the first (title) and noise
    lines = [ln.strip() for ln in link_tag.get_text(separator="\n").split("\n") if ln.strip()]
    candidates = [
        ln for ln in lines[1:]
        if len(ln) > 1
        and len(ln) < 80  # skip long description snippets
        and not _CARD_NOISE.search(ln)
    ]
    company = candidates[0] if candidates else "Unknown"
    location = candidates[1] if len(candidates) > 1 else ""
    return company, location


def _stable_job_key(url: str, source_key: str) -> str:
    """Return a stable dedup key regardless of tracking parameters in the URL."""
    if source_key == "linkedin":
        m = re.search(r"/jobs/view/(\d+)", url)
        return f"linkedin:{m.group(1)}" if m else url
    # Indeed: extract jk= job key from any URL type (viewjob, rc/clk, pagead/clk)
    m = re.search(r"[?&]jk=([a-z0-9]+)", url)
    return f"indeed:{m.group(1)}" if m else url


def _parse_html(
    html: str, subject: str, date_str: str, source_key: str, cfg: dict, max_jobs: int = 6
) -> list[EmailJobAlert]:
    soup = BeautifulSoup(html, "html.parser")
    alerts: list[EmailJobAlert] = []
    seen_in_email: set[str] = set()

    job_links = soup.find_all("a", href=cfg["job_link_pattern"])
    for link in job_links:
        if len(alerts) >= max_jobs:
            break
        raw_url = link.get("href", "")
        url_match = cfg["url_clean_pattern"].search(raw_url)
        url = url_match.group(1) if url_match else raw_url

        # Dedup within a single email using stable job key
        key = _stable_job_key(url, source_key)
        if key in seen_in_email:
            continue
        seen_in_email.add(key)

        title = _extract_title(link)
        if not title or len(title) < 3:
            continue

        company, location = _extract_company_location(link)
        alerts.append(EmailJobAlert(
            title=title,
            company=company,
            location=location,
            job_url=url,
            email_date=_format_date(date_str),
            email_subject=subject,
            source=source_key,
        ))
    return alerts


def _format_date(date_str: str) -> str:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%d %b %Y")
    except Exception:
        return date_str[:16] if date_str else ""


# ── Mock data (demo / deployed environment) ───────────────────────────────────

def _mock_alerts() -> list[EmailJobAlert]:
    return [
        # ── LinkedIn (3) ──
        EmailJobAlert(
            title="Senior Data Engineer",
            company="DBS Bank",
            location="Singapore",
            job_url="https://www.linkedin.com/jobs/view/1000000001",
            email_date="23 Jun 2026",
            email_subject="5 new Data Engineer jobs for you",
            source="linkedin",
        ),
        EmailJobAlert(
            title="AI/ML Engineer",
            company="GovTech Singapore",
            location="Singapore",
            job_url="https://www.linkedin.com/jobs/view/1000000002",
            email_date="23 Jun 2026",
            email_subject="5 new AI Engineer jobs for you",
            source="linkedin",
        ),
        EmailJobAlert(
            title="Data Scientist, Risk Analytics",
            company="OCBC Bank",
            location="Singapore",
            job_url="https://www.linkedin.com/jobs/view/1000000003",
            email_date="22 Jun 2026",
            email_subject="3 new Data Scientist jobs for you",
            source="linkedin",
        ),
        # ── Indeed (3) ──
        EmailJobAlert(
            title="Python Developer, Quantitative Finance",
            company="Temasek Holdings",
            location="Singapore",
            job_url="https://sg.indeed.com/viewjob?jk=mock000000001",
            email_date="23 Jun 2026",
            email_subject="New jobs matching 'Python Developer' in Singapore",
            source="indeed",
        ),
        EmailJobAlert(
            title="Analytics Engineer",
            company="Sea Group (Shopee)",
            location="Singapore",
            job_url="https://sg.indeed.com/viewjob?jk=mock000000002",
            email_date="22 Jun 2026",
            email_subject="New jobs matching 'Analytics Engineer' in Singapore",
            source="indeed",
        ),
        EmailJobAlert(
            title="Software Engineer – Data Platform",
            company="Grab",
            location="Singapore",
            job_url="https://sg.indeed.com/viewjob?jk=mock000000003",
            email_date="21 Jun 2026",
            email_subject="New jobs matching 'Software Engineer' in Singapore",
            source="indeed",
        ),
    ]
