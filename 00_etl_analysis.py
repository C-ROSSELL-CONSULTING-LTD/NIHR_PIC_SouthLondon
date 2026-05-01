"""
ETL Data Exploration & Cleaning - Standalone Script
Runs the analysis without Jupyter dependencies

Sources (March 2026):
  - pcdem-prac-ass-plans-feb-2026.csv: Practice-level dementia metrics (Feb 2026)
  - gp-reg-pat-prac-map-03-2026.csv: GP registry with ODS codes & postcodes (Mar 2026)

Merge strategy (2-level ODS identifier):
  1. PCN_ODS_CODE / PCN_CODE: Primary Care Network ODS code
  2. PRACTICE_NAME: Practice name (unique within PCN)
"""

import pandas as pd
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INTEGRATED_CARE_SYSTEMS, PROCESSED_DATA_DIR

print("\n" + "="*80)
print("  NIHR PIC SOUTH LONDON - ETL DATA EXPLORATION & ANALYSIS")
print("="*80 + "\n")

# ============================================================================
# 1. LOAD RAW DATA
# ============================================================================

print("\n" + "="*80)
print("  STEP 1: LOAD RAW DATASETS")
print("="*80 + "\n")

# Resolve paths relative to this script file (robust regardless of cwd)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
data_dir = os.path.join(project_dir, "data")

data_files = {
    'dementia_metrics': os.path.join(data_dir, 'pcdem-prac-ass-plans-feb-2026.csv'),
    'gp_registry':      os.path.join(data_dir, 'gp-reg-pat-prac-map-03-2026.csv'),
}

print(f"  [DATA] Source directory : {data_dir}")
print(f"  [DATA] Dementia metrics : pcdem-prac-ass-plans-feb-2026.csv  (Feb 2026)")
print(f"  [DATA] GP registry      : gp-reg-pat-prac-map-03-2026.csv   (Mar 2026)")
print()

raw_data = {}
for name, path in data_files.items():
    if os.path.exists(path):
        print(f"  [OK]   Loading {name} ...")
        try:
            raw_data[name] = pd.read_csv(path, low_memory=False)
            print(f"         Rows    : {raw_data[name].shape[0]:,}")
            print(f"         Columns : {raw_data[name].shape[1]}")
            print(f"         Memory  : {raw_data[name].memory_usage(deep=True).sum() / 1024**2:.2f} MB")
            print()
        except Exception as e:
            print(f"  [ERROR] {e}\n")
    else:
        print(f"  [SKIP] File not found: {path}\n")

if not raw_data:
    print("\n[FATAL] No data files found!")
    sys.exit(1)

# ============================================================================
# 2. ANALYZE RAW DATA QUALITY
# ============================================================================

print("\n" + "="*80)
print("  STEP 2: RAW DATA QUALITY ASSESSMENT")
print("="*80 + "\n")

for name, df in raw_data.items():
    print(f"  Dataset : {name.upper()}")
    print(f"  {'-'*70}")
    print(f"  Rows            : {df.shape[0]:,}")
    print(f"  Columns         : {df.shape[1]}")
    print(f"  Duplicate rows  : {df.duplicated().sum():,}")
    print(f"  Missing cells   : {df.isnull().sum().sum():,}  ({df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100:.2f}%)")

    missing_by_col = df.isnull().sum()
    if (missing_by_col > 0).any():
        print(f"  Missing by col (top 5):")
        for col, count in missing_by_col[missing_by_col > 0].nlargest(5).items():
            pct = count / len(df) * 100
            print(f"    {col}: {count:,} ({pct:.1f}%)")
    print()

# ============================================================================
# 3. DATA CLEANING
# ============================================================================

print("\n" + "="*80)
print("  STEP 3: DATA CLEANING & PREPROCESSING")
print("="*80 + "\n")

dem_df = raw_data['dementia_metrics']
gp_df  = raw_data['gp_registry']

# South London ICB ODS codes from config
icb_codes = [v['icb_ods_code'] for v in INTEGRATED_CARE_SYSTEMS.values()]

# Clean dementia metrics: pivot from long to wide format
# Data is in long format: each row is practice + measure combination
# Measure column contains: DEMENTIA_REGISTER_0_64, DEMENTIA_REGISTER_65_PLUS, etc.
print("  [CLEAN] Dementia Metrics  (pcdem-prac-ass-plans-feb-2026.csv)")
print("  [PIVOT] Converting from long to wide format...")
dem_initial = len(dem_df)

