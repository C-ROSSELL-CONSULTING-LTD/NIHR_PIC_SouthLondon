"""
Script 02b: Aggregate practices by MSOA and create density choropleth visualization.

Workflow:
  1. Load gp_practices_msoa.csv from Script 02
  2. Aggregate dementia counts by MSOA
  3. Load MSOA 2021 GeoJSON boundaries
  4. Calculate MSOA area (km²) and density (counts per km²)
  5. Visualize:
     - MSOA choropleth layer (colored by density to account for MAUP)
     - GP practice markers with popups showing practice name + dementia count
     - Hospital location markers
  6. Output: HTML map + summary CSV
"""

import pandas as pd
import geopandas as gpd
import folium
import json
import logging
import sys
import os
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

INPUT_PRACTICES_FILE = os.path.join(PROCESSED_DATA_DIR, "gp_practices_msoa.csv")
INPUT_HOSPITALS_FILE = os.path.join(PROCESSED_DATA_DIR, "hospital_sites_geocoded.csv")
MSOA_GEOJSON = str(BOUNDARIES_DIR / "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BSC_V3_1633701655676791957.geojson")


OUTPUT_MAP_HTML = os.path.join(PROCESSED_DATA_DIR, "msoa_dementia_map.html")
OUTPUT_MSOA_SUMMARY = os.path.join(PROCESSED_DATA_DIR, "msoa_dementia_summary.csv")

