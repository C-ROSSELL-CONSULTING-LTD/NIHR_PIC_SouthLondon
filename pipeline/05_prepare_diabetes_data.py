"""
Extract and prepare diabetes data from National Diabetes Audit
Matches diabetes registrations to GP practices in South London

Sources:
  - National_Diabetes_Audit_2025-26.xlsx (Type 1 & Type 2)
  - gp_practices_geocoded.csv (for matching)
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("\n" + "="*80)
print("  NIHR PIC SOUTH LONDON - DIABETES AUDIT DATA PREPARATION")
print("="*80 + "\n")

# ============================================================================
# PATHS
# ============================================================================

script_dir = Path(__file__).parent
project_dir = script_dir.parent
data_dir = project_dir / "data"
raw_dir = data_dir / "raw"
processed_dir = data_dir / "processed"

audit_file = raw_dir / "National Diabetes Audit, 2025-26, April 2025 to December 2025.xlsx"
gp_geocoded_file = processed_dir / "gp_practices_geocoded.csv"
practice_data_file = processed_dir / "practice_data_cleaned.csv"

print(f"[DATA] Raw file: {audit_file.name}")
print(f"[DATA] GP reference: {gp_geocoded_file.name}\n")

# ============================================================================
# LOAD DATA
# ============================================================================

print("="*80)
print("  STEP 1: LOAD DIABETES AUDIT DATA")
print("="*80 + "\n")

# Load both Type 1 and Type 2
type1_df = pd.read_excel(audit_file, sheet_name='Type 1 registrations', skiprows=7)
type2_df = pd.read_excel(audit_file, sheet_name='Type 2 and other registrations', skiprows=7)

print(f"[OK]   Type 1 rows: {len(type1_df)}")
print(f"[OK]   Type 2 rows: {len(type2_df)}\n")

# ============================================================================
# FILTER TO SOUTH LONDON ICBs
# ============================================================================

print("="*80)
print("  STEP 2: FILTER TO SOUTH LONDON ICBS")
print("="*80 + "\n")

# South London ICBs
SOUTH_LONDON_ICBS = ['QKK', 'QWE']  # QKK = SE London, QWE = SW London
ICB_NAMES = {
    'QKK': 'NHS South East London Integrated Care Board',
    'QWE': 'NHS South West London Integrated Care Board'
}

type1_sl = type1_df[type1_df['ICB code'].isin(SOUTH_LONDON_ICBS)].copy()
type2_sl = type2_df[type2_df['ICB code'].isin(SOUTH_LONDON_ICBS)].copy()

print(f"[OK]   Type 1 (South London): {len(type1_sl)} rows")
print(f"[OK]   Type 2 (South London): {len(type2_sl)} rows\n")

# ============================================================================
# EXTRACT GP-LEVEL DATA
# ============================================================================

print("="*80)
print("  STEP 3: EXTRACT GP-LEVEL DATA")
print("="*80 + "\n")

# Filter to GP records (where GP code is not NaN and is valid)
type1_gp = type1_sl[(type1_sl['GP code'].notna()) & (type1_sl['GP code'].astype(str).str.len() > 2)].copy()
type2_gp = type2_sl[(type2_sl['GP code'].notna()) & (type2_sl['GP code'].astype(str).str.len() > 2)].copy()

print(f"[OK]   Type 1 GP records: {len(type1_gp)}")
print(f"[OK]   Type 2 GP records: {len(type2_gp)}\n")

# Rename columns for clarity
type1_gp = type1_gp.rename(columns={'Number': 'diabetes_type1_count', 'Per cent': 'diabetes_type1_pct'})
type2_gp = type2_gp.rename(columns={'Number': 'diabetes_type2_count', 'Per cent': 'diabetes_type2_pct'})

# Convert percentage columns to numeric (handle strings)
for col in ['diabetes_type1_pct', 'diabetes_type2_pct']:
    if 'diabetes_type1_pct' in type1_gp.columns:
        type1_gp['diabetes_type1_pct'] = pd.to_numeric(type1_gp['diabetes_type1_pct'], errors='coerce')
    if 'diabetes_type2_pct' in type2_gp.columns:
        type2_gp['diabetes_type2_pct'] = pd.to_numeric(type2_gp['diabetes_type2_pct'], errors='coerce')

# Convert count columns to numeric
for col in ['diabetes_type1_count', 'diabetes_type2_count']:
    if 'diabetes_type1_count' in type1_gp.columns:
        type1_gp['diabetes_type1_count'] = pd.to_numeric(type1_gp['diabetes_type1_count'], errors='coerce')
    if 'diabetes_type2_count' in type2_gp.columns:
        type2_gp['diabetes_type2_count'] = pd.to_numeric(type2_gp['diabetes_type2_count'], errors='coerce')

# Extract relevant columns
type1_extract = type1_gp[['GP code', 'GP name', 'ICB code', 'diabetes_type1_count', 'diabetes_type1_pct']].copy()
type2_extract = type2_gp[['GP code', 'GP name', 'ICB code', 'diabetes_type2_count', 'diabetes_type2_pct']].copy()

# Merge Type 1 and Type 2
diabetes_merged = type1_extract.merge(
    type2_extract,
    on=['GP code', 'GP name', 'ICB code'],
    how='outer'
).fillna(0)

# Calculate total diabetes (safely, handling any remaining NaNs)
diabetes_merged['diabetes_total_count'] = (
    pd.to_numeric(diabetes_merged['diabetes_type1_count'], errors='coerce').fillna(0) +
    pd.to_numeric(diabetes_merged['diabetes_type2_count'], errors='coerce').fillna(0)
)
diabetes_merged['diabetes_total_pct'] = (
    pd.to_numeric(diabetes_merged['diabetes_type1_pct'], errors='coerce').fillna(0) +
    pd.to_numeric(diabetes_merged['diabetes_type2_pct'], errors='coerce').fillna(0)
)

print(f"[OK]   Total unique GPs with diabetes data: {len(diabetes_merged)}\n")

# ============================================================================
# LOAD EXISTING GP DATA FOR MATCHING
# ============================================================================

print("="*80)
print("  STEP 4: MERGE WITH EXISTING GP PRACTICES")
print("="*80 + "\n")

gp_ref = pd.read_csv(gp_geocoded_file)
print(f"[OK]   Loaded {len(gp_ref)} existing GP practices\n")

# Load practice data for population info
if practice_data_file.exists():
    practice_data = pd.read_csv(practice_data_file)
    print(f"[OK]   Loaded practice data with population info ({len(practice_data)} records)\n")
else:
    practice_data = None
    print(f"[WARN] Practice data file not found - population data unavailable\n")

# Rename GP code column for merging (might be different names)
gp_ref_copy = gp_ref.copy()
if 'practice_code_gp' in gp_ref_copy.columns:
    gp_ref_copy = gp_ref_copy.rename(columns={'practice_code_gp': 'GP code'})

# Merge diabetes data onto GP practices
merged_result = gp_ref_copy.merge(
    diabetes_merged[['GP code', 'diabetes_type1_count', 'diabetes_type1_pct', 
                      'diabetes_type2_count', 'diabetes_type2_pct', 
                      'diabetes_total_count', 'diabetes_total_pct']],
    left_on='GP code' if 'GP code' in gp_ref_copy.columns else 'practice_code_gp',
    right_on='GP code',
    how='left'
)

# Merge population data from practice_data_cleaned if available
if practice_data is not None:
    pop_data = practice_data[['PRACTICE_CODE', 'PAT_LIST_0_64', 'PAT_LIST_65_PLUS']].drop_duplicates()
    pop_data = pop_data.rename(columns={'PRACTICE_CODE': 'GP code'})
    
    merged_result = merged_result.merge(
        pop_data,
        on='GP code',
        how='left'
    )
    
    # Calculate total population
    merged_result['TOTAL_POPULATION'] = (
        pd.to_numeric(merged_result['PAT_LIST_0_64'], errors='coerce').fillna(0) +
        pd.to_numeric(merged_result['PAT_LIST_65_PLUS'], errors='coerce').fillna(0)
    )
    
    print(f"[OK]   Added population data to {merged_result['TOTAL_POPULATION'].notna().sum()} practices\n")

# Count matches
matches = merged_result['diabetes_total_count'].notna().sum()
print(f"[OK]   Matched diabetes data to {matches} practices ({matches/len(gp_ref)*100:.1f}%)\n")

# ============================================================================
# LOAD POPULATION DATA
# ============================================================================

print("="*80)
print("  STEP 5: ADD POPULATION DATA")
print("="*80 + "\n")

# Add population info to diabetes_merged for diabetes_by_practice.csv
if practice_data is not None:
    pop_data_merged = practice_data[['PRACTICE_CODE', 'PAT_LIST_0_64', 'PAT_LIST_65_PLUS']].drop_duplicates()
    pop_data_merged = pop_data_merged.rename(columns={'PRACTICE_CODE': 'GP code'})
    
    diabetes_merged_with_pop = diabetes_merged.merge(
        pop_data_merged,
        on='GP code',
        how='left'
    )
    
    # Calculate total population for diabetes data
    diabetes_merged_with_pop['TOTAL_POPULATION'] = (
        pd.to_numeric(diabetes_merged_with_pop['PAT_LIST_0_64'], errors='coerce').fillna(0) +
        pd.to_numeric(diabetes_merged_with_pop['PAT_LIST_65_PLUS'], errors='coerce').fillna(0)
    )
    
    print(f"[OK]   Added population data to {diabetes_merged_with_pop['TOTAL_POPULATION'].notna().sum()} diabetes records\n")
else:
    diabetes_merged_with_pop = diabetes_merged
    print(f"[WARN] Population data unavailable - using diabetes data only\n")

# ============================================================================
# SAVE OUTPUTS
# ============================================================================

print("="*80)
print("  STEP 6: SAVE OUTPUTS")
print("="*80 + "\n")

# Save diabetes-only dataset (with population if available)
# Drop age-stratified population columns since diabetes isn't age-stratified
diabetes_output = diabetes_merged_with_pop.drop(columns=['PAT_LIST_0_64', 'PAT_LIST_65_PLUS'], errors='ignore')
diabetes_output.to_csv(processed_dir / 'diabetes_by_practice.csv', index=False)
print(f"[OK]   Saved: diabetes_by_practice.csv ({len(diabetes_output)} records)")

# Save merged GP + diabetes
# Drop age-stratified population columns since diabetes isn't age-stratified
merged_output = merged_result.drop(columns=['PAT_LIST_0_64', 'PAT_LIST_65_PLUS'], errors='ignore')
merged_output.to_csv(processed_dir / 'gp_practices_with_diabetes.csv', index=False)
print(f"[OK]   Saved: gp_practices_with_diabetes.csv ({len(merged_output)} records)\n")

# ============================================================================
# SUMMARY STATS
# ============================================================================

print("="*80)
print("  STEP 7: SUMMARY STATISTICS")
print("="*80 + "\n")

print(f"Type 1 Diabetes (South London):")
print(f"  - Total practices: {(diabetes_merged['diabetes_type1_count'] > 0).sum()}")
print(f"  - Total registered: {diabetes_merged['diabetes_type1_count'].sum():.0f}")
print(f"  - Avg per practice: {diabetes_merged['diabetes_type1_count'].mean():.1f}\n")

print(f"Type 2 Diabetes (South London):")
print(f"  - Total practices: {(diabetes_merged['diabetes_type2_count'] > 0).sum()}")
print(f"  - Total registered: {diabetes_merged['diabetes_type2_count'].sum():.0f}")
print(f"  - Avg per practice: {diabetes_merged['diabetes_type2_count'].mean():.1f}\n")

print(f"Combined:")
print(f"  - Total practices with diabetes data: {len(diabetes_merged)}")
print(f"  - Practices matched to existing GP list: {matches}")

print("\n" + "="*80)
print("  ✅ DIABETES DATA PREPARATION COMPLETE")
print("="*80 + "\n")
