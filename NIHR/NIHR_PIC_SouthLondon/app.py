"""
Main Streamlit Application for NIHR PIC South London Mapping Tool.
Interactive web app for visualizing GP practices, hospitals, and travel times.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="NIHR PIC Mapping - South London",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        .main { padding: 0rem 2rem; }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and cache processed data files."""
    data_files = {
        'gp': 'data/processed/gp_practices_geocoded.csv',
        'hospitals': 'data/processed/hospital_sites_geocoded.csv',
        'travel_times': 'data/processed/travel_times_optimized.csv',
        'dementia': 'data/processed/dementia_by_practice.csv'
    }
    
    loaded_data = {}
    for key, path in data_files.items():
        try:
            if os.path.exists(path):
                loaded_data[key] = pd.read_csv(path)
                logger.info(f"Loaded {key}: {len(loaded_data[key])} rows")
            else:
                logger.warning(f"File not found: {path}")
                loaded_data[key] = None
        except Exception as e:
            logger.error(f"Error loading {key}: {e}")
            loaded_data[key] = None
    
    return loaded_data

def create_base_map(center=[51.4, -0.1], zoom=10):
    """Create a base folium map for South London."""
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='OpenStreetMap'
    )
    return m

def add_gp_markers(m, gp_df, travel_times=None, selected_travel_mode='car'):
    """Add GP practice markers to map."""
    if gp_df is None or len(gp_df) == 0:
        st.warning("No GP data available")
        return m
    
    # Filter for practices with coordinates
    gp_df = gp_df.dropna(subset=['latitude', 'longitude'])
    
    # Get travel times for color coding if available
    if travel_times is not None:
        travel_times_avg = travel_times.drop_duplicates(subset=['gp_code'])[
            ['gp_code', 'avg_travel_time_car_min', 'avg_travel_time_transit_min', 
             'avg_travel_time_walk_min']
        ]
    
    for idx, row in gp_df.iterrows():
        # Determine color based on travel time
        color = 'blue'
        travel_time_text = ''
        
        if travel_times is not None:
            tt = travel_times_avg[travel_times_avg['gp_code'] == row['practice_code']]
            if len(tt) > 0:
                if selected_travel_mode == 'car':
                    tt_val = tt.iloc[0]['avg_travel_time_car_min']
                elif selected_travel_mode == 'transit':
                    tt_val = tt.iloc[0]['avg_travel_time_transit_min']
                else:
                    tt_val = tt.iloc[0]['avg_travel_time_walk_min']
                
                travel_time_text = f"<br><b>Travel Time ({selected_travel_mode}):</b> {tt_val:.0f} min"
                
                # Color code: green < 30 min, yellow 30-45, red > 45
                if tt_val < 30:
                    color = 'green'
                elif tt_val < 45:
                    color = 'orange'
                else:
                    color = 'red'
        
        popup_text = f"""
        <b>{row['practice_name']}</b><br>
        Code: {row['practice_code']}<br>
        ICB: {row['icb_name']}<br>
        PCN: {row['pcn_name']}
        {travel_time_text}
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(m)
    
    return m

def add_hospital_markers(m, hospital_df):
    """Add hospital site markers to map."""
    if hospital_df is None or len(hospital_df) == 0:
        st.warning("No hospital data available")
        return m
    
    # Filter for hospitals with coordinates
    hospital_df = hospital_df.dropna(subset=['latitude', 'longitude'])
    
    for idx, row in hospital_df.iterrows():
        popup_text = f"""
        <b>{row['hospital_name']}</b><br>
        Trust: {row['trust']}<br>
        Code: {row['ods_code']}<br>
        Postcode: {row['postcode']}
        """
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color='red', icon='hospital-o', prefix='fa')
        ).add_to(m)
    
    return m

# ============================================================================
# MAIN APP LAYOUT
# ============================================================================

st.title("🗺️ NIHR PIC Mapping Tool - South London")
st.markdown("""
Interactive tool for mapping Participation Identification Centres (PICs) across South London.
Visualize GP practices, hospital sites, and travel times to support research participation.
""")

# Load data
with st.spinner("Loading data..."):
    data = load_data()
    gp_df = data['gp']
    hospital_df = data['hospitals']
    travel_times_df = data['travel_times']

# Sidebar Controls
st.sidebar.header("⚙️ Map Controls")

show_hospitals = st.sidebar.checkbox("Show Hospital Sites", value=True)
show_gps = st.sidebar.checkbox("Show GP Practices", value=True)

travel_mode = st.sidebar.radio(
    "Travel Mode:",
    ["car", "transit", "walking"],
    format_func=lambda x: {"car": "🚗 Car", "transit": "🚌 Public Transport", "walking": "🚶 Walking"}[x]
)

zoom_level = st.sidebar.slider("Map Zoom Level", 8, 15, 10)

# Data Summary
st.sidebar.header("📊 Summary")
if gp_df is not None:
    st.sidebar.metric("GP Practices", len(gp_df.dropna(subset=['latitude'])))
if hospital_df is not None:
    st.sidebar.metric("Hospital Sites", len(hospital_df.dropna(subset=['latitude'])))
if travel_times_df is not None:
    st.sidebar.metric("Travel Time Routes", len(travel_times_df))

# Main Map
st.subheader("Interactive Map")

m = create_base_map(zoom=zoom_level)

if show_hospitals and hospital_df is not None:
    m = add_hospital_markers(m, hospital_df)

if show_gps and gp_df is not None:
    m = add_gp_markers(m, gp_df, travel_times_df, travel_mode)

# Display map
map_data = st_folium(m, width=1200, height=600)

# Travel Time Statistics
if travel_times_df is not None:
    st.subheader("📈 Travel Time Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_car = travel_times_df['travel_time_car_minutes'].mean()
        st.metric("Avg Travel Time (Car)", f"{avg_car:.0f} min")
    
    with col2:
        avg_transit = travel_times_df['travel_time_transit_minutes'].mean()
        st.metric("Avg Travel Time (Transit)", f"{avg_transit:.0f} min")
    
    with col3:
        avg_walk = travel_times_df['travel_time_walk_minutes'].mean()
        st.metric("Avg Travel Time (Walk)", f"{avg_walk:.0f} min")
    
    # Distribution chart
    st.subheader("Travel Time Distribution")
    
    travel_mode_col = {
        'car': 'travel_time_car_minutes',
        'transit': 'travel_time_transit_minutes',
        'walking': 'travel_time_walk_minutes'
    }[travel_mode]
    
    dist_data = travel_times_df[travel_mode_col].value_counts().sort_index()
    st.bar_chart(dist_data)

# Data Preview
st.subheader("📋 Data Preview")

tab1, tab2, tab3 = st.tabs(["GP Practices", "Hospital Sites", "Travel Times"])

with tab1:
    if gp_df is not None:
        st.dataframe(gp_df.head(10), use_container_width=True)

with tab2:
    if hospital_df is not None:
        st.dataframe(hospital_df.head(10), use_container_width=True)

with tab3:
    if travel_times_df is not None:
        st.dataframe(travel_times_df.head(10), use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
**About This Tool**: Built with free and open-source software using publicly available NHS and ONS data.
[View on GitHub](https://github.com/nihr-pic-southlondon) | 
[Report Issue](https://github.com/nihr-pic-southlondon/issues)
""")
