# Data Acquisition - March 2026 Deliverables

## Objective
Document and organize raw data sources for the NIHR PIC South London mapping project.

## Raw Data Sources - Currently Available

### 1. GP Practice Data
**File**: `egpcur (Include headers).csv`
**Location**: Parent NIHR directory
**Description**: NHS Organisation Data Services (ODS) current GP practice registry
**Key Columns**:
- Organisation Code
- Name (Practice Name)
- Address Line 1-5
- Postcode
- Status (ACTIVE/INACTIVE)
- Organisation Sub-Type Code
- Contact Telephone Number

**Rows**: ~3,000+ GP records (includes inactive)
**Last Updated**: Extracted from live ODS data

### 2. Practice-Level Multimorbidity Data
**File**: `pcdem-prac-data-date-mar-2024.csv`
**Location**: Parent NIHR directory
**Description**: Practice-level data with ICB, PCN, and disease prevalence codes
**Key Columns**:
- REGION_ODS_CODE
- REGION_NAME (London)
- ICB_ODS_CODE (NHS South East London, NHS South West London)
- ICB_NAME
- SUB_ICB_ODS_CODE
- PCN_ODS_CODE
- PCN_NAME
- PRACTICE_CODE
- PRACTICE_NAME
- LATEST_DATA_SUBMISSION (March 2024)

**Rows**: ~800+ practices (filtered for South London)
**Submission Date**: March 31, 2024
**Coverage**: South East London ICS (QKK) & South West London ICS (QWE)

### 3. Dementia Surveillance Data
**File**: `DementiaSurveillanceData.csv`
**Location**: Parent NIHR directory
**Description**: Dementia prevalence and surveillance data
**Note**: Reviewed for schema matching with practice codes

**File**: `DementiaSurveillanceMetadata.csv`
**Location**: Parent NIHR directory
**Description**: Metadata and data dictionary for Dementia Surveillance Data

### 4. Additional Disease Data
**File**: `pcdem-sum-mar-2024-v2.0.xlsx`
**Location**: Parent NIHR directory
**Description**: Summary-level dementia data (Excel format)

**Files**: `pcdem-prac-anti-psy-mar-2024-csv.zip`, `pcdem-prac-ass-plans-mar-2024-csv.zip`
**Location**: Parent NIHR directory
**Description**: Additional practice-level multimorbidity datasets (compressed)

## Data Structure

```
NIHR/
├── egpcur (Include headers).csv              [GP practice registry]
├── pcdem-prac-data-date-mar-2024.csv        [Practice multimorbidity - March 2024]
├── DementiaSurveillanceData.csv             [Dementia surveillance]
├── DementiaSurveillanceMetadata.csv         [Dementia metadata]
├── pcdem-sum-mar-2024-v2.0.xlsx             [Summary dementia data]
├── pcdem-prac-anti-psy-mar-2024-csv.zip     [Antipsychotic data]
├── pcdem-prac-ass-plans-mar-2024-csv.zip    [Assessment plans data]
│
└── NIHR_PIC_SouthLondon/
    ├── data/processed/                       [To be populated April+]
    └── scripts/                              [Data processing pipeline]
```

## South London Geography Filter

### Integrated Care Systems (ICS)
1. **South East London ICS**
   - ICB ODS Code: QKK
   - ICB ONS Code: E54000030
   - Includes: Bexley, Bromley, Greenwich, Lewisham, Southwark

2. **South West London ICS**
   - ICB ODS Code: QWE
   - ICB ONS Code: E54000063
   - Includes: Croydon, Kingston, Merton, Richmond, Sutton, Wandsworth

### Delivery Organisations (11, excl. London Ambulance)
- Croydon Health Services NHS Trust (RXF)
- Epsom and St Helier University Hospitals NHS Trust (RXL)
- Guy's and St Thomas' NHS Foundation Trust (RJ1)
- Kingston and Richmond NHS Foundation Trust (RWH)
- King's College Hospital NHS Foundation Trust (RJ2)
- Lewisham and Greenwich NHS Trust (RWE)
- Oxleas NHS Foundation Trust (RWK)
- South London and Maudsley NHS Foundation Trust (RWL)
- South West London and St George's Mental Health NHS Trust (RCA)
- St George's University Hospitals NHS Foundation Trust (RJ7)
- The Royal Marsden NHS Foundation Trust (RID)

## Data Quality Notes

### GP Registry (egpcur)
- Status: Mix of ACTIVE and INACTIVE practices - need to filter for ACTIVE only in April data prep
- Coverage: National dataset - South London filtering applied via postcode/ICB code
- Validation: Postcodes present for geocoding

### Practice Data (pcdem)
- Submission Date: March 31, 2024 (current baseline for MVP)
- ICB Filtering: Pre-filtered to South East (QKK) and South West (QWE) ICS
- Completeness: ~800 practices with codes and names
- Disease Codes: Practice-level disease prevalence indicators included

### Dementia Data
- Matches practice codes from pcdem dataset
- Ready for April integration with practice coordinates

## Next Steps (April - Data Prep Phase)

1. **Filter & Clean**
   - Extract ACTIVE practices only from egpcur
   - Filter for South London ICS codes

2. **Geocoding**
   - Convert postcodes to latitude/longitude coordinates
   - Use free geocoding services (Nominatim, OSM)

3. **Standardization**
   - Align practice codes across datasets
   - Match practice names for quality assurance

4. **Hospital Data**
   - Extract NHS ODS data for hospital sites
   - Obtain coordinates for 11 Delivery Organisations

5. **File Export**
   - Save cleaned datasets to `data/processed/` directory
   - Create CSV exports for Streamlit pipeline

## References
- NHS ODS: https://www.nhsdigitals.nhs.uk/services/organisation-data-service/
- ONS Open Geography: https://geoportal.statistics.gov.uk/
- Fingertips PHE: https://fingertips.phe.org.uk/

---
**Status**: ✅ March 2026 Goal - Raw Data Collection Complete
**Date Created**: 20 March 2026
**Last Updated**: 20 March 2026
