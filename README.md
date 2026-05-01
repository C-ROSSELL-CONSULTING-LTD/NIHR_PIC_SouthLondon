# NIHR_PIC_SouthLondon

This project is an interactive mapping tool built in Streamlit to identify and analyze potential GP Participation Identification Centre (PIC) sites across South London. It helps researchers find suitable practices by visualising GP/hospital locations, calculating travel times (car, public transport, walking), and overlaying key demographic and disease prevalence data to boost inclusion in clinical research.

This tool is built entirely with free and open-source software, using publicly available data, to provide a no-cost solution for NHS staff.

# Project Aims

The primary goal is to support the South London Regional Research Delivery Network in engaging with GP practices, particularly those that can help increase inclusion in research.

I will achieve this by doing the following:
1. Map Potential Sites: Comprehensively map the geographical distribution of potential PIC sites (GP Practices) in South London (SE & SW ICSs).
2. Analyse Accessibility: Understand the proximity and travel time from GP practices to acute hospital research sites.
3. Enable Inclusion: Integrate demographic and health data to identify GPs that serve underrepresented populations.
4. Provide a Free Tool: Create a solution that is free for staff to use, without requiring paid software licenses.

# Core Features

Interactive Map: A Folium map displaying all GP practices and NHS Hospital Sites in South London.

Travel Time Analysis: Displays the pre-computed average travel time from each GP to its nearest hospital.

Accessibility Toggles: A filter to switch the travel time view between Car, Public Transport, and Walking.

Demographic & Health Overlays: Choropleth map layers to visualize LSOA-level data, including:
Ethnicity
Index of Multiple Deprivation (IMD)
Age Bands
Disease Prevalence (major conditions only, dementia, CVD, cancer, chronic respiratory, mental health, MSK)

Dynamic PIC Site Finder: An advanced search tool that allows a user to:
Select a specific Hospital (Study Site).
Set a maximum travel time (e.g., 45 minutes).
Select an "condition of interest" (e.g., 'Dementia').
Dynamically returns and highlights all GPs that match the criteria.

# Tech Stack

Python 3.x

Streamlit: For the interactive web application framework.

Folium: For rendering the interactive map.

Geopandas & Pandas: For all geospatial processing and data manipulation.

RoutingPy: Used for the one-off calculation of travel times via a free API (e.g., OpenRouteService).

# Data Sources

All data used in this project is publicly available

NHS Organisation Data Services (ODS): For GP practice and hospital site locations.

ONS Open Geography Portal: For LSOA geographic boundaries and demographic data.

Public Health England (Fingertips): For disease prevalence data.

# Key Caveats & Limitations

Patient Population Proxy: The tool uses the demographics of the LSOA (Lower Layer Super Output Area) where a GP practice is physically located as a proxy for its patient population. This is an estimate and does not reflect the exact registered patient list.

Travel Times: Travel time calculations are a one-off snapshot based on the routing API. They do not account for real-time traffic, route diversions, or service changes.

Student Populations: When viewing age-band data, note that areas with large universities may show high 16-24 year-old populations, who may not be residents outside of term-time

Migrant Populations: Equally London is a city with many migrants. Not all citizens are registered with GP practices close to their residence or at all.

# Project Status & Timeline

## Current Phase: March 2026 - Data Acquisition ✅ COMPLETE

**Deliverable**: Raw data collection downloaded and stored locally.

See: [March 2026 Checklist](MARCH_2026_CHECKLIST.md) and [Data Acquisition Report](DATA_ACQUISITION_MARCH_2026.md)

### Available Raw Data:
- ✅ GP Practice Registry (ODS data)
- ✅ Practice-level Multimorbidity Data (March 2024)  
- ✅ Dementia Surveillance Data
- ✅ Delivery Organisation mapping

### Next Phase: April 2026 - Data Cleaning & Preparation
- Filter for South London ICS only
- Geocode addresses to lat/lon coordinates
- Clean and standardize datasets
- Prepare for travel time calculations

---

# Getting Started (April+)

Once cleaned data is prepared, the project will include:

```bash
# Local setup
git clone https://github.com/nihr-pic-southlondon/mapping
cd mapping
pip install -r requirements.txt

# Run data preparation scripts (April)
python scripts/01_prepare_gp_data.py
python scripts/02_get_hospital_data.py
python scripts/03_calculate_travel_times.py
python scripts/04_prepare_dementia_data.py

# Launch Streamlit app (May+)
streamlit run app.py
```

# License

This project is licensed under the MIT License - see the LICENSE.txt file for details.
