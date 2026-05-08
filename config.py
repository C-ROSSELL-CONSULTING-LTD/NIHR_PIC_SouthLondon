"""
Configuration file for NIHR PIC South London project.
Contains constants, hospital data, and project settings.
"""

# South London Delivery Organisations (11, exc. London Ambulance Service)
DELIVERY_ORGANISATIONS = {
    "Croydon Health Services NHS Trust": {"ods_code": "RXF"},
    "Epsom and St Helier University Hospitals NHS Trust": {"ods_code": "RXL"},
    "Guy's and St Thomas' NHS Foundation Trust": {"ods_code": "RJ1"},
    "Kingston and Richmond NHS Foundation Trust": {"ods_code": "RWH"},
    "King's College Hospital NHS Foundation Trust": {"ods_code": "RJ2"},
    "Lewisham and Greenwich NHS Trust": {"ods_code": "RWE"},
    "Oxleas NHS Foundation Trust": {"ods_code": "RWK"},
    "South London and Maudsley NHS Foundation Trust": {"ods_code": "RWL"},
    "South West London and St George's Mental Health NHS Trust": {"ods_code": "RCA"},
    "St George's University Hospitals NHS Foundation Trust": {"ods_code": "RJ7"},
    "The Royal Marsden NHS Foundation Trust": {"ods_code": "RID"},
}

# South East London & South West London ICBs
INTEGRATED_CARE_SYSTEMS = {
    "South East London ICS": {
        "icb_ods_code": "QKK",
        "icb_ons_code": "E54000030"
    },
    "South West London ICS": {
        "icb_ods_code": "QWE",
        "icb_ons_code": "E54000063"
    }
}

# South London approximate geographical boundaries (lat/lon)
SOUTH_LONDON_BOUNDS = {
    "north": 51.45,
    "south": 51.35,
    "east": 0.15,
    "west": -0.35
}

# API settings
GEOCODING_TIMEOUT = 10  # seconds
TRAVEL_TIME_TIMEOUT = 30  # seconds
MAX_HOSPITALS_PER_GP = 5  # Limit travel time calculations to 5 nearest hospitals

# Data paths
DATA_DIR = "data/"
PROCESSED_DATA_DIR = "data/processed/"
RAW_DATA_DIR = "data/raw/"
SCRIPTS_DIR = "pipeline/"

# Output files
GP_DATA_FILE = "data/processed/gp_practices_geocoded.csv"
HOSPITAL_DATA_FILE = "data/processed/hospital_sites_geocoded.csv"
TRAVEL_TIMES_FILE = "data/processed/travel_times_optimized.csv"
DEMENTIA_DATA_FILE = "data/processed/dementia_data.csv"

# Travel modes
TRAVEL_MODES = {
    "car": "driving",
    "public_transport": "transit",
    "walking": "walking"
}

# Dementia data sources
DEMENTIA_DATA_SOURCE = "Fingertips PHE API or Manual Entry"

# Streamlit config
MAP_CENTER = [51.4, -0.1]  # South London center
DEFAULT_ZOOM = 10
