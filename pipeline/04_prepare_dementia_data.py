"""
Script 4: Prepare dementia prevalence data for visualization.
Sources:
  - DementiaSurveillanceData.csv and Metadata
  - LSOA-level disease prevalence from PHE
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
    3. Prepare for LSOA-level overlay mapping
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
    pcdem_data_path = os.path.join(project_dir, "data", "archive", "pcdem-prac-data-date-mar-2024.csv")
    if os.path.exists(pcdem_data_path):
        logger.info(f"Loading practice dementia data from {pcdem_data_path}...")
        try:
            pcdem_df = pd.read_csv(pcdem_data_path)
            
            # Extract practice-level dementia info if available
            dementia_summary = pcdem_df[[
                'PRACTICE_CODE', 'PRACTICE_NAME', 'ICB_NAME', 
                'LATEST_DATA_SUBMISSION'
            ]].drop_duplicates()
            
            logger.info(f"Found {len(dementia_summary)} unique practices with dementia data")
            
            # Save practice-level data
            output_path = os.path.join(PROCESSED_DATA_DIR, "dementia_by_practice.csv")
            os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
            dementia_summary.to_csv(output_path, index=False)
            logger.info(f"Saved practice-level dementia data to {output_path}")
            
            return dementia_summary
            
        except Exception as e:
            logger.error(f"Error processing dementia data: {e}")
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
