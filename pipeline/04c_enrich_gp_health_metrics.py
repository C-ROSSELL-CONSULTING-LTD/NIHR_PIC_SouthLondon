"""
Script 04c: Enrich GP practices with QOF prevalence health metrics (Fingertips).

Joins Fingertips GP geography (area type 7) onto local GP practice data using
ODS practice code, for a registry of QOF prevalence indicators (see
config.HEALTH_METRIC_REGISTRY).

Outputs:
  - data/processed/gp_practices_geocoded.csv (updated with one column pair per metric)
  - data/processed/health_metrics_match_audit.csv (long-format per-practice, per-metric audit)
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd
import fingertips_py as ftp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR, HEALTH_METRIC_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE = "Fingertips API"

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

GP_FILE = Path(PROCESSED_DATA_DIR) / "gp_practices_geocoded.csv"
AUDIT_FILE = Path(PROCESSED_DATA_DIR) / "health_metrics_match_audit.csv"


def _normalize_code(series: pd.Series) -> pd.Series:
    """Standardize ODS-like codes for robust joins."""
    return series.astype(str).str.strip().str.upper()


def fetch_metric_for_gp(indicator_id: int, key: str) -> pd.DataFrame:
    """Fetch a single GP-level QOF prevalence metric from Fingertips.

    Rows are restricted to the unstratified national breakdown (no deprivation-
    decile category rows) and the latest available time period per practice.
    """
    raw = ftp.get_data_by_indicator_ids(indicator_ids=indicator_id, area_type_id=7)
    if raw.empty:
        raise RuntimeError(f"Fingertips returned zero rows for indicator {indicator_id} ({key}).")

    required_cols = ["Area Code", "Value", "Time period", "Category Type"]
    missing_required = [c for c in required_cols if c not in raw.columns]
    if missing_required:
        raise RuntimeError(f"Indicator {indicator_id} ({key}) missing expected columns: {missing_required}")

    # Keep only the unstratified row per practice/period (exclude deprivation-decile breakdowns).
    unstratified = raw[raw["Category Type"].isna()].copy()
    unstratified = unstratified[unstratified["Value"].notna()].copy()
    if unstratified.empty:
        raise RuntimeError(f"No unstratified rows with values for indicator {indicator_id} ({key}).")

    unstratified["Area Code"] = _normalize_code(unstratified["Area Code"])

    if "Time period Sortable" in unstratified.columns and unstratified["Time period Sortable"].notna().any():
        unstratified = unstratified.sort_values(["Area Code", "Time period Sortable"]).groupby("Area Code", as_index=False).tail(1)
    else:
        unstratified = unstratified.sort_values(["Area Code", "Time period"]).groupby("Area Code", as_index=False).tail(1)

    out = unstratified[["Area Code", "Value", "Time period"]].rename(
        columns={
            "Area Code": "practice_code_gp",
            "Value": f"{key}_value",
            "Time period": f"{key}_time_period",
        }
    )
    out["practice_code_gp"] = _normalize_code(out["practice_code_gp"])
    out[f"{key}_value"] = pd.to_numeric(out[f"{key}_value"], errors="coerce")

    return out.drop_duplicates(subset=["practice_code_gp"], keep="last")


def enrich_gp_with_health_metrics() -> pd.DataFrame:
    """Main ETL function to enrich GP data with all registered QOF prevalence metrics."""
    logger.info("=" * 70)
    logger.info("STEP 04C: Enrich GP Data with QOF Prevalence Metrics (Fingertips)")
    logger.info("=" * 70)

    gp_path = PROJECT_DIR / GP_FILE
    audit_path = PROJECT_DIR / AUDIT_FILE

    if not gp_path.exists():
        raise FileNotFoundError(f"GP base file not found: {gp_path}")

    gp = pd.read_csv(gp_path)
    if "practice_code_gp" not in gp.columns:
        raise RuntimeError("Column 'practice_code_gp' not found in gp_practices_geocoded.csv")
    gp["practice_code_gp"] = _normalize_code(gp["practice_code_gp"])

    # Idempotency: drop any pre-existing columns for these metrics before re-joining.
    existing_metric_cols = []
    for metric in HEALTH_METRIC_REGISTRY:
        existing_metric_cols += [f"{metric['key']}_value", f"{metric['key']}_time_period"]
    drop_cols = [c for c in existing_metric_cols if c in gp.columns]
    if drop_cols:
        gp = gp.drop(columns=drop_cols)

    enriched = gp.copy()
    audit_frames = []

    for metric in HEALTH_METRIC_REGISTRY:
        key = metric["key"]
        indicator_id = metric["indicator_id"]
        label = metric["label"]
        try:
            metric_df = fetch_metric_for_gp(indicator_id, key)
            enriched = enriched.merge(metric_df, on="practice_code_gp", how="left")

            matched = int(enriched[f"{key}_value"].notna().sum())
            total = len(enriched)
            logger.info("[OK] %s (id=%s): matched %s/%s (%.1f%%)", label, indicator_id, matched, total, 100 * matched / total)

            audit = enriched[["practice_code_gp", f"{key}_value"]].copy()
            audit["metric_key"] = key
            audit["metric_label"] = label
            audit["indicator_id"] = indicator_id
            audit["match_status"] = audit[f"{key}_value"].apply(lambda v: "matched" if pd.notna(v) else "unmatched")
            audit = audit.rename(columns={f"{key}_value": "value"})
            audit_frames.append(audit[["practice_code_gp", "metric_key", "metric_label", "indicator_id", "value", "match_status"]])

        except Exception as exc:
            logger.warning("[SKIP] %s (id=%s): %s", label, indicator_id, exc)
            enriched[f"{key}_value"] = pd.NA
            enriched[f"{key}_time_period"] = pd.NA

    os.makedirs(gp_path.parent, exist_ok=True)
    enriched.to_csv(gp_path, index=False)
    logger.info("[SAVE] Updated GP file: %s", gp_path)

    if audit_frames:
        audit_all = pd.concat(audit_frames, ignore_index=True)
        audit_all.to_csv(audit_path, index=False)
        logger.info("[SAVE] Health metrics audit file: %s", audit_path)

    return enriched


if __name__ == "__main__":
    try:
        df = enrich_gp_with_health_metrics()
        logger.info("[DONE] Enriched rows: %s", len(df))
    except Exception as exc:
        logger.error("[ERROR] %s", exc)
        sys.exit(1)
