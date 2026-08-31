"""Simple CSV matrix query for PIC Finder coverage checks.

This script does not emulate the Streamlit app. It reads the processed CSVs and
counts non-null travel-time combinations across destinations, sex, age ticks,
IMD bins, and GP size bins.
"""

from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import HEALTH_METRIC_REGISTRY


AGE_TICK_MIN = 0
AGE_TICK_MAX = 100
AGE_TICK_STEP = 5
IMD_TICK_STEP = 10
GP_SIZE_TICK_STEP = 1000


def age_band_sort_key(value: str) -> tuple[int, str]:
    text = str(value).strip().upper()
    if text.endswith("+"):
        try:
            return (int(text[:-1]), text)
        except ValueError:
            return (10_000, text)
    if "-" in text:
        try:
            return (int(text.split("-")[0]), text)
        except ValueError:
            return (10_000, text)
    return (10_000, text)


def age_band_range_to_values(age_options: list[str], age_start: int, age_end: int) -> list[str]:
    selected = []
    for band in age_options:
        band_text = str(band).strip().upper()
        if band_text.endswith("+"):
            lower = int(band_text[:-1])
            upper = 10_000
        elif "-" in band_text:
            lower_text, upper_text = band_text.split("-")
            lower = int(lower_text)
            upper = int(upper_text)
        else:
            continue
        if lower < age_end and upper >= age_start:
            selected.append(band_text)
    return selected


def build_bins(start: int, stop: int, step: int) -> list[tuple[int, int]]:
    return [(value, min(value + step, stop)) for value in range(start, stop, step)]


def disease_labels() -> list[str]:
    return ["None", "Dementia", "Diabetes"] + [metric["label"] for metric in HEALTH_METRIC_REGISTRY]


def main() -> int:
    parser = argparse.ArgumentParser(description="Query non-null travel-time combinations from CSV files.")
    parser.add_argument("--sex", choices=["FEMALE", "MALE", "Both"], default="Both")
    parser.add_argument("--transport", choices=["Transit", "Walking", "Both"], default="Transit")
    parser.add_argument("--disease", default="Both", help="Disease label or Both")
    parser.add_argument("--destinations", nargs="*", default=None)
    parser.add_argument("--sweep-imd", action="store_true", help="Sweep IMD bins")
    parser.add_argument("--sweep-gp-size", action="store_true", help="Sweep GP size bins")
    parser.add_argument("--imd-min", type=int, default=None)
    parser.add_argument("--imd-max", type=int, default=None)
    parser.add_argument("--gp-size-min", type=int, default=None)
    parser.add_argument("--gp-size-max", type=int, default=None)
    args = parser.parse_args()

    gp_df = pd.read_csv("data/processed/gp_practices_geocoded.csv")
    cohort_df = pd.read_csv("data/processed/gp_age_sex_cohorts_long.csv")
    travel_times_df = pd.read_csv("data/processed/travel_times_optimized.csv")

    if "practice_code_gp" not in gp_df.columns and "PRACTICE_CODE" in gp_df.columns:
        gp_df = gp_df.rename(columns={"PRACTICE_CODE": "practice_code_gp"})

    destinations = args.destinations or sorted(travel_times_df["destination_name"].dropna().astype(str).unique().tolist())
    sexes = [args.sex] if args.sex != "Both" else ["FEMALE", "MALE"]
    transport_modes = [args.transport] if args.transport != "Both" else ["Transit", "Walking"]
    diseases = [args.disease] if args.disease != "Both" else disease_labels()
    age_options = sorted(cohort_df["AGE_GROUP_5"].dropna().astype(str).unique().tolist(), key=age_band_sort_key)
    age_ranges = build_bins(AGE_TICK_MIN, AGE_TICK_MAX, AGE_TICK_STEP)
    imd_ranges = build_bins(0, 100, IMD_TICK_STEP) if args.sweep_imd else [(args.imd_min, args.imd_max)] if args.imd_min is not None and args.imd_max is not None else [(None, None)]
    gp_size_ranges = build_bins(0, 100000, GP_SIZE_TICK_STEP) if args.sweep_gp_size else [(args.gp_size_min, args.gp_size_max)] if args.gp_size_min is not None and args.gp_size_max is not None else [(None, None)]

    rows = []
    for destination, disease, sex, (age_start, age_end), transport, (imd_min, imd_max), (gp_size_min, gp_size_max) in product(destinations, diseases, sexes, age_ranges, transport_modes, imd_ranges, gp_size_ranges):
        results = gp_df.copy()

        if "imd_score_raw" in results.columns and imd_min is not None and imd_max is not None:
            imd_series = pd.to_numeric(results["imd_score_raw"], errors="coerce")
            results = results[(imd_series >= imd_min) & (imd_series <= imd_max)]

        if "TOTAL_POPULATION" in results.columns and gp_size_min is not None and gp_size_max is not None:
            gp_size_series = pd.to_numeric(results["TOTAL_POPULATION"], errors="coerce")
            results = results[(gp_size_series >= gp_size_min) & (gp_size_series <= gp_size_max)]

        if disease != "None":
            metric_key = disease.lower().replace(" ", "_")
            metric = next((metric for metric in HEALTH_METRIC_REGISTRY if metric["key"] == metric_key), None)
            if metric is not None:
                col_name = f"{metric['key']}_value"
                if col_name in results.columns:
                    results = results[results[col_name].notna()]

        cohort_filtered = cohort_df[
            cohort_df["SEX"].isin([sex]) & cohort_df["AGE_GROUP_5"].isin(age_band_range_to_values(age_options, age_start, age_end))
        ].copy()
        cohort_by_practice = (
            cohort_filtered.groupby("practice_code_gp", as_index=False)["cohort_population"]
            .sum()
            .rename(columns={"cohort_population": "selected_cohort_population"})
        )
        results = results.merge(cohort_by_practice, on="practice_code_gp", how="inner")

        destination_times = travel_times_df[travel_times_df["destination_name"] == destination].copy()
        merged = destination_times.merge(results[["practice_code_gp"]], left_on="practice_code", right_on="practice_code_gp", how="inner")

        travel_col = "travel_time_transit_minutes" if transport == "Transit" else "travel_time_walking_minutes"
        travel_times = pd.to_numeric(merged[travel_col], errors="coerce")

        rows.append(
            {
                "destination": destination,
                "disease": disease,
                "sex": sex,
                "age_start": age_start,
                "age_end": age_end,
                "transport": transport,
                "imd_min": imd_min,
                "imd_max": imd_max,
                "gp_size_min": gp_size_min,
                "gp_size_max": gp_size_max,
                "matched_practices": int(merged["practice_code_gp"].nunique()),
                "non_null_travel_times": int(travel_times.notna().sum()),
            }
        )

    output = pd.DataFrame(rows)
    summary = (
        output.groupby(["destination", "disease"], as_index=False)["non_null_travel_times"]
        .sum()
        .sort_values("non_null_travel_times", ascending=False)
    )
    print(summary.to_csv(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())