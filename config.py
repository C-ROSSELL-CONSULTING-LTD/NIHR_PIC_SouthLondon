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
UNIVERSITIES_DATA_FILE = "data/processed/universities_geocoded.csv"
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

# GP-level QOF prevalence metrics from Fingertips (area_type_id=7).
# Excludes Dementia (247) and Diabetes (241): already covered by dedicated pipelines.
# Verified live against Fingertips API and data/lookups/api_annex.ods on 2026-08-19.
HEALTH_METRIC_REGISTRY = [
    {"key": "asthma", "indicator_id": 90933, "label": "Asthma"},
    {"key": "atrial_fibrillation", "indicator_id": 280, "label": "Atrial Fibrillation"},
    {"key": "chd", "indicator_id": 273, "label": "CHD"},
    {"key": "ckd", "indicator_id": 258, "label": "CKD"},
    {"key": "copd", "indicator_id": 253, "label": "COPD"},
    {"key": "cancer", "indicator_id": 276, "label": "Cancer"},
    {"key": "depression", "indicator_id": 848, "label": "Depression"},
    {"key": "epilepsy", "indicator_id": 224, "label": "Epilepsy"},
    {"key": "heart_failure", "indicator_id": 262, "label": "Heart Failure"},
    {"key": "heart_failure_lvsd", "indicator_id": 849, "label": "Heart Failure (LVSD)"},
    {"key": "hypertension", "indicator_id": 219, "label": "Hypertension"},
    {"key": "learning_disability", "indicator_id": 200, "label": "Learning Disability"},
    {"key": "mental_health", "indicator_id": 90581, "label": "Mental Health (SMI)"},
    {"key": "ndh", "indicator_id": 93797, "label": "Non-Diabetic Hyperglycaemia"},
    {"key": "obesity", "indicator_id": 94136, "label": "Obesity"},
    {"key": "osteoporosis", "indicator_id": 90443, "label": "Osteoporosis"},
    {"key": "pad", "indicator_id": 92590, "label": "PAD"},
    {"key": "palliative_care", "indicator_id": 294, "label": "Palliative/Supportive Care"},
    {"key": "rheumatoid_arthritis", "indicator_id": 91269, "label": "Rheumatoid Arthritis"},
    {"key": "smoking", "indicator_id": 91280, "label": "Smoking"},
    {"key": "stroke", "indicator_id": 212, "label": "Stroke"},
]

# Streamlit config
MAP_CENTER = [51.4, -0.1]  # South London center
DEFAULT_ZOOM = 10
