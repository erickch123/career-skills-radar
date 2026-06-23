"""
ETL: SkillsFuture Excel files → 5 clean CSVs in data/processed/

Run from the project root:
    python3 scripts/01_extract.py

Inputs  (data/raw/):
    jobsandskills-skillsfuture-skills-framework-dataset.xlsx
    jobsandskills-skillsfuture-tsc-to-unique-skills-mapping.xlsx
    jobsandskills-skillsfuture-unique-skills-list.xlsx

Outputs (data/processed/):
    skills_master.csv   — canonical skill list with is_emerging / is_casl flags
    role_skills.csv     — job role → canonical skill mapping (the key join table)
    roles.csv           — job role descriptions
    role_tasks.csv      — critical work functions and key tasks per role
    tsc_key.csv         — TSC/CCS code reference dictionary
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

FRAMEWORK = RAW / "jobsandskills-skillsfuture-skills-framework-dataset.xlsx"
MAPPING   = RAW / "jobsandskills-skillsfuture-tsc-to-unique-skills-mapping.xlsx"
SKILLS    = RAW / "jobsandskills-skillsfuture-unique-skills-list.xlsx"

for f in [FRAMEWORK, MAPPING, SKILLS]:
    if not f.exists():
        print(f"ERROR: {f} not found. Download from SkillsFuture Jobs-Skills Portal.")
        sys.exit(1)


def extract_skills_master() -> pd.DataFrame:
    df = pd.read_excel(SKILLS, sheet_name="Unique Skills List")
    df = df.rename(columns={
        "skill_title":       "skill_title",
        "skill_description": "skill_description",
        "skill_type":        "skill_type",
        "Emerging Skills":   "is_emerging",
        "CASL Skills":       "is_casl",
    })
    df["is_emerging"] = df["is_emerging"].astype(bool)
    df["is_casl"]     = df["is_casl"].astype(bool)
    df = df.dropna(subset=["skill_title"]).drop_duplicates(subset=["skill_title"])
    return df[["skill_title", "skill_description", "skill_type", "is_emerging", "is_casl"]]


def extract_roles() -> pd.DataFrame:
    df = pd.read_excel(FRAMEWORK, sheet_name="Job Role_Description")
    df.columns = ["sector", "track", "job_role", "job_role_description", "performance_expectation"]
    return df.dropna(subset=["job_role"])


def extract_role_tasks() -> pd.DataFrame:
    df = pd.read_excel(FRAMEWORK, sheet_name="Job Role_CWF_KT")
    df.columns = ["sector", "track", "job_role", "critical_work_function", "key_tasks"]
    return df.dropna(subset=["job_role"])


def extract_tsc_key() -> pd.DataFrame:
    df = pd.read_excel(FRAMEWORK, sheet_name="TSC_CCS_Key")
    df.columns = ["tsc_code", "sector", "category", "title", "description", "type", "latest_update_date"]
    return df.dropna(subset=["tsc_code"])


def extract_role_skills(skills_master: pd.DataFrame) -> pd.DataFrame:
    role_tcs = pd.read_excel(FRAMEWORK, sheet_name="Job Role_TCS_CCS")
    role_tcs.columns = ["sector", "track", "job_role", "tsc_ccs_title", "tsc_ccs_type", "proficiency_level", "tsc_ccs_code"]

    mapping = pd.read_excel(MAPPING, sheet_name="data")[[
        "skills_framework_skill_code",
        "Unique skill_updated_skill_title",
    ]].rename(columns={"Unique skill_updated_skill_title": "canonical_skill_title"})

    # Join 1: role_tcs → mapping (100% match confirmed)
    df = role_tcs.merge(mapping, left_on="tsc_ccs_code", right_on="skills_framework_skill_code", how="left")

    # Join 2: → skills_master for is_emerging / is_casl flags (99.7% match)
    df = df.merge(
        skills_master[["skill_title", "is_emerging", "is_casl"]],
        left_on="canonical_skill_title",
        right_on="skill_title",
        how="left",
    )

    unmatched = df["canonical_skill_title"].isna().sum()
    if unmatched:
        print(f"  WARNING: {unmatched} rows have no canonical skill title (kept with null)")

    return df[[
        "sector", "track", "job_role",
        "tsc_ccs_code", "tsc_ccs_title", "tsc_ccs_type", "proficiency_level",
        "canonical_skill_title", "is_emerging", "is_casl",
    ]]


def main():
    print("Extracting SkillsFuture data...")

    print("  skills_master.csv")
    skills_master = extract_skills_master()
    skills_master.to_csv(OUT / "skills_master.csv", index=False)
    print(f"    {len(skills_master)} canonical skills ({skills_master['is_emerging'].sum()} emerging, {skills_master['is_casl'].sum()} CASL)")

    print("  roles.csv")
    roles = extract_roles()
    roles.to_csv(OUT / "roles.csv", index=False)
    print(f"    {len(roles)} job roles across {roles['sector'].nunique()} sectors")

    print("  role_tasks.csv")
    role_tasks = extract_role_tasks()
    role_tasks.to_csv(OUT / "role_tasks.csv", index=False)
    print(f"    {len(role_tasks)} task rows")

    print("  tsc_key.csv")
    tsc_key = extract_tsc_key()
    tsc_key.to_csv(OUT / "tsc_key.csv", index=False)
    print(f"    {len(tsc_key)} TSC/CCS entries")

    print("  role_skills.csv")
    role_skills = extract_role_skills(skills_master)
    role_skills.to_csv(OUT / "role_skills.csv", index=False)
    print(f"    {len(role_skills)} role-skill rows across {role_skills['job_role'].nunique()} roles")

    print("\nDone. CSVs written to data/processed/")


if __name__ == "__main__":
    main()
