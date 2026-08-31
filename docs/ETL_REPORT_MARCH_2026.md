# ETL Data Exploration Report - March 2026

## Executive Summary

Initial ETL analysis completed on NIHR PIC South London datasets. Successfully loaded, cleaned, and analyzed 3 raw datasets. **Key Finding: Data merge issue identified** requiring resolution before proceeding to April geocoding phase.

**Status**: ⚠️ READY WITH CAVEATS

---

## Data Loading Results

| Dataset | Source | Rows | Columns | Size | Quality |
|---------|--------|------|---------|------|---------|
| GP Practice Registry | NHS ODS | 120,058 | 27 | 38.2 MB | Good (100% postcode) |
| Practice Multimorbidity | PHE/NHS | 6,252 | 14 | 1.8 MB | Excellent (no missing) |
| Dementia Surveillance | PHE | 4,680 | 28 | 1.3 MB | Excellent (no missing) |

---

## Data Cleaning & Filtering

### Step 1: Geographic Filtering
✅ **GP Registry**: No cleaning needed
- All 120,058 records retained
- 100% have postcodes (critical for geocoding)

✅ **Practice Data**: Filtered for South London
- Original: 6,252 practices (national)
- Filtered: 363 practices (94.2% reduction)
- Breakdown:
  - South East London ICS: 192 practices
  - South West London ICS: 171 practices

✅ **Dementia Data**: 4,680 records (no filtering needed)

### Step 2: Deduplication
- GP Registry: 0 duplicates
- Practice Data: 0 duplicates  
- Dementia Data: 0 duplicates
- **Overall data quality: EXCELLENT**

---

## Data Merge Analysis

### ⚠️ Critical Finding: Merge Key Mismatch

**Issue**: Practice codes don't align between datasets

```
Practice Data Codes:      G83001, G83002, G83004, ...
GP Registry Codes:        G0102926, G0105912, G0107031, ...

Result: 0/363 (0%) direct code match
```

### Merge Strategies Tested

| Strategy | Method | Success Rate | Records Matched |
|----------|--------|--------------|-----------------|
| 1 | Direct code match (PRACTICE_CODE ↔ Org Code) | 0% | 0/363 |
| 2 | Name-based match (PRACTICE_NAME ↔ Name) | 32.2% | 117/363 |

### Root Cause Analysis
- Practice data uses **contemporary ICB/PCN coding** (shortened codes)
- GP registry uses **historical ODS codes** (longer, legacy format)
- No direct code translation available in the datasets

---

## Data Quality Metrics - Cleaned South London Data (363 practices)

### Field Completeness

| Field | Complete | % | Status |
|-------|----------|---|--------|
| PRACTICE_CODE | 363 | 100% | ✓ READY |
| PRACTICE_NAME | 363 | 100% | ✓ READY |
| ICB_ODS_CODE | 363 | 100% | ✓ READY |
| Postcode | 363 | 100% | ✓ READY |
| Contact Telephone | *N/A | - | ⚠️ NOT MERGED |

*Contact info requires successful merge with GP registry

### Geographic Distribution
- **Lowest common geographic unit**: Postcode (fully available)
- **LSOA-level data**: Not available in current datasets
- **PCN (Primary Care Network)**: 76 unique networks represented
- **Data ready for**: Postcode-based geocoding ✓

---

## Artifacts & Outputs

### Generated Files
```
data/processed/
├── gp_practices_cleaned.csv          (120,058 rows)
├── practice_data_cleaned.csv         (363 rows)
├── dementia_data_cleaned.csv         (4,680 rows)
├── merged_southlondon.csv            (363 rows)
└── etl_analysis_visualization.png    (dashboard)
```

### Visualizations Generated
- Dataset size comparison (before/after)
- Data reduction percentages
- Practice distribution by ICB
- Postcode coverage (pie charts)
- Missing values analysis
- Merge success rate

---

## Recommendations for April Proceeding

### Immediate Actions Required ✓ PRIORITY

1. **Resolve Practice ID Mismatch**
   - Option A: Use NHS API to fetch current practice coordinates directly
   - Option B: Use postcode as primary geocoding key (more reliable)
   - Option C: Obtain NHS mapping table (legacy codes → current codes)

