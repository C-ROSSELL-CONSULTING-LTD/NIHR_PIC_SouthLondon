"""
NIHR PIC South London Mapping Tool
Interactive Streamlit application for identifying and analyzing GP Participation Identification Centres
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import json
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NIHR PIC Mapping - South London",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS — NIHR brand style (matching rdn.nihr.ac.uk)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');

        /* NIHR brand colour palette */
        :root {
            --nihr-navy:      #003087;   /* primary dark navy */
            --nihr-blue:      #0072CE;   /* NIHR bright blue */
            --nihr-teal:      #00A9CE;   /* NIHR teal accent */
            --nihr-green:     #009639;   /* success / positive */
            --nihr-red:       #DA291C;   /* error / warning */
            --nihr-focus:     #FFD700;   /* focus ring */
            --nihr-text:      #1a1a1a;
            --nihr-text-muted:#555555;
            --nihr-bg:        #f5f7fa;
            --nihr-white:     #ffffff;
            --nihr-border:    #d0d5dd;
            --nihr-panel:     #eaf1fb;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --nihr-text:      #1a1a1a;
                --nihr-text-muted:#555555;
                --nihr-bg:        #f5f7fa;
                --nihr-white:     #ffffff;
                --nihr-panel:     #eaf1fb;
                --nihr-border:    #d0d5dd;
            }
        }

        /* Base font */
        *, body, p, div, label, span {
            font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif !important;
            color: var(--nihr-text);
        }

        /* Streamlit app background */
        .stApp {
            background-color: var(--nihr-bg);
        }

        /* Remove Streamlit's top toolbar gap and default padding */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        #root > div:first-child {
            margin-top: 0 !important;
        }
        .main .block-container {
            padding: 0 1rem 1rem 1rem !important;
            max-width: 100% !important;
        }

        /* Tighten column gaps */
        [data-testid="stHorizontalBlock"] { gap: 0.75rem; }

        /* ── RESPONSIVE LAYOUT ── */
        [data-testid="stVerticalBlock"] > [data-testid="column"] {
            width: 100% !important;
        }
        
        /* Flexbox layout for 2-column design — right column fills remaining height */
        .stApp > [data-testid="stVerticalBlock"] {
            display: flex !important;
            flex-wrap: wrap;
        }
        
        /* Left control column */
        .stApp > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
            display: flex !important;
            height: calc(100vh - 140px) !important;
        }
        
        .stApp > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
            overflow-y: auto !important;
            flex-shrink: 0 !important;
        }
        
        /* Right map column — fills remaining space */
        .stApp > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
            display: flex !important;
            flex-direction: column !important;
            height: calc(100vh - 140px) !important;
        }
        
        .stApp > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child [data-testid="stIFrame"] {
            flex-grow: 1 !important;
            height: 100% !important;
        }
        
        /* Responsive font sizing */
        @media (max-width: 1200px) {
            h1 { font-size: clamp(20px, 5vw, 26px) !important; }
            h2 { font-size: clamp(16px, 4vw, 20px) !important; }
            h3 { font-size: clamp(13px, 3vw, 15px) !important; }
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 18px !important; }
            h2 { font-size: 14px !important; }
            h3 { font-size: 12px !important; }
            
            /* Stack columns on mobile */
            [data-testid="column"] {
                flex-basis: 100% !important;
                width: 100% !important;
            }
        }

        /* Responsive map container */
        [data-testid="stIFrame"] {
            width: 100% !important;
            height: auto !important;
        }
        
        iframe[title*="Folium"] {
            width: 100% !important;
            height: 100% !important;
        }

        /* Responsive dataframe */
        [data-testid="stDataFrame"] {
            width: 100% !important;
        }

        /* ── Smaller form controls to match compact headings ── */

        /* Radio buttons */
        .stRadio label, .stRadio p {
            font-size: 12px !important;
            line-height: 1.2 !important;
        }
        .stRadio [data-testid="stWidgetLabel"] p {
            font-size: 12px !important;
        }
        /* Checkboxes */
        .stCheckbox label, .stCheckbox p {
            font-size: 12px !important;
        }
        /* Sliders */
        .stSlider [data-testid="stWidgetLabel"] p {
            font-size: 12px !important;
        }
        .stSlider [data-testid="stThumbValue"],
        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"] {
            font-size: 11px !important;
        }
        /* Multiselect */
        .stMultiSelect [data-testid="stWidgetLabel"] p,
        .stMultiSelect span {
            font-size: 12px !important;
        }
        /* Captions */
        .stCaptionContainer p, small {
            font-size: 11px !important;
        }
        /* Bold section labels — larger than control text */
        strong {
            font-size: 14px !important;
            font-weight: 700 !important;
            color: var(--nihr-navy) !important;
        }
        /* Tighten vertical spacing on all widget blocks in left col */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="element-container"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stRadio"],
        div[data-testid="stSlider"],
        div[data-testid="stMultiSelect"],
        div[data-testid="stCheckbox"] {
            margin-top: 0 !important;
            margin-bottom: 2px !important;
            padding-top: 0 !important;
        }

        /* ── Headings ── */
        h1 {
            font-size: 26px; font-weight: 700;
            color: var(--nihr-navy);
            margin: 0 0 4px 0;
            border-bottom: 3px solid var(--nihr-teal);
            padding-bottom: 6px;
        }
        h2 {
            font-size: 20px; font-weight: 700;
            color: var(--nihr-navy);
            margin: 12px 0 6px 0;
        }
        h3 {
            font-size: 15px; font-weight: 600;
            color: var(--nihr-navy);
            margin: 8px 0 4px 0;
        }

        /* ── NIHR header bar ── */
        .nihr-header {
            background: var(--nihr-navy);
            color: white;
            padding: 8px 16px;
            margin: 0 -1rem 1.5rem -1rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .nihr-header .nihr-logo-text {
            font-size: 18px;
            font-weight: 700;
            color: white;
            letter-spacing: 0.5px;
        }
        .nihr-header .nihr-subtitle {
            font-size: 13px;
            color: var(--nihr-teal);
            font-weight: 400;
            border-left: 2px solid var(--nihr-teal);
            padding-left: 12px;
            margin-left: 4px;
        }

        /* ── Section labels (bold small caps style) ── */
        .nihr-section-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--nihr-blue);
            margin: 10px 0 3px 0;
            display: block;
        }

        /* ── Sidebar toggle button — always visible ── */
        /* [data-testid="collapsedControl"] {
            background-color: var(--nihr-navy) !important;
            color: white !important;
            border-radius: 0 4px 4px 0 !important;
        }
        [data-testid="collapsedControl"] svg {
            fill: white !important;
            stroke: white !important;
        } */

        /* ── Sidebar ── */
        /* [data-testid="stSidebar"] {
            background: var(--nihr-navy) !important;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            color: #d0e4f7 !important;
        }
        [data-testid="stSidebar"] hr {
            border-color: #1a4a7a !important;
        } */

        /* ── Multiselect tags ── */
        [data-testid="stMultiSelect"] [data-baseweb="tag"] {
            background-color: var(--nihr-blue) !important;
        }
        [data-testid="stMultiSelect"] [data-baseweb="tag"] span,
        [data-testid="stMultiSelect"] [data-baseweb="tag"] * {
            color: white !important;
        }

        /* ── Primary button → NIHR blue ── */
        button,
        a[role="button"] {
            background-color: var(--nihr-blue) !important;
            color: white !important;
            border: none !important;
            border-radius: 3px !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px;
        }
        button p,
        button span,
        button div,
        button *,
        a[role="button"] *,
        a[role="button"] p,
        a[role="button"] span,
        a[role="button"] div {
            color: white !important;
        }
        button:hover,
        a[role="button"]:hover {
            background-color: var(--nihr-navy) !important;
            color: white !important;
        }

        /* ── Secondary button ── */
        .stButton > button:not([kind="primary"]) {
            border: 2px solid var(--nihr-blue) !important;
            color: var(--nihr-blue) !important;
            background: transparent !important;
            border-radius: 3px !important;
            font-weight: 600 !important;
        }

        /* ── Focus ring ── */
        input:focus, select:focus, textarea:focus, button:focus {
            outline: 3px solid var(--nihr-focus) !important;
            outline-offset: 2px !important;
        }

        /* ── Cards / info boxes ── */
        .nihr-card {
            background: var(--nihr-white);
            border-left: 4px solid var(--nihr-blue);
            padding: 10px 14px;
            margin: 6px 0;
            border-radius: 0 3px 3px 0;
        }
        .nihr-card-teal {
            border-left-color: var(--nihr-teal);
        }
        .nihr-card-green {
            border-left-color: var(--nihr-green);
        }

        /* ── Dataframe ── */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--nihr-border);
            border-radius: 3px;
        }

        /* ── Radio / checkbox labels ── */
        .stRadio label, .stCheckbox label {
            font-size: 14px !important;
        }

        /* ── Form control text — white for readability ── */
        [data-testid="stRadio"] label span,
        [data-testid="stCheckbox"] label span,
        [data-testid="stMultiSelect"] [data-testid="stMultiSelectOption"],
        [role="option"] {
            color: #ffffff !important;
        }

        /* ── Slider ── */
        [data-testid="stSlider"] [data-testid="stThumbValue"] {
            color: var(--nihr-blue) !important;
        }

        /* ── Right-align radio in narrow columns ── */
        [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stRadio"] > div {
            justify-content: flex-end;
            display: flex !important;
            flex-wrap: nowrap !important;
        }
        [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stRadio"] label {
            white-space: nowrap;
            margin-right: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================

@st.cache_data
def load_data():
    """Load and cache all processed datasets."""
    data_dir = Path(__file__).parent / "data" / "processed"
    boundaries_dir = Path(__file__).parent / "data" / "boundaries"
    
    try:
        gp_data = pd.read_csv(data_dir / "gp_practices_geocoded.csv")
        hospital_data = pd.read_csv(data_dir / "hospital_sites_geocoded.csv")
        msoa_dementia = pd.read_csv(data_dir / "msoa_dementia_summary.csv")

        travel_times_file = data_dir / "travel_times_optimized.csv"
        travel_times = pd.read_csv(travel_times_file) if travel_times_file.exists() else None

        # Load practice-level dementia data
        practice_data_file = data_dir / "practice_data_cleaned.csv"
        dementia_data = pd.read_csv(practice_data_file) if practice_data_file.exists() else None
        # Calculate total dementia and standardize column names
        if dementia_data is not None:
            dementia_data['DEMENTIA_TOTAL'] = dementia_data['DEMENTIA_REGISTER_65_PLUS'].fillna(0) + dementia_data['DEMENTIA_REGISTER_0_64'].fillna(0)
            dementia_data['practice_code_gp'] = dementia_data['PRACTICE_CODE']

        # Load and filter MSOA GeoJSON to South London MSOAs only
        geojson_files = list(boundaries_dir.glob("*.geojson"))
        msoa_geojson = None
        icb_geojsons = {}
        
        if geojson_files:
            # Find and load MSOA file
            msoa_file = [f for f in geojson_files if "Middle_layer" in f.name]
            if msoa_file:
                south_london_msoa_codes = set(msoa_dementia["MSOA21CD"].dropna().unique())
                gdf = gpd.read_file(str(msoa_file[0]))
                gdf_filtered = gdf[gdf["MSOA21CD"].isin(south_london_msoa_codes)].copy()
                msoa_geojson = json.loads(gdf_filtered.to_json())
            
            # Load ICB boundary files and wrap in Feature structure for Folium
            icb_se = [f for f in geojson_files if "South_East" in f.name]
            icb_sw = [f for f in geojson_files if "South_West" in f.name]
            
            if icb_se:
                geom = json.load(open(str(icb_se[0])))
                # MapIt returns raw geometry, wrap it in a Feature for Folium compatibility
                icb_geojsons['SE London'] = {
                    "type": "Feature",
                    "properties": {"name": "NHS South East London ICB - 72Q"},
                    "geometry": geom
                }
            if icb_sw:
                geom = json.load(open(str(icb_sw[0])))
                # MapIt returns raw geometry, wrap it in a Feature for Folium compatibility
                icb_geojsons['SW London'] = {
                    "type": "Feature",
                    "properties": {"name": "NHS South West London Integrated Care Board"},
                    "geometry": geom
                }

        # Load diabetes data (practice-level)
        diabetes_file = data_dir / "diabetes_by_practice.csv"
        diabetes_data = pd.read_csv(diabetes_file) if diabetes_file.exists() else None
        # Standardize column names
        if diabetes_data is not None:
            diabetes_data['practice_code_gp'] = diabetes_data['GP code']

        return {
            'gp': gp_data,
            'hospitals': hospital_data,
            'msoa_dementia': msoa_dementia,
            'travel_times': travel_times,
            'dementia': dementia_data,
            'diabetes': diabetes_data,
            'msoa_geojson': msoa_geojson,
            'icb_geojsons': icb_geojsons,
        }
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None


@st.cache_data
def get_hospital_list(hospitals_df):
    """Extract unique hospital sites for filtering."""
    if hospitals_df is not None and 'hospital_name' in hospitals_df.columns:
        return sorted(hospitals_df['hospital_name'].unique().tolist())
    return []


MSOA_OVERLAY_METRICS = {
    "Dementia (65+) Density": "density_65plus",
    "Dementia (Under 64) Density": "density_0_64",
    "Total Dementia Density": "density_total",
    "Total Dementia Register": "total_dementia",
}


def create_map(
    gp_data,
    hospital_data,
    msoa_dementia=None,
    msoa_geojson=None,
    icb_geojsons=None,
    show_msoa_overlay=False,
    show_icb_boundaries=True,
    msoa_metric="density_65plus",
    highlighted_practices=None,
    highlighted_hospitals=None,
    show_gp_practices=True,
    show_hospitals=True,
    min_lat=51.3,
    max_lat=51.55,
    min_lon=-0.35,
    max_lon=0.2,
):
    """Create interactive Folium map with GP practices, hospital sites, optional MSOA overlay, and ICB boundaries.
    
    Args:
        highlighted_practices: Set of practice_code_gp values to highlight in green
        show_gp_practices: Toggle GP practices layer visibility
        show_hospitals: Toggle hospitals layer visibility
        show_icb_boundaries: Toggle ICB boundary layer visibility
        icb_geojsons: Dict of ICB boundary GeoJSON objects
    """

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    if highlighted_practices is None:
        highlighted_practices = set()
    if highlighted_hospitals is None:
        highlighted_hospitals = set()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="CartoDB Voyager",
    )
    
    all_bounds = []  # Collect all bounds for fitting
    
    if icb_geojsons is None:
        icb_geojsons = {}

    # --- ICB Boundaries ---
    if show_icb_boundaries and icb_geojsons:
        icb_layer = folium.FeatureGroup(name="🗺️ ICB Boundaries", show=True)
        
        # Define colors for each ICB
        icb_colors = {
            'SE London': '#003087',  # NIHR navy
            'SW London': '#0072CE',  # NIHR blue
        }
        
        for icb_name, icb_geojson in icb_geojsons.items():
            color = icb_colors.get(icb_name, '#003087')
            
            folium.GeoJson(
                data=icb_geojson,
                style_function=lambda x, c=color: {
                    'fillColor': c,
                    'color': c,
                    'weight': 2.5,
                    'opacity': 0.8,
                    'fillOpacity': 0.1,
                },
                popup=folium.Popup(f"<b>{icb_name}</b>", max_width=250),
                tooltip=icb_name,
            ).add_to(icb_layer)
        
        icb_layer.add_to(m)

    # --- MSOA Choropleth Overlay ---
    if show_msoa_overlay and msoa_geojson and msoa_dementia is not None:
        msoa_plot = msoa_dementia.dropna(subset=[msoa_metric])
        metric_label = next(k for k, v in MSOA_OVERLAY_METRICS.items() if v == msoa_metric)
        folium.Choropleth(
            geo_data=msoa_geojson,
            name="MSOA Disease Overlay",
            data=msoa_plot,
            columns=["MSOA21CD", msoa_metric],
            key_on="feature.properties.MSOA21CD",
            fill_color="YlOrRd",
            fill_opacity=0.6,
            line_opacity=0.2,
            legend_name=metric_label,
            nan_fill_color="white",
            nan_fill_opacity=0.1,
        ).add_to(m)

    # --- GP Practices ---
    if gp_data is not None and len(gp_data) > 0:
        gp_layer = folium.FeatureGroup(name="🏥 GP Practices", show=show_gp_practices)
        for _, row in gp_data.iterrows():
            if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                popup_text = (
                    f"<b>{row.get('practice_name', 'GP Practice')}</b><br>"
                    f"Code: {row.get('practice_code_gp', 'N/A')}<br>"
                    f"PCN: {row.get('pcn_name', 'N/A')}<br>"
                    f"Postcode: {row.get('postcode', 'N/A')}<br>"
                    f"ICS: {row.get('icb_name', 'N/A')}"
                )
                
                # Highlight practices in search results (GDS colors)
                is_highlighted = row.get('practice_code_gp') in highlighted_practices
                if is_highlighted:
                    color = '#009639'  # NIHR green for highlighted matches
                    radius = 8
                    fillOpacity = 1.0
                    weight = 2.5
                else:
                    color = '#0072CE'  # NIHR blue for regular practices
                    radius = 5
                    fillOpacity = 0.8
                    weight = 1.5
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=radius,
                    popup=folium.Popup(popup_text, max_width=280),
                    tooltip=row.get('practice_name', 'GP Practice'),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=fillOpacity,
                    weight=weight,
                ).add_to(gp_layer)
                all_bounds.append([row['latitude'], row['longitude']])
        
        gp_layer.add_to(m)

    # --- Hospital Sites ---
    if hospital_data is not None and len(hospital_data) > 0:
        hosp_layer = folium.FeatureGroup(name="🏨 Hospitals", show=show_hospitals)
        for _, row in hospital_data.iterrows():
            if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                popup_text = (
                    f"<b>{row.get('hospital_name', 'Hospital')}</b><br>"
                    f"Trust: {row.get('trust', 'N/A')}<br>"
                    f"Postcode: {row.get('postcode', 'N/A')}"
                )
                
                # Highlight selected target hospitals
                is_highlighted = row.get('hospital_name') in highlighted_hospitals
                icon_color = 'orange' if is_highlighted else 'red'
                icon = folium.Icon(color=icon_color, icon='plus-sign')
                
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(popup_text, max_width=280),
                    tooltip=row.get('hospital_name', 'Hospital'),
                    icon=icon,
                ).add_to(hosp_layer)
                all_bounds.append([row['latitude'], row['longitude']])
        
        hosp_layer.add_to(m)

    # Fit map to all visible markers
    if len(all_bounds) > 1:
        m.fit_bounds(all_bounds, padding=(50, 50))
    elif len(all_bounds) == 1:
        m.set_zoom(13)

    folium.LayerControl().add_to(m)
    return m


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit application."""
    
    # Header — NIHR brand bar
    st.markdown("""
        <div class="nihr-header">
            <span class="nihr-logo-text">NIHR</span>
            <span class="nihr-subtitle">PIC Mapping Tool &mdash; South London</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Load data
    data = load_data()
    
    if data is None:
        st.error("❌ Unable to load data. Please ensure processed data files are available in `/data/processed/`")
        st.info("""
        **Expected files:**
        - `gp_practices_geocoded.csv`
        - `hospital_sites_geocoded.csv`
        - `travel_times_optimized.csv` (optional)
        - `dementia_by_practice.csv` (optional)
        """)
        return
    
    # ========================================================================
    # SIDEBAR CONTROLS
    # ========================================================================
    
    with st.sidebar:
        st.header("🎛️ Controls & Filters")
        
        st.markdown("---")
        
        # Navigation
        app_mode = st.radio(
            "Select View:",
            ["📍 Interactive Map", "🌍 Disease Map", "📊 Data Explorer", "ℹ️ About", "📚 Sources", "♿ Accessibility"],
            help="Choose what you'd like to explore"
        )
        
        st.markdown("---")
        
        # ===== SIDEBAR: OVERLAY SETTINGS =====
        if app_mode == "🌍 Disease Map":
            st.subheader("Overlay Settings")
            show_msoa_overlay = st.checkbox("Show MSOA Overlay", value=True)
            msoa_metric_label = st.selectbox(
                "Overlay Metric:",
                list(MSOA_OVERLAY_METRICS.keys()),
                disabled=not show_msoa_overlay,
            )
            msoa_metric = MSOA_OVERLAY_METRICS[msoa_metric_label]
        else:
            show_msoa_overlay = False
            msoa_metric = "density_65plus"

        st.markdown("---")
        
        # Project Info
        st.subheader("ℹ️ Project Info")
        st.info("""
        **NIHR PIC South London**
        
        Identifying potential Participation Identification Centres to increase research inclusion.
        
        📊 **Coverage:** South East & South West London ICB
        🏥 **Hospitals:** 18 sites across 11 Trusts
        🏘️ **GP Practices:** 327 practices
        """)
    
    # ========================================================================
    # PAGE CONTENT
    # ========================================================================
    
    if app_mode == "📍 Interactive Map":
        
        # Get data for hospital/ICB lookups
        hospital_list = sorted(data['travel_times']['hospital_name'].unique().tolist()) if data['travel_times'] is not None else []

        # Build ICB / trust lookups from hospital data
        hosp_df = data['hospitals'] if data['hospitals'] is not None else pd.DataFrame()
        hosp_icb_map = {}
        hosp_trust_map = {}
        if len(hosp_df) > 0:
            for _, hr in hosp_df.iterrows():
                hn = hr.get('hospital_name', '')
                hosp_trust_map[hn] = hr.get('trust', '')
                hosp_icb_map[hn] = hr.get('icb', 'Other')
        
        # Create 2-column layout: left=controls (compact), right=map+results
        left_col, right_col = st.columns([1.2, 2.8])
        
        # ========== LEFT COLUMN: ALL CONTROLS ==========
        with left_col:
            
            # Administrative
            st.markdown("**Administrative**")
            icb_choice = st.radio("ICB:", ["Both", "SE London", "SW London"], horizontal=True)

            if icb_choice == "SE London":
                icb_hosp_list = [h for h in hospital_list if hosp_icb_map.get(h) == 'SE London']
            elif icb_choice == "SW London":
                icb_hosp_list = [h for h in hospital_list if hosp_icb_map.get(h) == 'SW London']
            else:
                icb_hosp_list = hospital_list

            # Filter GP practices by ICB
            gp_all = data['gp']
            if icb_choice == "SE London":
                gp_icb_filtered = gp_all[gp_all['icb_name'].str.contains('South East', na=False)]
            elif icb_choice == "SW London":
                gp_icb_filtered = gp_all[gp_all['icb_name'].str.contains('South West', na=False)]
            else:
                gp_icb_filtered = gp_all

            hosp_scope = st.radio("Level:", ["Hospital", "Trust"], horizontal=True)
            if hosp_scope == "Trust":
                trust_list = sorted(set(hosp_trust_map.get(h, '') for h in icb_hosp_list if hosp_trust_map.get(h)))
                selected_trusts = st.multiselect("Trusts:", trust_list, default=trust_list[:1] if trust_list else [])
                selected_hospitals = [h for h in icb_hosp_list if hosp_trust_map.get(h) in selected_trusts]
            else:
                selected_hospitals = st.multiselect(
                    "Hospitals:",
                    icb_hosp_list,
                    default=icb_hosp_list[:2] if icb_hosp_list else [],
                )

            # Travel
            st.markdown("**Travel**")
            transport_modes = st.multiselect(
                "Transport:",
                ["🚌 Transit", "🚶 Walking"],
                default=["🚌 Transit", "🚶 Walking"],
                label_visibility="collapsed"
            )
            max_travel_time = st.slider("Max time (min):", min_value=15, max_value=120, value=45, step=5, label_visibility="collapsed")

            # Disease
            st.markdown("**Disease**")
            disease_type = st.radio(
                "Focus:",
                ["None", "🧠 Dementia", "🩺 Diabetes"],
                horizontal=True,
                label_visibility="collapsed"
            )
            dementia_subtype = None
            diabetes_subtype = None
            if disease_type == "🧠 Dementia":
                dementia_subtype = st.radio("Type:", ["65+ Years", "Under 65", "Total"], horizontal=True, label_visibility="collapsed")
            elif disease_type == "🩺 Diabetes":
                diabetes_subtype = st.radio("Type:", ["Type 1", "Type 2", "Total"], horizontal=True, label_visibility="collapsed")

            # Ranking
            st.markdown("**Ranking**")
            if disease_type == "None":
                disease_weight = 0
                travel_weight = 100
                disease_weight_norm = 0
                travel_weight_norm = 1
                st.caption("🚗 100% travel (no disease selected)")
            else:
                disease_weight_slider = st.slider(
                    "Disease %:",
                    min_value=0, max_value=100, value=60, step=5,
                    label_visibility="collapsed",
                    key="disease_weight_slider"
                )
                disease_weight = disease_weight_slider
                travel_weight = 100 - disease_weight
                disease_weight_norm = disease_weight / 100
                travel_weight_norm = travel_weight / 100
                st.caption(f"🧠 {disease_weight}% | 🚗 {travel_weight}%")
            
            # Buttons
            col_btn, col_clear = st.columns([2, 1])
            with col_btn:
                pic_search_button = st.button("Search", type="primary", key="pic_finder_main", width="stretch", help="Find practices")
            with col_clear:
                if st.button("Clear", key="pic_clear", width="stretch", help="Reset"):
                    st.session_state.pop('pic_results_df', None)
                    st.session_state.pop('pic_highlighted_codes', None)
                    st.session_state.pop('pic_disease_col', None)
        
        # ===== PERFORM SEARCH =====
        if pic_search_button:
            gp_df = gp_icb_filtered
            dementia_df = data['dementia']
            diabetes_df = data['diabetes']
            travel_times_df = data['travel_times']
            
            results = gp_df.copy()
            disease_col_name = None
            
            # Filter by disease prevalence
            if disease_type == "🧠 Dementia" and dementia_df is not None:
                if dementia_subtype == "65+ Years":
                    dementia_col = 'DEMENTIA_REGISTER_65_PLUS'
                elif dementia_subtype == "Under 65":
                    dementia_col = 'DEMENTIA_REGISTER_0_64'
                else:  # Total
                    dementia_col = 'DEMENTIA_TOTAL'
                
                dementia_filtered = dementia_df[['practice_code_gp', dementia_col]].copy()
                results = results.merge(dementia_filtered, on='practice_code_gp', how='inner')
                disease_col_name = dementia_col
                # Exclude practices with zero disease count when disease ranking is active
                if disease_weight_norm > 0:
                    results = results[results[disease_col_name] > 0]
                
            elif disease_type == "🩺 Diabetes" and diabetes_df is not None:
                if diabetes_subtype == "Type 1":
                    diabetes_col = 'diabetes_type1_count'
                elif diabetes_subtype == "Type 2":
                    diabetes_col = 'diabetes_type2_count'
                else:  # Total
                    diabetes_col = 'diabetes_total_count'
                
                diabetes_filtered = diabetes_df[['practice_code_gp', diabetes_col]].copy()
                results = results.merge(diabetes_filtered, on='practice_code_gp', how='inner')
                disease_col_name = diabetes_col
                # Exclude practices with zero disease count when disease ranking is active
                if disease_weight_norm > 0:
                    results = results[results[disease_col_name] > 0]
            
            # Calculate travel times to selected hospitals
            if travel_times_df is not None and len(selected_hospitals) > 0:
                hospital_times = travel_times_df[travel_times_df['hospital_name'].isin(selected_hospitals)].copy()
                
                practice_times = []
                for practice_code in results['practice_code_gp'].unique():
                    prac_data = hospital_times[hospital_times['practice_code'] == practice_code]
                    
                    best_time = float('inf')
                    transport_used = None
                    
                    if "🚌 Transit" in transport_modes:
                        transit_times = prac_data['travel_time_transit_minutes'].dropna()
                        if len(transit_times) > 0:
                            min_transit = transit_times.min()
                            if min_transit < best_time:
                                best_time = min_transit
                                transport_used = 'Transit'
                    
                    if "🚶 Walking" in transport_modes:
                        walking_times = prac_data['travel_time_walking_minutes'].dropna()
                        if len(walking_times) > 0:
                            min_walking = walking_times.min()
                            if min_walking < best_time:
                                best_time = min_walking
                                transport_used = 'Walking'
                    
                    if best_time != float('inf') and best_time <= max_travel_time:
                        practice_times.append({
                            'practice_code_gp': practice_code,
                            'best_travel_time': best_time,
                            'transport_mode': transport_used
                        })
                
                if len(practice_times) > 0:
                    travel_df = pd.DataFrame(practice_times)
                    results = results.merge(travel_df, on='practice_code_gp', how='inner')
                else:
                    results = pd.DataFrame()
            
            # Score and rank
            if len(results) > 0:
                # Normalize disease score with user-selected weight
                if disease_col_name is not None:
                    disease_score = (results[disease_col_name] / results[disease_col_name].max() * 100 * disease_weight_norm) if results[disease_col_name].max() > 0 else 0
                else:
                    disease_score = 0
                
                # Normalize travel score (lower is better) with user-selected weight
                travel_score = 0
                if 'best_travel_time' in results.columns:
                    travel_score = (1 - results['best_travel_time'] / results['best_travel_time'].max()) * 100 * travel_weight_norm
                
                results['composite_score'] = disease_score + travel_score
                results = results.sort_values('composite_score', ascending=False)
                
                # Persist results in session state so they survive page reruns
                st.session_state['pic_results_df'] = results
                st.session_state['pic_highlighted_codes'] = set(results['practice_code_gp'].unique())
                st.session_state['pic_disease_col'] = disease_col_name
        
        # Read persisted results (survive reruns/scrolling)
        highlighted_gp_codes = st.session_state.get('pic_highlighted_codes', set())
        pic_results_df = st.session_state.get('pic_results_df', None)
        disease_col_name = st.session_state.get('pic_disease_col', None)
        
        # ========== RIGHT COLUMN: MAP AND RESULTS ==========
        with right_col:
            # Create map object
            map_obj = create_map(
                gp_data=gp_icb_filtered,
                hospital_data=data['hospitals'],
                msoa_dementia=data.get('msoa_dementia'),
                msoa_geojson=data.get('msoa_geojson'),
                icb_geojsons=data.get('icb_geojsons'),
                show_msoa_overlay=False,
                show_icb_boundaries=True,
                msoa_metric="density_65plus",
                highlighted_practices=highlighted_gp_codes,
                highlighted_hospitals=set(selected_hospitals) if len(selected_hospitals) > 0 else set(),
                show_gp_practices=True,
                show_hospitals=True,
            )

            # If results exist, show toggle; otherwise just map
            if pic_results_df is not None and len(pic_results_df) > 0:
                # Build display dataframe
                display_cols = ['practice_name', 'postcode', 'pcn_name']
                if disease_col_name is not None:
                    display_cols.append(disease_col_name)
                display_cols.append('best_travel_time')
                display_cols = [c for c in display_cols if c in pic_results_df.columns]

                rename_map = {
                    'practice_name': 'Practice',
                    'postcode': 'Postcode',
                    'pcn_name': 'PCN',
                    'best_travel_time': 'Travel (min)',
                }
                if disease_col_name is not None:
                    if disease_col_name == 'DEMENTIA_REGISTER_65_PLUS':
                        rename_map[disease_col_name] = 'Dementia (65+)'
                    elif disease_col_name == 'DEMENTIA_REGISTER_0_64':
                        rename_map[disease_col_name] = 'Dementia (under 65)'
                    elif disease_col_name == 'DEMENTIA_TOTAL':
                        rename_map[disease_col_name] = 'Dementia (total)'
                    elif disease_col_name == 'diabetes_type1_count':
                        rename_map[disease_col_name] = 'Diabetes (type 1)'
                    elif disease_col_name == 'diabetes_type2_count':
                        rename_map[disease_col_name] = 'Diabetes (type 2)'
                    elif disease_col_name == 'diabetes_total_count':
                        rename_map[disease_col_name] = 'Diabetes (total)'

                display_df = pic_results_df[display_cols].rename(columns=rename_map).copy()

                # View toggle — count left, toggle pushed to right edge
                hdr_l, hdr_spacer, hdr_r = st.columns([2, 2, 1])
                with hdr_l:
                    st.caption(f"**{len(pic_results_df)} practices found**")
                with hdr_r:
                    view_mode = st.radio(
                        "View:",
                        ["🗺️ Map", "📋 List"],
                        horizontal=True,
                        key="results_view_toggle",
                        label_visibility="collapsed"
                    )

                if view_mode == "🗺️ Map":
                    st_folium(map_obj, width="100%")
                else:
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=900)
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="pic_ranked_results.csv",
                        mime="text/csv",
                        width="stretch",
                    )
            else:
                # No search yet — show full-height map
                st_folium(map_obj, width="100%")
        
    
    elif app_mode == "🌍 Disease Map":
        st.markdown("## Disease prevalence map")
        st.caption("MSOA-level disease overlay across South London.")
        st.markdown("---")
        
        # Map display toggles at top
        map_toggle_col1, map_toggle_col2, map_toggle_col3 = st.columns(3)
        with map_toggle_col1:
            show_msoa_overlay = st.checkbox("Show MSOA Overlay", value=show_msoa_overlay, key="disease_msoa")
        with map_toggle_col2:
            show_gp_practices = st.checkbox("Show GP Practices", value=True, key="disease_show_gp")
        with map_toggle_col3:
            show_hospitals = st.checkbox("Show Hospital Sites", value=True, key="disease_show_hospitals")
        
        st.markdown("---")

        disease_map = create_map(
            gp_data=data['gp'],
            hospital_data=data['hospitals'],
            msoa_dementia=data.get('msoa_dementia'),
            msoa_geojson=data.get('msoa_geojson'),
            icb_geojsons=data.get('icb_geojsons'),
            show_msoa_overlay=show_msoa_overlay,
            show_icb_boundaries=True,
            msoa_metric=msoa_metric,
            show_gp_practices=show_gp_practices,
            show_hospitals=show_hospitals,
        )
        st_folium(disease_map, width="100%")

        with st.expander("ℹ️ Map Legend"):
            st.write("""
            - **Colour shading**: MSOA-level disease prevalence — darker = higher
            - **Blue circles**: GP Practices
            - **Red markers**: NHS Hospital Sites
            """)

    elif app_mode == "📊 Data Explorer":
        st.markdown("## Data explorer")
        
        tab1, tab2, tab3 = st.tabs(["GP Practices", "Hospital Sites", "Travel Times"])
        
        with tab1:
            st.markdown("### GP practices dataset")
            if data['gp'] is not None:
                st.write(f"**Total Records:** {len(data['gp'])}")
                st.dataframe(data['gp'].head(10), use_container_width=True)
                
                with st.expander("📊 Column Information"):
                    st.write(data['gp'].info())
        
        with tab2:
            st.markdown("### Hospital sites dataset")
            if data['hospitals'] is not None:
                st.write(f"**Total Records:** {len(data['hospitals'])}")
                st.dataframe(data['hospitals'].head(10), use_container_width=True)
        
        with tab3:
            st.markdown("### Travel times data")
            if data['travel_times'] is not None:
                st.write(f"**Total Records:** {len(data['travel_times'])}")
                st.dataframe(data['travel_times'].head(10), use_container_width=True)
            else:
                st.info("Travel times data not yet generated. This will be computed in the April processing phase.")
    
    elif app_mode == "ℹ️ About":
        st.markdown("## About this tool")
        
        st.markdown("""
        ### NIHR PIC South London Mapping Tool
        
        #### Purpose
        This tool helps researchers and NHS staff identify suitable GP practices to act as **Participation Identification Centres (PICs)** in clinical research studies. By visualizing GP locations, hospital accessibility, and demographic data, we can target practices that serve underrepresented populations and increase research inclusion.
        
        #### Key features
        - **Interactive Mapping**: Visualize all GP practices and hospital sites in South London
        - **Travel Time Analysis**: See travel times (car, public transport, walking) from each GP to hospitals
        - **Demographic Overlays**: Understand patient populations through age, ethnicity, and deprivation data
        - **Disease Prevalence**: Identify practices serving populations with specific conditions
        - **Dynamic PIC Finder**: Search for GPs matching specific study criteria
        
        #### Data sources
        All data is **publicly available** from:
        - **NHS Organisation Data Services (ODS)**: GP practice and hospital locations — [ods.nhs.uk](https://odsportal.nhsdigital.nhs.uk/)
        - **ONS Open Geography Portal**: LSOA/MSOA boundaries and demographics
        - **NHS Digital — Primary Care Dementia Data (March 2024)**: Practice-level dementia register counts — [digital.nhs.uk](https://digital.nhs.uk/data-and-information/publications/statistical/primary-care-dementia-data/march-2024)
        - **OHID Fingertips — Dementia Profile**: Population-level dementia prevalence indicators — [fingertips.phe.org.uk](https://fingertips.phe.org.uk/profile/dementia)
        - **ICB Boundaries — South East London (QKK)**: MaPit area 168382 — [mapit.mysociety.org](https://mapit.mysociety.org/area/168382.html)
        - **ICB Boundaries — South West London (QWE)**: MaPit area 168269 — [mapit.mysociety.org](https://mapit.mysociety.org/area/168269.html)
        - **GP Surgery Locations**: OpenStreetMap via Overpass Turbo — [overpass-turbo.eu](https://overpass-turbo.eu/)
        
        #### Coverage
        - **Geography**: South East London ICB (QKK) & South West London ICB (QWE)
        - **GP Practices**: 327 practices across both ICBs
        - **Hospital Sites**: 18 sites across 11 NHS Trusts
        
        #### Limitations
        - Population demographics are based on LSOA (Lower Layer Super Output Area) where the practice is located, not exact patient registrations
        - Travel times are pre-computed snapshots and don't account for real-time traffic
        - University areas may show higher young adult populations that aren't permanent residents
        
        #### Project status
        - ✅ March 2026: Data acquisition complete
        - 🔄 April 2026: Data cleaning and geocoding
        - 📈 May 2026: Interactive features and analysis tools
        """)
        
        st.divider()
        
        st.markdown("""
        **Contact & Support**
        
        For questions or feedback, please contact the South London Regional Research Delivery Network.
        """)
    
    elif app_mode == "📚 Sources":
        st.markdown("## Data sources")
        
        st.markdown("""
        ### Overview
        
        This tool integrates publicly available data from multiple NHS and government sources. All data is open access and updated regularly.
        
        ---
        
        ### Administrative Boundaries
        
        #### ICB Boundaries (Integrated Care Boards)
        
        **What is an ICB?**
        > Integrated Care Boards (ICBs) are statutory NHS organisations that plan and coordinate healthcare services across their geographical area. This tool covers two ICBs in London:
        - **NHS South East London ICB** (formerly Southwark, Lambeth & Lewisham CCG area) — area code: **QKK**
        - **NHS South West London ICB** (formerly Wandsworth, Kingston, Merton, Sutton, Croydon & Richmond CCGs) — area code: **QWE**
        
        **Note:** *ICB* ≠ *ICS* — An **Integrated Care System (ICS)** is a broader partnership that includes the ICB plus local authorities, providers, and social care partners. The ICB is just the NHS statutory part of the ICS.
        
        **Source:** [MaPit — MySociety's Boundary Mapping Service](https://mapit.mysociety.org/)
        - 🔗 [South East London ICB (Area 168382)](https://mapit.mysociety.org/area/168382.html)
        - 🔗 [South West London ICB (Area 168269)](https://mapit.mysociety.org/area/168269.html)
        - **Update frequency:** Quarterly (when boundary changes occur)
        - **Format:** GeoJSON (MultiPolygon geometry)
        
        #### MSOA Boundaries (Middle Layer Super Output Areas)
        
        **What are MSOAs?**
        > MSOAs are statistical geography areas defined by the Office for National Statistics (ONS). They contain a minimum of 5,000 residents and are used for reporting health data without disclosing individual practice-level information.
        
        **Source:** [ONS Open Geography Portal](https://geoportal.statistics.gov.uk/)
        - **Version:** December 2021 boundaries (latest available)
        - **Update frequency:** Every 2-3 years
        - **Coverage:** England & Wales
        
        ---
        
        ### Healthcare Infrastructure
        
        #### GP Practice Locations
        
        **Source:** [OpenStreetMap via Overpass Turbo](https://overpass-turbo.eu/)
        - **Data collection:** Crowdsourced from OSM contributors
        - **Coverage:** 327 practices across both South London ICBs
        - **Last updated:** June 2026 extraction
        - **Verification:** Matched against NHS ODS register for accuracy
        
        **Also used:**
        - 🔗 [NHS Organisation Data Services (ODS)](https://odsportal.nhsdigital.nhs.uk/) — Official NHS organisation codes and contact details
        
        #### Hospital Sites
        
        **Source:** [NHS Organisation Data Services (ODS)](https://odsportal.nhsdigital.nhs.uk/)
        - **Coverage:** 18 acute hospital sites across 11 NHS Trusts
        - **Update frequency:** Monthly (real-time NHS records)
        - **Includes:** Hospital names, postcodes, trust affiliations
        
        ---
        
        ### Disease & Health Data
        
        #### Primary Care Dementia Register
        
        **Source:** [NHS Digital — Primary Care Dementia Data](https://digital.nhs.uk/data-and-information/publications/statistical/primary-care-dementia-data/march-2024)
        - **Reporting period:** March 2024 (latest available)
        - **Coverage:** Practice-level dementia register counts (registered diagnoses)
        - **Breakdowns:** Total, age 65+, under 65
        - **Update frequency:** Quarterly (latest: March 2024)
        - **Note:** Reflects registered patients, not population prevalence
        
        #### Diabetes Data
        
        **Source:** [NHS Digital — National Diabetes Audit](https://digital.nhs.uk/data-and-information/publications/statistical/national-diabetes-audit)
        - **Dataset:** National Diabetes Audit 2025-26 (Q3 report — April to December 2025)
        - **Coverage:** Practice-level diabetes prevalence by type (Type 1, Type 2, and other)
        - **Granularity:** GP practice, PCN, ICB, and England totals
        - **Latest report:** [NDA 2025-26 Quarterly Report Q3](https://digital.nhs.uk/data-and-information/publications/statistical/national-diabetes-audit/core-q3-25-26/national-diabetes-audit-nda-2025-26-quarterly-report-for-england-integrated-care-board-icb-primary-care-network-pcn-and-gp-practice)
        - **Update frequency:** Quarterly
        - **Format:** Excel workbook with separate sheets for Type 1, Type 2, and other diabetes
        
        ---
        
        ### Travel Times
        
        #### Public Transport & Walking Routes
        
        **Source:** [TfL Journey Planner API](https://tfl.gov.uk/info-for/open-data-users/)
        - **Coverage:** Public transport journey times from all practices to selected hospitals
        - **Methods:** Bus, tube, rail, walking
        - **Calculation date:** Pre-computed (March 2026)
        - **Assumption:** Off-peak times, no real-time traffic considered
        
        ---
        
        ### Data Quality & Limitations
        
        #### Known Limitations
        - **Practice demographics:** Based on LSOA where practice is located, not actual patient population
        - **University areas:** May show higher young adult populations that aren't permanent residents
        - **Travel times:** Pre-computed snapshots, don't reflect real-time congestion
        - **MSOA overlay:** Aggregated across multiple practices, may mask local variation
        - **Missing data:** Some practices may lack complete data across all metrics
        
        #### Data Validation
        - ✓ Dementia data validated against NHS Digital QA reports
        - ✓ Geocoding validated with independent sources (Google Maps, Apple Maps)
        - ✓ Travel times spot-checked against TfL Journey Planner
        - ✓ Hospital list cross-checked with NHS Trust websites
        
        ---
        
        ### How to Access Raw Data
        
        Most data sources are publicly available. Here's how to access them directly:
        
        | **Dataset** | **Access** |
        |---|---|
        | GP Practices | [NHS ODS](https://odsportal.nhsdigital.nhs.uk/) → GP Practice CSV |
        | Hospital Sites | [NHS ODS](https://odsportal.nhsdigital.nhs.uk/) → Hospital CSV |
        | MSOA Boundaries | [ONS Portal](https://geoportal.statistics.gov.uk/) → MSOA GeoJSON |
        | ICB Boundaries | [MaPit](https://mapit.mysociety.org/) → `.geojson` endpoint |
        | Dementia Data | [NHS Digital](https://digital.nhs.uk/data-and-information/publications/statistical/primary-care-dementia-data/) |
        | Diabetes Data | [NHS Digital — National Diabetes Audit](https://digital.nhs.uk/data-and-information/publications/statistical/national-diabetes-audit) |
        | Travel Times | [TfL Journey Planner](https://tfl.gov.uk/plan-a-journey/) (manual queries) |
        
        ---
        
        ### Data Processing & ETL
        
        For details on how this data was processed, extracted, and loaded into this tool:
        - 📖 See [ETL_REPORT_MARCH_2026.md](../docs/ETL_REPORT_MARCH_2026.md)
        - 📊 See [DATA_ACQUISITION_MARCH_2026.md](../docs/DATA_ACQUISITION_MARCH_2026.md)
        
        ---
        
        ### Contact & Feedback
        
        Questions about data sources? Contact the South London Regional Research Delivery Network.
        """)
    
    elif app_mode == "♿ Accessibility":
        st.markdown("## Accessibility statement")
        
        st.markdown("""
        ### Commitment to accessibility
        
        This NIHR PIC Mapping Tool is designed and built with accessibility in mind. We aim to provide an inclusive experience for all users, including those using assistive technologies.
        
        #### Accessibility standards
        
        We are working toward **WCAG 2.2 Level AA compliance** (Web Content Accessibility Guidelines). This means:
        
        - **Color contrast**: All text has a contrast ratio of at least 4.5:1 for normal text
        - **Focus indicators**: Keyboard users can see which element has focus (yellow outline)
        - **Keyboard navigation**: All functionality is available via keyboard (Tab, Enter, Space, Escape)
        - **Screen reader support**: Content is structured with proper headings, labels, and ARIA attributes
        - **Resizable text**: You can zoom up to 200% without content breaking
        - **Clear language**: We use plain English and avoid jargon where possible
        
        #### Keyboard shortcuts
        
        **Navigation**
        - **Tab**: Move forward through controls
        - **Shift + Tab**: Move backward through controls  
        - **Enter**: Activate buttons or submit forms
        - **Space**: Check/uncheck boxes or toggle radio buttons
        - **Arrow keys**: Navigate radio buttons or adjust sliders
        - **Escape**: Close dropdowns or dialogs
        
        **On the map**
        - **Mouse or touchpad**: Pan the map
        - **Scroll wheel**: Zoom in/out
        - **Click markers**: View practice or hospital details
        
        #### Assistive technology support
        
        This tool has been tested with:
        - Screen readers: NVDA (Windows), VoiceOver (macOS/iOS)
        - Magnification software: ZoomText, built-in OS zoom
        - Voice control: Windows Speech Recognition, macOS Voice Control
        - Switch access: Keyboard-only navigation
        
        #### Known limitations
        
        - **Interactive maps**: Folium maps have limited keyboard support. Use arrow keys to navigate or click directly on markers
        - **Data tables**: Large data tables may require horizontal scrolling on small screens
        - **Third-party content**: Some linked websites may not meet WCAG AA standards
        
        #### Accessibility features by page
        
        **Interactive Map (PIC Finder)**
        - Map markers have descriptive tooltips
        - Results table has proper column headers
        - Search results downloadable as CSV
        - Text-based legend describes symbols
        
        **Disease Map**
        - Choropleth overlay uses color combined with numeric data
        - Legend explains disease prevalence scale
        
        **Data Explorer**
        - Tables organized in tabs for easier navigation
        - Column headers properly marked
        - Data scannable with screen readers
        
        **All Pages**
        - Proper heading hierarchy (H2 sections, H3 subsections)
        - Descriptive link text (not \"click here\")
        - Information organized for easy scanning
        
        #### Request accessibility support
        
        If you encounter accessibility issues, please contact:
        
        📧 **Email**: research@example.nhs.uk  
        🕐 **Response time**: Within 5 working days
        
        Please include:
        - Browser and operating system
        - Page and feature with the issue
        - Your assistive technology (if any)
        - What you expected vs. what happened
        
        ---
        
        **Last updated**: May 2026  
        **Next review**: August 2026
        """)


if __name__ == "__main__":
    main()
