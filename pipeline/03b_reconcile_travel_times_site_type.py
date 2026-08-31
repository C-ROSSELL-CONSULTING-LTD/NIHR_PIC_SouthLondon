"""
Reconcile travel_times_optimized.csv row shapes and infer site_type safely.

Rules implemented:
1. Canonical lookup from reference tables:
   - hospital_sites_geocoded.csv names -> Hospital
   - universities_geocoded.csv names -> University
2. For 9-field legacy rows:
   - match site name to lookup -> Hospital/University
   - no match -> Unknown
3. For 12-field rows:
   - keep provided site_type if present
   - if blank -> lookup fallback (or Unknown)

Matching strategy:
- Normalize names with lowercase, trim, collapsed spaces.
- Also remove punctuation variants (' . -) for resilient exact matching.
- Exact match only after normalization; no fuzzy matching.
"""

import csv
import os
import sys
import re
import shutil
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR

TRAVEL_FILE = os.path.join(PROCESSED_DATA_DIR, "travel_times_optimized.csv")
HOSPITAL_FILE = os.path.join(PROCESSED_DATA_DIR, "hospital_sites_geocoded.csv")
UNIVERSITY_FILE = os.path.join(PROCESSED_DATA_DIR, "universities_geocoded.csv")
REPORT_FILE = os.path.join(PROCESSED_DATA_DIR, "travel_times_site_type_reconciliation_report.txt")

TARGET_HEADER = [
    "practice_code",
    "practice_name",
    "destination_name",
    "destination_type",
    "destination_group",
    "hospital_name",
    "hospital_trust",
    "travel_time_car_minutes",
    "travel_time_transit_minutes",
    "closest_travel_mode",
    "closest_travel_minutes",
]


def normalize_name(value: str) -> str:
    if value is None:
        return ""
    v = str(value).strip().lower()
    v = re.sub(r"\s+", " ", v)
    return v


def normalize_name_no_punct(value: str) -> str:
    v = normalize_name(value)
    v = re.sub(r"['.\-]", "", v)
    v = re.sub(r"\s+", " ", v).strip()
    return v


def load_lookup_names(csv_path: str, name_col: str):
    exact = set()
    nopunct = set()

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nm = row.get(name_col, "")
            n1 = normalize_name(nm)
            n2 = normalize_name_no_punct(nm)
            if n1:
                exact.add(n1)
            if n2:
                nopunct.add(n2)

    return exact, nopunct


def infer_site_type(name: str, hosp_exact, hosp_nopunct, uni_exact, uni_nopunct):
    n1 = normalize_name(name)
    n2 = normalize_name_no_punct(name)

    if n1 in hosp_exact or n2 in hosp_nopunct:
        return "Hospital", "matched"
    if n1 in uni_exact or n2 in uni_nopunct:
        return "University", "matched"
    return "Unknown", "unknown"