# Identify the grouping columns (practice info) and value column
# Assuming structure: PRACTICE_CODE, PRACTICE_NAME, PCN_ODS_CODE, ..., Measure, Value
group_cols = ['PRACTICE_CODE', 'PRACTICE_NAME', 'PCN_ODS_CODE', 'PCN_NAME',
              'SUB_ICB_ODS_CODE', 'SUB_ICB_ONS_CODE']

# Check if Measure and Value columns exist
if 'Measure' in dem_df.columns and 'Value' in dem_df.columns:
    print(f"  Data format: LONG (Measure={dem_df['Measure'].nunique()} unique, rows={len(dem_df)})")
    print(f"  Unique measures: {dem_df['Measure'].unique()[:10].tolist()}")
    
    # Pivot: make each measure a column
    dem_unique = dem_df.pivot_table(
        index=group_cols,
        columns='Measure',
        values='Value',
        aggfunc='first'
    ).reset_index()
    
    print(f"  After pivot: {dem_unique.shape[0]} practices × {dem_unique.shape[1]} columns")
else:
    print(f"  Data format: WIDE (columns already separated)")
    actual_cols = [col for col in group_cols if col in dem_df.columns]
    dem_unique = dem_df.drop_duplicates(subset=['PRACTICE_CODE'])[actual_cols + 
                                                                   [col for col in dem_df.columns 
                                                                    if col not in actual_cols]].copy()

print(f"  Raw rows (input)         : {dem_initial:,}")
print(f"  Unique practices (output): {len(dem_unique):,}")
print()

# Clean GP registry: remove rows without postcode, then filter to South London
# ICB codes live in the GP registry, not in the dementia file
print("  [CLEAN] GP Registry  (gp-reg-pat-prac-map-03-2026.csv)")
gp_initial = len(gp_df)
gp_cleaned = gp_df[gp_df['PRACTICE_POSTCODE'].notna()].copy()
removed = gp_initial - len(gp_cleaned)
print(f"  Removed (no postcode) : {removed:,}")
print(f"  Rows kept             : {len(gp_cleaned):,}")
print()

print(f"  [FILTER] South London ICB codes : {icb_codes}")
gp_south = gp_cleaned[gp_cleaned['ICB_CODE'].isin(icb_codes)].copy()
dem_cleaned = dem_unique  # no ICB filter possible here; inner merge handles it
print(f"  South London GP practices (registry) : {len(gp_south):,}")
print()

# ============================================================================
# 4. MERGE DATASETS
# ============================================================================

print("\n" + "="*80)
print("  STEP 4: MERGE DATASETS  (2-level ODS code strategy)")
print("="*80 + "\n")

print("  Merge keys:")
print("    PCN_ODS_CODE (DEM) <-> PCN_CODE (GP registry) : authoritative NHS identifier")
print("    PRACTICE_NAME                                  : unique within PCN")
print()

merged_data = dem_unique.merge(
    gp_south[['PRACTICE_CODE', 'PRACTICE_NAME', 'PRACTICE_POSTCODE',
               'PCN_CODE', 'ICB_CODE', 'ICB_NAME', 'SUPPLIER_NAME']],
    how='inner',
    left_on=['PRACTICE_NAME', 'PCN_ODS_CODE'],
    right_on=['PRACTICE_NAME', 'PCN_CODE'],
    suffixes=('_DEM', '_GP')
)

matched = merged_data['PRACTICE_POSTCODE'].notna().sum()
match_pct = matched / len(merged_data) * 100
print(f"  South London practices matched        : {len(merged_data):,}")
print(f"  With postcode                         : {matched:,} / {len(merged_data):,}  ({match_pct:.1f}%)")
print(f"  Missing postcode                      : {len(merged_data) - matched:,}")
print()

# ============================================================================
# 5. BEFORE & AFTER COMPARISON
# ============================================================================

print("\n" + "="*80)
print("  STEP 5: BEFORE & AFTER TRANSFORMATION SUMMARY")
print("="*80 + "\n")

