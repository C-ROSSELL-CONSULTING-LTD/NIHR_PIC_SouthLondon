"""
Script 03: Calculate travel times from GPs to destinations using TfL Journey API.
Supports three travel modes: Car, Public Transit, Walking.

Workflow:
    1. Load geocoded GP practices plus destination sites (hospitals + universities)
    2. Query TfL API for each GP→Destination pair
  3. Calculate travel time for each mode: car, public transit, walking
  4. Cache results to avoid re-querying
  5. Output: travel_times_optimized.csv with all three modes

Rate Limiting:
  - TfL allows 500 requests per minute
  - Uses asyncio + aiohttp with semaphore (8 concurrent requests)
  - Exponential backoff on 429 (rate limit) errors
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# Input files (already geocoded)
GP_FILE = os.path.join(PROCESSED_DATA_DIR, "gp_practices_geocoded.csv")
HOSPITAL_FILE = os.path.join(PROCESSED_DATA_DIR, "hospital_sites_geocoded.csv")
UNIVERSITY_FILE = os.path.join(PROCESSED_DATA_DIR, "universities_geocoded.csv")

# Output
OUTPUT_FILE = os.path.join(PROCESSED_DATA_DIR, "travel_times_optimized.csv")
CACHE_FILE = os.path.join(PROCESSED_DATA_DIR, "tfl_cache.json")

# TfL API Configuration
TFL_API_KEY = os.getenv("TFL_API_KEY", "b119b88e11354e31ada1bbd880a1e6c4")
TFL_API_URL = "https://api.tfl.gov.uk"
TFL_TIMEOUT_SECONDS = 30
TFL_SEMAPHORE_SIZE = 5  # 5 concurrent requests — stays safely under 500/min to avoid 429 rate limits

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# ============================================================================
# Utilities
# ============================================================================

def load_tfl_cache(path):
    """Load cached TfL results."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Corrupted cache file: {path} — starting fresh")
    return {}

_cache_lock = Lock()

