# PeatGuard: Plans for Improvement

## Objective
Improve the clarity and confidence of peatland restoration zone detection.
Each improvement is assessed for scientific impact, implementation effort,
and data availability.

---

## 1. Confidence Mapping (High Impact, Low Effort)

### Problem
The pipeline produces velocity and risk maps but provides no per-pixel
confidence indicator. A stakeholder looking at the risk map cannot
distinguish between a high-confidence measurement over cleared land and
a noisy estimate at the edge of forest cover. The velocity uncertainty
file exists but is not used in classification or risk scoring.

### Proposed Solution
Create a composite confidence layer (0-1) combining:
- **Temporal coherence** (already computed): higher = more reliable
- **Velocity uncertainty** (already computed): lower = more reliable
- **Number of valid interferograms** per pixel: more = more reliable
- **Spatial consistency**: agreement with neighboring pixels (local std dev of velocity)

Formula:
```
confidence = w1 * coherence + w2 * (1 - norm_uncertainty) + w3 * norm_n_pairs + w4 * spatial_consistency
```

### Integration
- Weight the risk score by confidence: `adjusted_risk = risk * confidence`
- Add confidence as a band or separate product
- In the dashboard, display confidence as a semi-transparent overlay
- Classification could use confidence to downgrade low-confidence severe pixels to "uncertain"

### Data Required
All inputs already exist in the pipeline. No new data needed.

---

## 2. Seasonal Decomposition (High Impact, Medium Effort)

### Problem
Tropical peatlands expand and contract seasonally with wet/dry cycles.
A single linear velocity over one year conflates true subsidence (irreversible
peat loss) with seasonal oscillation (reversible water table fluctuation).
This introduces 5-15 mm/yr of apparent velocity variation depending on
which part of the cycle the time series starts and ends.

### Proposed Solution
Enable MintPy's periodic signal estimation to separate:
- **Linear trend**: the true subsidence rate (irreversible)
- **Seasonal amplitude**: the magnitude of wet/dry oscillation
- **Seasonal phase**: timing of peak/trough relative to monsoon

MintPy supports this natively:
```
mintpy.velocity.excludeDate = auto
mintpy.velocity.startDate   = auto
mintpy.velocity.endDate     = auto
# Add:
mintpy.timeseries.periodicSignal = 365.25
```

### Integration
- Export both linear velocity and seasonal amplitude as separate products
- Classification should use linear trend only (not raw velocity)
- Seasonal amplitude itself is informative: high amplitude = responsive
  water table = potentially restorable

### Data Required
Existing data, but benefits from extending to 2+ years of acquisitions.

---

## 3. Land Cover Stratification (High Impact, Medium Effort)

### Problem
The risk score treats all land equally, but subsidence interpretation
differs fundamentally by land cover:
- **Oil palm plantation on peat**: subsidence is expected and ongoing
- **Degraded peat forest**: subsidence indicates active drainage impact
- **Intact peat swamp forest**: any subsidence is alarming
- **Recently cleared**: subsidence rate is highest in first 5 years

Without land cover context, a -30 mm/yr measurement over a mature
plantation has the same risk score as -30 mm/yr under degraded forest,
even though the restoration priority is very different.

### Proposed Solution
Derive a land cover map from Sentinel-2 optical imagery (free):
- NDVI thresholding + temporal signature distinguishes:
  - Water (NDVI < 0)
  - Bare/cleared (NDVI 0-0.3)
  - Plantation (NDVI 0.3-0.6, regular grid pattern)
  - Degraded forest (NDVI 0.4-0.7, irregular)
  - Intact forest (NDVI > 0.7)
- Use Google Earth Engine for cloud-free composite (free tier sufficient)

Integrate into risk scoring:
```
restoration_priority = risk_score * land_cover_weight * peat_depth_factor
```
Where `land_cover_weight` is highest for degraded forest (most
restorable) and lowest for active plantation concessions (legally
constrained).

### Data Required
- Sentinel-2 cloud-free composite (free, Copernicus Open Access Hub)
- Optionally: Indonesian land cover map from MoEF (publicly available)

---

## 4. Peat Depth Integration (High Impact, Low Effort)

### Problem
The risk score does not account for peat depth. A subsiding area with
10m of peat contains far more carbon at risk than a 2m peat area with
the same subsidence rate. Restoration prioritization should weight by
the total carbon stock that would be lost without intervention.

### Proposed Solution
Overlay the CIFOR Indonesian Peat Map (free download from cifor.org):
- Provides peat extent polygons and depth estimates (shallow/moderate/deep)
- Rasterize to the pipeline grid
- Create a peat depth factor:
  - No peat: 0.0 (exclude from risk)
  - Shallow (<2m): 0.5
  - Moderate (2-4m): 0.8
  - Deep (>4m): 1.0

Multiply into the risk score to create a carbon-weighted priority map.

### Data Required
- CIFOR Indonesian Peat Map (free download)
- Rasterization with GDAL (trivial)

---

## 5. Spatial Coherence Filtering (Medium Impact, Low Effort)

### Problem
Isolated single pixels of "severe subsidence" surrounded by stable
pixels are almost certainly noise (unwrapping errors, atmospheric
residuals). These noisy pixels erode confidence in the results and
can mislead restoration planning.

### Proposed Solution
Apply a spatial consistency filter after classification:
- For each pixel, check if >50% of neighbors within a 5x5 window
  share the same or adjacent class
