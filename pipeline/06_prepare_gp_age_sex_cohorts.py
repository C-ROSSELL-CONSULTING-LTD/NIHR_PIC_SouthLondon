"""
Script 06: Prepare GP age/sex cohort table for PIC Finder filtering.

Source:
  - data/raw/gp-reg-pat-prac-quin-age.csv

Output:
  - data/processed/gp_age_sex_cohorts_long.csv
  - data/processed/gp_age_sex_cohorts_unmatched_codes.csv
"""

import os
import sys
import logging
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


RAW_FILE = "gp-reg-pat-prac-quin-age.csv"
OUTPUT_FILE = "gp_age_sex_cohorts_long.csv"
UNMATCHED_FILE = "gp_age_sex_cohorts_unmatched_codes.csv"


def prepare_gp_age_sex_cohorts():
    logger.info("=" * 70)
    logger.info("STEP 06: Prepare GP Age/Sex Cohort Table")
    logger.info("=" * 70)

    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    processed_dir = project_dir / "data" / "processed"
    raw_path = project_dir / "data" / "raw" / RAW_FILE
    gp_ref_path = project_dir / "data" / "processed" / "gp_practices_geocoded.csv"

    if not raw_path.exists():
        logger.error(f"Raw file not found: {raw_path}")
        return None

    logger.info(f"[LOAD] Reading {raw_path.name}")
    raw_df = pd.read_csv(raw_path, low_memory=False)
    logger.info(f"[OK] Rows loaded: {len(raw_df):,}")

    required_cols = ["ORG_TYPE", "ORG_CODE", "SEX", "AGE_GROUP_5", "NUMBER_OF_PATIENTS"]
    missing_cols = [c for c in required_cols if c not in raw_df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        return None

    # Keep GP rows only and normalize key fields.
    gp_rows = raw_df[raw_df["ORG_TYPE"].astype(str).str.strip().str.upper() == "GP"].copy()
    logger.info(f"[FILTER] ORG_TYPE == GP rows: {len(gp_rows):,}")

    gp_rows["practice_code_gp"] = gp_rows["ORG_CODE"].astype(str).str.strip().str.upper()
    gp_rows["SEX"] = gp_rows["SEX"].astype(str).str.strip().str.upper()
    gp_rows["AGE_GROUP_5"] = gp_rows["AGE_GROUP_5"].astype(str).str.strip().str.upper()
    gp_rows["NUMBER_OF_PATIENTS"] = pd.to_numeric(gp_rows["NUMBER_OF_PATIENTS"], errors="coerce").fillna(0)

    # Use granular rows only to avoid duplicate counting from ALL aggregates.
    cohorts = gp_rows[
        gp_rows["SEX"].isin(["MALE", "FEMALE"]) &
        (gp_rows["AGE_GROUP_5"] != "ALL")
    ][["practice_code_gp", "SEX", "AGE_GROUP_5", "NUMBER_OF_PATIENTS"]].copy()

    cohorts = cohorts.rename(columns={"NUMBER_OF_PATIENTS": "cohort_population"})

    # Consolidate any duplicates within a practice-sex-age tuple.
    cohorts = (
        cohorts.groupby(["practice_code_gp", "SEX", "AGE_GROUP_5"], as_index=False)["cohort_population"]
        .sum()
    )

    logger.info(f"[OK] Cohort rows (granular): {len(cohorts):,}")
    logger.info(f"[OK] Distinct practices in cohorts: {cohorts['practice_code_gp'].nunique():,}")

    # Join quality checks against canonical geocoded GP table.
    if gp_ref_path.exists():
        gp_ref = pd.read_csv(gp_ref_path, usecols=["practice_code_gp"]) 
        gp_ref["practice_code_gp"] = gp_ref["practice_code_gp"].astype(str).str.strip().str.upper()
        gp_ref = gp_ref.drop_duplicates(subset=["practice_code_gp"])

        merged = cohorts.merge(gp_ref, on="practice_code_gp", how="left", indicator=True)
        matched = (merged["_merge"] == "both").sum()
        coverage = matched / len(merged) * 100 if len(merged) else 0
        logger.info(f"[QA] Row-level join coverage to gp_practices_geocoded: {matched:,}/{len(merged):,} ({coverage:.1f}%)")

        unmatched = (
            merged[merged["_merge"] != "both"][["practice_code_gp"]]
            .drop_duplicates()
            .sort_values("practice_code_gp")
        )

        # Keep only practices that exist in this project's GP reference list.
        before_rows = len(cohorts)
        cohorts = cohorts.merge(gp_ref, on="practice_code_gp", how="inner")
        logger.info(f"[FILTER] Kept project GP cohort rows: {len(cohorts):,}/{before_rows:,}")
        logger.info(f"[FILTER] Distinct project practices in cohorts: {cohorts['practice_code_gp'].nunique():,}")
    else:
        logger.warning(f"[QA] GP reference file missing: {gp_ref_path}")
        unmatched = pd.DataFrame(columns=["practice_code_gp"])

    os.makedirs(processed_dir, exist_ok=True)

    output_path = processed_dir / OUTPUT_FILE
    cohorts.to_csv(output_path, index=False)
    logger.info(f"[SAVE] {OUTPUT_FILE} ({len(cohorts):,} rows)")

    unmatched_path = processed_dir / UNMATCHED_FILE
    unmatched.to_csv(unmatched_path, index=False)
    logger.info(f"[SAVE] {UNMATCHED_FILE} ({len(unmatched):,} rows)")

    # Optional internal consistency check using raw ALL categories.
    all_rows = gp_rows[(gp_rows["SEX"] == "ALL") & (gp_rows["AGE_GROUP_5"] == "ALL")].copy()
    if not all_rows.empty:
        total_by_practice = cohorts.groupby("practice_code_gp", as_index=False)["cohort_population"].sum()
        all_rows = all_rows[["practice_code_gp", "NUMBER_OF_PATIENTS"]].rename(columns={"NUMBER_OF_PATIENTS": "all_population"})
        all_rows = all_rows[all_rows["practice_code_gp"].isin(total_by_practice["practice_code_gp"])].copy()
        check = all_rows.merge(total_by_practice, on="practice_code_gp", how="left")
        check["cohort_population"] = check["cohort_population"].fillna(0)
        check["abs_diff"] = (check["all_population"] - check["cohort_population"]).abs()
        mismatch_count = (check["abs_diff"] > 1).sum()
        logger.info(f"[QA] Practice total mismatch count (>1 patient diff): {mismatch_count:,}/{len(check):,}")

    logger.info("=" * 70)
    logger.info("GP age/sex cohort preparation complete")
    logger.info("=" * 70)

    return cohorts


if __name__ == "__main__":
    prepare_gp_age_sex_cohorts()