def calculate_msoa_density():
    """
    Main workflow:
    1. Load and aggregate practice data by MSOA
    2. Load MSOA boundaries
    3. Calculate density (counts per km²)
    4. Create choropleth map with practice markers
    """
    
    logger.info("=" * 70)
    logger.info("STEP 02b: MSOA Aggregation & Density Visualization")
    logger.info("=" * 70)
    
    # Load practice data
    logger.info(f"\n[LOAD] Reading {INPUT_PRACTICES_FILE}...")
    if not os.path.exists(INPUT_PRACTICES_FILE):
        logger.error(f"[ERROR] File not found: {INPUT_PRACTICES_FILE}")
        logger.error("[HINT] Run Script 02 first to prepare MSOA-matched practice data")
        return None
    
    practices_df = pd.read_csv(INPUT_PRACTICES_FILE)
    logger.info(f"[OK] Loaded {len(practices_df)} practices")
    
    # Filter to the 2 South London ICBs
    south_london_icbs = ['72Q', '36L']  # SEL and SWL
    practices_df = practices_df[practices_df['SUB_ICB_ODS_CODE'].isin(south_london_icbs)].copy()
    logger.info(f"[FILTER] Filtered to {len(practices_df)} practices in South London ICBs")
    
    # Aggregate by MSOA
    logger.info(f"\n[AGGREGATE] Aggregating dementia counts by MSOA...")
    
    agg_cols = ['DEMENTIA_REGISTER_0_64', 'DEMENTIA_REGISTER_65_PLUS', 'PAT_LIST_0_64', 'PAT_LIST_65_PLUS']
    existing_cols = [col for col in agg_cols if col in practices_df.columns]
    
    agg_dict = {col: 'sum' for col in existing_cols}
    agg_dict['PRACTICE_NAME'] = 'count'  # Count practices per MSOA
    
    msoa_summary = practices_df.groupby('MSOA21CD', as_index=False).agg(agg_dict)
    msoa_summary.rename(columns={'PRACTICE_NAME': 'practice_count'}, inplace=True)
    
    # Calculate totals
    if 'DEMENTIA_REGISTER_0_64' in msoa_summary.columns and 'DEMENTIA_REGISTER_65_PLUS' in msoa_summary.columns:
        msoa_summary['total_dementia'] = msoa_summary['DEMENTIA_REGISTER_0_64'] + msoa_summary['DEMENTIA_REGISTER_65_PLUS']
    else:
        msoa_summary['total_dementia'] = 0
    
    if 'PAT_LIST_0_64' in msoa_summary.columns and 'PAT_LIST_65_PLUS' in msoa_summary.columns:
        msoa_summary['total_registered'] = msoa_summary['PAT_LIST_0_64'] + msoa_summary['PAT_LIST_65_PLUS']
    else:
        msoa_summary['total_registered'] = 0
    
    logger.info(f"[OK] Aggregated to {len(msoa_summary)} MSOAs with dementia data")
    
    # Load MSOA boundaries
    logger.info(f"\n[LOAD] Reading MSOA boundaries from {MSOA_GEOJSON}...")
    try:
        msoa_gdf = gpd.read_file(MSOA_GEOJSON)
        logger.info(f"[OK] Loaded {len(msoa_gdf)} MSOA")
    except Exception as e:
        logger.error(f"[ERROR] Failed to load MSOA boundaries: {str(e)}")
        logger.error("[HINT] Check file format or path")
        return None
    
    # Calculate area in km²
    # First, project to British National Grid (EPSG:27700) for accurate area calculation
    msoa_gdf = msoa_gdf.to_crs(epsg=27700)
    msoa_gdf['area_km2'] = msoa_gdf.geometry.area / 1e6  # Convert m² to km²
    msoa_gdf = msoa_gdf.to_crs(epsg=4326)  # Convert back to WGS84 for mapping
    
    # Merge summaries with geometries
    logger.info(f"\n[MERGE] Merging dementia data with MSOA boundaries...")
    
    # Rename MSOA column in GeoDataFrame if needed
    if 'MSOA21CD' not in msoa_gdf.columns and 'msoa21cd' in msoa_gdf.columns:
        msoa_gdf.rename(columns={'msoa21cd': 'MSOA21CD'}, inplace=True)
    
    # Merge only MSOA boundaries that have South London practice data (inner join)
    msoa_combined = msoa_gdf.merge(
        msoa_summary,
        on='MSOA21CD',
        how='inner'
    )
    logger.info(f"[FILTER] Retained {len(msoa_combined)} MSOAs with South London practices (from {len(msoa_gdf)} total)")
    
    # Calculate density
    logger.info(f"\n[DENSITY] Calculating dementia density (counts per km²)...")
    
    if 'DEMENTIA_REGISTER_65_PLUS' in msoa_combined.columns:
        msoa_combined['density_65plus'] = msoa_combined['DEMENTIA_REGISTER_65_PLUS'] / msoa_combined['area_km2']
        msoa_combined['density_65plus'] = msoa_combined['density_65plus'].fillna(0).replace([float('inf'), float('-inf')], 0)
    else:
        msoa_combined['density_65plus'] = 0
    
    if 'DEMENTIA_REGISTER_0_64' in msoa_combined.columns:
        msoa_combined['density_0_64'] = msoa_combined['DEMENTIA_REGISTER_0_64'] / msoa_combined['area_km2']
        msoa_combined['density_0_64'] = msoa_combined['density_0_64'].fillna(0).replace([float('inf'), float('-inf')], 0)
    else:
        msoa_combined['density_0_64'] = 0
    
    if 'total_dementia' in msoa_combined.columns:
        msoa_combined['density_total'] = msoa_combined['total_dementia'] / msoa_combined['area_km2']
        msoa_combined['density_total'] = msoa_combined['density_total'].fillna(0).replace([float('inf'), float('-inf')], 0)
    else:
        msoa_combined['density_total'] = 0
    
    logger.info(f"[OK] Density calculated")
    
    # Save summary
    output_cols = ['MSOA21CD', 'practice_count', 'DEMENTIA_REGISTER_65_PLUS', 
                   'DEMENTIA_REGISTER_0_64', 'total_dementia', 'total_registered',
                   'area_km2', 'density_65plus', 'density_0_64', 'density_total']
    summary_out = msoa_combined[[col for col in output_cols if col in msoa_combined.columns]].copy()
    summary_out.to_csv(OUTPUT_MSOA_SUMMARY, index=False)
    logger.info(f"\n[SAVE] MSOA summary saved to {OUTPUT_MSOA_SUMMARY}")
    
    # Create map
    logger.info(f"\n[MAP] Creating interactive map...")
    
    # Center map on South London
    map_center = [51.4, -0.1]
    m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB positron')
    
    # Convert gdf to GeoJSON for Folium (it needs proper feature collection)
    geojson_data = json.loads(msoa_combined.to_json())
    
    # Add MSOA choropleth layers with popups (toggable)
    logger.info(f"  [LAYER] Adding MSOA choropleth layers (65+, 0-64, total)...")
    
    # For each feature, add popup data
    for feature in geojson_data['features']:
        msoa_cd = feature['properties']['MSOA21CD']
        row_data = msoa_combined[msoa_combined['MSOA21CD'] == msoa_cd]
        if len(row_data) > 0:
            row = row_data.iloc[0]
            feature['properties']['popup_65'] = f"""<b>MSOA: {msoa_cd}</b><br><hr><b>Dementia (65+)</b><br>Count: {int(row.get('DEMENTIA_REGISTER_65_PLUS', 0))}<br>Density: {row.get('density_65plus', 0):.2f} per km²<br>Area: {row.get('area_km2', 0):.2f} km²<br>Practices: {int(row.get('practice_count', 0))}"""
            feature['properties']['popup_0_64'] = f"""<b>MSOA: {msoa_cd}</b><br><hr><b>Dementia (0-64)</b><br>Count: {int(row.get('DEMENTIA_REGISTER_0_64', 0))}<br>Density: {row.get('density_0_64', 0):.2f} per km²<br>Area: {row.get('area_km2', 0):.2f} km²<br>Practices: {int(row.get('practice_count', 0))}"""
            feature['properties']['popup_total'] = f"""<b>MSOA: {msoa_cd}</b><br><hr><b>Total Dementia</b><br>Count: {int(row.get('total_dementia', 0))}<br>Density: {row.get('density_total', 0):.2f} per km²<br>Area: {row.get('area_km2', 0):.2f} km²<br>Practices: {int(row.get('practice_count', 0))}"""
    
    # Layer 1: Dementia Density (65+)
    def style_65plus(feature):
        msoa_cd = feature['properties']['MSOA21CD']
        value = msoa_combined[msoa_combined['MSOA21CD'] == msoa_cd]['density_65plus'].values
        value = value[0] if len(value) > 0 else 0
        if pd.isna(value) or value == 0:
            return {'fillColor': '#cccccc', 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
        # Normalize and get color
        vmin = msoa_combined['density_65plus'].min()
        vmax = msoa_combined['density_65plus'].max()
        norm_val = (value - vmin) / (vmax - vmin) if vmax > vmin else 0
        # YlOrRd colormap approximation
        if norm_val < 0.25:
            color = '#ffffcc'
        elif norm_val < 0.5:
            color = '#ffeda0'
        elif norm_val < 0.75:
            color = '#fc4e2a'
        else:
            color = '#b10026'
        return {'fillColor': color, 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
    
    fg_65plus = folium.FeatureGroup(name='Dementia Density (65+)', show=True)
    folium.GeoJson(
        geojson_data,
        style_function=style_65plus,
        tooltip=folium.GeoJsonTooltip(fields=['MSOA21CD', 'density_65plus'])
    ).add_child(folium.Popup(field='popup_65')).add_to(fg_65plus)
    fg_65plus.add_to(m)
    
    # Layer 2: Dementia Density (0-64)
    def style_0_64(feature):
        msoa_cd = feature['properties']['MSOA21CD']
        value = msoa_combined[msoa_combined['MSOA21CD'] == msoa_cd]['density_0_64'].values
        value = value[0] if len(value) > 0 else 0
        if pd.isna(value) or value == 0:
            return {'fillColor': '#cccccc', 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
        vmin = msoa_combined['density_0_64'].min()
        vmax = msoa_combined['density_0_64'].max()
        norm_val = (value - vmin) / (vmax - vmin) if vmax > vmin else 0
        # YlGnBu colormap approximation
        if norm_val < 0.25:
            color = '#ffffcc'
        elif norm_val < 0.5:
            color = '#a1dab4'
        elif norm_val < 0.75:
            color = '#41b6c4'
        else:
            color = '#225ea8'
        return {'fillColor': color, 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
    
    fg_0_64 = folium.FeatureGroup(name='Dementia Density (0-64)', show=False)
    folium.GeoJson(
        geojson_data,
        style_function=style_0_64,
        tooltip=folium.GeoJsonTooltip(fields=['MSOA21CD', 'density_0_64'])
    ).add_child(folium.Popup(field='popup_0_64')).add_to(fg_0_64)
    fg_0_64.add_to(m)
    
    # Layer 3: Total Dementia Density
    def style_total(feature):
        msoa_cd = feature['properties']['MSOA21CD']
        value = msoa_combined[msoa_combined['MSOA21CD'] == msoa_cd]['density_total'].values
        value = value[0] if len(value) > 0 else 0
        if pd.isna(value) or value == 0:
            return {'fillColor': '#cccccc', 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
        vmin = msoa_combined['density_total'].min()
        vmax = msoa_combined['density_total'].max()
        norm_val = (value - vmin) / (vmax - vmin) if vmax > vmin else 0
        # RdPu colormap approximation
        if norm_val < 0.25:
            color = '#feebe2'
        elif norm_val < 0.5:
            color = '#fbb4b9'
        elif norm_val < 0.75:
            color = '#f768a1'
        else:
            color = '#ae017e'
        return {'fillColor': color, 'color': 'none', 'weight': 0, 'fillOpacity': 0.7}
    
    fg_total = folium.FeatureGroup(name='Dementia Density (Total)', show=False)
    folium.GeoJson(
        geojson_data,
        style_function=style_total,
        tooltip=folium.GeoJsonTooltip(fields=['MSOA21CD', 'density_total'])
    ).add_child(folium.Popup(field='popup_total')).add_to(fg_total)
    fg_total.add_to(m)
    
    # Add practice markers
    logger.info(f"  [LAYER] Adding GP practice markers...")
    
    practice_group = folium.FeatureGroup(name='GP Practices', show=True)
    
    non_null_practices = practices_df[practices_df['latitude'].notna()].copy()
    logger.info(f"    {len(non_null_practices)}/{len(practices_df)} practices have coordinates")
    
    for idx, row in non_null_practices.iterrows():
        practice_name = row.get('PRACTICE_NAME', 'Unknown Practice')
        count_65plus = row.get('DEMENTIA_REGISTER_65_PLUS', 0) or 0
        count_0_64 = row.get('DEMENTIA_REGISTER_0_64', 0) or 0
        count_total = count_65plus + count_0_64
        postalcode = row.get('PRACTICE_POSTCODE', '')
        
        popup_text = f"""
        <b>{practice_name}</b><br>
        Postcode: {postalcode}<br>
        <hr>
        <b>Dementia Register:</b><br>
        65+ years: <b>{int(count_65plus)}</b><br>
        0-64 years: <b>{int(count_0_64)}</b><br>
        <span style="color: darkred;"><b>Total: {int(count_total)}</b></span>
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=2,
            popup=folium.Popup(popup_text, max_width=300),
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.4,
            weight=1,
            tooltip=practice_name
        ).add_to(practice_group)
    
    # Add hospital markers if available
    if os.path.exists(INPUT_HOSPITALS_FILE):
        logger.info(f"  [LAYER] Adding hospital location markers...")
        
        hospitals_df = pd.read_csv(INPUT_HOSPITALS_FILE)
        hospitals_geocoded = hospitals_df[hospitals_df['latitude'].notna()].copy()
        logger.info(f"    {len(hospitals_geocoded)}/{len(hospitals_df)} hospitals have coordinates")
        
        # Create hospital feature group (toggable layer)
        hospital_group = folium.FeatureGroup(name='Hospital Sites', show=True)
        
        # Use logo for markers
        logo_path = os.path.join(PROJECT_DIR, 'logo2.png')
        
        for idx, row in hospitals_geocoded.iterrows():
            hospital_name = row.get('hospital_name', 'Unknown Hospital')
            trust = row.get('trust', '')
            hospital_type = row.get('type', 'Hospital')
            postcode = row.get('postcode', '')
            
            popup_text = f"""
            <b>{hospital_name}</b><br>
            Trust: {trust}<br>
            Type: {hospital_type}<br>
            Postcode: {postcode}
            """
            
            # Use logo as marker icon if available
            if os.path.exists(logo_path):
                # Add white circle background first
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=10,
                    popup=folium.Popup(popup_text, max_width=300),
                    color='white',
                    fill=True,
                    fillColor='white',
                    fillOpacity=1.0,
                    weight=1,
                    opacity=1.0
                ).add_to(hospital_group)
                
                icon = folium.CustomIcon(
                    icon_image=logo_path,
                    icon_size=(39, 13),  # Maintains 196:64 aspect ratio (~3:1)
                    popup_anchor=(0, -9)
                )
            else:
                icon = folium.Icon(color='blue', icon='hospital-o', prefix='fa')
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=icon,
                tooltip=f"{hospital_name} ({hospital_type})",
            ).add_to(hospital_group)
        
        hospital_group.add_to(m)
    
    # Add practices on top (last layer so visible)
    practice_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(OUTPUT_MAP_HTML)
    logger.info(f"\n[SAVE] Interactive map saved to {OUTPUT_MAP_HTML}")
    logger.info(f"  Open in browser: file://{os.path.abspath(OUTPUT_MAP_HTML)}")
    
    # Summary stats
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"MSOAs visualized: {len(msoa_combined)}")
    logger.info(f"GP practices: {len(non_null_practices)}")
    logger.info(f"Hospital sites: {len(hospitals_geocoded) if os.path.exists(INPUT_HOSPITALS_FILE) else 'N/A'}")
    
    if 'DEMENTIA_REGISTER_65_PLUS' in msoa_combined.columns:
        logger.info(f"\nDementia Register (65+):")
        logger.info(f"  Total: {msoa_combined['DEMENTIA_REGISTER_65_PLUS'].sum():,.0f}")
        logger.info(f"  By MSOA - Min: {msoa_combined['DEMENTIA_REGISTER_65_PLUS'].min():.0f}, "
                    f"Max: {msoa_combined['DEMENTIA_REGISTER_65_PLUS'].max():.0f}")
    
    if 'DEMENTIA_REGISTER_0_64' in msoa_combined.columns:
        logger.info(f"\nDementia Register (0-64):")
        logger.info(f"  Total: {msoa_combined['DEMENTIA_REGISTER_0_64'].sum():,.0f}")
        logger.info(f"  By MSOA - Min: {msoa_combined['DEMENTIA_REGISTER_0_64'].min():.0f}, "
                    f"Max: {msoa_combined['DEMENTIA_REGISTER_0_64'].max():.0f}")
    
    logger.info(f"\nDensity (to account for MAUP):")
    if 'density_65plus' in msoa_combined.columns:
        logger.info(f"  65+ density:")
        logger.info(f"    Min: {msoa_combined['density_65plus'].min():.2f} per km²")
        logger.info(f"    Median: {msoa_combined['density_65plus'].median():.2f} per km²")
        logger.info(f"    Max: {msoa_combined['density_65plus'].max():.2f} per km²")
    if 'density_0_64' in msoa_combined.columns:
        logger.info(f"  0-64 density:")
        logger.info(f"    Min: {msoa_combined['density_0_64'].min():.2f} per km²")
        logger.info(f"    Median: {msoa_combined['density_0_64'].median():.2f} per km²")
        logger.info(f"    Max: {msoa_combined['density_0_64'].max():.2f} per km²")
    if 'density_total' in msoa_combined.columns:
        logger.info(f"  Total density:")
        logger.info(f"    Min: {msoa_combined['density_total'].min():.2f} per km²")
        logger.info(f"    Median: {msoa_combined['density_total'].median():.2f} per km²")
        logger.info(f"    Max: {msoa_combined['density_total'].max():.2f} per km²")
    
    return msoa_combined

if __name__ == "__main__":
    msoa_data = calculate_msoa_density()
    if msoa_data is not None:
        logger.info(f"\n✓ SUCCESS! Created MSOA density visualization")
    else:
        logger.error("\n✗ FAILED to create MSOA visualization")
        sys.exit(1)
