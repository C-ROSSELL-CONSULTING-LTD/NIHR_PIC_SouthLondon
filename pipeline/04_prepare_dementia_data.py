"""
Script 4: Prepare dementia prevalence data for visualization.
Sources:
  - DementiaSurveillanceData.csv and Metadata
"""

import pandas as pd
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROCESSED_DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_dementia_data():
    """
    Prepare dementia prevalence data:
    1. Load dementia surveillance data
    2. Clean and standardize
    """
    
    logger.info("=" * 60)
    logger.info("STEP 4: Prepare Dementia Prevalence Data")
    logger.info("=" * 60)
    
    # Load dementia data from project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)  # NIHR_PIC_SouthLondon/
    
    data_files = {
        "dementia_data": os.path.join(project_dir, "data", "archive", "DementiaSurveillanceData.csv"),
        "dementia_metadata": os.path.join(project_dir, "data", "archive", "DementiaSurveillanceMetadata.csv"),
    }
    
    # Try to load available data
    dementia_dfs = {}
    for name, path in data_files.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                dementia_dfs[name] = df
                logger.info(f"Loaded {name}: {len(df)} rows, {len(df.columns)} columns")
                logger.info(f"  Columns: {list(df.columns)[:5]}...")
            except Exception as e:
                logger.warning(f"Could not load {name}: {e}")
        else:
            logger.warning(f"File not found: {path}")
    
    # If we have multimorbidity data, use that
    practice_data_path = os.path.join(project_dir, "data", "processed", "practice_data_cleaned.csv")
    if os.path.exists(practice_data_path):
        logger.info(f"Loading practice dementia data from {practice_data_path}...")
        try:
            practice_df = pd.read_csv(practice_data_path)
            
            # Extract practice-level dementia info with dementia registers and patient lists
            dementia_summary = practice_df[[
                'PRACTICE_CODE', 'PRACTICE_NAME', 
                'DEMENTIA_REGISTER_0_64', 'DEMENTIA_REGISTER_65_PLUS',
                'PAT_LIST_0_64', 'PAT_LIST_65_PLUS'
            ]].drop_duplicates()
            
            # Convert to numeric
            for col in ['DEMENTIA_REGISTER_0_64', 'DEMENTIA_REGISTER_65_PLUS', 'PAT_LIST_0_64', 'PAT_LIST_65_PLUS']:
                dementia_summary[col] = pd.to_numeric(dementia_summary[col], errors='coerce')
            
            # Calculate total population and prevalence percentages
            dementia_summary['TOTAL_POPULATION'] = (
                pd.to_numeric(dementia_summary['PAT_LIST_0_64'], errors='coerce').fillna(0) +
                pd.to_numeric(dementia_summary['PAT_LIST_65_PLUS'], errors='coerce').fillna(0)
            )
            
            dementia_summary['DEMENTIA_REGISTER_TOTAL'] = (
                pd.to_numeric(dementia_summary['DEMENTIA_REGISTER_0_64'], errors='coerce').fillna(0) +
                pd.to_numeric(dementia_summary['DEMENTIA_REGISTER_65_PLUS'], errors='coerce').fillna(0)
            )
            
            # Calculate prevalence percentages (safe division)
            dementia_summary['DEMENTIA_PREVALENCE_0_64_PCT'] = dementia_summary.apply(
                lambda row: (row['DEMENTIA_REGISTER_0_64'] / row['PAT_LIST_0_64'] * 100) 
                if pd.notna(row['PAT_LIST_0_64']) and row['PAT_LIST_0_64'] > 0 else None,
                axis=1
            )
            
            dementia_summary['DEMENTIA_PREVALENCE_65PLUS_PCT'] = dementia_summary.apply(
                lambda row: (row['DEMENTIA_REGISTER_65_PLUS'] / row['PAT_LIST_65_PLUS'] * 100) 
                if pd.notna(row['PAT_LIST_65_PLUS']) and row['PAT_LIST_65_PLUS'] > 0 else None,
                axis=1
            )
            
            dementia_summary['DEMENTIA_PREVALENCE_TOTAL_PCT'] = dementia_summary.apply(
                lambda row: (row['DEMENTIA_REGISTER_TOTAL'] / row['TOTAL_POPULATION'] * 100) 
                if row['TOTAL_POPULATION'] > 0 else None,
                axis=1
            )
            
            logger.info(f"Found {len(dementia_summary)} unique practices with dementia data")
            logger.info(f"Calculated prevalence percentages and total population:")
            logger.info(f"  - Practices with 0-64 prevalence: {dementia_summary['DEMENTIA_PREVALENCE_0_64_PCT'].notna().sum()}")
            logger.info(f"  - Practices with 65+ prevalence: {dementia_summary['DEMENTIA_PREVALENCE_65PLUS_PCT'].notna().sum()}")
            logger.info(f"  - Practices with total prevalence: {dementia_summary['DEMENTIA_PREVALENCE_TOTAL_PCT'].notna().sum()}")
            
            # Save practice-level data
            output_path = os.path.join(PROCESSED_DATA_DIR, "dementia_by_practice.csv")
            os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
            dementia_summary.to_csv(output_path, index=False)
            logger.info(f"Saved practice-level dementia data to {output_path}")
            
            return dementia_summary
            
        except Exception as e:
            logger.error(f"Error processing dementia data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    logger.warning("No practice-level dementia data found")
    return None

if __name__ == "__main__":
    dementia_data = prepare_dementia_data()
    if dementia_data is not None:
        logger.info(f"\nSuccess! Prepared dementia data")
        logger.info(f"\nSample:\n{dementia_data.head()}")
    else:
        logger.warning("Could not prepare dementia data - will proceed with limited data")