2. **Contact Information Recovery**
   - GP Registry has contact numbers (but merge failed)
   - Recommend sourcing from NHS Trusts directly if needed for Phase 3

### April Geocoding Approach (RECOMMEND OPTION B)

```
Postcode → Geocoding Service → Lat/Lon
(363 practices) → Nominatim/OSM → (363 coords)
```

**Advantages**:
- No merge dependencies
- 100% data completeness
- Free, reliable service
- Suitable for mapping

**Timeline**: 2-4 hours with rate limiting

### Hospital Sites
- No merge issues (curated list in config.py)
- Ready for April geocoding

### Travel Times
- Waiting on: GP practice coordinates  
- Once geocoded: Calculate travel matrix (48-72 hours estimated)

---

## Data Quality Summary

| Metric | Status | Notes |
|--------|--------|-------|
| Completeness | ✓ 98%+ | Except merged contact info |
| Duplicates | ✓ 0% | All datasets clean |
| Geographic Data | ✓ Ready | Postcodes 100% complete |
| Codes/IDs | ⚠️ Mismatch | Documented, workaround identified |
| Dementia Prevalence | ✓ Ready | 4,680 records available |
| LSOA Data | ❌ Not available | Future enhancement |

---

## April 2026 Proceeding Decision

**PROCEED with CAUTION** ✓

### Go/No-Go Checklist
- [x] Raw data loaded successfully
- [x] Cleaning & filtering complete
- [x] Geographic filters applied (South London confirmed)  
- [x] Data quality issues identified  
- [x] Workarounds documented
- [x] Visualization dashboard created
- [x] Cleaned CSVs exported
- [ ] ⚠️ Practice code merge resolved (REQUIRED for April)

**Recommend**: Resolve practice ID issue before starting April coding phase (1-2 hours work).

---

## Technical Notes

- **Python Version**: 3.11.14
- **Key Libraries**: pandas, matplotlib, seaborn
- **Total Processing Time**: ~2 minutes
- **Code Quality**: ASCII-safe, encodings validated
- **Reproducibility**: Scripts available in `/scripts/`

---

## IMD Methods Note (March 2026 Update)

- Source: Fingertips indicator `94240`, GP area type `7`, time period `2025`.
- ETL keeps `imd_score_raw` as the authoritative raw deprivation value matched by GP practice code.
- Additional interpretability fields are computed from the matched GP set:
   - `imd_local_percentile` (0-100, monotonic rank percentile within current matched GP dataset)
   - `imd_local_quintile` (1-5 bands derived from local percentile distribution)
   - `imd_local_rank_note` (explicit display caveat text)
- These local fields support interpretation of spread and relative position only.
- They are not equivalent to official national IMD deciles and should not be reported as such.

---

## Next Steps

### Before April Coding Starts

1. [ ] Decide on practice ID resolution approach (API vs. postcode)
2. [ ] If using API: Obtain NHS digital credentials
3. [ ] If using postcode: Prepare Nominatim rate limiting configuration

### April Phase 1 (Week 1)
- Implement chosen practice ID strategy
- Re-run ETL with corrected merge
- Geocode 363 practice postcodes

### April Phase 2 (Week 2-3)
- Extract hospital site data
- Geocode hospital addresses  
- Validate all coordinates on test map

### April Phase 3 (Week 4)
- Calculate travel time matrix
- Cache results for Streamlit

---

**Report Generated**: 20 March 2026  
**Analysis Status**: ✓ COMPLETE  
**Next Review**: Start of April 2026 (Data Prep Phase)

---

## Appendix: Data Sample

### Top 10 South London Practices (Sample)
```
PRACTICE_NAME                  | ICB_NAME                       | POSTCODE
MANOR BROOK PMS                | NHS South East London ICB      | ...
THE WESTWOOD SURGERY           | NHS South East London ICB      | ...
BARNARD MEDICAL GROUP          | NHS South East London ICB      | ...
THE ALBION SURGERY             | NHS South East London ICB      | ...
BELLEGROVE SURGERY             | NHS South East London ICB      | ...
...
```

### Diagnostic Information
- Practices without postcode: 0
- Practices without practice code: 0
- Dementia data records: 4,680
- Coverage: 100% of South London delivery networks
