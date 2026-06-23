"""
Gap engine: CV skills × saved JD skills → ranked gaps, readiness score, pathfinder.

Functions:
  analyze_jd_vs_cv       — per-JD have/missing split
  aggregate_demand       — across all JDs, count how often each skill is demanded
  rank_action_list       — top-N ranked gaps with plain-language reason per item
  find_closest_roles     — Career Pathfinder: SkillsFuture roles ranked by overlap count
  readiness_score        — average % of each JD's required skills already evidenced
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed"

EMERGING_BONUS  = 0.15   # added to priority score when skill is flagged is_emerging
CASL_BONUS      = 0.10   # added to priority score when skill is flagged is_casl
INTEREST_WEIGHT = {      # multiplier on the signal_strength contribution
    "high":   1.5,
    "medium": 1.0,
    "low":    0.5,
}
TOP_N_DEFAULT = 10
MIN_ROLE_SKILLS = 5      # Career Pathfinder: ignore roles with fewer required skills


@dataclass
class JDAnalysis:
    jd_id: int
    title: str
    company: str
    have: list[str]
    missing: list[str]
    coverage_pct: float


@dataclass
class DemandEntry:
    skill_title: str
    demand_count: int          # how many JDs require it
    total_jds: int
    signal_strength: float     # demand_count / total_jds
    is_emerging: bool
    is_casl: bool


@dataclass
class RankedGap:
    rank: int
    skill_title: str
    priority_score: float
    why: str                   # plain-language explanation (explainability requirement)
    demand_count: int
    total_jds: int
    is_emerging: bool
    is_casl: bool


@dataclass
class ClosestRole:
    job_role: str
    sector: str
    overlap_count: int
    total_required: int
    matched_skills: list[str]
    gap_skills: list[str]


class GapEngine:
    def __init__(self, data_dir: Path = DATA_DIR):
        role_skills_path = data_dir / "role_skills.csv"
        if not role_skills_path.exists():
            raise FileNotFoundError(
                f"{role_skills_path} not found. Run scripts/01_extract.py first."
            )
        self._role_skills = pd.read_csv(role_skills_path)
        self._skills_meta = pd.read_csv(data_dir / "skills_master.csv").set_index("skill_title")

    def _skill_meta(self, title: str) -> tuple[bool, bool]:
        """Return (is_emerging, is_casl) for a canonical skill title."""
        if title in self._skills_meta.index:
            row = self._skills_meta.loc[title]
            return bool(row["is_emerging"]), bool(row["is_casl"])
        return False, False

    # ------------------------------------------------------------------
    # Per-JD analysis
    # ------------------------------------------------------------------
    def analyze_jd_vs_cv(
        self,
        jd_id: int,
        title: str,
        company: str,
        jd_skills: list[str],
        cv_skills: list[str],
    ) -> JDAnalysis:
        cv_set = set(cv_skills)
        have    = [s for s in jd_skills if s in cv_set]
        missing = [s for s in jd_skills if s not in cv_set]
        coverage = len(have) / len(jd_skills) * 100 if jd_skills else 0.0
        return JDAnalysis(jd_id, title, company, have, missing, round(coverage, 1))

    # ------------------------------------------------------------------
    # Aggregate demand across all saved JDs
    # ------------------------------------------------------------------
    def aggregate_demand(
        self,
        jd_analyses: list[JDAnalysis],
        interest_levels: Optional[dict[int, str]] = None,
    ) -> list[DemandEntry]:
        """
        Count how many JDs demand each missing skill.
        interest_levels: {jd_id: 'low'|'medium'|'high'} — if provided, used by rank_action_list.
        Returns all missing skills with their demand counts.
        """
        total = len(jd_analyses)
        counts: dict[str, int] = {}
        for analysis in jd_analyses:
            for skill in analysis.missing:
                counts[skill] = counts.get(skill, 0) + 1

        entries = []
        for skill, count in counts.items():
            is_em, is_casl = self._skill_meta(skill)
            entries.append(DemandEntry(
                skill_title=skill,
                demand_count=count,
                total_jds=total,
                signal_strength=count / total if total else 0.0,
                is_emerging=is_em,
                is_casl=is_casl,
            ))
        return sorted(entries, key=lambda e: -e.demand_count)

    # ------------------------------------------------------------------
    # Ranked action list — top-N gaps
    # ------------------------------------------------------------------
    def rank_action_list(
        self,
        jd_analyses: list[JDAnalysis],
        interest_levels: Optional[dict[int, str]] = None,
        top_n: int = TOP_N_DEFAULT,
    ) -> list[RankedGap]:
        """
        Priority score = signal_strength × interest_weight + emerging_bonus + casl_bonus

        interest_weight is the average interest multiplier across JDs that demand the skill.
        Every ranking factor is surfaced in the 'why' field — no opaque scores.
        """
        if not jd_analyses:
            return []

        # Build per-skill, per-jd demand map for interest weighting
        skill_jd_map: dict[str, list[int]] = {}
        for analysis in jd_analyses:
            for skill in analysis.missing:
                skill_jd_map.setdefault(skill, []).append(analysis.jd_id)

        total = len(jd_analyses)
        demand_entries = self.aggregate_demand(jd_analyses)

        ranked = []
        for entry in demand_entries:
            # Interest weighting
            if interest_levels:
                jd_ids = skill_jd_map.get(entry.skill_title, [])
                weights = [
                    INTEREST_WEIGHT.get(interest_levels.get(jid, "medium"), 1.0)
                    for jid in jd_ids
                ]
                avg_weight = sum(weights) / len(weights) if weights else 1.0
            else:
                avg_weight = 1.0

            score = entry.signal_strength * avg_weight
            if entry.is_emerging:
                score += EMERGING_BONUS
            if entry.is_casl:
                score += CASL_BONUS

            # Plain-language explanation — every factor stated
            reasons = [
                f"required by {entry.demand_count} of {total} saved job{'s' if total != 1 else ''} "
                f"({entry.signal_strength * 100:.0f}%)"
            ]
            if entry.is_emerging:
                reasons.append("flagged Emerging by SkillsFuture")
            if entry.is_casl:
                reasons.append("flagged CASL priority by SkillsFuture")
            if interest_levels and avg_weight != 1.0:
                level = "high-interest" if avg_weight > 1.0 else "low-interest"
                reasons.append(f"appears in {level} saved jobs")

            ranked.append(RankedGap(
                rank=0,
                skill_title=entry.skill_title,
                priority_score=round(score, 4),
                why="; ".join(reasons),
                demand_count=entry.demand_count,
                total_jds=total,
                is_emerging=entry.is_emerging,
                is_casl=entry.is_casl,
            ))

        ranked.sort(key=lambda g: -g.priority_score)
        for i, gap in enumerate(ranked[:top_n], start=1):
            gap.rank = i

        return ranked[:top_n]

    # ------------------------------------------------------------------
    # Readiness score
    # ------------------------------------------------------------------
    def readiness_score(self, jd_analyses: list[JDAnalysis]) -> dict:
        """Average % of each JD's required skills already evidenced."""
        if not jd_analyses:
            return {"overall_pct": 0.0, "per_jd": []}

        per_jd = [
            {"jd_id": a.jd_id, "title": a.title, "company": a.company,
             "coverage_pct": a.coverage_pct, "have": a.have, "missing": a.missing}
            for a in jd_analyses
        ]
        overall = sum(a.coverage_pct for a in jd_analyses) / len(jd_analyses)
        return {"overall_pct": round(overall, 1), "per_jd": per_jd}

    # ------------------------------------------------------------------
    # Career Pathfinder
    # ------------------------------------------------------------------
    def find_closest_roles(
        self,
        cv_skills: list[str],
        top_n: int = 10,
        min_role_skills: int = MIN_ROLE_SKILLS,
    ) -> list[ClosestRole]:
        """
        Rank SkillsFuture job roles by overlap COUNT (not percentage).
        Percentage is biased toward roles with very few required skills — see ARCHITECTURE §2.3.
        Roles with fewer than min_role_skills required skills are excluded.
        """
        cv_set = set(cv_skills)

        # Build role → required canonical skills map
        role_skills_map = (
            self._role_skills
            .dropna(subset=["canonical_skill_title"])
            .groupby(["job_role", "sector"])["canonical_skill_title"]
            .apply(set)
            .reset_index()
        )

        results = []
        for _, row in role_skills_map.iterrows():
            required: set[str] = row["canonical_skill_title"]
            if len(required) < min_role_skills:
                continue
            matched  = cv_set & required
            gap      = required - cv_set
            if not matched:
                continue
            results.append(ClosestRole(
                job_role=row["job_role"],
                sector=row["sector"],
                overlap_count=len(matched),
                total_required=len(required),
                matched_skills=sorted(matched),
                gap_skills=sorted(gap),
            ))

        results.sort(key=lambda r: -r.overlap_count)
        return results[:top_n]


# Module-level singleton
_engine: Optional[GapEngine] = None


def get_gap_engine() -> GapEngine:
    global _engine
    if _engine is None:
        _engine = GapEngine()
    return _engine
