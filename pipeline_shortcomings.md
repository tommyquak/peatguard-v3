# PeatGuard Pipeline Shortcomings
## Identified 2026-03-27 -- Methodology Audit

Reference: These issues affect the accuracy and confidence of restoration
zone detection in the Kapuas AOI. Ordered by impact on results.

---

### S1. No Atmospheric Correction (CRITICAL)
**Impact:** 5-15 mm/yr systematic velocity bias
**Status:** Code written, CDS API times out at runtime

Tropical Kalimantan has high water vapor causing 5-20mm equivalent
phase delay per acquisition. Without ERA5 correction, the reported
mean velocity of -31 mm/yr could actually be -16 to -26 mm/yr.
That is a ~50% uncertainty band on the headline number.

PyAPS/ERA5 is configured but `tropo_pyaps3.py` crashes during ERA5
data download (CDS API timeout or rate limit). Alternative: use
GACOS (Generic Atmospheric Correction Online Service) which provides
pre-computed tropospheric delay maps and does not require the CDS API.

**Fix:** Try GACOS as alternative to ERA5, or pre-download ERA5 data
outside the pipeline and mount as a volume.

---

### S2. Wrong or Suboptimal Subswath (CRITICAL)
**Impact:** 45% interferometric pair failure rate
**Status:** Unresolved

The AOI at 114.3E may be at the edge of IW3's ground coverage.
Evidence: 13 of 29 pairs failed with "insufficient burst overlap in
IW3." A 55% pair success rate is well below the >80% target for SBAS.
Sparse network connectivity makes some dates vulnerable to single
unwrapping errors propagating through the time series.

IW1 (near-range) or a different orbit track may provide full AOI
coverage with all bursts, potentially doubling the usable pair count.

**Fix:** Query ASF for burst coverage of IW1/IW2/IW3 at 114.3E on the
current orbit. If IW1 covers the AOI fully, switch subswath.

---

### S3. Approximate Georeferencing (HIGH)
**Impact:** 1-3 km positional error
**Status:** Known since initial deployment, unfixed

Velocity uses an affine approximation from burst-merged lat/lon
lookup tables. The 1-3 km error exceeds the canal influence radius
(1200m), meaning we cannot reliably attribute subsidence to specific
canals. MintPy has a built-in geocoding step (`mintpy.geocode = yes`)
that was disabled because export handles it separately, but the
export uses the same approximate transform.

**Fix:** Enable MintPy's geocoding step, which uses the full geometry
lookup tables for proper radar-to-geographic coordinate conversion.
Or use ISCE2's geocodeGdal step post-unwrapping.

---

### S4. Misleading "Stable" Classification (HIGH)
**Impact:** Underestimates degradation extent
**Status:** Unresolved

The "stable" class spans -20 to 0 mm/yr. In peatland science,
natural peat accumulation is ~1 mm/yr. Any subsidence rate below
about -5 mm/yr on peat indicates net carbon loss. Labeling -15 mm/yr
as "stable" misleads stakeholders into thinking those areas are fine
when they are actively losing carbon.

**Fix:** Reclassify:
- Severe: < -50 mm/yr (unchanged)
- Active drying: -50 to -20 mm/yr (unchanged)
- Moderate drying: -20 to -5 mm/yr (NEW -- ongoing but slow carbon loss)
- Stable: -5 to +5 mm/yr (natural variability range)
- Rebound/noise: > +5 mm/yr

---

### S5. Questionable Reference Point (MEDIUM)
**Impact:** Unknown velocity baseline shift
**Status:** Workaround applied (maskFile=no)

The fixed reference at [-2.4969, 114.312148] falls in a masked-out
area (low coherence / disconnected connected component). We bypassed
the mask check, but this means MintPy uses a potentially unreliable
pixel as the zero-velocity reference. Any error in the reference
pixel shifts the entire velocity field uniformly.

**Fix:** Analyze the coherence and connected component maps to find
the highest-coherence pixel within the AOI that is on stable ground
(ideally non-peat substrate). Update config with verified coordinates.

---

### S6. No Independent Validation (MEDIUM)
**Impact:** Cannot confirm results are correct
**Status:** No validation performed

There are no ground truth measurements (GPS, leveling, piezometers)
in the AOI. The subsidence rates have not been cross-validated against
any independent dataset. Published rates for Kalimantan peatlands
(Hooijer et al. 2012) provide a plausibility check but not validation.

**Fix:** Compute Sentinel-2 NDVI trend for the AOI and calculate
spatial correlation with InSAR velocity. If r > 0.5, this provides
independent evidence that the subsidence signal is real. Also overlay
Global Forest Watch deforestation timing to check if high-subsidence
areas correspond to recently cleared peat.

---

### S7. Canal Detection Lacks Linearity Filter (LOW)
**Impact:** False positive canals from dark patches
**Status:** Unresolved

The canal detection uses a simple backscatter threshold that catches
any dark feature, not specifically linear structures. Dark water
bodies, shadows, and wet bare soil can be misidentified as canals.
The water mask removes large water bodies but small non-linear dark
patches remain.

**Fix:** Add a linearity metric (e.g., ratio of major to minor axis
of each connected component, or Hough line detection) to filter out
non-linear features from the canal mask.

---

### S8. Single-Year Temporal Coverage (LOW for now)
**Impact:** Higher velocity noise, seasonal aliasing
**Status:** By design (2024 data only)

16 valid pairs over 12 months provides minimal temporal sampling.
Random atmospheric noise averages down with sqrt(N), so doubling the
pairs from 16 to 32 would reduce noise by ~30%. Extending to 2+ years
also enables seasonal decomposition (separating irreversible
subsidence from reversible wet/dry oscillation).

**Fix:** Extend the acquisition search to 2023-01-01 through
2024-12-31 (or later). Download additional SLC scenes and reprocess.
This is a data volume increase, not a code change.

---

### S9. Risk Score Not Site-Calibrated (LOW)
**Impact:** Relative ranking is valid but absolute scores are arbitrary
**Status:** Literature-calibrated but not site-calibrated

The 0.45/0.55 weights and 1200m influence radius are from Hooijer et
al. (2012) for Sumatran peatlands. Kalimantan peat may have different
hydraulic conductivity, meaning different influence radius and
subsidence-drainage relationships. Without field measurements, we
cannot calibrate to this specific site.

**Fix:** Long-term: field collaboration with Tanjungpura University
for piezometer data. Short-term: sensitivity analysis showing how
results change with different weight/radius assumptions.