def save_tfl_cache(path, cache):
    """Save cache atomically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = path + ".tmp"
    with _cache_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp_path, path)


def valid_journey_coverage(df):
    """Return fraction of rows with at least one valid travel time."""
    if df is None or df.empty:
        return 0.0

    mode_cols = [
        'travel_time_car_minutes',
        'travel_time_transit_minutes',
        'travel_time_walking_minutes',
        'closest_travel_minutes',
    ]
    available_cols = [c for c in mode_cols if c in df.columns]
    if not available_cols:
        return 0.0

    valid_mask = pd.Series(False, index=df.index)
    for col in available_cols:
        valid_mask = valid_mask | pd.to_numeric(df[col], errors='coerce').notna()

    return float(valid_mask.mean())


def nearest_wednesday_9am(now=None):
    """Return the nearest Wednesday at 09:00 as (YYYYMMDD, HHMM)."""
    current = now or datetime.now()
    target_weekday = 2  # Monday=0, Wednesday=2
    days_forward = (target_weekday - current.weekday()) % 7
    days_backward = (current.weekday() - target_weekday) % 7

    if days_forward < days_backward:
        target_date = current.date() + timedelta(days=days_forward)
    elif days_backward < days_forward:
        target_date = current.date() - timedelta(days=days_backward)
    else:
        target_date = current.date()

    target_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=9, minute=0)
    return target_dt.strftime("%Y%m%d"), target_dt.strftime("%H%M")

# ============================================================================
# TfL API
# ============================================================================

async def query_tfl_mode(session, from_coord, to_coord, mode, semaphore, max_retries=5):
    """Query TfL for a specific travel mode (Car, Transit, or Walking)."""
    from_str = f"{from_coord[0]},{from_coord[1]}"
    to_str = f"{to_coord[0]},{to_coord[1]}"
    
    url = f"{TFL_API_URL}/Journey/JourneyResults/{from_str}/to/{to_str}"
    
    # Map mode names to TfL parameters
    # Note: TfL uses "tube" not "underground"; "driving" is not supported by TfL
    mode_param_map = {
        "Transit": "bus,tube,overground,dlr,tram,national-rail",
        "Walking": "walking",
    }
    
    # Car is not supported by TfL Journey API — skip
    if mode == "Car":
        return None
    
    tfl_date, tfl_time = nearest_wednesday_9am()
    params = {
        "app_key": TFL_API_KEY,
        "date": tfl_date,
        "time": tfl_time,
        "timeIs": "Departing",
        "mode": mode_param_map.get(mode, "driving"),
    }
    
    timeout = aiohttp.ClientTimeout(total=TFL_TIMEOUT_SECONDS)
    wait_before = 0  # sleep OUTSIDE semaphore to avoid deadlock
    
    for attempt in range(max_retries):
        if wait_before > 0:
            await asyncio.sleep(wait_before)
        
        async with semaphore:
            try:
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 404:
                        return -1  # No route
                    
                    if response.status == 200:
                        data = await response.json()
                        journeys = data.get("journeys", [])
                        
                        if journeys:
                            minutes = min(j.get("duration", float("inf")) for j in journeys)
                            return float(minutes)
                        else:
                            return -1  # No journeys found
                    
                    if response.status == 429:  # Rate limited — sleep outside semaphore
                        wait_before = 10 * (2 ** attempt)
                        continue
                    
                    return None
                    
            except asyncio.TimeoutError:
                wait_before = 2 ** attempt
                continue
            
            except Exception:
                return None
    
    return None

# ============================================================================
# Main
# ============================================================================

def main():
    logger.info("=" * 80)
    logger.info("STEP 03: Calculate Travel Times (TfL API - 3 Modes)")
    logger.info("=" * 80)
    
    # Load data
    logger.info("\n[LOAD] Reading GP practices and destination sites...")
    
    if not os.path.exists(GP_FILE):
        logger.error(f"GP file not found: {GP_FILE}")
        return
    
    if not os.path.exists(HOSPITAL_FILE):
        logger.error(f"Hospital file not found: {HOSPITAL_FILE}")
        return

    if not os.path.exists(UNIVERSITY_FILE):
        logger.error(f"University file not found: {UNIVERSITY_FILE}")
        return
    
    gp_df = pd.read_csv(GP_FILE)
    hospital_df = pd.read_csv(HOSPITAL_FILE)
    university_df = pd.read_csv(UNIVERSITY_FILE)
    
    # Filter to valid coordinates
    gp_valid = gp_df[gp_df['latitude'].notna() & gp_df['longitude'].notna()].copy()
    hosp_valid = hospital_df[hospital_df['latitude'].notna() & hospital_df['longitude'].notna()].copy()
    uni_valid = university_df[university_df['latitude'].notna() & university_df['longitude'].notna()].copy()

    # Build unified destination table while preserving hospital metadata for downstream compatibility.
    hosp_destinations = hosp_valid.copy()
    hosp_destinations['destination_name'] = hosp_destinations['hospital_name']
    hosp_destinations['destination_type'] = 'Hospital'
    hosp_destinations['destination_group'] = hosp_destinations.get('trust', None)

    uni_destinations = uni_valid.copy()
    uni_destinations['destination_name'] = uni_destinations['university_name']
    uni_destinations['destination_type'] = 'University'
    uni_destinations['destination_group'] = None

    destination_df = pd.concat([hosp_destinations, uni_destinations], ignore_index=True)
    
    logger.info(f"[OK] Loaded {len(gp_valid)} GP practices (with coordinates)")
    logger.info(f"[OK] Loaded {len(hosp_valid)} hospital sites (with coordinates)")
    logger.info(f"[OK] Loaded {len(uni_valid)} university sites (with coordinates)")
    logger.info(f"[OK] Total destinations: {len(destination_df)}")
    
    if gp_valid.empty or destination_df.empty:
        logger.error("No valid coordinates found!")
        return
    
    # Load cache
    logger.info("\n[CACHE] Loading TfL journey cache...")
    tfl_cache = load_tfl_cache(CACHE_FILE)
    logger.info(f"[OK] Cache contains {len(tfl_cache)} queries")
    
    # Build work list
    work_items = []
    for gp_idx, gp_row in gp_valid.iterrows():
        for dest_idx, dest_row in destination_df.iterrows():
            gp_code = gp_row.get('practice_code_gp', str(gp_idx))
            dest_name = dest_row.get('destination_name', str(dest_idx))
            dest_type = dest_row.get('destination_type', 'Destination')
            cache_key = f"{gp_code}→{dest_type}:{dest_name}"
            
            # Skip if Transit and Walking both cached (Car is estimated, not queried)
            if cache_key in tfl_cache:
                existing = tfl_cache[cache_key]
                if all(mode in existing for mode in ['Transit', 'Walking']):
                    continue
            
            work_items.append({
                'gp_code': gp_code,
                'destination_name': dest_name,
                'destination_type': dest_type,
                'gp_lat': gp_row['latitude'],
                'gp_lon': gp_row['longitude'],
                'dest_lat': dest_row['latitude'],
                'dest_lon': dest_row['longitude'],
                'cache_key': cache_key,
            })
    
    total_queries = len(work_items) * 3
    logger.info(f"\n[QUERY] Need {len(work_items)} GP→Destination pairs ({total_queries} total mode queries)")
    
    if not work_items:
        logger.info("  All queries already cached!")
    else:
        # Run async queries
        async def run_queries():
            nonlocal tfl_cache
            
            semaphore = asyncio.Semaphore(TFL_SEMAPHORE_SIZE)
            connector = aiohttp.TCPConnector(
                limit=TFL_SEMAPHORE_SIZE * 3,
                limit_per_host=TFL_SEMAPHORE_SIZE * 3,
                ssl=True,
            )
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async def query_all_modes(item):
                    cache_key = item['cache_key']
                    
                    if cache_key not in tfl_cache:
                        tfl_cache[cache_key] = {}
                    
                    # Query Transit and Walking in parallel (Car is estimated via haversine)
                    modes_needed = [m for m in ['Transit', 'Walking'] if m not in tfl_cache[cache_key]]
                    
                    if modes_needed:
                        mode_tasks = [
                            query_tfl_mode(
                                session,
                                (item['gp_lat'], item['gp_lon']),
                                (item['dest_lat'], item['dest_lon']),
                                mode,
                                semaphore
                            )
                            for mode in modes_needed
                        ]
                        results = await asyncio.gather(*mode_tasks)
                        for mode, minutes in zip(modes_needed, results):
                            tfl_cache[cache_key][mode] = minutes
                    
                    return cache_key
                
                tasks = [query_all_modes(item) for item in work_items]
                completed = 0
                
                for coro in asyncio.as_completed(tasks):
                    try:
                        await coro
                        completed += 1
                        
                        if completed % 10 == 0 or completed <= 5:
                            logger.info(f"  {completed}/{len(work_items)} pairs done")
                        
                        if completed % 200 == 0:
                            try:
                                save_tfl_cache(CACHE_FILE, tfl_cache)
                                logger.info(f"    [checkpoint] Saved at {completed} pairs")
                            except Exception as e:
                                logger.error(f"    [ERROR] Cache save failed: {e}")
                    
                    except Exception as e:
                        logger.error(f"  Error: {e}")
        
        try:
            asyncio.run(run_queries())
            save_tfl_cache(CACHE_FILE, tfl_cache)
            logger.info(f"✓ TfL cache saved: {CACHE_FILE}")
        except Exception as e:
            logger.error(f"✗ Query failed: {e}")
            return
    
    # Build output
    logger.info("\n[OUTPUT] Building results dataset...")
    
    results = []
    for gp_idx, gp_row in gp_valid.iterrows():
        for dest_idx, dest_row in destination_df.iterrows():
            gp_code = gp_row.get('practice_code_gp', str(gp_idx))
            dest_name = dest_row.get('destination_name', str(dest_idx))
            dest_type = dest_row.get('destination_type', 'Destination')
            cache_key = f"{gp_code}→{dest_type}:{dest_name}"
            
            cached = tfl_cache.get(cache_key, {})
            
            # Car times are a placeholder for future integration (TfL does not support driving)
            car_time = None
            transit_time = cached.get('Transit')
            walk_time = cached.get('Walking')
            
            # Find closest mode
            times = {
                'car': car_time if isinstance(car_time, (int, float)) and car_time > 0 else None,
                'transit': transit_time if isinstance(transit_time, (int, float)) and transit_time > 0 else None,
                'walking': walk_time if isinstance(walk_time, (int, float)) and walk_time > 0 else None,
            }
            closest_mode = min((k for k in times if times[k] is not None), key=lambda k: times[k], default=None)
            closest_time = times[closest_mode] if closest_mode else None
            
            results.append({
                'practice_code': gp_code,
                'practice_name': gp_row.get('practice_name', 'Unknown'),
                'destination_name': dest_name,
                'destination_type': dest_type,
                'destination_group': dest_row.get('destination_group'),
                'hospital_name': dest_name if dest_type == 'Hospital' else None,
                'hospital_trust': dest_row.get('trust', 'Unknown') if dest_type == 'Hospital' else None,
                'travel_time_car_minutes': car_time if isinstance(car_time, (int, float)) and car_time > 0 else None,
                'travel_time_transit_minutes': transit_time if isinstance(transit_time, (int, float)) and transit_time > 0 else None,
                'travel_time_walking_minutes': walk_time if isinstance(walk_time, (int, float)) and walk_time > 0 else None,
                'closest_travel_mode': closest_mode.upper() if closest_mode else None,
                'closest_travel_minutes': closest_time,
            })
    
    result_df = pd.DataFrame(results)
    
    logger.info(f"[SAVE] Writing {len(result_df)} results to CSV...")

    # Guard against accidental wipe: do not replace an existing dataset with near-empty times.
    new_coverage = valid_journey_coverage(result_df)
    existing_df = None
    existing_coverage = 0.0
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            existing_coverage = valid_journey_coverage(existing_df)
        except Exception as e:
            logger.warning(f"Could not read existing output for safeguard check: {e}")

    if existing_df is not None and existing_coverage > 0.50 and new_coverage < 0.10:
        logger.error(
            "[SAFEGUARD] New travel times are mostly empty "
            f"(coverage {new_coverage:.1%}) while existing output has data "
            f"(coverage {existing_coverage:.1%}). Keeping existing file."
        )
        return

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)

    key_cols = ['practice_code', 'destination_name', 'destination_type']
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
        except Exception as e:
            logger.warning(f"Could not read existing output for append-only write: {e}")
            existing_df = pd.DataFrame()

        if not existing_df.empty and all(col in existing_df.columns for col in key_cols):
            existing_keys = set(existing_df[key_cols].astype(str).itertuples(index=False, name=None))
        else:
            existing_keys = set()

        new_mask = ~result_df[key_cols].astype(str).apply(tuple, axis=1).isin(existing_keys)
        append_df = result_df[new_mask].copy()

        if append_df.empty:
            logger.info("[OK] No new rows to append; existing file unchanged")
        else:
            append_df.to_csv(OUTPUT_FILE, mode='a', index=False, header=False)
            logger.info(f"[OK] Appended {len(append_df)} new rows to: {OUTPUT_FILE}")
    else:
        result_df.to_csv(OUTPUT_FILE, index=False)
        logger.info(f"[OK] Created and saved: {OUTPUT_FILE}")
    
    # Statistics
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total GP→Destination pairs:     {len(result_df)}")
    if 'destination_type' in result_df.columns:
        logger.info("\nPairs by destination type:")
        print(result_df['destination_type'].value_counts().to_string())
    
    for mode, col in [('Car', 'travel_time_car_minutes'), 
                      ('Transit', 'travel_time_transit_minutes'),
                      ('Walking', 'travel_time_walking_minutes')]:
        valid = result_df[result_df[col].notna()]
        if len(valid) > 0:
            logger.info(f"\n{mode}:")
            logger.info(f"  Valid results:  {len(valid):,} ({100*len(valid)/len(result_df):.1f}%)")
            logger.info(f"  Mean time:      {valid[col].mean():.1f} min")
            logger.info(f"  Median time:    {valid[col].median():.1f} min")
            logger.info(f"  Min - Max:      {valid[col].min():.1f} - {valid[col].max():.1f} min")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ TRAVEL TIMES COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
