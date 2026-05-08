"""
Script 01: Extract and geocode hospital locations for the 11 Delivery Organisations.
Sources:
  - Manually curated hospital registry (comprehensive list of acute, mental health, and specialist hospitals)
  - Postcode lookup for fast geocoding (no API rate-limiting)

Workflow:
  1. Load fallback hospital registry (21 sites across 11 trusts)
  2. Match postcodes to coordinates using ONS postcode lookup
  3. Save hospital_sites_geocoded.csv
"""

import pandas as pd
import logging
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.geocoding import geocode_address
from config import PROCESSED_DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOSPITAL_DATA_FILE = os.path.join(PROCESSED_DATA_DIR, "hospital_sites_geocoded.csv")

# Postcode lookup for coordinates
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
LOOKUPS_DIR = DATA_DIR / "lookups"
POSTCODE_LOOKUP = str(LOOKUPS_DIR / "National_Statistics_Postcode_Lookup_(February_2026)_for_the_UK_(Hosted_Table).csv")

# Fallback: Manually curated major hospital sites for South London (primary research sites)
# Used when ODS queries fail or incomplete
FALLBACK_HOSPITAL_REGISTRY = [
    {
        "hospital_name": "St George's University Hospital",
        "trust": "St George's University Hospitals NHS Foundation Trust",
        "trust_ods_code": "RJ7",
        "site_ods_code": "RJ7",
        "address": "Blackshaw Road, London, SW17 8QT",
        "postcode": "SW17 8QT",
        "type": "Hospital"
    },
    {
        "hospital_name": "King's College Hospital",
        "trust": "King's College Hospital NHS Foundation Trust",
        "trust_ods_code": "RJ2",
        "site_ods_code": "RJ2",
        "address": "Denmark Hill, London, SE5 9RS",
        "postcode": "SE5 9RS",
        "type": "Hospital"
    },
    {
        "hospital_name": "Guy's Hospital",
        "trust": "Guy's and St Thomas' NHS Foundation Trust",
        "trust_ods_code": "RJ1",
        "site_ods_code": "RJ1",
        "address": "Great Maze Pond, London, SE1 9RT",
        "postcode": "SE1 9RT",
        "type": "Hospital"
    },
    {
        "hospital_name": "St Thomas' Hospital",
        "trust": "Guy's and St Thomas' NHS Foundation Trust",
        "trust_ods_code": "RJ1",
        "site_ods_code": "RJ1A",
        "address": "Lambeth Palace Road, London, SE1 7EH",
        "postcode": "SE1 7EH",
        "type": "Hospital"
    },
    {
        "hospital_name": "The Royal Marsden",
        "trust": "The Royal Marsden NHS Foundation Trust",
        "trust_ods_code": "RID",
        "site_ods_code": "RID",
        "address": "Fulham Road, London, SW3 6JJ",
        "postcode": "SW3 6JJ",
        "type": "Hospital"
    },
    {
        "hospital_name": "Queen Elizabeth Hospital",
        "trust": "Lewisham and Greenwich NHS Trust",
        "trust_ods_code": "RWE",
        "site_ods_code": "RWE",
        "address": "Stadium Road, London, SE18 4QH",
        "postcode": "SE18 4QH",
        "type": "Hospital"
    },
    {
        "hospital_name": "Lewisham Hospital",
        "trust": "Lewisham and Greenwich NHS Trust",
        "trust_ods_code": "RWE",
        "site_ods_code": "RWE2",
        "address": "High Street, London, SE13 6LH",
        "postcode": "SE13 6LH",
        "type": "Hospital"
    },
    {
        "hospital_name": "Princess Royal University Hospital",
        "trust": "King's College Hospital NHS Foundation Trust",
        "trust_ods_code": "RJ2",
        "site_ods_code": "RJ2A",
        "address": "Farnborough, Orpington, BR6 8ND",
        "postcode": "BR6 8ND",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "The Royal Marsden - Sutton",
        "trust": "The Royal Marsden NHS Foundation Trust",
        "trust_ods_code": "RID",
        "site_ods_code": "RIDA",
        "address": "Downs Road, Sutton, SM2 5PT",
        "postcode": "SM2 5PT",
        "type": "Cancer Centre"
    },
    {
        "hospital_name": "Kingston Hospital",
        "trust": "Kingston and Richmond NHS Foundation Trust",
        "trust_ods_code": "RWH",
        "site_ods_code": "RWH",
        "address": "Galsworthy Road, Kingston Upon Thames, KT2 7QB",
        "postcode": "KT2 7QB",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "Richmond Hospital",
        "trust": "Kingston and Richmond NHS Foundation Trust",
        "trust_ods_code": "RWH",
        "site_ods_code": "RWHA",
        "address": "Kew Foot Road, Richmond, TW9 2TE",
        "postcode": "TW9 2TE",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "Croydon University Hospital",
        "trust": "Croydon Health Services NHS Trust",
        "trust_ods_code": "RXF",
        "site_ods_code": "RXF",
        "address": "530 South End, Croydon, CR7 7YE",
        "postcode": "CR7 7YE",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "St Helier Hospital",
        "trust": "Epsom and St Helier University Hospitals NHS Trust",
        "trust_ods_code": "RXL",
        "site_ods_code": "RXL",
        "address": "Wrythe Lane, Carshalton, SM5 1AA",
        "postcode": "SM5 1AA",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "Epsom Hospital",
        "trust": "Epsom and St Helier University Hospitals NHS Trust",
        "trust_ods_code": "RXL",
        "site_ods_code": "RXLA",
        "address": "Canada Avenue, Epsom, KT18 7EG",
        "postcode": "KT18 7EG",
        "type": "Acute Hospital"
    },
    {
        "hospital_name": "Maudsley Hospital",
        "trust": "South London and Maudsley NHS Foundation Trust",
        "trust_ods_code": "RWL",
        "site_ods_code": "RWL",
        "address": "Denmark Hill, London, SE5 8AZ",
        "postcode": "SE5 8AZ",
        "type": "Mental Health Hospital"
    },
    {
        "hospital_name": "Bethlem Royal Hospital",
        "trust": "South London and Maudsley NHS Foundation Trust",
        "trust_ods_code": "RWL",
        "site_ods_code": "RWLA",
        "address": "Monks Orchard Road, Beckenham, BR3 3BX",
        "postcode": "BR3 3BX",
        "type": "Mental Health Hospital"
    },
    {
        "hospital_name": "Oxleas NHS Foundation Trust - Tarn Ward",
        "trust": "Oxleas NHS Foundation Trust",
        "trust_ods_code": "RWK",
        "site_ods_code": "RWK",
        "address": "Plumstead Common Road, London, SE18 2PH",
        "postcode": "SE18 2PH",
        "type": "Mental Health Inpatient"
    },
    {
        "hospital_name": "Springfield Hospital",
        "trust": "South West London and St George's Mental Health NHS Trust",
        "trust_ods_code": "RCA",
        "site_ods_code": "RCA",
        "address": "61 Glenburnie Road, London, SW19 3ND",
        "postcode": "SW19 3ND",
        "type": "Mental Health Hospital"
    },
    {
        "hospital_name": "Tolworth Hospital",
        "trust": "South West London and St George's Mental Health NHS Trust",
        "trust_ods_code": "RCA",
        "site_ods_code": "RCAA",
        "address": "Tolworth Rise South, Surbiton, KT6 7QU",
        "postcode": "KT6 7QU",
        "type": "Mental Health Hospital"
    },
]



