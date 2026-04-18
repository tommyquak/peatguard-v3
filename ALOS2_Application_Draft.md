# ALOS-2 PALSAR-2 Data Application -- JAXA EORC

**Application portal:** https://www.eorc.jaxa.jp/ALOS-2/en/calval/calval_index.htm

Use the information below to fill in the JAXA EORC Research Announcement (RA) application form. Adapt wording as needed to match the specific form fields.

---

## Applicant Information

- **Name:** Tommy Quak
- **Affiliation:** National University of Singapore (NUS), Department of Geography
- **Position:** Undergraduate Research Student
- **Email:** [your NUS email]
- **Supervisor/PI:** [your faculty supervisor name -- required for student applications]

---

## Research Title

**L-band InSAR Monitoring of Peatland Subsidence for Carbon Credit Verification in West Kalimantan, Indonesia**

---

## Research Summary (300 words)

Tropical peatlands in Indonesia store approximately 30% of global soil carbon despite covering less than 3% of the land surface. Drainage for agriculture triggers irreversible peat oxidation and surface subsidence, releasing substantial greenhouse gas emissions. Quantifying this subsidence at landscape scale is essential for prioritizing canal blocking interventions and verifying carbon emission reductions under the Verra VCS VM0007 methodology for peatland rewetting credits.

We have developed PeatGuard, a cloud-native satellite monitoring pipeline that uses Sentinel-1 C-band InSAR to map peatland subsidence rates in the Kapuas River region of West Kalimantan, Indonesia. The pipeline processes Sentinel-1 SLC data through ISCE2 and MintPy SBAS time-series analysis, producing subsidence velocity maps, drainage canal detection, and composite risk scores. Results show mean line-of-sight subsidence rates of -31 mm/yr concentrated near drainage canal networks, consistent with published rates for drained tropical peatlands (Hooijer et al., 2012).

However, C-band radar (5.6 cm wavelength) cannot penetrate dense tropical forest canopy, causing approximately 45% of the study area to be masked due to temporal decorrelation. This limitation is critical because subsidence beneath intact peat forest -- caused by encroaching drainage from nearby canals -- represents an early warning signal of degradation that C-band cannot detect.

ALOS-2 PALSAR-2 L-band data (23 cm wavelength) would address this gap by maintaining interferometric coherence through the forest canopy, enabling wall-to-wall subsidence measurement across the entire study area. The existing pipeline supports L-band processing through ISCE2 stripmapApp with sensor-aware configuration. A coherence-weighted multi-sensor fusion model combines C-band and L-band velocity maps to produce a unified subsidence product that leverages the complementary strengths of both wavelengths.

---

## Study Area

- **Region:** Kapuas River peatland complex, West Kalimantan, Indonesia
- **Coordinates:** 114.277-114.431 E, 2.511-2.611 S (center: 114.354 E, 2.561 S)
- **Area:** Approximately 17 x 11 km (18,700 hectares)
- **Terrain:** Flat tropical peatland, elevation less than 10 m above sea level
- **Land cover:** Mix of oil palm plantation, degraded peat forest, intact peat swamp forest, and drainage canal networks

---

## Data Requirements

| Parameter | Specification |
|---|---|
| Satellite | ALOS-2 |
| Sensor | PALSAR-2 |
| Mode | Stripmap Fine (SM1 or SM2) |
| Polarization | HH (single polarization preferred for InSAR; HH+HV dual-pol acceptable) |
| Processing level | SLC (Single Look Complex) -- required for interferometric processing |
| Observation period | January 2023 to December 2024 (2 years for time-series analysis) |
| Repeat passes | Same relative orbit, ascending preferred |
| Minimum scenes | 12 scenes (approximately one per month for 2 years) |
| Area of interest | 114.20 E to 114.50 E, 2.70 S to 2.45 S (slightly larger than study area for processing margin) |

**Justification for SLC level:** Interferometric SAR processing requires the preserved phase information in SLC products. GRD or geocoded products cannot be used for InSAR analysis.

---

## Methodology

1. **SBAS InSAR processing** using ISCE2 stripmapApp to generate interferometric pairs from repeat-pass ALOS-2 SLC acquisitions
2. **Time-series inversion** using MintPy Small Baseline Subset algorithm to estimate cumulative displacement and mean velocity at each pixel
3. **Multi-sensor fusion** combining ALOS-2 L-band velocity with Sentinel-1 C-band velocity using coherence-weighted averaging:
   - C-band provides high deformation sensitivity over cleared/plantation areas
   - L-band provides forest-penetrating measurement under intact canopy
   - Fusion produces a unified velocity map with complete spatial coverage
4. **Subsidence classification and risk scoring** using literature-calibrated thresholds (Hooijer et al., 2012) to identify restoration priority zones
5. **Carbon loss estimation** converting subsidence rates to CO2 emission rates for Verra VCS MRV compliance

---

## Expected Outcomes

1. L-band subsidence velocity map covering the full AOI including forested areas
2. Fused C+L band velocity product with complete peatland coverage
3. Validation of C-band results in cleared areas where both sensors overlap
4. Quantification of subsidence beneath intact peat forest canopy (not possible with C-band alone)
5. Improved carbon loss estimates for the entire peatland landscape

---

## Data Management

- All data will be processed on Google Cloud Platform (Cloud Run Jobs) using containerized ISCE2 and MintPy
- Results will be stored as Cloud-Optimized GeoTIFFs in Google Cloud Storage
- The processing pipeline is open-source: https://github.com/tommyquak/peatguard-v3
- Data will be used solely for academic research and the Hult Prize social entrepreneurship competition
- No commercial redistribution of raw ALOS-2 data

---

## Relevant Publications

1. Hooijer, A., et al. (2012). "Subsidence and carbon loss in drained tropical peatlands." Biogeosciences, 9(3), 1053-1071.
2. Hoyt, A. M., et al. (2020). "Widespread subsidence and carbon emissions across Southeast Asian peatlands." Nature Geoscience, 13(6), 435-440.
3. Yunjun, Z., et al. (2019). "Small baseline InSAR time series analysis: Unwrapping error correction and noise reduction." Computers and Geosciences, 133, 104331.

---

## Additional Notes for the Application

- **NUS institutional access:** Check with CRISP (Centre for Remote Imaging, Sensing and Processing, NUS) whether they have an existing ALOS-2 data sharing agreement with JAXA. If so, you may be able to access data through CRISP without a separate application.
- **Supervisor endorsement:** The application requires a faculty supervisor signature. Speak with your Geography department advisor.
- **Sang-Ho Yun** (InSAR radar scientist on the team) may have existing JAXA contacts or institutional access that could expedite the process.
- **Timeline:** Applications typically take 2-4 weeks for approval. Submit as soon as possible.
- **Alternative portal:** ALOS-2 data may also be available through:
  - ASF DAAC (some ALOS-2 products are distributed by ASF)
  - JAXA G-Portal (https://gportal.jaxa.jp/) -- requires separate registration
  - ESA Third Party Mission access (https://earth.esa.int/eogateway/) -- slower approval
