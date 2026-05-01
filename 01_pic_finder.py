"""
Dynamic PIC Finder Tool - Streamlit Page
Allows users to find suitable GP practices as PICs based on:
- Study site (hospital)
- Maximum travel time
- Disease focus (dementia for MVP)
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="PIC Finder - NIHR",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Dynamic PIC Finder Tool")
st.markdown("""
Find suitable GP practices as Participation Identification Centres (PICs) based on your study criteria.
""")

@st.cache_data
def load_data():
    """Load processed data."""
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
            else:
                loaded_data[key] = None
        except Exception as e:
            logger.error(f"Error loading {key}: {e}")
            loaded_data[key] = None
    
    return loaded_data

# Load data
data = load_data()
gp_df = data['gp']
hospital_df = data['hospitals']
travel_times_df = data['travel_times']
dementia_df = data['dementia']

# Sidebar Input Form
st.sidebar.header("📋 Search Criteria")

if hospital_df is not None and len(hospital_df) > 0:
    hospital_options = hospital_df[['hospital_name', 'trust']].drop_duplicates()
    hospital_list = [f"{row['hospital_name']} ({row['trust']})" 
                     for _, row in hospital_options.iterrows()]
    
    selected_hospital = st.sidebar.selectbox(
        "Select Study Site (Hospital):",
        hospital_list
    )
    
    # Extract hospital name
    hospital_name = selected_hospital.split(" (")[0]
else:
    st.warning("⚠️ No hospital data available")
    hospital_name = None

max_travel_time = st.sidebar.slider(
    "Maximum Travel Time (minutes):",
    min_value=15,
    max_value=120,
    value=45,
    step=5
)

disease_focus = st.sidebar.radio(
    "Disease Focus:",
    ["Dementia", "All Conditions"],
    help="MVP focuses on Dementia. Future versions will include other conditions."
)

travel_preferences = st.sidebar.multiselect(
    "Travel Preferences:",
    ["🚗 Car", "🚌 Public Transport", "🚶 Walking"],
    default=["🚗 Car", "🚌 Public Transport"]
)

if st.sidebar.button("🔍 Find PICs", use_container_width=True):
    
    if hospital_name is None or travel_times_df is None:
        st.error("Cannot perform search - missing data")
    else:
        # Filter travel times for this hospital
        hospital_times = travel_times_df[
            travel_times_df['hospital_name'].str.contains(hospital_name, case=False, na=False)
        ].copy()
        
        if len(hospital_times) == 0:
            st.warning(f"No travel time data found for {hospital_name}")
        else:
            # Apply travel time filter based on preferences
            filters = []
            
            for pref in travel_preferences:
                if "Car" in pref:
                    filters.append(hospital_times[hospital_times['travel_time_car_minutes'] <= max_travel_time])
                elif "Public Transport" in pref:
                    filters.append(hospital_times[hospital_times['travel_time_transit_minutes'] <= max_travel_time])
                elif "Walking" in pref:
                    filters.append(hospital_times[hospital_times['travel_time_walk_minutes'] <= max_travel_time])
            
            # Combine filters (union of all travel preferences)
            if filters:
                suitable_practices = pd.concat(filters).drop_duplicates(subset=['gp_code'])
            else:
                suitable_practices = hospital_times
            
            # Filter by disease if applicable
            if disease_focus == "Dementia" and dementia_df is not None:
                dementia_practices = dementia_df['PRACTICE_CODE'].unique()
                suitable_practices = suitable_practices[suitable_practices['gp_code'].isin(dementia_practices)]
            
            # Merge with GP details
            if gp_df is not None:
                suitable_practices = suitable_practices.merge(
                    gp_df, 
                    left_on='gp_code', 
                    right_on='practice_code', 
                    how='left'
                )
            
            # Display results
            st.subheader(f"✅ Results: {len(suitable_practices)} Suitable PICs Found")
            
            if len(suitable_practices) == 0:
                st.info("No practices meet the criteria. Try adjusting your filters.")
            else:
                # Create results map
                st.markdown("### Map of Results")
                
                # Get hospital location for map center
                hosp_data = hospital_df[
                    hospital_df['hospital_name'].str.contains(hospital_name, case=False, na=False)
                ]
                
                if len(hosp_data) > 0:
                    center_lat = hosp_data.iloc[0]['latitude']
                    center_lon = hosp_data.iloc[0]['longitude']
                else:
                    center_lat, center_lon = 51.4, -0.1
                
                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=11,
                    tiles='OpenStreetMap'
                )
                
                # Add hospital marker
                if len(hosp_data) > 0:
                    folium.Marker(
                        location=[hosp_data.iloc[0]['latitude'], hosp_data.iloc[0]['longitude']],
                        popup=hosp_data.iloc[0]['hospital_name'],
                        icon=folium.Icon(color='red', icon='hospital-o', prefix='fa')
                    ).add_to(m)
                
                # Add GP markers (suitable practices)
                for _, gp in suitable_practices.iterrows():
                    if pd.notna(gp.get('latitude')) and pd.notna(gp.get('longitude')):
                        # Determine color by travel mode
                        color = 'green'
                        
                        popup_text = f"""
                        <b>{gp.get('practice_name', 'Unknown')}</b><br>
                        Code: {gp.get('gp_code', 'N/A')}<br>
                        ICB: {gp.get('icb_name', 'N/A')}<br>
                        """
                        
                        if 'travel_time_car_minutes' in gp and pd.notna(gp['travel_time_car_minutes']):
                            popup_text += f"Car: {gp['travel_time_car_minutes']:.0f} min<br>"
                        if 'travel_time_transit_minutes' in gp and pd.notna(gp['travel_time_transit_minutes']):
                            popup_text += f"Transit: {gp['travel_time_transit_minutes']:.0f} min<br>"
                        
                        folium.CircleMarker(
                            location=[gp['latitude'], gp['longitude']],
                            radius=6,
                            popup=folium.Popup(popup_text, max_width=300),
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.7,
                            weight=2
                        ).add_to(m)
                
                st_folium(m, width=1200, height=500)
                
                # Results table
                st.markdown("### Detailed Results")
                
                # Prepare display dataframe
                display_cols = ['practice_name', 'gp_code', 'icb_name', 'pcn_name', 
                               'travel_time_car_minutes', 'travel_time_transit_minutes', 
                               'travel_time_walk_minutes']
                display_cols = [c for c in display_cols if c in suitable_practices.columns]
                
                results_display = suitable_practices[display_cols].drop_duplicates()
                results_display = results_display.sort_values('travel_time_car_minutes', ascending=True)
                
                st.dataframe(
                    results_display,
                    use_container_width=True,
                    height=400
                )
                
                # Export option
                csv = results_display.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name=f"PIC_search_results_{hospital_name.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

# Info section
st.markdown("---")
st.markdown("""
### How to Use This Tool

1. **Select Study Site**: Choose the hospital where your research will take place
2. **Set Travel Time Limit**: Specify the maximum acceptable travel time for participants
3. **Choose Preferences**: Select which travel modes are most relevant to your study
4. **Pick Disease Focus**: For MVP, dementia data is available
5. **Find PICs**: Click the button to see suitable practices

The tool will show you all GP practices that meet your criteria, with their locations on a map
and detailed travel time information.
""")