def prepare_hospital_data():
    """
    Main workflow:
    1. Load hospital registry (curated list of 21 sites across 11 trusts)
    2. Match postcodes to coordinates using ONS postcode lookup
    3. Save to CSV
    """
    
    logger.info("=" * 70)
    logger.info("STEP 01: Prepare Hospital Sites")
    logger.info("=" * 70)
    logger.info(f"\nLoading hospital registry...\n")
    
    hospital_data = FALLBACK_HOSPITAL_REGISTRY.copy()
    
    # Create DataFrame
    hospital_df = pd.DataFrame(hospital_data)
    logger.info(f"\n[LOAD] Loaded {len(hospital_df)} hospital sites from registry")
    
    # Load postcode lookup for coordinates (replaces Nominatim geocoding)
    logger.info(f"\n[LOOKUP] Loading postcode→coordinates lookup...")
    try:
        postcode_lookup = pd.read_csv(POSTCODE_LOOKUP, low_memory=False)
        # Normalize postcode column name if different
        if 'pcds' in postcode_lookup.columns:
            postcode_lookup.rename(columns={'pcds': 'postcode_norm'}, inplace=True)
        else:
            postcode_lookup.rename(columns={postcode_lookup.columns[0]: 'postcode_norm'}, inplace=True)
        
        postcode_lookup['postcode_norm'] = postcode_lookup['postcode_norm'].str.replace(' ', '').str.upper()
        logger.info(f"[OK] Loaded postcode lookup with {len(postcode_lookup)} postcodes")
    except FileNotFoundError:
        logger.error(f"[ERROR] Postcode lookup not found: {POSTCODE_LOOKUP}")
        logger.error("[HINT] Download from ONS or copy to data/lookups/ directory")
        return None
    
    # Normalize hospital postcodes for lookup
    hospital_df['postcode_norm'] = hospital_df['postcode'].fillna('').str.replace(' ', '').str.upper()
    
    # Merge with postcode lookup to get coordinates
    logger.info(f"\n[MERGE] Matching hospital postcodes to coordinates...")
    hospital_df = hospital_df.merge(
        postcode_lookup[['postcode_norm', 'lat', 'long']],
        on='postcode_norm',
        how='left'
    )
    
    # Rename columns to match expected output
    hospital_df.rename(columns={'lat': 'latitude', 'long': 'longitude'}, inplace=True)
    
    lookup_success = hospital_df['latitude'].notna().sum()
    logger.info(f"\n[RESULT] Postcode→coordinates mapping: {lookup_success}/{len(hospital_df)} hospitals matched")
    
    # Drop temporary postcode_norm column
    hospital_df.drop(columns=['postcode_norm'], inplace=True)
    
    # Fallback: Geocode missing locations using Nominatim
    missing_coords = hospital_df[hospital_df['latitude'].isna()].copy()
    if len(missing_coords) > 0:
        logger.info(f"\n[FALLBACK] Geocoding {len(missing_coords)} missing locations with Nominatim...")
        
        for idx, row in missing_coords.iterrows():
            address = row.get('address', '')
            if address:
                lat, lon = geocode_address(address)
                if lat and lon:
                    hospital_df.at[idx, 'latitude'] = lat
                    hospital_df.at[idx, 'longitude'] = lon
                    logger.info(f"  [{row['hospital_name']}]: ({lat:.4f}, {lon:.4f})")
                else:
                    logger.warning(f"  [{row['hospital_name']}]: Nominatim geocoding failed")
    
    final_success = hospital_df['latitude'].notna().sum()
    logger.info(f"\n[COMPLETE] Final geocoding result: {final_success}/{len(hospital_df)} hospitals have coordinates")
    
    
    # Save data
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    hospital_df.to_csv(HOSPITAL_DATA_FILE, index=False)
    logger.info(f"\n[SAVE] Saved {len(hospital_df)} hospital sites to {HOSPITAL_DATA_FILE}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total sites: {len(hospital_df)}")
    logger.info(f"Geocoded (via postcode lookup): {lookup_success}")
    logger.info(f"Geocoded (via Nominatim fallback): {hospital_df['latitude'].notna().sum() - lookup_success}")
    logger.info(f"Total geocoded: {hospital_df['latitude'].notna().sum()}")
    logger.info(f"Trusts represented: {hospital_df['trust_ods_code'].nunique()}")
    logger.info(f"\nSites by type:")
    print(hospital_df['type'].value_counts().to_string())
    
    logger.info(f"\nSample sites:")
    sample_cols = ['hospital_name', 'trust_ods_code', 'postcode', 'latitude', 'longitude']
    print(hospital_df[sample_cols].head(10).to_string())
    
    return hospital_df

if __name__ == "__main__":
    hospital_data = prepare_hospital_data()
    if hospital_data is not None:
        logger.info(f"\nSuccess! Prepared {len(hospital_data)} hospital sites")
        logger.info(f"\nSample:\n{hospital_data[['hospital_name', 'postcode', 'latitude', 'longitude']].head()}")
    else:
        logger.error("Failed to prepare hospital data")
        sys.exit(1)
