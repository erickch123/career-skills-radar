"""
Tests for matcher.py — specifically the 5 failure modes documented in ARCHITECTURE §2.2.
These are regression tests for bugs that were found during the original planning build.
Do not remove or weaken these tests — they exist because each failure mode was real.
"""

import pytest
from core.matcher import SkillMatcher, SYNONYMS

@pytest.fixture(scope="module")
def matcher():
    return SkillMatcher()


# ---------------------------------------------------------------------------
# Synonym validation — all targets must exist in skills_master.csv
# ---------------------------------------------------------------------------
def test_synonym_targets_all_valid(matcher):
    """Failure mode 5: invented/unverified canonical skill names."""
    for alias, target in SYNONYMS.items():
        assert matcher.skill_exists(target), (
            f"Synonym target '{target}' (for alias '{alias}') "
            "does not exist in skills_master.csv"
        )


# ---------------------------------------------------------------------------
# Failure mode 1: subset/superset false matches
# ---------------------------------------------------------------------------
def test_no_subset_superset_false_match(matcher):
    """
    'change management' must NOT match longer titles like
    'Organisational Change Management' or 'Climate Change Management'.
    Using token_sort_ratio instead of token_set_ratio guards against this.
    """
    text = "Experience with change management processes."
    matches = {m.skill_title for m in matcher.extract_skills(text)}

    assert "Change Management" in matches, "Should match 'Change Management' exactly"
    assert "Organisational Change Management" not in matches, (
        "Subset false match: 'change management' should not match "
        "'Organisational Change Management'"
    )


# ---------------------------------------------------------------------------
# Failure mode 2: near-miss-but-distinct words
# ---------------------------------------------------------------------------
def test_near_miss_words_rejected(matcher):
    """
    'channel strategy' must NOT match 'Change Management' (change/channel).
    'product owner' must NOT match 'Project Management' (project/product).
    Threshold 94 guards against this.
    """
    text = "Defined channel strategy and product owner responsibilities."
    matches = {m.skill_title for m in matcher.extract_skills(text)}

    assert "Change Management" not in matches, (
        "Near-miss false match: 'channel' should not match 'Change Management'"
    )
    assert "Project Management" not in matches, (
        "Near-miss false match: 'product owner' should not match 'Project Management'"
    )


# ---------------------------------------------------------------------------
# Failure mode 3: common English single-word skill titles
# ---------------------------------------------------------------------------
def test_single_word_titles_require_capitalisation(matcher):
    """
    Common-English words that are also canonical skill titles (Research, Documentation)
    must NOT fire on lowercase usage in normal prose.
    """
    lowercase_prose = (
        "we conducted research into market trends and "
        "maintained internal documentation for the project."
    )
    matches = {m.skill_title for m in matcher.extract_skills(lowercase_prose)}

    assert "Research" not in matches, (
        "Single-word false match: lowercase 'research' should not match 'Research'"
    )
    assert "Documentation" not in matches, (
        "Single-word false match: lowercase 'documentation' should not match 'Documentation'"
    )

def test_single_word_titles_match_when_capitalised(matcher):
    """The same words DO match when capitalised (intentional signal)."""
    text = "Core competency: Research. Maintained full Documentation."
    matches = {m.skill_title for m in matcher.extract_skills(text)}
    assert "Research" in matches
    assert "Documentation" in matches


# ---------------------------------------------------------------------------
# Failure mode 4: substring matches inside unrelated words
# ---------------------------------------------------------------------------
def test_no_substring_match_inside_words(matcher):
    """
    'aws' must NOT match inside 'laws', 'draws', 'raw'.
    Word-boundary regex guards against this.
    """
    text = "Familiar with environmental laws and raw material workflows."
    matches = {m.skill_title for m in matcher.extract_skills(text)}

    cloud_skills = {m for m in matches if "Cloud" in m}
    assert not cloud_skills, (
        f"Substring false match: 'aws' inside 'laws'/'raw' should not fire. Got: {cloud_skills}"
    )


# ---------------------------------------------------------------------------
# Positive smoke tests — real skills in real JD language
# ---------------------------------------------------------------------------
def test_synonym_match_aws(matcher):
    text = "5 years of AWS experience, managing EC2 and S3 buckets."
    matches = {m.skill_title for m in matcher.extract_skills(text)}
    assert "Cloud Computing Implementation" in matches

def test_synonym_match_python(matcher):
    text = "Strong Python and SQL skills required."
    matches = {m.skill_title for m in matcher.extract_skills(text)}
    assert "Software Design" in matches
    assert "Database Administration" in matches

def test_synonym_match_machine_learning(matcher):
    text = "Experience building machine learning pipelines with PyTorch."
    matches = {m.skill_title for m in matcher.extract_skills(text)}
    assert "Artificial Intelligence Application" in matches

def test_exact_match_multiword(matcher):
    text = "Responsible for Agile Software Development and sprint ceremonies."
    matches = {m.skill_title for m in matcher.extract_skills(text)}
    assert "Agile Software Development" in matches

def test_returns_evidence_snippet(matcher):
    text = "Proficient in Python development."
    results = matcher.extract_skills(text)
    assert any(r.evidence_snippet for r in results), "Each match must carry an evidence snippet"

def test_empty_text_returns_empty(matcher):
    assert matcher.extract_skills("") == []
    assert matcher.extract_skills("   ") == []
