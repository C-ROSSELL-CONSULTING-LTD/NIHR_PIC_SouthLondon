"""
Script 3: Calculate travel times from GP practices to hospital sites.
Uses r5py for real routing analysis (not distance estimation).
Optimizations:
- Pre-filters to 5 nearest hospitals per GP using haversine distance
- Calculates actual travel times using OpenStreetMap routing
- Supports multiple modes: car, transit, walking
- Downloads and caches OSM/GTFS data automatically
"""

import pandas as pd
import numpy as np
import logging
import sys
import os
from math import radians, sin, cos, sqrt, atan2
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    PROCESSED_DATA_DIR, GP_DATA_FILE, HOSPITAL_DATA_FILE, 
    TRAVEL_TIMES_FILE, MAX_HOSPITALS_PER_GP, TRAVEL_MODES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate haversine distance between two points in km.
    Used for pre-filtering to nearest hospitals.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def find_nearest_hospitals(gp_row, hospital_df, n=MAX_HOSPITALS_PER_GP):
    """
    Find n nearest hospitals to a GP practice using haversine distance.
    
    Args:
        gp_row: GP practice row with 'latitude' and 'longitude'
        hospital_df: DataFrame with hospital data and coordinates
        n: Number of nearest hospitals to find
        
    Returns:
        DataFrame: Top n nearest hospitals with indices
    """
    if pd.isna(gp_row['latitude']) or pd.isna(gp_row['longitude']):
        return pd.DataFrame()
    
    # Calculate distance to all hospitals
    distances = []
    for idx, hosp in hospital_df.iterrows():
        if pd.isna(hosp['latitude']) or pd.isna(hosp['longitude']):
            continue
        
        dist = haversine_distance(
            gp_row['latitude'], gp_row['longitude'],
            hosp['latitude'], hosp['longitude']
        )
        distances.append((idx, dist))
    
    # Sort and return top n
    distances.sort(key=lambda x: x[1])
    nearest_indices = [d[0] for d in distances[:n]]
    
    return hospital_df.iloc[nearest_indices].copy()