def backup_file(path: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{ts}"
    shutil.copy2(path, backup_path)
    return backup_path


def reconcile():
    if not os.path.exists(TRAVEL_FILE):
        raise FileNotFoundError(f"Missing file: {TRAVEL_FILE}")
    if not os.path.exists(HOSPITAL_FILE):
        raise FileNotFoundError(f"Missing file: {HOSPITAL_FILE}")
    if not os.path.exists(UNIVERSITY_FILE):
        raise FileNotFoundError(f"Missing file: {UNIVERSITY_FILE}")

    hosp_exact, hosp_nopunct = load_lookup_names(HOSPITAL_FILE, "hospital_name")
    uni_exact, uni_nopunct = load_lookup_names(UNIVERSITY_FILE, "university_name")

    backup_path = backup_file(TRAVEL_FILE)

    new_rows = []
    row_len_counts = Counter()
    source_counts = Counter()
    type_counts = Counter()
    unknown_names = Counter()

    with open(TRAVEL_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])

        for row in reader:
            row_len_counts[len(row)] += 1

            if len(row) == 9:
                # legacy shape: practice_code,practice_name,destination_name,destination_type,destination_group,
                # hospital_name,hospital_trust,closest_travel_mode,closest_travel_minutes
                practice_code, practice_name, site_name = row[0], row[1], row[2]
                inferred_type, status = infer_site_type(
                    site_name, hosp_exact, hosp_nopunct, uni_exact, uni_nopunct
                )

                destination_group = row[4]
                hospital_name = site_name if inferred_type == "Hospital" else ""
                hospital_trust = row[6] if inferred_type == "Hospital" else ""
                car_minutes = ""
                transit_minutes = ""
                closest_mode = row[7]
                closest_minutes = row[8]

                new_rows.append([
                    practice_code,
                    practice_name,
                    site_name,
                    inferred_type,
                    destination_group,
                    hospital_name,
                    hospital_trust,
                    car_minutes,
                    transit_minutes,
                    closest_mode,
                    closest_minutes,
                ])

                source_counts["9_field_rows"] += 1
                source_counts[f"9_field_{status}"] += 1
                type_counts[inferred_type] += 1
                if inferred_type == "Unknown":
                    unknown_names[site_name] += 1

            elif len(row) == 12:
                # malformed shape seen in file:
                # [0 code,1 practice,2 site,3 type,4 trust,5 site_dup,6 trust_dup,7 blank,8 maybe_car,9 maybe_transit,10 mode,11 closest]
                practice_code, practice_name, site_name = row[0], row[1], row[2]
                provided_type = (row[3] or "").strip()

                if provided_type:
                    site_type = provided_type
                    source_counts["12_field_kept_type"] += 1
                else:
                    site_type, status = infer_site_type(
                        site_name, hosp_exact, hosp_nopunct, uni_exact, uni_nopunct
                    )
                    source_counts["12_field_fallback_lookup"] += 1
                    source_counts[f"12_field_fallback_{status}"] += 1
                    if site_type == "Unknown":
                        unknown_names[site_name] += 1

                destination_group = row[4]
                hospital_name = site_name if site_type == "Hospital" else ""
                hospital_trust = row[6] if site_type == "Hospital" else ""
                car_minutes = row[8]
                transit_minutes = row[9]
                closest_mode = row[10]
                closest_minutes = row[11]

                new_rows.append([
                    practice_code,
                    practice_name,
                    site_name,
                    site_type,
                    destination_group,
                    hospital_name,
                    hospital_trust,
                    car_minutes,
                    transit_minutes,
                    closest_mode,
                    closest_minutes,
                ])

                source_counts["12_field_rows"] += 1
                type_counts[site_type] += 1

            elif len(row) == 11:
                # already target shape; keep as-is except blank type fallback.
                row_copy = row[:]
                if not (row_copy[3] or "").strip():
                    inferred_type, status = infer_site_type(
                        row_copy[2], hosp_exact, hosp_nopunct, uni_exact, uni_nopunct
                    )
                    row_copy[3] = inferred_type
                    source_counts["11_field_blank_type_fallback"] += 1
                    source_counts[f"11_field_fallback_{status}"] += 1
                    if inferred_type == "Unknown":
                        unknown_names[row_copy[2]] += 1
                else:
                    source_counts["11_field_kept"] += 1

                type_counts[row_copy[3] if row_copy[3] else "Unknown"] += 1
                new_rows.append(row_copy)
                source_counts["11_field_rows"] += 1

            else:
                source_counts["skipped_unexpected_shape"] += 1

    with open(TRAVEL_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TARGET_HEADER)
        writer.writerows(new_rows)

    lines = []
    lines.append("Travel Times Site Type Reconciliation Report")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"Input file: {TRAVEL_FILE}")
    lines.append(f"Backup file: {backup_path}")
    lines.append("")
    lines.append("Row length counts before rewrite:")
    for k in sorted(row_len_counts):
        lines.append(f"  {k}: {row_len_counts[k]}")
    lines.append("")
    lines.append("Processing counts:")
    for k, v in source_counts.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Final counts by site_type:")
    for k, v in type_counts.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Unknown site names (top 25):")
    if unknown_names:
        for name, cnt in unknown_names.most_common(25):
            lines.append(f"  {name} ({cnt})")
    else:
        lines.append("  none")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("Reconciliation complete")
    print(f"Backup: {backup_path}")
    print(f"Output: {TRAVEL_FILE}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    reconcile()
