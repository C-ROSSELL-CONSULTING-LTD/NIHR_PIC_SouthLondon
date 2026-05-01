"""
Geocoding utilities using multiple free services.
Tries Nominatim (OSM) first, falls back to geopy options if needed.
"""

import logging
from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize geocoders
nominatim = Nominatim(user_agent="nihr_pic_southlondon_app")

def geocode_address(address, attempt=1, max_attempts=3):
    """
    Geocode an address using Nominatim (OpenStreetMap) with retry logic.
    
    Args:
        address (str): Full address string to geocode
        attempt (int): Current attempt number
        max_attempts (int): Maximum number of retry attempts
        
    Returns:
        tuple: (latitude, longitude) or (None, None) if failed
    """
    try:
        location = nominatim.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        else:
            logger.warning(f"No result found for: {address}")
            return (None, None)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        if attempt < max_attempts:
            wait = 10 * attempt  # 10s, 20s backoff for rate limits
            logger.info(f"Attempt {attempt} failed for {address}, retrying in {wait}s... ({str(e)})")
            time.sleep(wait)
            return geocode_address(address, attempt + 1, max_attempts)
        else:
            logger.error(f"Failed to geocode {address} after {max_attempts} attempts: {str(e)}")
            return (None, None)
    except Exception as e:
        logger.error(f"Unexpected error geocoding {address}: {str(e)}")
        return (None, None)

def geocode_dataframe(df, address_column, batch_log_interval=50):
    """
    Geocode a dataframe column containing addresses.
    
    Args:
        df (pd.DataFrame): DataFrame with addresses
        address_column (str): Name of column containing addresses
        batch_log_interval (int): Log progress every N addresses
        
    Returns:
        pd.DataFrame: DataFrame with added latitude and longitude columns
    """
    df = df.copy()
    df['latitude'] = None
    df['longitude'] = None
    
    total = len(df)
    for idx, address in enumerate(df[address_column]):
        if pd.isna(address) or address == "":
            logger.warning(f"Row {idx}: Empty address")
            continue
            
        lat, lon = geocode_address(address)
        df.at[idx, 'latitude'] = lat
        df.at[idx, 'longitude'] = lon
        
        if (idx + 1) % batch_log_interval == 0:
            logger.info(f"Geocoded {idx + 1}/{total} addresses ({(idx + 1) / total * 100:.1f}%)")
        time.sleep(1.1)  # Nominatim policy: max 1 request/second
    
    logger.info(f"Geocoding complete: {df['latitude'].notna().sum()}/{total} successful")
    return df

def create_full_address(row):
    """
    Create a full address string from address components.
    
    Args:
        row (pd.Series): Row with address components
        
    Returns:
        str: Full address string
    """
    parts = []
    for col in ['Address Line 1', 'Address Line 2', 'Address Line 3', 
                'Address Line 4', 'Address Line 5']:
        if col in row and pd.notna(row[col]) and row[col] != "":
            parts.append(str(row[col]))
    
    if 'Postcode' in row and pd.notna(row['Postcode']):
        parts.append(str(row['Postcode']))
    
    return ", ".join(parts)
