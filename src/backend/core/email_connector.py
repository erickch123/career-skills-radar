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
        "query": "from:jobalerts-noreply@linkedin.com",
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

def fetch_job_alerts(max_per_source: int = 3) -> list[EmailJobAlert]:
    """Return job alerts. Uses Gmail API if token.json exists, otherwise mock data."""
    if TOKEN_PATH.exists():
        try:
            return _fetch_via_api(max_per_source)
        except Exception as e:
            print(f"[email_connector] Gmail API error, falling back to mock: {e}")
    return _mock_alerts()


def is_connected() -> bool:
    return TOKEN_PATH.exists()


# ── Gmail API fetch ───────────────────────────────────────────────────────────

def _fetch_via_api(max_per_source: int) -> list[EmailJobAlert]:
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
            alerts = _parse_api_message(msg, source_key, cfg)
            print(f"[email_connector] {source_key} msg — parsed {len(alerts)} job alert(s)")
            all_alerts.extend(alerts)

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[EmailJobAlert] = []
    for a in all_alerts:
        if a.job_url not in seen:
            seen.add(a.job_url)
            unique.append(a)
    return unique


def _parse_api_message(msg: dict, source_key: str, cfg: dict) -> list[EmailJobAlert]:
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("Subject", "")
    date_str = headers.get("Date", "")

    html_body = _extract_html_body(msg.get("payload", {}))
    if not html_body:
        return []

    return _parse_html(html_body, subject, date_str, source_key, cfg)


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

def _parse_html(
    html: str, subject: str, date_str: str, source_key: str, cfg: dict
) -> list[EmailJobAlert]:
    soup = BeautifulSoup(html, "html.parser")
    alerts: list[EmailJobAlert] = []

    job_links = soup.find_all("a", href=cfg["job_link_pattern"])
    for link in job_links:
        title = link.get_text(separator=" ", strip=True)
        if not title or len(title) < 3:
            continue

        raw_url = link.get("href", "")
        url_match = cfg["url_clean_pattern"].search(raw_url)
        url = url_match.group(1) if url_match else raw_url

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


def _extract_company_location(link_tag) -> tuple[str, str]:
    parent = link_tag.parent
    for _ in range(3):
        if parent is None:
            break
        texts = [
            t.strip()
            for t in parent.stripped_strings
            if t.strip() and t.strip() != link_tag.get_text(strip=True)
        ]
        non_empty = [t for t in texts if len(t) > 1]
        if non_empty:
            company = non_empty[0]
            location = non_empty[1] if len(non_empty) > 1 else ""
            if re.match(r"^\d+", company):
                company = "Unknown"
            if re.match(r"^\d+", location):
                location = ""
            return company, location
        parent = parent.parent
    return "Unknown", ""


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
