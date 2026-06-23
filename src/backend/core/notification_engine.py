"""
Schema-driven notification engine using Resend.

Live mode  — RESEND_API_KEY set → real emails delivered.
Demo mode  — key absent → logs what would be sent, returns preview.
"""

import os
from dataclasses import dataclass
from typing import Any

RESEND_KEY   = os.getenv("RESEND_API_KEY")
FROM_EMAIL   = os.getenv("RESEND_FROM_EMAIL", "Career Radar <noreply@careerradar.app>")
NOTIFY_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")

# ── Rule schemas ──────────────────────────────────────────────────────────────

RULES: dict[str, dict] = {
    "new_job_matches": {
        "subject": "Career Radar: {count} new jobs match your profile",
        "description": "Fired when Apify finds jobs matching your top CV skills.",
    },
    "gap_reminder": {
        "subject": "Career Radar: Your top {count} skill gaps this week",
        "description": "Weekly summary of the skills most in demand that you're missing.",
    },
}


@dataclass
class NotificationResult:
    sent: bool
    mode: str          # 'live' | 'demo'
    subject: str
    to_email: str
    error: str = ""


# ── Public entry point ────────────────────────────────────────────────────────

def fire_rule(rule_name: str, context: dict, to_email: str) -> NotificationResult:
    """Render and send (or preview) a notification rule."""
    rule = RULES.get(rule_name)
    if not rule:
        return NotificationResult(sent=False, mode="error", subject="", to_email=to_email,
                                  error=f"Unknown rule: {rule_name}")

    subject = rule["subject"].format(**context)
    html    = _render_html(rule_name, context)

    if not RESEND_KEY:
        print(f"[notification_engine] DEMO — would send to {to_email}: {subject}")
        return NotificationResult(sent=False, mode="demo", subject=subject, to_email=to_email)

    try:
        import resend
        resend.api_key = RESEND_KEY
        resend.Emails.send({"from": FROM_EMAIL, "to": to_email, "subject": subject, "html": html})
        print(f"[notification_engine] Sent '{subject}' → {to_email}")
        return NotificationResult(sent=True, mode="live", subject=subject, to_email=to_email)
    except Exception as e:
        return NotificationResult(sent=False, mode="error", subject=subject, to_email=to_email,
                                  error=str(e))


def default_email() -> str:
    return NOTIFY_EMAIL


# ── HTML templates ────────────────────────────────────────────────────────────

def _render_html(rule_name: str, ctx: dict) -> str:
    if rule_name == "new_job_matches":
        return _jobs_email(ctx)
    if rule_name == "gap_reminder":
        return _gap_email(ctx)
    return f"<p>{ctx}</p>"


def _jobs_email(ctx: dict) -> str:
    jobs  = ctx.get("jobs", [])
    skills = ctx.get("top_skills", [])
    rows = ""
    for j in jobs:
        source_badge = "#0a66c2" if getattr(j, "source", "") == "linkedin" else "#003a9b"
        rows += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #eee;">
            <strong>{j.title}</strong>
            <span style="background:{source_badge};color:#fff;font-size:10px;
                         padding:1px 6px;border-radius:4px;margin-left:6px;">
              {j.source}
            </span><br>
            <span style="color:#555;font-size:13px;">{j.company} · {j.location}</span><br>
            <span style="color:#888;font-size:12px;">{j.description_snippet[:150]}…</span><br>
            <a href="{j.job_url}" style="font-size:12px;color:#4f46e5;">View job →</a>
          </td>
        </tr>"""

    skills_html = ", ".join(skills[:5]) if skills else "your CV skills"
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#1e1b4b;">Career Radar found {len(jobs)} new jobs for you</h2>
      <p style="color:#555;">Based on your top skills: <strong>{skills_html}</strong></p>
      <table style="width:100%;border-collapse:collapse;">{rows}</table>
      <hr style="margin:24px 0;border:none;border-top:1px solid #eee;">
      <p style="color:#aaa;font-size:11px;">
        Sent by Career Radar · SkillsFuture SG ·
        These are jobs found by AI — curate your shortlist on the dashboard.
      </p>
    </div>"""


def _gap_email(ctx: dict) -> str:
    gaps  = ctx.get("gaps", [])
    count = ctx.get("count", len(gaps))
    rows  = "".join(
        f'<li style="padding:4px 0;color:#333;">'
        f'<strong>{g.get("skill","")}</strong> — demanded by {g.get("job_count",0)} of your saved jobs</li>'
        for g in gaps[:5]
    )
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#1e1b4b;">Your top {count} skill gaps this week</h2>
      <p style="color:#555;">Skills most in demand across your curated shortlist that aren't on your CV yet:</p>
      <ul style="padding-left:20px;">{rows}</ul>
      <p><a href="https://skillsfuture.gov.sg" style="color:#4f46e5;">Browse SkillsFuture courses →</a></p>
      <hr style="margin:24px 0;border:none;border-top:1px solid #eee;">
      <p style="color:#aaa;font-size:11px;">Sent by Career Radar · SkillsFuture SG</p>
    </div>"""