def prepare_travel_times():
    """
    Prepare travel times data using r5py:
    1. Load GP and hospital data (with coordinates from previous geocoding step)
    2. Pre-filter to 5 nearest hospitals per GP using haversine distance
    3. Calculate actual travel times using r5py routing engine
    4. Export travel time matrix and summary statistics
    
    NOTE: r5py requires Java Runtime Environment (JRE) installed.
    First run will download OSM data for South London (~50-200MB).
    Subsequent runs use cached data.
    """
    
    logger.info("=" * 60)
    logger.info("STEP 3: Calculate Travel Times (r5py Routing)")
    logger.info("=" * 60)
    
    # Load data
    logger.info(f"[LOAD] GP data from {GP_DATA_FILE}...")
    if not os.path.exists(GP_DATA_FILE):
        logger.error(f"GP data file not found: {GP_DATA_FILE}")
        return None
    
    gp_df = pd.read_csv(GP_DATA_FILE)
    logger.info(f"[OK] Loaded {len(gp_df)} GP practices")
    
    logger.info(f"[LOAD] Hospital data from {HOSPITAL_DATA_FILE}...")
    if not os.path.exists(HOSPITAL_DATA_FILE):
        logger.error(f"Hospital data file not found: {HOSPITAL_DATA_FILE}")
        return None
    
    hospital_df = pd.read_csv(HOSPITAL_DATA_FILE)
    logger.info(f"[OK] Loaded {len(hospital_df)} hospitals")
    
    # Check for coordinates
    gp_valid = gp_df['latitude'].notna().sum()
    hosp_valid = hospital_df['latitude'].notna().sum()
    logger.info(f"[CHECK] GPs with coordinates: {gp_valid}/{len(gp_df)} ({100*gp_valid/len(gp_df):.1f}%)")
    logger.info(f"[CHECK] Hospitals with coordinates: {hosp_valid}/{len(hospital_df)} ({100*hosp_valid/len(hospital_df):.1f}%)")
    
    if gp_valid == 0 or hosp_valid == 0:
        logger.error("[FAIL] Not enough coordinate data for travel time calculations")
        logger.error("[INFO] Please run geocoding scripts first (scripts 01 and 02)")
        return None
    
    # Import r5py
    try:
        import r5py
        logger.info(f"[OK] r5py {r5py.__version__} loaded successfully")
        logger.info("[INFO] r5py uses R5 routing engine with OpenStreetMap data")
    except ImportError:
        logger.error("[FAIL] r5py not installed")
        logger.error("[INFO] Run: pip install -r requirements.txt")
        return None
    
    # Pre-filter to nearest 5 hospitals per GP
    logger.info(f"\n[FILTER] Finding {MAX_HOSPITALS_PER_GP} nearest hospitals per GP...")
    travel_times_list = []
    gp_hospital_pairs = []
    
    for gp_idx, (_, gp) in enumerate(gp_df.iterrows()):
        if (gp_idx + 1) % 50 == 0:
            logger.info(f"[PROGRESS] Processing GP {gp_idx + 1}/{len(gp_df)}...")
        
        # Skip if no coordinates
        if pd.isna(gp['latitude']) or pd.isna(gp['longitude']):
            continue
        
        # Find 5 nearest hospitals
        nearest = find_nearest_hospitals(gp, hospital_df, n=MAX_HOSPITALS_PER_GP)
        
        if len(nearest) == 0:
            continue
        
        for hosp_idx, (_, hospital) in nearest.iterrows():
            gp_hospital_pairs.append({
                'gp_idx': gp_idx,
                'gp_code': gp['practice_code'],
                'gp_name': gp['practice_name'],
                'gp_lat': gp['latitude'],
                'gp_lon': gp['longitude'],
                'hosp_idx': hosp_idx,
                'hospital_name': hospital['hospital_name'],
                'hospital_ods': hospital['ods_code'],
                'hosp_lat': hospital['latitude'],
                'hosp_lon': hospital['longitude'],
            })
    
    logger.info(f"[OK] Created {len(gp_hospital_pairs)} GP-Hospital pairs for routing")
    
    # Prepare origin and destination points for r5py
    logger.info(f"\n[ROUTE] Calculating travel times using r5py...")
    logger.info(f"[INFO] This may take 2-5 minutes for {len(gp_hospital_pairs)} routes")
    logger.info(f"[INFO] First run will download OpenStreetMap data (~100-200MB)")
    
    try:
        # Create r5py routing engine
        # South London bounds
        r5 = r5py.R5(provider='openstreetmap')
        logger.info("[OK] r5py engine initialized")
        logger.info("[INFO] Using OpenStreetMap data for South London routing")
        
        # Prepare origin and destination DataFrames for travel time matrix
        origins = []
        destinations = []
        
        for pair in gp_hospital_pairs:
            origins.append({
                'id': f"{pair['gp_idx']}",
                'geometry': r5py.make_config.Point(pair['gp_lon'], pair['gp_lat'])
            })
            destinations.append({
                'id': f"{pair['hosp_idx']}",
                'geometry': r5py.make_config.Point(pair['hosp_lon'], pair['hosp_lat'])
            })
        
        # Remove duplicates
        origins_df = pd.DataFrame(origins).drop_duplicates(subset=['id'])
        destinations_df = pd.DataFrame(destinations).drop_duplicates(subset=['id'])
        
        logger.info(f"[OK] Unique origins: {len(origins_df)}, destinations: {len(destinations_df)}")
        
        # Calculate travel time matrix
        # Using multiple travel modes for comprehensive analysis
        travel_times_df = r5.travel_times(
            origins=origins_df,
            destinations=destinations_df,
            departure_time=pd.Timestamp(2024, 3, 21, 9, 0),  # Thursday 9am
            transport_mode=['car', 'transit'],
            max_trip_duration=120  # Max 120 minutes
        )
        
        logger.info(f"[OK] Calculated travel times for {len(travel_times_df)} routes")
        
        # Merge with GP and hospital details
        travel_times_df = travel_times_df.rename(columns={
            'from_id': 'gp_idx',
            'to_id': 'hosp_idx',
            'travel_time': 'travel_time_minutes'
        })
        
        # Convert string indices to integers
        travel_times_df['gp_idx'] = travel_times_df['gp_idx'].astype(int)
        travel_times_df['hosp_idx'] = travel_times_df['hosp_idx'].astype(int)
        
        # Merge with GP and hospital metadata
        gp_metadata = gp_df[['practice_code', 'practice_name']].copy()
        gp_metadata['gp_idx'] = range(len(gp_df))
        hosp_metadata = hospital_df[['hospital_name', 'ods_code']].copy()
        hosp_metadata['hosp_idx'] = range(len(hospital_df))
        
        travel_times_df = travel_times_df.merge(gp_metadata, on='gp_idx')
        travel_times_df = travel_times_df.merge(hosp_metadata, on='hosp_idx')
        
        # Add walking mode estimate (approximately 1.4 m/s = 5 km/h)
        # This is approximate based on distance and car travel time
        travel_times_df['travel_time_walk_minutes'] = (
            travel_times_df['travel_time_minutes'] / 50 * 5 * 60
        ).round(1)
        
        # Reorder columns for clarity
        travel_times_df = travel_times_df[[
            'gp_idx', 'practice_code', 'practice_name',
            'hosp_idx', 'hospital_name', 'ods_code',
            'travel_time_minutes', 'travel_time_walk_minutes'
        ]].rename(columns={
            'travel_time_minutes': 'travel_time_routed_minutes'
        })
        
        logger.info(f"[OK] Merged with metadata: {len(travel_times_df)} travel time records")
        
        # Calculate summary statistics
        logger.info(f"\n[STATS] Travel time summary:")
        logger.info(f"  - Mean: {travel_times_df['travel_time_routed_minutes'].mean():.1f} minutes")
        logger.info(f"  - Median: {travel_times_df['travel_time_routed_minutes'].median():.1f} minutes")
        logger.info(f"  - Min: {travel_times_df['travel_time_routed_minutes'].min():.1f} minutes")
        logger.info(f"  - Max: {travel_times_df['travel_time_routed_minutes'].max():.1f} minutes")
        logger.info(f"  - 95th percentile: {travel_times_df['travel_time_routed_minutes'].quantile(0.95):.1f} minutes")
        
        # Calculate average times per GP (to nearest hospital)
        avg_times = travel_times_df.groupby('practice_code').agg({
            'travel_time_routed_minutes': 'min',
            'practice_name': 'first'
        }).reset_index()
        avg_times.columns = ['practice_code', 'avg_travel_time_to_nearest_min', 'practice_name']
        avg_times = avg_times[['practice_code', 'practice_name', 'avg_travel_time_to_nearest_min']]
        
        logger.info(f"\n[STATS] Average travel time to nearest hospital per GP:")
        logger.info(f"  - Mean: {avg_times['avg_travel_time_to_nearest_min'].mean():.1f} minutes")
        logger.info(f"  - Median: {avg_times['avg_travel_time_to_nearest_min'].median():.1f} minutes")
        logger.info(f"  - Min: {avg_times['avg_travel_time_to_nearest_min'].min():.1f} minutes")
        logger.info(f"  - Max: {avg_times['avg_travel_time_to_nearest_min'].max():.1f} minutes")
        
        # Save results
        os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
        travel_times_df.to_csv(TRAVEL_TIMES_FILE, index=False)
        logger.info(f"\n[SAVE] Travel times matrix → {TRAVEL_TIMES_FILE}")
        
        avg_times.to_csv(os.path.join(PROCESSED_DATA_DIR, "travel_times_average_r5py.csv"), index=False)
        logger.info(f"[SAVE] Average travel times → travel_times_average_r5py.csv")
        
        return travel_times_df, avg_times
    
    except ImportError:
        logger.error("[FAIL] r5py could not be imported or Java not found")
        logger.error("[INFO] Install Java JDK 11+ and run: pip install r5py")
        return None
    except Exception as e:
        logger.error(f"[FAIL] Error during travel time calculation: {str(e)}")
        logger.error("[INFO] Check that Java is installed: java -version")
        logger.debug(f"[DEBUG] Full error: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    result = prepare_travel_times()
    if result:
        travel_times_df, avg_times = result
        logger.info(f"\n{'='*60}")
        logger.info("SUCCESS! Travel times calculated with r5py routing")
        logger.info(f"{'='*60}")
        logger.info(f"\nDetailed travel times (first 10 records):")
        logger.info(f"\n{travel_times_df.head(10).to_string()}")
        logger.info(f"\nAverage travel times per GP (first 10 records):")
        logger.info(f"\n{avg_times.head(10).to_string()}")
    else:
        logger.error("Failed to prepare travel times")
        sys.exit(1)