comparison_data = {
    'Dataset': ['Dementia Metrics (all rows)', 'Dementia Metrics (unique practices)', 'GP Registry', 'GP Registry (South London)'],
    'Before':  [dem_initial,      dem_initial,       gp_initial,       gp_initial],
    'After':   [len(dem_unique),  len(dem_unique),   len(gp_cleaned),  len(gp_south)],
}
comparison_df = pd.DataFrame(comparison_data)
comparison_df['Removed'] = comparison_df['Before'] - comparison_df['After']
comparison_df['% Reduction'] = (comparison_df['Removed'] / comparison_df['Before'] * 100).round(1)

print("\n" + comparison_df.to_string(index=False))
print()

# ============================================================================
# 6. TEXT REPORT (replaces graphical visualizations)
# ============================================================================

print("\n" + "="*80)
print("  STEP 6: GENERATING TEXT REPORT")
print("="*80 + "\n")

# --- ICB breakdown from merged data ---
icb_counts = merged_data['ICB_NAME'].value_counts()

# --- Postcode coverage ---
gp_with_pc  = len(gp_cleaned)
gp_without_pc = gp_initial - gp_with_pc

# --- Missing values in merged output (top columns only) ---
missing_pct = (merged_data.isnull().sum() / len(merged_data) * 100).sort_values(ascending=False)
missing_pct = missing_pct[missing_pct > 0].head(15)

# Build report lines
report_lines = []
report_lines.append("=" * 80)
report_lines.append("  NIHR PIC SOUTH LONDON - ETL ANALYSIS REPORT  (March 2026)")
report_lines.append("=" * 80)
report_lines.append("")

report_lines.append("  SECTION A  Dataset Sizes: Raw vs Cleaned")
report_lines.append("  " + "-" * 70)
report_lines.append(f"  {'Dataset':<45} {'Before':>8}  {'After':>8}  {'Removed':>8}  {'%Red':>6}")
report_lines.append("  " + "-" * 70)
for _, row in comparison_df.iterrows():
    report_lines.append(
        f"  {row['Dataset']:<45} {row['Before']:>8,}  {row['After']:>8,}  {row['Removed']:>8,}  {row['% Reduction']:>5.1f}%"
    )
report_lines.append("")

report_lines.append("  SECTION B  South London Practices by ICB")
report_lines.append("  " + "-" * 70)
report_lines.append(f"  {'ICB Name':<55} {'Practices':>9}")
report_lines.append("  " + "-" * 70)
for icb_name, count in icb_counts.items():
    report_lines.append(f"  {icb_name:<55} {count:>9,}")
report_lines.append(f"  {'TOTAL':<55} {icb_counts.sum():>9,}")
report_lines.append("")

report_lines.append("  SECTION C  GP Registry: Postcode Coverage")
report_lines.append("  " + "-" * 70)
report_lines.append(f"  With postcode    : {gp_with_pc:>7,}  ({100 * gp_with_pc / gp_initial:.1f}%)")
report_lines.append(f"  Without postcode : {gp_without_pc:>7,}  ({100 * gp_without_pc / gp_initial:.1f}%)")
report_lines.append(f"  Total registry   : {gp_initial:>7,}")
report_lines.append("")

report_lines.append("  SECTION D  Merge Result  (PCN_ODS_CODE + PRACTICE_NAME)")
report_lines.append("  " + "-" * 70)
report_lines.append(f"  Matched (postcode resolved) : {matched:>7,}  ({match_pct:.1f}%)")
report_lines.append(f"  Not matched                 : {len(merged_data) - matched:>7,}  ({100 - match_pct:.1f}%)")
report_lines.append(f"  Total practices             : {len(merged_data):>7,}")
report_lines.append("")

if len(missing_pct) > 0:
    report_lines.append("  SECTION E  Missing Values in Merged Dataset (top columns)")
    report_lines.append("  " + "-" * 70)
    report_lines.append(f"  {'Column':<40} {'Missing':>8}  {'%':>6}")
    report_lines.append("  " + "-" * 70)
    for col, pct in missing_pct.items():
        count = int(pct / 100 * len(merged_data))
        report_lines.append(f"  {col:<40} {count:>8,}  {pct:>5.1f}%")
    report_lines.append("")

report_lines.append("=" * 80)
report_lines.append("")

report_text = "\n".join(report_lines)
print(report_text)

