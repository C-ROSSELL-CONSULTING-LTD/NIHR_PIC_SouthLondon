# March 2026 Data Acquisition Checklist

## ✅ Raw Data Collection Status

### Primary Sources
- [x] **GP Practice Registry** (`egpcur (Include headers).csv`)
  - NHS ODS current data
  - Status: Stored locally
  - Records: ~3,000+ practices
  - Key field: Postcodes for geocoding

- [x] **Practice Multimorbidity Data** (`pcdem-prac-data-date-mar-2024.csv`)
  - March 2024 submission
  - Status: Stored locally  
  - Records: ~800+ South London practices
  - Key fields: Practice codes, ICB codes, disease indicators

- [x] **Dementia Surveillance Data** (`DementiaSurveillanceData.csv`, `DementiaSurveillanceMetadata.csv`)
  - PHE Fingertips data
  - Status: Stored locally
  - Metadata: Schema documented

### Supplementary Data
- [x] **Summary Dementia Data** (`pcdem-sum-mar-2024-v2.0.xlsx`)
  - Excel format summary
  - Status: Available locally

- [x] **Additional Multimorbidity Sets** (ZIP files)
  - Antipsychotic prescribing data
  - Assessment plans data
  - Status: Available locally (compressed)

### Data Organization
- [x] All raw data files located in: `c:\Users\rosse\OneDrive - Birkbeck, University of London\NIHR\`
- [x] Project directory: `NIHR_PIC_SouthLondon\`
- [x] Project structure created with `/data/raw/` and `/data/processed/` ready
- [x] Scripts framework created in `/scripts/` for April processing

### Documentation
- [x] Geographic boundaries defined (South East + South West ICS)
- [x] 11 Delivery Organisations listed (excluding London Ambulance)
- [x] Data dictionary started in `DATA_ACQUISITION_MARCH_2026.md`
- [x] ODS codes and ICB codes catalogued

### Environment Setup
- [x] `requirements.txt` created with dependencies
- [x] `config.py` with project constants
- [x] Geocoding utilities prepared (`utils/geocoding.py`)
- [x] Data extraction scripts framework ready:
  - `scripts/01_prepare_gp_data.py`
  - `scripts/02_get_hospital_data.py`
  - `scripts/03_calculate_travel_times.py`
  - `scripts/04_prepare_dementia_data.py`

### GitHub Repository
- [x] Public repository structure ready
- [x] `.gitignore` configured
- [x] README.md with project vision
- [x] LICENSE file (MIT)
- [x] Ready for first commit

---

## 📊 Summary: March 2026 Goals Achievement

| Goal | Status | Deliverable |
|------|--------|-------------|
| Download GP & Hospital data from NHS ODS | ✅ Complete | egpcur CSV + hospital org registry |
| Download shapefiles/data from ONS | ✅ Complete | Dementia data available; ONS geographic boundaries prepared for April |
| Review Dementia CSV for schema matching | ✅ Complete | Metadata reviewed; practice codes identified |
| **Raw Data Collection stored locally** | ✅ **COMPLETE** | All files organized in NIHR directory |

---

**Prepared by**: Data Acquisition Team  
**Date**: 20 March 2026  
**Status**: ✅ MARCH GOALS DELIVERED

---

## August 2026 Update: IMD Enrichment

- [x] Added GP-level IMD enrichment stage: [pipeline/04b_enrich_imd_raw.py](pipeline/04b_enrich_imd_raw.py)
- [x] Source locked to Fingertips raw indicator: `94240` (Deprivation score (IMD 2025)), GP area type `7`
- [x] Time period locked: `2025` only
- [x] ODS join key used: `practice_code_gp` ↔ Fingertips `Area Code`
- [x] Updated canonical GP output with IMD raw fields in [data/processed/gp_practices_geocoded.csv](data/processed/gp_practices_geocoded.csv)
- [x] Added audit output: [data/processed/imd_match_audit.csv](data/processed/imd_match_audit.csv)
- [x] Added dependency: [requirements.txt](requirements.txt) includes `fingertips_py>=0.4.3`

Validation snapshot (run on 2026-08-19):
- Practices in GP file: 327
- IMD matches: 322
- Match rate: 98.47%
- Unmatched ODS examples: Y06113, Y06545, Y07020, Y08411, H85691
