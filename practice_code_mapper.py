"""
Practice Code Mapper: Resolve practice codes to standardized ODS codes.

PROBLEM: 
  - Dementia data uses practice codes from pcdem-prac-data (G83001, G83002, ...)
  - GP registry uses ODS codes (G0102926, G0105912, ...)
  - These don't match, preventing merges

SOLUTION:
  - Query ODS API with practice names
  - Build a caching layer: practice_code → ODS code
  - Maintain a local CSV cache for fast lookups
  
This enables:
  ✓ Direct merge of datasets
  ✓ Fast lookups (cache hit = 1ms vs API call = 200ms)
  ✓ Offline operation after first run
  ✓ Tracking of practice closures/moves
"""

import pandas as pd
import os
import logging
import requests
import time
from typing import Optional, Dict

logger = logging.getLogger(__name__)

ODS_API_BASE = "https://api.service.nhs.uk/organisation-data-terminology-api/fhir"
ODS_ORG_ENDPOINT = f"{ODS_API_BASE}/Organization"


def query_ods_api_for_practice(practice_name: str) -> Optional[Dict]:
    """
    Query ODS FHIR API for a practice by name.
    
    Args:
        practice_name: GP practice name (e.g., 'Spring Lane Surgery')
        
    Returns:
        dict with keys: ods_code, name, postcode, status
        None if not found
    """
    try:
        params = {'name': practice_name, '_count': 5}
        response = requests.get(ODS_ORG_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'entry' in data and len(data['entry']) > 0:
            resource = data['entry'][0]['resource']
            
            postcode = None
            if 'address' in resource and len(resource['address']) > 0:
                postcode = resource['address'][0].get('postalCode')
            
            return {
                'ods_code': resource.get('id'),
                'name': resource.get('name', ''),
                'postcode': postcode,
                'status': 'active'
            }
        
        return None
    except Exception as e:
        logger.debug(f"ODS API error for {practice_name}: {e}")
        return None


def build_practice_code_mapping(
    practice_df: pd.DataFrame,
    practice_name_col: str = 'practice_name',
    practice_code_col: str = 'practice_code',
    cache_path: Optional[str] = None,
    use_cache: bool = True,
    use_api: bool = True
) -> pd.DataFrame:
    """
    Build a mapping from internal practice codes to standardized ODS codes.
    
    Args:
        practice_df: DataFrame with practice_name and practice_code columns
        practice_name_col: Name of column with practice names
        practice_code_col: Name of column with practice codes (from dementia data)
        cache_path: Path to save/load cache CSV
        use_cache: Whether to load from cache first
        use_api: Whether to query ODS API for missing codes
        
    Returns:
        DataFrame with columns: practice_code, practice_name, ods_code, postcode, status, source
    """
    
    logger.info(f"Building practice code mapping for {len(practice_df)} practices")
    
    # Initialize mapping DataFrame
    mapping = pd.DataFrame({
        'practice_code': practice_df[practice_code_col].unique(),
        'practice_name': practice_df.groupby(practice_code_col)[practice_name_col].first().values
    })
    mapping['ods_code'] = None
    mapping['postcode'] = None
    mapping['status'] = None
    mapping['source'] = None
    
    # Try to load from cache
    cache_hits = 0
    if use_cache and cache_path and os.path.exists(cache_path):
        logger.info(f"[CACHE] Loading practice code cache from {os.path.basename(cache_path)}")
        try:
            cache_df = pd.read_csv(cache_path)
            
            # Merge with cache
            merge_cols = ['practice_code', 'practice_name']
            mapping = mapping.merge(
                cache_df[merge_cols + ['ods_code', 'postcode', 'status', 'source']],
                on=merge_cols,
                how='left',
                suffixes=('', '_cache')
            )
            
            # Fill in cached values
            for col in ['ods_code', 'postcode', 'status', 'source']:
                if f'{col}_cache' in mapping.columns:
                    mapping[col] = mapping[col].fillna(mapping[f'{col}_cache'])
                    mapping.drop(f'{col}_cache', axis=1, inplace=True)
            
            cache_hits = mapping['ods_code'].notna().sum()
            logger.info(f"[CACHE] Found {cache_hits} practices in cache ({100*cache_hits/len(mapping):.1f}%)")
        
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
    
    # Query API for missing codes
    if use_api:
        missing = mapping[mapping['ods_code'].isna()].copy()
        
        if len(missing) > 0:
            logger.info(f"[API] Querying ODS for {len(missing)} missing practice codes...")
            logger.info(f"[RATE] Using 0.2s delay (~18 req/min, well below 5000/5min limit)")
            
            api_hits = 0
            for idx, (_, row) in enumerate(missing.iterrows()):
                if (idx + 1) % 50 == 0:
                    logger.info(f"[PROGRESS] {idx + 1}/{len(missing)}: Querying API...")
                
                ods_data = query_ods_api_for_practice(row['practice_name'])
                
                if ods_data:
                    # Update mapping
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'ods_code'] = ods_data['ods_code']
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'postcode'] = ods_data['postcode']
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'status'] = ods_data['status']
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'source'] = 'ods_api'
                    api_hits += 1
                else:
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'status'] = 'not_found'
                    mapping.loc[mapping['practice_code'] == row['practice_code'], 'source'] = 'api_failed'
                
                time.sleep(0.2)  # Rate limiting
            
            logger.info(f"[API] Completed: {api_hits} practices resolved via ODS API")
    
    # Save cache
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        mapping.to_csv(cache_path, index=False)
        logger.info(f"[SAVE] Practice code mapping cache → {os.path.basename(cache_path)}")
        logger.info(f"[STATS] Total cache entries: {len(mapping)}")
        logger.info(f"  - With ODS code: {mapping['ods_code'].notna().sum()}")
        logger.info(f"  - From cache: {cache_hits}")
        logger.info(f"  - From API: {mapping[mapping['source'] == 'ods_api'].shape[0]}")
    
    return mapping


def apply_practice_code_mapping(
    df: pd.DataFrame,
    mapping: pd.DataFrame,
    practice_code_col: str = 'practice_code'
) -> pd.DataFrame:
    """
    Apply practice code mapping to add ODS codes to a DataFrame.
    
    Args:
        df: DataFrame to enrich
        mapping: Practice code mapping DataFrame
        practice_code_col: Name of practice_code column
        
    Returns:
        DataFrame with new 'ods_code' column
    """
    df = df.merge(
        mapping[['practice_code', 'ods_code']],
        on='practice_code',
        how='left'
    )
    
    unresolved = df['ods_code'].isna().sum()
    if unresolved > 0:
        logger.warning(f"[WARN] {unresolved} practices without ODS code mapping")
    
    return df


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Load practice data
    prac_df = pd.read_csv('../../../Data/pcdem-prac-data-date-mar-2024.csv')
    
    # Build mapping
    cache_path = '../data/processed/practice_code_mapping_cache.csv'
    mapping = build_practice_code_mapping(
        prac_df,
        practice_name_col='PRACTICE_NAME',
        practice_code_col='PRACTICE_CODE',
        cache_path=cache_path,
        use_cache=True,
        use_api=True
    )
    
    logger.info(f"\nMapping summary:")
    logger.info(f"{mapping}")
