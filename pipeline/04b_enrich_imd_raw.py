"""
Script 04b: Enrich GP practices with raw Fingertips IMD score.

Joins Fingertips GP geography (area type 7) onto local GP practice data using
ODS practice code, and persists a raw deprivation score field.

Outputs:
  - data/processed/gp_practices_geocoded.csv (updated with IMD columns)
  - data/processed/imd_match_audit.csv (per-practice match status)
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd
import fingertips_py as ftp

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Live GP-level deprivation score indicator discovered from Fingertips metadata
IMD_INDICATOR_ID = 94240
IMD_SOURCE = "Fingertips API"
IMD_TIME_PERIOD = "2025"

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

GP_FILE = Path(PROCESSED_DATA_DIR) / "gp_practices_geocoded.csv"
AUDIT_FILE = Path(PROCESSED_DATA_DIR) / "imd_match_audit.csv"


def _normalize_code(series: pd.Series) -> pd.Series:
    """Standardize ODS-like codes for robust joins."""
    return series.astype(str).str.strip().str.upper()


def fetch_imd_raw_for_gp() -> pd.DataFrame:
    """Fetch GP-level raw IMD score data from Fingertips."""
    logger.info("[API] Fetching Fingertips indicator %s for GP area type 7...", IMD_INDICATOR_ID)

    raw = ftp.get_data_by_indicator_ids(indicator_ids=IMD_INDICATOR_ID, area_type_id=7)
    if raw.empty:
        raise RuntimeError(
            "Fingertips returned zero rows for indicator 94240 at area type 7. "
            "Check API availability or indicator configuration."
        )

    required_cols = ["Area Code", "Value", "Time period", "Indicator Name"]
    missing_required = [c for c in required_cols if c not in raw.columns]
    if missing_required:
        raise RuntimeError(f"Fingertips response missing expected columns: {missing_required}")

    # Keep 2025 rows only, then rows with a usable value; normalize area code.
    imd = raw[required_cols].copy()
    imd = imd[imd["Time period"].astype(str).str.strip() == IMD_TIME_PERIOD].copy()
    if imd.empty:
        raise RuntimeError(
            "No 2025 rows returned for indicator 94240 at GP area type 7. "
            "Check API data availability."
        )
    imd = imd[imd["Value"].notna()].copy()
    imd["Area Code"] = _normalize_code(imd["Area Code"])

    # When multiple rows exist per area, keep the latest record.
    if "Time period Sortable" in raw.columns and raw["Time period Sortable"].notna().any():
        sortable = raw[["Area Code", "Time period Sortable"]].copy()
        sortable["Area Code"] = _normalize_code(sortable["Area Code"])
        imd = imd.merge(sortable, on="Area Code", how="left")
        imd = imd.sort_values(["Area Code", "Time period Sortable"]).groupby("Area Code", as_index=False).tail(1)
    else:
        imd = imd.sort_values(["Area Code", "Time period"]).groupby("Area Code", as_index=False).tail(1)

    imd = imd.rename(
        columns={
            "Area Code": "practice_code_gp",
            "Value": "imd_score_raw",
            "Time period": "imd_time_period",
            "Indicator Name": "imd_indicator_name",
        }
    )

    imd["practice_code_gp"] = _normalize_code(imd["practice_code_gp"])
    imd["imd_score_raw"] = pd.to_numeric(imd["imd_score_raw"], errors="coerce")
    imd["imd_indicator_id"] = IMD_INDICATOR_ID
    imd["imd_source"] = IMD_SOURCE

    keep_cols = [
        "practice_code_gp",
        "imd_score_raw",
        "imd_time_period",
        "imd_indicator_name",
        "imd_indicator_id",
        "imd_source",
    ]

    imd = imd[keep_cols].drop_duplicates(subset=["practice_code_gp"], keep="last")

    logger.info("[API] Retrieved %s GP IMD rows with non-null values", len(imd))
    return imd


def enrich_gp_with_imd_raw() -> pd.DataFrame:
    """Main ETL function to enrich GP data with raw IMD score."""
    logger.info("=" * 70)
    logger.info("STEP 04B: Enrich GP Data with Raw IMD Score (Fingertips)")
    logger.info("=" * 70)

    gp_path = PROJECT_DIR / GP_FILE
    audit_path = PROJECT_DIR / AUDIT_FILE

    if not gp_path.exists():
        raise FileNotFoundError(f"GP base file not found: {gp_path}")

    gp = pd.read_csv(gp_path)
    if "practice_code_gp" not in gp.columns:
        raise RuntimeError("Column 'practice_code_gp' not found in gp_practices_geocoded.csv")

    gp["practice_code_gp"] = _normalize_code(gp["practice_code_gp"])

    imd = fetch_imd_raw_for_gp()

    # Idempotency: remove existing IMD columns before re-joining.
    imd_cols = [
        "imd_score_raw",
        "imd_time_period",
        "imd_indicator_name",
        "imd_indicator_id",
        "imd_source",
        "imd_local_percentile",
        "imd_local_quintile",
        "imd_local_rank_note",
    ]
    drop_cols = [c for c in imd_cols if c in gp.columns]
    if drop_cols:
        gp = gp.drop(columns=drop_cols)

    enriched = gp.merge(imd, on="practice_code_gp", how="left")

    # Local interpretation fields are computed relative to the currently matched GP set.
    score = pd.to_numeric(enriched["imd_score_raw"], errors="coerce")
    matched_mask = score.notna()
    if matched_mask.any():
        pct = score[matched_mask].rank(method="average", pct=True) * 100
        enriched.loc[matched_mask, "imd_local_percentile"] = pct.round(1)
        quintile = pd.qcut(pct, q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
        enriched.loc[matched_mask, "imd_local_quintile"] = pd.to_numeric(quintile, errors="coerce").astype("Int64")
    else:
        enriched["imd_local_percentile"] = pd.NA
        enriched["imd_local_quintile"] = pd.NA

    enriched["imd_local_rank_note"] = (
        "Relative within current matched GP dataset (not national IMD deciles)"
    )

    enriched["imd_match_status"] = enriched["imd_score_raw"].apply(
        lambda v: "matched" if pd.notna(v) else "unmatched"
    )

    matched = int((enriched["imd_match_status"] == "matched").sum())
    total = len(enriched)
    match_rate = 100 * matched / total if total else 0

    os.makedirs(gp_path.parent, exist_ok=True)
    enriched.drop(columns=["imd_match_status"]).to_csv(gp_path, index=False)

    audit = enriched[[
        "practice_code_gp",
        "practice_name",
        "icb_code",
        "imd_score_raw",
        "imd_time_period",
        "imd_indicator_id",
        "imd_match_status",
    ]].copy()
    audit.to_csv(audit_path, index=False)

    logger.info("[SAVE] Updated GP file: %s", gp_path)
    logger.info("[SAVE] Match audit file: %s", audit_path)
    logger.info("[QA] Match coverage: %s/%s (%.2f%%)", matched, total, match_rate)

    if matched < total:
        unmatched_examples = audit[audit["imd_match_status"] == "unmatched"]["practice_code_gp"].head(10).tolist()
        logger.warning("[QA] Unmatched practice examples: %s", unmatched_examples)

    return enriched


if __name__ == "__main__":
    try:
        df = enrich_gp_with_imd_raw()
        logger.info("[DONE] Enriched rows: %s", len(df))
    except Exception as exc:
        logger.error("[ERROR] %s", exc)
        sys.exit(1)
