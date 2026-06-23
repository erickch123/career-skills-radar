"""
Two-tier seniority classifier.
Tier 1: regex rules on title + years-of-experience extraction from JD text.
Tier 2: Claude Haiku fallback for ambiguous cases.
"""

import os
import re

TIERS = ["entry", "mid", "senior", "staff_principal", "manager_plus"]

# Title keyword → tier (checked in order; first match wins)
_TITLE_RULES: list[tuple[str, list[str]]] = [
    ("manager_plus", [
        r"\bmanager\b", r"\bdirector\b", r"\bvice\s+president\b", r"\bvp\b",
        r"\bhead\s+of\b", r"\bchief\b", r"\bcto\b", r"\bcpo\b", r"\bcdo\b",
    ]),
    ("staff_principal", [
        r"\bstaff\b", r"\bprincipal\b", r"\blead\b", r"\barchitect\b",
    ]),
    ("senior", [
        r"\bsenior\b", r"\bsr\b", r"\bsr\.\b",
    ]),
    ("entry", [
        r"\bintern\b", r"\binternship\b", r"\bjunior\b", r"\bjr\b", r"\bjr\.\b",
        r"\bgraduate\b", r"\bgrad\b", r"\bentry.level\b", r"\btrainee\b",
        r"\bapprentice\b", r"\bfresh\s+grad\b",
    ]),
]

# Patterns to extract minimum years of experience from JD body
_YEARS_PATTERNS = [
    r"(\d+)\+\s*years?\s+of\s+(relevant\s+)?experience",
    r"(\d+)\+\s*years?\s+(of\s+)?working",
    r"minimum\s+(?:of\s+)?(\d+)\s*years?",
    r"at\s+least\s+(\d+)\s*years?",
    r"more\s+than\s+(\d+)\s*years?",
    r"typically\s+(\d+)\+?\s*years?",
    r"(\d+)\s*[-–]\s*\d+\s*years?\s+of\s+experience",  # lower bound of range
    r"(\d+)\s*[-–]\s*\d+\s*years?\s+experience",
]


def _years_to_tier(years: int) -> str:
    if years <= 1:
        return "entry"
    if years <= 4:
        return "mid"
    if years <= 7:
        return "senior"
    if years <= 10:
        return "staff_principal"
    return "manager_plus"


def _rule_classify(title: str, jd_text: str) -> tuple[str | None, str, str]:
    """Return (tier | None, method, reasoning)."""
    title_lower = title.lower()

    for tier, patterns in _TITLE_RULES:
        for pat in patterns:
            if re.search(pat, title_lower):
                return tier, "rule", f"title matches '{pat}'"

    jd_lower = jd_text.lower()
    for pat in _YEARS_PATTERNS:
        m = re.search(pat, jd_lower)
        if m:
            years = int(m.group(1))
            tier = _years_to_tier(years)
            return tier, "rule", f"JD requires {years}+ years → {tier}"

    return None, "", ""


def _llm_classify(title: str, jd_text: str) -> tuple[str, str]:
    """Return (tier, reasoning) via Claude Haiku."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = (
        f"Job title: {title}\n\n"
        f"Job description excerpt:\n{jd_text[:800]}\n\n"
        "Classify the seniority level of this role. "
        "Reply with EXACTLY one of these words and nothing else:\n"
        "entry | mid | senior | staff_principal | manager_plus"
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip().lower().replace(" ", "_")
    tier = raw if raw in TIERS else "mid"
    return tier, "llm"


def classify_job(title: str, jd_text: str) -> tuple[str, str, str]:
    """Return (tier, method, reasoning)."""
    tier, method, reasoning = _rule_classify(title, jd_text)
    if tier:
        return tier, method, reasoning

    tier, method = _llm_classify(title, jd_text)
    return tier, method, f"LLM classified as {tier} (rules inconclusive)"
