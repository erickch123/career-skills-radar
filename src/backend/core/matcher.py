"""
Hybrid skill matcher: free text → canonical SkillsFuture skill titles.

Three tiers (in order):
  1. Exact phrase match  — word-boundary regex; single-word titles require capitalisation
  2. Synonym layer       — tool/framework → canonical capability mapping
  3. Fuzzy match         — rapidfuzz token_sort_ratio ≥ 94; multi-word titles only

Every match returned carries method, confidence (0-100), and evidence_snippet.

Failure modes actively guarded against (see ARCHITECTURE §2.2):
  1. Subset/superset false matches  → token_sort_ratio not token_set_ratio
  2. Near-miss-but-distinct words   → threshold 94 (not lower)
  3. Common-English single-word titles → require capitalisation; excluded from fuzzy
  4. Substring inside unrelated words → word-boundary \\b in all regex
  5. Invented synonym targets        → SYNONYMS validated against skills_master.csv on load
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"

# ---------------------------------------------------------------------------
# Synonym dictionary — tool/framework names → canonical SkillsFuture titles
# Every value MUST exist in skills_master.csv (enforced on load)
# ---------------------------------------------------------------------------
SYNONYMS: dict[str, str] = {
    # Cloud
    "aws":                         "Cloud Computing Implementation",
    "amazon web services":         "Cloud Computing Implementation",
    "azure":                       "Cloud Computing Implementation",
    "microsoft azure":             "Cloud Computing Implementation",
    "gcp":                         "Cloud Computing Application",
    "google cloud":                "Cloud Computing Application",
    "google cloud platform":       "Cloud Computing Application",
    "terraform":                   "Cloud Computing Implementation",
    "infrastructure as code":      "Cloud Computing Implementation",
    "docker":                      "Cloud Computing Implementation",
    "kubernetes":                  "Cloud Computing Implementation",
    "k8s":                         "Cloud Computing Implementation",
    # Programming languages
    "python":                      "Software Design",
    "java":                        "Software Design",
    "javascript":                  "Software Design",
    "typescript":                  "Software Design",
    "golang":                      "Software Design",
    "rust":                        "Software Design",
    "scala":                       "Software Design",
    "kotlin":                      "Software Design",
    "c++":                         "Software Design",
    # Backend frameworks
    "fastapi":                     "Software Design",
    "django":                      "Software Design",
    "flask":                       "Software Design",
    "nodejs":                      "Software Design",
    "node.js":                     "Software Design",
    "spring boot":                 "Software Design",
    # Frontend
    "react":                       "Website Design",
    "vue":                         "Website Design",
    "angular":                     "Website Design",
    "nextjs":                      "Website Design",
    "next.js":                     "Website Design",
    "html":                        "Website Design",
    "css":                         "Website Design",
    # Data / BI tools
    "pandas":                      "Data Analytics",
    "numpy":                       "Data Analytics",
    "spark":                       "Data Analytics",
    "apache spark":                "Data Analytics",
    "tableau":                     "Business Intelligence and Data Analytics",
    "power bi":                    "Business Intelligence and Data Analytics",
    "looker":                      "Business Intelligence and Data Analytics",
    # Data engineering
    "dbt":                         "Data Engineering",
    "airflow":                     "Data Engineering",
    "apache airflow":              "Data Engineering",
    "kafka":                       "Data Engineering",
    "apache kafka":                "Data Engineering",
    "etl":                         "Data Engineering",
    # Databases
    "sql":                         "Database Administration",
    "postgresql":                  "Database Administration",
    "postgres":                    "Database Administration",
    "mysql":                       "Database Administration",
    "mongodb":                     "Database Administration",
    "redis":                       "Database Administration",
    "elasticsearch":               "Database Administration",
    "snowflake":                   "Database Administration",
    "bigquery":                    "Database Administration",
    # ML / AI
    "machine learning":            "Artificial Intelligence Application",
    "deep learning":               "Artificial Intelligence Application",
    "neural network":              "Artificial Intelligence Application",
    "tensorflow":                  "Artificial Intelligence Application",
    "pytorch":                     "Artificial Intelligence Application",
    "scikit-learn":                "Artificial Intelligence Application",
    "sklearn":                     "Artificial Intelligence Application",
    "hugging face":                "Artificial Intelligence Application",
    "langchain":                   "Artificial Intelligence Application",
    "llm":                         "Artificial Intelligence Application",
    "large language model":        "Artificial Intelligence Application",
    "generative ai":               "Artificial Intelligence Application",
    "computer vision":             "Artificial Intelligence Application",
    "natural language processing": "Analytics and Computational Modelling",
    "nlp":                         "Analytics and Computational Modelling",
    # DevOps / CI/CD
    "devops":                      "Software Configuration",
    "ci/cd":                       "Software Configuration",
    "cicd":                        "Software Configuration",
    "jenkins":                     "Software Configuration",
    "github actions":              "Software Configuration",
    "gitlab ci":                   "Software Configuration",
    "git":                         "Software Configuration",
    "version control":             "Software Configuration",
    # APIs / integration
    "rest api":                    "Systems Integration",
    "restful api":                 "Systems Integration",
    "graphql":                     "Systems Integration",
    "microservices":               "Systems Integration",
    "api development":             "Systems Integration",
    # Security
    "penetration testing":         "Cybersecurity",
    "vulnerability assessment":    "Cybersecurity",
    "zero trust":                  "Cybersecurity",
    "siem":                        "Cybersecurity",
    # Architecture
    "system design":               "Solution Architecture",
    "solution design":             "Solution Architecture",
    "microservices architecture":  "Solution Architecture",
    "domain driven design":        "Solution Architecture",
    # Agile / PM
    "scrum":                       "Agile Software Development",
    "kanban":                      "Agile Software Development",
    "sprint planning":             "Agile Software Development",
    "jira":                        "Project Management",
    "pmp":                         "Project Management",
    "prince2":                     "Project Management",
    # UX / Product
    "ux design":                   "User Experience Design",
    "ui/ux":                       "User Experience Design",
    "figma":                       "User Experience Design",
    "user research":               "User Experience Design",
    "product roadmap":             "Product Management",
}


@dataclass
class SkillMatch:
    skill_title: str
    method: str           # exact_phrase | synonym | fuzzy
    confidence: int       # 0-100
    evidence_snippet: str


class SkillMatcher:
    def __init__(self, data_dir: Path = DATA_DIR):
        skills_path = data_dir / "skills_master.csv"
        if not skills_path.exists():
            raise FileNotFoundError(
                f"{skills_path} not found. Run scripts/01_extract.py first."
            )
        df = pd.read_csv(skills_path)
        self._all_titles: list[str] = df["skill_title"].dropna().tolist()
        self._title_set: set[str] = set(self._all_titles)
        self._single_word: set[str] = {t for t in self._all_titles if len(t.split()) == 1}
        self._multi_word: list[str] = [t for t in self._all_titles if len(t.split()) > 1]
        self._synonyms = self._validate_synonyms()

    def _validate_synonyms(self) -> dict[str, str]:
        bad = [v for v in SYNONYMS.values() if v not in self._title_set]
        if bad:
            raise ValueError(
                f"Synonym targets not in skills_master.csv: {bad}\n"
                "Fix SYNONYMS before using the matcher."
            )
        return SYNONYMS

    # ------------------------------------------------------------------
    # Tier 1 — exact phrase match
    # ------------------------------------------------------------------
    def _exact_matches(self, text: str) -> list[SkillMatch]:
        results = []
        for title in self._all_titles:
            if title in self._single_word:
                # Single-word titles require capitalisation in the source text
                pattern = rf"\b{re.escape(title)}\b"
                if re.search(pattern, text):
                    results.append(SkillMatch(title, "exact_phrase", 100, title))
            else:
                # Multi-word: case-insensitive word-boundary match
                pattern = rf"\b{re.escape(title)}\b"
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    results.append(SkillMatch(title, "exact_phrase", 100, m.group()))
        return results

    # ------------------------------------------------------------------
    # Tier 2 — synonym match
    # ------------------------------------------------------------------
    def _synonym_matches(self, text: str, already_found: set[str]) -> list[SkillMatch]:
        results = []
        text_lower = text.lower()
        for alias, canonical in self._synonyms.items():
            if canonical in already_found:
                continue
            pattern = rf"\b{re.escape(alias)}\b"
            m = re.search(pattern, text_lower)
            if m:
                results.append(SkillMatch(canonical, "synonym", 90, m.group()))
                already_found.add(canonical)
        return results

    # ------------------------------------------------------------------
    # Tier 3 — fuzzy match (multi-word titles only)
    # ------------------------------------------------------------------
    def _fuzzy_matches(self, text: str, already_found: set[str]) -> list[SkillMatch]:
        THRESHOLD = 94
        results = []
        text_lower = text.lower()
        words = text_lower.split()

        for title in self._multi_word:
            if title in already_found:
                continue
            n = len(title.split())
            # Slide a window of the same word-count as the title
            for i in range(len(words) - n + 1):
                window = " ".join(words[i : i + n])
                score = fuzz.token_sort_ratio(window, title.lower())
                if score >= THRESHOLD:
                    results.append(SkillMatch(title, "fuzzy", score, window))
                    already_found.add(title)
                    break

        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract_skills(self, text: str) -> list[SkillMatch]:
        """Extract canonical SkillsFuture skills from free text."""
        if not text or not text.strip():
            return []

        found: set[str] = set()
        results: list[SkillMatch] = []

        exact = self._exact_matches(text)
        for m in exact:
            if m.skill_title not in found:
                found.add(m.skill_title)
                results.append(m)

        results.extend(self._synonym_matches(text, found))
        results.extend(self._fuzzy_matches(text, found))

        return sorted(results, key=lambda m: (-m.confidence, m.skill_title))

    def skill_exists(self, title: str) -> bool:
        return title in self._title_set


# Module-level singleton — loaded once at startup
_matcher: Optional[SkillMatcher] = None


def get_matcher() -> SkillMatcher:
    global _matcher
    if _matcher is None:
        _matcher = SkillMatcher()
    return _matcher