# Save as .txt
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
report_path = os.path.join(PROCESSED_DATA_DIR, 'etl_analysis_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_text)
print(f"  [OK] Text report saved : {report_path}")

# Save summary comparison table as .csv
csv_path = os.path.join(PROCESSED_DATA_DIR, 'etl_analysis_summary.csv')
comparison_df.to_csv(csv_path, index=False)
print(f"  [OK] Summary CSV saved : {csv_path}")
print()

# ============================================================================
# 7. DATA QUALITY METRICS
# ============================================================================

print("\n" + "="*80)
print("  STEP 7: DATA QUALITY METRICS - MERGED DATA")
print("="*80 + "\n")

print("  Field completeness check:")
print(f"  {'─'*70}")
print(f"  {'Field':<30}  {'Status':<6}  {'Complete':>10}  {'%':>6}  Description")
print(f"  {'─'*70}")
critical_fields = {
    'PRACTICE_CODE': 'Practice identifier',
    'PRACTICE_NAME':     'Practice name',
    'ICB_CODE':      'ICB code',
    'PRACTICE_POSTCODE': 'Postcode for geocoding',
    'SUPPLIER_NAME':     'System supplier',
}

for field, description in critical_fields.items():
    if field in merged_data.columns:
        complete = merged_data[field].notna().sum()
        pct = (complete / len(merged_data)) * 100
        status = "[OK]  " if pct >= 95 else "[WARN]" if pct >= 80 else "[FAIL]"
        print(f"  {field:<30}  {status}  {complete:>5,}/{len(merged_data):,}  {pct:>5.1f}%  {description}")
    else:
        print(f"  {field:<30}  [MISS]  {'N/A':>10}  {'N/A':>6}  {description}")
print()

# ============================================================================
# 8. EXPORT CLEANED DATA
# ============================================================================

print("\n" + "="*80)
print("  STEP 8: EXPORTING CLEANED DATASETS")
print("="*80 + "\n")

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

export_files = {
    'gp_practices_cleaned.csv':   gp_south,
    'practice_data_cleaned.csv':  dem_unique,
    'merged_southlondon.csv':     merged_data,
}

for filename, df in export_files.items():
    filepath = os.path.join(PROCESSED_DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"  [OK] {filename:<40}  {len(df):>6,} rows")

print(f"\n  Saved to: {PROCESSED_DATA_DIR}")
print()

# ============================================================================
# 9. SUMMARY & RECOMMENDATIONS
# ============================================================================

print("\n" + "="*80)
print("  SUMMARY & APRIL 2026 ROADMAP")
print("="*80)

print(f"""
  [COMPLETE] MARCH 2026
  ─────────────────────────────────────────────────────────────────────────
  Data sources     : pcdem-prac-ass-plans-feb-2026.csv
                     gp-reg-pat-prac-map-03-2026.csv
  Cleaned outputs  : {len(export_files)} CSV files
  South London     : {len(dem_cleaned):,} practices
  Merge strategy   : 2-level ODS  (PCN_ODS_CODE + PRACTICE_NAME)
  Match rate       : {match_pct:.1f}%
  Status           : READY for geocoding


  [NEXT] APRIL 2026
  ─────────────────────────────────────────────────────────────────────────

  1. GEOCODING
     Convert {matched:,} postcodes -> lat/lon via Nominatim (OpenStreetMap)
     Output: gp_practices_geocoded.csv

  2. HOSPITAL SITES
     Extract and geocode 11 Delivery Organisation locations
     Output: hospital_sites_geocoded.csv

  3. TRAVEL TIME CALCULATIONS
     GP -> 5 nearest hospitals  |  haversine, pre-filter <25 km
     Output: travel_times_optimized.csv

  4. STREAMLIT MAPPING  (May)
     Interactive Folium maps with travel time toggles


  [KEY STATS]
  ─────────────────────────────────────────────────────────────────────────
  South London ICBs       : {', '.join(icb_codes)}
  Practices analysed      : {len(merged_data):,}
  GP registry (postcode)  : {len(gp_cleaned):,}
  Postcode match rate     : {match_pct:.1f}%
  Geocoding readiness     : HIGH
""")

print("="*80)
print("  ETL ANALYSIS COMPLETE")
print("="*80 + "\n")