- Isolated severe pixels surrounded by stable pixels get downgraded
- Alternatively: require a minimum connected area (e.g., 1 hectare)
  for each severity class to be reported

This is conceptually similar to the morphological cleanup already
applied to the canal mask and water mask.

### Data Required
No new data. Applied to existing classification output.

---

## 6. Cross-Validation with Optical Time Series (Medium Impact, Medium Effort)

### Problem
InSAR velocity has no independent validation. There are no ground truth
measurements in the AOI. Without cross-validation, the results depend
entirely on the InSAR processing chain and its assumptions.

### Proposed Solution
Use Sentinel-2 NDVI time series as an independent degradation indicator:
- Peat degradation causes vegetation stress and NDVI decline
- Canal construction is visible as abrupt NDVI drops
- Water table rise (after rewetting) shows NDVI recovery

Spatial correlation analysis:
- Areas of high subsidence should correlate with NDVI decline
- Areas near canals should show lower NDVI than areas far from canals
- Report the Pearson correlation coefficient as a pipeline-level
  quality metric

If InSAR subsidence and NDVI decline are spatially correlated (r > 0.5),
this provides independent evidence that the subsidence signal is real
and related to peat degradation rather than atmospheric or processing
artifacts.

### Data Required
- Sentinel-2 NDVI (free, same Copernicus access)
- Google Earth Engine or direct download + composite

---

## 7. Error Budget and Sensitivity Analysis (Medium Impact, Low Effort)

### Problem
When presenting results to Verra auditors or investors, the question
"how accurate is this?" has no quantitative answer. The velocity is
reported as a point estimate without systematic error characterization.

### Proposed Solution
Compute and report an explicit error budget:

| Error Source | Estimated Magnitude | Status |
|---|---|---|
| Atmospheric delay (tropospheric) | 5-15 mm/yr | Corrected (ERA5) |
| Atmospheric delay (ionospheric) | 2-5 mm/yr | Corrected (split-spectrum) |
| Reference point uncertainty | 3-8 mm/yr | Mitigated (fixed point) |
| Temporal decorrelation bias | 2-10 mm/yr | Partially mitigated (coherence mask) |
| Unwrapping errors | 0-28 mm/yr per event | Mitigated (MCF + network) |
| Georeferencing error | 1-3 km spatial | Known limitation |
| Seasonal aliasing | 5-15 mm/yr | Not yet corrected |
| **Total RSS (corrected)** | **~8-12 mm/yr** | |

Report this in the metadata of each product and in the dashboard legend.
A measurement of -30 +/- 10 mm/yr is far more useful than just -30 mm/yr.

### Data Required
No new data. Computed from existing uncertainty products and literature values.

---

## 8. Restoration Effectiveness Monitoring (High Impact, High Effort)

### Problem
The current pipeline detects where restoration is needed but cannot
verify whether restoration interventions (canal blocking) are working.
This is the critical gap for carbon credit MRV: Verra requires evidence
that interventions are reducing emissions.

### Proposed Solution
Before/after comparison capability:
- Split the time series at the intervention date
- Compare pre-intervention and post-intervention velocity
- Successful canal blocking should show:
  - Subsidence rate decrease (velocity becomes less negative)
  - Backscatter decrease near blocked canals (rising water table)
  - Coherence decrease in rewetted areas (changing surface conditions)

Create a "restoration effectiveness" product:
```
effectiveness = velocity_post - velocity_pre
```
Positive values = subsidence slowing = intervention working.

### Data Required
- Pre-intervention baseline (current pipeline output)
- Post-intervention acquisitions (future Sentinel-1 data)
- Intervention dates and locations from field teams (Pak Agus)

---

## 9. Coherence as Land Cover Proxy (Low Impact, Very Low Effort)

### Problem
No land cover information is used in the current analysis, and obtaining
optical imagery requires a separate data pipeline.

### Proposed Solution
InSAR temporal coherence is already a land cover indicator in tropical
peatlands:
- High coherence (>0.6): bare soil, urban, bridges, cleared land
- Moderate coherence (0.3-0.6): plantation, sparse vegetation
- Low coherence (<0.3): dense forest, water

Export the coherence map with a land-cover-proxy classification.
This is a free byproduct of existing processing -- zero additional
computation or data.

### Data Required
Already computed (coherence_median.tif).

---

## Implementation Priority

| # | Improvement | Impact | Effort | Dependencies | Suggested Phase |
|---|---|---|---|---|---|
| 1 | Confidence mapping | High | Low | None | Phase 1 (immediate) |
| 5 | Spatial coherence filtering | Medium | Low | None | Phase 1 |
| 9 | Coherence as land cover proxy | Low | Very low | None | Phase 1 |
| 7 | Error budget | Medium | Low | None | Phase 1 |
| 4 | Peat depth integration | High | Low | CIFOR peat map download | Phase 2 |
| 2 | Seasonal decomposition | High | Medium | 2+ years of data preferred | Phase 2 |
| 3 | Land cover stratification | High | Medium | Sentinel-2 composite | Phase 2 |
| 6 | Optical cross-validation | Medium | Medium | Sentinel-2 NDVI | Phase 2 |
| 8 | Restoration effectiveness | High | High | Post-intervention data | Phase 3 |

Phase 1 items use only existing pipeline outputs and can be implemented
in 1-2 days. Phase 2 items require one additional free dataset each.
Phase 3 requires future temporal data.
