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

## IMD Interpretation Notes

- GP-level IMD source in this app is Fingertips indicator `94240`, area type `7` (GP), time period `2025`.
- `imd_score_raw` is the authoritative score persisted from the ETL enrichment step.
- `imd_local_percentile` and `imd_local_quintile` are computed locally from the currently matched GP dataset to provide distribution context.
- Local percentile/quintile values are for interpretation only and are not equivalent to official national IMD deciles.

# Key Caveats & Limitations

Patient Population Proxy: The tool uses the demographics of the LSOA (Lower Layer Super Output Area) where a GP practice is physically located as a proxy for its patient population. This is an estimate and does not reflect the exact registered patient list.

Travel Times: Travel time calculations are a one-off snapshot based on the routing API. They do not account for real-time traffic, route diversions, or service changes.

Student Populations: When viewing age-band data, note that areas with large universities may show high 16-24 year-old populations, who may not be residents outside of term-time

Migrant Populations: Equally London is a city with many migrants. Not all citizens are registered with GP practices close to their residence or at all.

This project is licensed under the MIT License - see the LICENSE.txt file for details.
