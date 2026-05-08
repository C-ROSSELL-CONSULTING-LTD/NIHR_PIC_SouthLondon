"""
Script 02: Geocode practices and match to MSOA boundaries.
Retains postcode for later travel time calculations.

Workflow:
  1. Read merged_southlondon.csv from Script 00
  2. Geocode practice postcodes to lat/lon via Nominatim
  3. Load MSOA 2021 boundaries (GeoJSON)
  4. Spatial join: assign each practice to its MSOA
  5. Retain all columns: postcode, lat/lon, MSOA, counts
  6. Output: gp_practices_msoa.csv
"""

import pandas as pd
import geopandas as gpd
import logging
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Files
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
LOOKUPS_DIR = DATA_DIR / "lookups"

INPUT_FILE = os.path.join(PROCESSED_DATA_DIR, "merged_southlondon.csv")
MSOA_GEOJSON = str(BOUNDARIES_DIR / "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V3_1633701655676791957.geojson")
POSTCODE_MSOA_LOOKUP = str(LOOKUPS_DIR / "National_Statistics_Postcode_Lookup_(February_2026)_for_the_UK_(Hosted_Table).csv")
OUTPUT_FILE = os.path.join(PROCESSED_DATA_DIR, "gp_practices_msoa.csv")

def match_postcode_to_msoa_via_lookup(gp_data):
    """
    Match postcodes to MSOA using ONS NSPL lookup table.
    
    Args:
        gp_data: DataFrame with 'PRACTICE_POSTCODE' column
        
    Returns:
        DataFrame with new 'MSOA21CD' column
    """
    logger.info(f"[LOOKUP] Loading postcode→MSOA lookup from {POSTCODE_MSOA_LOOKUP}...")
    
    if not os.path.exists(POSTCODE_MSOA_LOOKUP):
        logger.error(f"[ERROR] Postcode lookup file not found: {POSTCODE_MSOA_LOOKUP}")
        logger.error("[HINT] Run scripts/download_boundaries.py first to fetch MSOA data")
        return None
    
    postcode_lookup = pd.read_csv(POSTCODE_MSOA_LOOKUP)
    
    # Normalize postcodes (remove spaces, uppercase)
    gp_data['postcode_norm'] = gp_data['PRACTICE_POSTCODE'].str.replace(' ', '').str.upper()
    postcode_lookup['postcode_norm'] = postcode_lookup['pcds'].str.replace(' ', '').str.upper()
    
    # Left merge to assign MSOA and coordinates to each practice
    gp_data = gp_data.merge(
        postcode_lookup[['postcode_norm', 'msoa21cd', 'lat', 'long']],
        on='postcode_norm',
        how='left'
    )
    
    gp_data.rename(columns={'msoa21cd': 'MSOA21CD', 'lat': 'latitude', 'long': 'longitude'}, inplace=True)
    gp_data.drop('postcode_norm', axis=1, inplace=True)
    
    # Check coverage
    matched = gp_data['MSOA21CD'].notna().sum()
    total = len(gp_data)
    logger.info(f"[RESULT] Postcode→MSOA matching: {matched}/{total} practices matched ({100*matched/total:.1f}%)")
    
    if matched < total:
        unmatched_postcodes = gp_data[gp_data['MSOA21CD'].isna()]['PRACTICE_POSTCODE'].unique()
        logger.warning(f"[WARN] {len(unmatched_postcodes)} postcodes could not be matched:")
        for pc in unmatched_postcodes[:5]:
            logger.warning(f"      {pc}")
        if len(unmatched_postcodes) > 5:
            logger.warning(f"      ... and {len(unmatched_postcodes) - 5} more")
    
    return gp_data

def prepare_msoa_data():
    """
    Main workflow:
    1. Load practice data from Script 00
    2. Geocode postcodes to lat/lon
    3. Match postcodes to MSOA via lookup
    4. Output enriched dataset
    """
    
    logger.info("=" * 70)
    logger.info("STEP 02: Geocode Practices & Match to MSOA")
    logger.info("=" * 70)
    
    # Load practice data
    logger.info(f"\n[LOAD] Reading {INPUT_FILE}...")
    if not os.path.exists(INPUT_FILE):
        logger.error(f"[ERROR] Input file not found: {INPUT_FILE}")
        logger.error("[HINT] Run Script 00 first to prepare merged data")
        return None
    
    gp_data = pd.read_csv(INPUT_FILE)
    logger.info(f"[OK] Loaded {len(gp_data)} practices")
    
    # Get lat/lon from postcode lookup (no Nominatim needed)
    logger.info(f"\n[LOOKUP] Loading postcode→MSOA lookup and coordinates...")
    gp_data = match_postcode_to_msoa_via_lookup(gp_data)
    
    if gp_data is None:
        return None
    
    # Output columns: keep postcode, lat/lon, MSOA, counts, practice info
    output_cols = [
        'PRACTICE_CODE', 'PRACTICE_NAME', 'PRACTICE_POSTCODE',
        'latitude', 'longitude', 'MSOA21CD',
        'DEMENTIA_REGISTER_0_64', 'DEMENTIA_REGISTER_65_PLUS',
        'PAT_LIST_0_64', 'PAT_LIST_65_PLUS',
        'PCN_ODS_CODE', 'PCN_NAME', 'SUB_ICB_ODS_CODE'
    ]
    
    # Keep only columns that exist
    output_cols = [col for col in output_cols if col in gp_data.columns]
    gp_data_out = gp_data[output_cols].copy()
    
    # Save
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    gp_data_out.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"\n[SAVE] Saved {len(gp_data_out)} practices to {OUTPUT_FILE}")
    
    # Summary stats
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total practices: {len(gp_data_out)}")
    logger.info(f"Coordinates from lookup (lat/lon): {gp_data_out['latitude'].notna().sum()}")
    logger.info(f"Matched to MSOA: {gp_data_out['MSOA21CD'].notna().sum()}")
    logger.info(f"Unique MSOAs: {gp_data_out['MSOA21CD'].nunique()}")
    
    if 'DEMENTIA_REGISTER_65_PLUS' in gp_data_out.columns:
        logger.info(f"\nDementia Register (65+):")
        logger.info(f"  Total patients: {gp_data_out['DEMENTIA_REGISTER_65_PLUS'].sum():,.0f}")
        logger.info(f"  Mean per practice: {gp_data_out['DEMENTIA_REGISTER_65_PLUS'].mean():.1f}")
    
    if 'DEMENTIA_REGISTER_0_64' in gp_data_out.columns:
        logger.info(f"\nDementia Register (0-64):")
        logger.info(f"  Total patients: {gp_data_out['DEMENTIA_REGISTER_0_64'].sum():,.0f}")
        logger.info(f"  Mean per practice: {gp_data_out['DEMENTIA_REGISTER_0_64'].mean():.1f}")
    
    logger.info("\nSample:")
    sample_cols = ['PRACTICE_NAME', 'PRACTICE_POSTCODE', 'MSOA21CD', 'latitude', 'longitude', 'DEMENTIA_REGISTER_65_PLUS']
    sample_cols = [col for col in sample_cols if col in gp_data_out.columns]
    if sample_cols:
        print(gp_data_out[sample_cols].head(10).to_string())
    
    return gp_data_out

if __name__ == "__main__":
    gp_data = prepare_msoa_data()
    if gp_data is not None:
        logger.info(f"\n✓ SUCCESS! Prepared {len(gp_data)} practices with MSOA assignments")
    else:
        logger.error("\n✗ FAILED to prepare MSOA data")
        sys.exit(1)
