# PeatGuard: A Scientific Report

**Satellite-based Peatland Subsidence Monitoring for Restoration Decision-Making**

Author: Tommy Quak, National University of Singapore
Date: 2026-04-19
For: Hult Prize 2026 · collaborators · restoration partners

---

## Executive Summary

PeatGuard is a system that uses free, public satellite radar data to measure how fast the ground is sinking on Indonesian peatlands, and to turn those measurements into a restoration-priority map that tells decision-makers *where to block drainage canals first*.

Tropical peat swamps hold more carbon per hectare than any other ecosystem on Earth, but when they are drained for oil palm, pulpwood, or small-holder farming, they begin to oxidise — slowly burning underground and releasing CO₂ for decades. Indonesia alone loses an estimated 100–250 million tonnes of CO₂ every year from drained peat. Rewetting and canal-blocking stop the process, but restoration budgets are finite and the degraded peat area is enormous: you cannot fund the restoration of every canal, so you need to know which canals are doing the most damage.

PeatGuard answers that question by producing a *risk map* every month, automatically, for any peatland in the world, at a cost of roughly ten US dollars per square kilometre per year. The inputs are free satellite data. The outputs are ordinary map layers that a district forestry office can open in QGIS or ArcGIS and hand to a restoration team.

This report is not a technical specification. It is a plain-language explanation of what PeatGuard is, why it works, what it does and does not tell you, and how it fits into the real-world restoration decision.

---

## Part 1 — The Problem

### 1.1 Peatlands in a sentence

Peatland is wet ground where dead plant material has piled up for thousands of years without fully decomposing. In Indonesia it forms domes 4–12 metres deep, covered by mangrove-like forest. As long as the peat stays wet, it is chemically stable and, per hectare, holds ten to thirty times the carbon of an equivalent rainforest.

### 1.2 What drainage does

When people dig canals to plant palm oil, pulpwood, or smallholder crops, the water table drops. Oxygen reaches the peat for the first time in millennia, and aerobic bacteria start to eat it. The surface slowly sinks — typically between two and five centimetres per year in drained plantations — and carbon dioxide leaves in the air above. A drained peatland is essentially a very slow coal fire with the smoke going straight into the atmosphere.

This is not a one-off: as long as the water table remains low, the peat keeps oxidising. A single 10 km canal can produce a zone of continuous CO₂ emission 1 to 3 kilometres wide that lasts until the peat is gone — in places, a century or more.

### 1.3 Why it is Indonesia's problem first

Indonesia holds approximately 36 % of the world's tropical peat. The 2015 peat fires — which burned through the dry season and produced haze that closed schools across Southeast Asia — caused an estimated 15 to 25 million tonnes of CO₂ per day at their peak. Global average daily anthropogenic emissions are roughly 100 million tonnes. For a few weeks in 2015, a small part of Sumatra and Kalimantan was emitting a quarter of the world's carbon.

The Indonesian government responded with the *Badan Restorasi Gambut dan Mangrove* (BRGM — Peatland and Mangrove Restoration Agency), which has a mandate to restore approximately 1.2 million hectares of degraded peat over five-year cycles. The two primary interventions are canal blocking and revegetation. Canal blocking is cheap and fast per unit; revegetation is slow and expensive. Priority matters enormously.

### 1.4 Why "priority" is hard

A restoration agency with a finite budget faces three questions it cannot answer without data:
1. Which drained peat areas are subsiding fastest?
2. Which canals are draining those fastest-subsiding areas?
3. Given limited money, where would a block save the most future emissions?

Until recently, the answers came from a thin mesh of ground stations — perhaps one piezometer or subsidence pole per 10 km². This is enough to produce national-scale averages, but not enough to tell a district office which of its twenty drainage canals to block first. You might block the least-damaging ones and think you had done your job.

### 1.5 Why satellites

Satellites do four things that ground stations cannot. First, they cover the whole peatland every six to twelve days, indefinitely, for free. Second, they see exactly the same way every visit, so they can measure change with a precision ground stations cannot match without enormous expense. Third, they see through cloud, which matters because the Indonesian peat belt is under cloud for most of the year. Fourth, their data is open: any analyst anywhere can verify your result.

PeatGuard is built entirely on free satellite data. Nothing in the pipeline depends on commercial imagery or proprietary sensors.

---

## Part 2 — How Satellites Measure Sinking Ground

### 2.1 Two useful kinds of satellite

Earth observation satellites come in roughly two flavours. Optical satellites (for example Sentinel-2 and Landsat) take colour photos — they see what we see, just from above, and only when there are no clouds. Radar satellites (Sentinel-1, NISAR, ALOS-2) send their own radio signal down and listen for the echo. Radar works in cloud, at night, and through thin vegetation. PeatGuard uses radar.

### 2.2 The trick: phase, not just brightness

A camera sees brightness. A radar can also see *phase* — the exact position within the radio wave's cycle that the returning echo is in, measured to a tiny fraction of the wavelength.

If the satellite visits the same spot twice and the ground has not moved, the phase of the echo is the same. If the ground has sunk by even a few millimetres, the echo now travels a slightly longer path back, and the phase shifts by an amount you can measure precisely.

Taking two radar images of the same place, stretched across time, and subtracting the phase of one from the other is called *interferometry*. The result is an *interferogram* — a map of phase change, which is a proxy for ground displacement. The precision is millimetres; the spatial coverage is tens of thousands of square kilometres per image. This is how PeatGuard — and every modern ground-motion monitoring system, from the London Crossrail tunnels to the Mexico City subsidence maps — measures how the surface is moving.

### 2.3 Why you need many pairs, not just two

A single interferogram tells you how much the ground moved between exactly two dates. That is noisy: weather, soil moisture, canopy growth, and instrument effects all corrupt any one measurement. To isolate the real, steady signal — *the long-term subsidence rate in millimetres per year* — you need many interferograms, distributed over time, and you need to invert them jointly.

The technique is called Small BAseline Subset InSAR (SBAS). The idea is the same as averaging many thermometers to get a more confident temperature reading, except the mathematics is considerably more involved: each interferogram constrains the *difference* between two dates, and you are solving for a consistent time series of heights. The output of SBAS is a velocity map: a number, in millimetres per year, at every location on the ground.

PeatGuard uses 31 satellite acquisitions between 2023 and 2024 (and a subset filter for 2024 when we want to isolate the most recent year). These are combined into 59 interferogram pairs, and all 59 are then blended by SBAS into one velocity map.

### 2.4 Why tropical peat is harder than other targets

Radar interferometry is easier over deserts, cities, and ice than over tropical forest. Three factors make peat tricky:

1. **Canopy decorrelation.** A radar echo from leaves is essentially random; the shorter the wavelength, the more easily it is scattered by small objects like twigs and leaves. The satellite PeatGuard primarily uses (Sentinel-1) transmits at C-band — wavelength about 5.6 centimetres, smaller than a typical leaf. Over intact peat-swamp forest, coherence (the measure of how "comparable" two radar images are) drops from close to 1 to close to 0 within a few weeks. Over cleared peat (palm plantation, burned-over land, bare soil), coherence holds up for months.

2. **Atmospheric water vapour.** Tropical air can carry 4–6 centimetres of precipitable water. That water slows down the radar signal, adding an apparent phase shift that looks exactly like ground motion. We correct for this using ERA5 reanalysis from the European Centre for Medium-Range Weather Forecasts, but the correction is not perfect.

3. **Phase wraps.** The phase of a radio wave is only defined modulo 2π. If the ground moves more than half a wavelength between acquisitions, the measurement "wraps around" — an ambiguity that must be resolved using neighbourhood information. Over flat, uniform peat, there aren't many neighbours to lean on, and phase-unwrapping errors can flip a measurement's sign.

The result is that, on any given peat AOI, a meaningful fraction of pixels will be *genuinely* unmeasurable with C-band. We cannot paper over this with processing. The honest answer — reflected in PeatGuard's output — is to publish an uncertainty band alongside the velocity. A pixel with high coherence gets a confident reading. A pixel with low coherence is flagged, and its risk estimate falls back on the only thing that *is* measurable there: proximity to drainage canals.

---

## Part 3 — What PeatGuard Does, Stage by Stage

PeatGuard has five sequential processing stages. Each takes the previous stage's output and adds a new piece of information. The full flow takes about fifteen hours for a 17 × 11 kilometre AOI on a laptop, or a couple of hours in the cloud.

### Stage 1 — Ingest (download)

The system searches the Alaska Satellite Facility (ASF) catalogue for every Sentinel-1 SAR acquisition covering the target area between the chosen start and end dates. For the Teluk Bayur pilot AOI in West Kalimantan, this is about thirty-one images totalling roughly 150 gigabytes. Each image is a *Single-Look Complex* product — raw radar data preserving both amplitude and phase, which is what interferometry needs.

Alongside the SAR data, the pipeline pulls down:
- ESA precise orbit files, which say exactly where each satellite was when it took each image (to a few centimetres);
- A digital elevation model (SRTM 30-metre), which is used to separate topographic phase from deformation phase.

Once a month (in the cloud-deployed version) or on demand (in the laptop version), Stage 1 adds any new acquisition to the local library.

### Stage 2 — InSAR pair processing

The heart of the pipeline. Given 31 SAR images, the system chooses which pairs to process. Not every pair — that would be 31×30/2 = 465 pairs. Instead, it chooses a *small baseline subset*: pairs where the two acquisition dates are close in time (≤ 48 days apart) and the two satellite positions in space are close together. This is the "SB" in SBAS: small-baseline pairs coherere more reliably.

For our AOI this yields 59 pairs.

Each pair is then processed through the ISCE2 software package:
1. Precise alignment (*co-registration*) of the two images to sub-pixel accuracy.
2. Terrain-corrected interferogram formation.
3. Phase filtering to suppress noise.
4. Phase unwrapping with SNAPHU (the industry-standard network-flow solver).
5. Geocoding to a common reference grid.

Each pair's products — unwrapped phase, coherence, connected components — are saved as cloud-optimised GeoTIFFs. For the Teluk Bayur run on 2026-04-19, all 59 pairs succeeded. Each pair takes about 8–10 minutes on an M4 laptop; the whole stage takes 8–10 hours.

### Stage 3 — Time-series inversion

The 59 interferograms are now jointly inverted by MintPy's *smallbaselineApp* into a single, coherent velocity map. The inversion does four things, in order:

1. **Network modification**: removes interferograms that are too noisy (coherence below a threshold) or too redundant.
2. **Reference-point selection**: picks one pixel on the ground as the "zero-motion" reference and expresses every other pixel's motion relative to it. This is a subtle choice — we come back to it in Part 5 — and is the single biggest source of calibration uncertainty in any InSAR velocity product.
3. **Phase-closure error correction**: detects and corrects cases where phase unwrapping went wrong in triangles of three interferograms that should sum to zero.
4. **SBAS inversion**: solves the joint least-squares problem that produces the final velocity map and an uncertainty estimate at every pixel.

The output is a raster of *line-of-sight velocity*: millimetres per year, positive towards the satellite, negative away. Since the satellite looks obliquely (not straight down), we convert LOS velocity to *vertical velocity* assuming all real motion is up-down (a reasonable assumption for peat subsidence, which is almost entirely vertical). The conversion factor at our viewing geometry is 1.25: a 1 mm/yr LOS motion corresponds to about 1.25 mm/yr of vertical subsidence.

This stage also produces a *coherence* raster: a value between 0 and 1 at every pixel that says how trustworthy the velocity estimate is there. High coherence (> 0.5) is confident. Low coherence (< 0.3) is unreliable — typically dense canopy, water, or rapid land-cover change.

### Stage 4 — Backscatter composite

In parallel, the pipeline processes Sentinel-1 *Ground Range Detected* (GRD) products, which are lower-resolution but amplitude-only. These go through:
1. Radiometric calibration to sigma-nought (a physical backscatter coefficient in decibels).
2. Lee-Sigma speckle filtering (removes the grainy "salt-and-pepper" noise inherent to radar).
3. Terrain correction using the SRTM DEM.
4. Temporal median composite over the 14–16 acquisitions in 2024.

The output is a cloud-free, seasonal backscatter map of the AOI in decibels. This serves two purposes: it is a *visual basemap* for the risk map, and it is the *input to canal detection*.

### Stage 5 — Analysis

This is where measurements become decisions. Stage 5 runs seven sub-steps:

1. **Water mask.** Any pixel with VV backscatter below −18 dB is flagged as open water (river, pond, lake). Water bodies should not be treated as land and should not contribute to risk.
2. **Canal detection.** The 5th percentile of VV backscatter — low enough to catch water-filled drainage ditches but not so low that it catches shadow — is used as a threshold. Connected-component filtering removes small noise blobs (minimum 300 pixels). Water bodies are then subtracted from the canal mask, so that rivers are not mistaken for drainage canals.
3. **Canal distance.** For every pixel on the ground, the Euclidean distance in metres to the nearest canal is computed. Pixels on a canal get distance zero; pixels far from any canal get a large number.
4. **Subsidence classification.** Velocity is sorted into five classes: severe (faster than −50 mm/yr), active drying (−50 to −20), moderate drying (−20 to −5), stable (−5 to +5), and rebound/noise (faster than +5, which is physically unusual for peat and typically indicates either measurement error or deliberate re-flooding). Water pixels are added as a sixth class.
5. **Peat-extent mapping.** Using the World Resources Institute's Indonesia peatland layer, we mask the risk computation to known peat soils. Mineral-soil areas, urban fabric, and non-peat wetland do not contribute to peatland restoration priority.
6. **Risk scoring.** The final decision layer. For every peat pixel, we combine two signals: the proximity to a drainage canal (a physical driver, strong near zero and falling linearly to zero at 600 metres, based on the Dupuit equation for groundwater drawdown) and the subsidence velocity (a physical observation, saturating at −40 mm/yr). The weighted sum (45 % proximity, 55 % subsidence) is the *canal risk score*: a number between 0 and 1 where 1 means "drain this one first".
7. **Cross-validation.** The pipeline compares its velocity against the Hansen Global Forest Change year-of-loss map. If our logic is sound, recently-cleared areas should show faster subsidence than long-ago-cleared areas — because drainage-induced subsidence is fastest in the first 5–10 years and decays thereafter. When this gradient comes out the right way round, we label the run **validation CONSISTENT**. When it reverses, we label it **INCONSISTENT** and treat the velocity result with suspicion.

The analysis stage emits a *confidence band* alongside the risk map. Every pixel is tagged as either velocity-backed (the subsidence signal was trustworthy here) or proximity-only (only canal-distance information is available; the risk is a linear extrapolation of canal proximity). This keeps the map honest: a judge can see at a glance which reds are built on evidence and which are inferred.

---

## Part 4 — Why the Risk Map is Built That Way

### 4.1 Why a weighted sum of proximity and velocity

A naive risk layer would just say "wherever the ground is sinking fastest is worst". That would be right over open, coherent peat, but wrong over canopy-covered peat where the subsidence signal is too noisy to see. A second naive layer would say "wherever there is a canal is worst". That would be right for the physical driver, but insensitive to the fact that some canals matter far more than others — a canal through a shallow peat margin moves very little carbon, while a canal through a 6-metre peat dome moves enormous amounts.

The weighted sum captures both: *where we can see the ground, we trust the measurement; where we can't, we fall back on the canal*. The weights (0.45 proximity, 0.55 subsidence) come from Hooijer et al. (2012), who fitted a water-table vs. subsidence curve across tropical peat and found the canal-proximity term and the direct-measurement term contribute in roughly that ratio when both are available.

### 4.2 Why 600 metres, not 1,200

The original Hooijer calibration uses a 1–1.5 km "zone of influence" around each canal — the distance over which the water table has been meaningfully lowered. PeatGuard's earlier runs used 1,200 metres. In our Teluk Bayur AOI, with a dense canal network and some over-detection noise, a 1,200-metre halo around every canal blob produced a map where almost the entire scene was rated "critical". That is not useful as a prioritisation tool.

We therefore use the lower bound of Hooijer's range (600 m) as the drainage-influence radius. This is conservative: it will miss some real far-field drainage effects, but it will not drown a district officer in false reds. The trade-off is documented explicitly in the methodology review and can be reverted via the config file.

### 4.3 Why −40 mm/yr is the "severe" threshold

Hooijer measured average subsidence rates of 20–50 millimetres per year in the first five years after drainage in Central Kalimantan and Riau. We pick the midpoint of the upper half of that range (−40 mm/yr) as the saturation point of the subsidence risk score. A pixel subsiding at −40 mm/yr or faster gets subsidence-risk = 1.0. A pixel subsiding at the natural peat-accumulation rate (around +1 mm/yr) gets subsidence-risk = 0.0.

This calibration is defensible in literature, transparent in the code, and tuneable for other regions where the subsidence regime may be different.

### 4.4 Why the confidence band matters

Early versions of PeatGuard published a single risk map with no indication of where the signal was strong and where it was extrapolated. A judge looking at the map could not tell whether they were being shown evidence or inference. The confidence band — published as a second raster alongside the risk map — removes that ambiguity. In ArcGIS or QGIS, a user can overlay the band as a hatched pattern on top of the risk map: solid fill for velocity-backed, hatched fill for proximity-only. That turns the map into an honest decision aid rather than a possibly-overconfident decision aid.

---

## Part 5 — How We Know the Map is Right

A risk map that nobody can audit is no better than a coin flip. PeatGuard ships four kinds of validation, running automatically at the end of every pipeline execution.

### 5.1 Forest-change cross-validation

The Hansen Global Forest Change dataset records, for every 30-metre pixel on Earth, the year of tree-cover loss (if any). From peatland drainage science, we expect a consistent pattern: pixels cleared recently should be subsiding faster than pixels cleared long ago, because the bulk of the oxidation happens in the first 5–10 years after water-table drop.

PeatGuard takes every peat pixel in the AOI, bins it by clearing cohort (2001–2005, 2006–2010, 2011–2015, 2016–2023), and computes the mean subsidence velocity per cohort. When the recent-cohort velocity is more negative than the old-cohort velocity — the expected gradient — the run is labelled **CONSISTENT** and the pipeline continues. When it is reversed or flat, the run is labelled **INCONSISTENT** and the user is told to treat the velocity product with care.

This is not a smoking-gun validation, but it is a strong falsification test: if our SBAS result is dominated by unwrap error or reference-point drift, we expect no gradient at all, and the test will flag it.

### 5.2 Backscatter–coherence consistency

Dense forest canopy has *high* backscatter (many leaves scattering the signal back) and *low* coherence (the leaves move between acquisitions). Cleared peat has the opposite. PeatGuard computes the Pearson correlation between VV backscatter (in dB) and temporal coherence at every pixel, and reports the coefficient in the validation JSON. A positive correlation of 0.1–0.3 is expected and signals that both measurements are responding to land-cover in the expected way. A zero or negative correlation would suggest something has gone wrong with either product.

### 5.3 OSM waterway cross-check

When OpenStreetMap has mapped waterways in the AOI, PeatGuard rasterises them and checks whether the detected canal mask agrees. Precision, recall, and F1 are reported. For sparsely-mapped areas (Teluk Bayur currently has almost no OSM canal polygons), the F1 is low not because our detector is bad but because the ground truth is incomplete. This validation becomes more meaningful in better-mapped areas, and flags cases where our detector has drifted from reality.

### 5.4 Sentinel-2 NDVI time-series (when available)

Where the `pystac_client` and `planetary-computer` Python packages are installed and Sentinel-2 optical imagery is available through the Microsoft Planetary Computer STAC catalogue, PeatGuard can optionally correlate its subsidence velocity with the trend in NDVI over the same period. Falling NDVI in subsiding peat is a strong sign of drainage stress; stable NDVI with falling elevation is a sign of either wetting or canopy persistence over drained peat. These patterns are diagnostic and can be published alongside the velocity map.

### 5.5 The honest limits of validation

None of the above is a replacement for ground-truth validation with piezometers, subsidence poles, or airborne LiDAR. PeatGuard's current validations are *internal consistency* checks — they can catch gross processing errors but cannot verify absolute accuracy. For carbon MRV (for example Verra VM0036 or VM0048 methodologies), external validation is mandatory and PeatGuard does not yet claim MRV-grade output.

The practical position we take in the pitch deck is: PeatGuard is a **restoration-priority decision layer** — it tells you *where to look first*, not *how many tonnes of CO₂ you have saved*. The former is an easier problem than the latter, and PeatGuard is deliberately scoped to the former.

---

## Part 6 — What the User Actually Sees

Loaded into ArcGIS Pro or QGIS, PeatGuard outputs 23 raster layers plus several JSON validation reports. For a decision-maker, the layers group into four stories.

### 6.1 The decision story

Two layers, shown together:
- **canal_risk** — red-to-yellow-to-green, showing priority. Darker red = block this canal sooner.
- **canal_risk_confidence** — a binary overlay (solid vs hatched) showing which pixels are built on direct subsidence evidence and which are inferred from canal proximity only.

A district officer can open these, zoom to their jurisdiction, identify the top-priority canals, and use them as the agenda for the next restoration planning meeting. No InSAR training is required.

### 6.2 The evidence story

Three layers, for anyone who asks "where does the red come from?":
- **subsidence_velocity** (millimetres per year): the actual measurement.
- **subsidence_class**: the measurement sorted into five intuitive classes (severe, active, moderate, stable, rebound/noise).
- **coherence_median**: the quality mask; bright pixels are trustworthy, dark pixels are unreliable.

These allow an auditor to drill into the risk map, inspect the underlying data at any location, and decide whether they trust the finding.

### 6.3 The context story

Four layers, for situational awareness:
- **canal_mask** (the detected drainage lines)
- **canal_distance** (metres to the nearest canal)
- **water_mask** (rivers and open water, excluded from risk)
- **peat_extent** (the WRI peat polygons, bounding the analysis)

### 6.4 The secondary-validation story

Five Hansen-forest-change layers, for the audit trail:
- **deforestation_year**, **time_since_clearing**, **clearing_risk_factor**, **treecover2000**, **degraded_peatland**

These let a reviewer check PeatGuard's cohort gradient for themselves, by hand if they want to.

### 6.5 The quality report

Every pipeline run writes `pipeline_report.json` summarising:
- mean velocity
- coherence mean and percentile survival
- canal coverage percentage
- classification histogram
- mean risk and critical-risk percentage
- validation verdict (CONSISTENT / INCONSISTENT)
- error-budget pointers (reference-point policy, atmospheric correction, unwrap-error method, thresholds applied)

A stakeholder does not need to read the JSON, but the JSON is what distinguishes a reproducible science product from a pretty picture.

---

## Part 7 — Honest Limitations

Everything in this section is known to PeatGuard's developers and is not obscured by the pipeline. A judge asking hard questions deserves hard answers.

### 7.1 C-band does not see under canopy

Sentinel-1 transmits at a wavelength too short to penetrate a dense, wet tropical canopy. Over intact peat-swamp forest (which is where *most undrained* peat still is), coherence collapses within weeks and PeatGuard cannot produce a velocity estimate. We fall back on canal-proximity risk, which is better than nothing but is not a measurement.

The fix is **L-band radar**: the Japanese ALOS-2 satellite (free to partner institutions through a JAXA Announcement of Opportunity) and NASA's NISAR satellite (launching 2026, free to all) both transmit at 24-centimetre wavelength, which penetrates canopy better. An L-band version of PeatGuard — running alongside the C-band version in a multi-sensor fusion mode — would be the single biggest accuracy improvement possible. A JAXA ALOS-2 application has been drafted and is ready for submission.

### 7.2 Two-year temporal baseline is at the edge of C-band coherence

The longer the time between two acquisitions, the more the forest canopy changes and the harder it is to make a coherent interferogram. For tropical C-band, the practical ceiling is about 12–24 months. Beyond that, coherence collapses to the noise floor. PeatGuard's 2023–2024 two-year window is pushing this limit, and the resulting thin coverage is one of the main reasons an L-band follow-up is needed.

For the current reporting period, we restrict the SBAS inversion to 2024-only pairs by default. This is configurable: a user analysing a less-forested site (a palm plantation, say) can extend back to 2023 or earlier without the coverage collapse.

### 7.3 Reference-point uncertainty is real

Every InSAR velocity map is *relative*. We define one pixel to be "stable" (velocity = 0) and measure every other pixel against it. If the reference pixel is itself subsiding by 5 mm/yr, every pixel in the map is off by 5 mm/yr. For absolute accuracy, the reference must be physically stable — on bedrock, concrete, or confirmed-stable ground. For Teluk Bayur's pilot, our pinned reference is a high-coherence pixel near the AOI's northern edge, assumed stable. This assumption is not verifiable without a ground GPS station at that pixel. We publish the pixel's location with every product so that any external reviewer can question it.

In operational mode, we apply a literature-based calibration (Hooijer et al. 2012 mean drainage-induced subsidence for Central Kalimantan ≈ −25 mm/yr) to shift the whole field into a physically-plausible range. This is a defensible operational choice for prioritisation but is not a substitute for ground truth.

### 7.4 Phase-unwrapping errors can flip individual pixels

Over flat terrain with low coherence, the unwrapping step sometimes produces results that differ from the true deformation by multiples of half the wavelength. These errors are mostly caught by MintPy's phase-closure correction, but not always. A single bad pixel in the velocity map can look like severe subsidence or severe uplift that is not real. PeatGuard's defence is the 9×9 median filter applied before risk scoring, plus the coherence mask that excludes unreliable pixels entirely. Residual errors can still appear and are one reason the map is sanity-checked against Hansen cohorts before it is published.

### 7.5 The carbon figure is a back-of-envelope, not an MRV claim

PeatGuard reports a total tCO₂/yr figure at the end of each analysis run, computed by multiplying subsidence velocity by an oxidation coefficient (≈ 0.5 tCO₂ per mm/yr per hectare, from Hooijer et al.). This is adequate for ballpark prioritisation ("block this canal before that one, because it affects 5× more carbon") but inadequate for issuance of carbon credits. A full MRV workflow needs per-pixel uncertainty propagation, compaction-vs-oxidation decomposition, and an independent verifier.

### 7.6 Canal detection sees water, not necessarily canals

Our canal detector finds low-backscatter linear features. Rivers, ponds, and deeply-flooded rice paddies look the same to C-band as a narrow drainage canal, so we explicitly subtract the water mask from the canal mask to avoid treating rivers as canals. The residual over-detection (plantation tracks with shaded undergrowth, for example) is usually a small percentage but is visible in the map. A future version may add an elongation filter (real canals are 10–30 m wide and kilometres long; false canals are typically blob-shaped) to suppress the remainder.

### 7.7 The pipeline runs for hours on a laptop

An end-to-end PeatGuard run for one 17 × 11 km AOI takes 10–15 hours on a MacBook Pro. This is acceptable for monthly monitoring but uncomfortable for rapid-response use. The cloud deployment (Cloud Run on Google Cloud Platform, 8 CPU / 32 GB) reduces this to ~3 hours and is how the production system is deployed. Neither is instant; neither is meant to be.

---

## Part 8 — What Comes Next

### 8.1 L-band integration

The single most impactful improvement is adding L-band data. The fusion layer in the pipeline is already scaffolded: when a second (L-band) velocity map is available, the pipeline will automatically combine it with C-band by coherence-weighted averaging, producing a single fused velocity map that sees both under canopy (L-band strength) and in cleared areas (C-band strength). The JAXA ALOS-2 Announcement of Opportunity and the NASA NISAR release in 2026 are the two paths to this.

### 8.2 Ground validation partnerships

Even a rough-and-ready piezometer network — five or ten water-table loggers across an AOI — would let PeatGuard calibrate its reference point against ground truth. Partnerships with BRGM, WWF-ID, and local university field teams are the natural path. The logistical and budget plan is a follow-up, not a software change.

### 8.3 Multi-AOI operational mode

The current pipeline processes one AOI at a time. An operational agency needs a view over dozens or hundreds of sites. The cloud deployment is already container-isolated per AOI; the remaining work is the dashboard that aggregates across sites and lets a district office see their jurisdiction in a single map. The TiTiler-based dashboard prototype in the repository is the starting point.

### 8.4 Seasonal decomposition

A single annual velocity figure blends two physically distinct processes: permanent oxidation (one-way carbon loss) and reversible water-table oscillation (dry-season shrink, wet-season swell). Separating them requires a seasonal decomposition of the time series — mathematically straightforward, but needs at least two years of data to resolve. When a 2025–2026 data set is available, PeatGuard will publish separate "irreversible" and "reversible" subsidence products, which is a step closer to MRV credibility.

### 8.5 Confidence layer that consumers can use

Current confidence is binary (velocity-backed or proximity-only). A future version will publish a continuous confidence band combining coherence, velocity uncertainty, number-of-contributing-pairs, and local spatial consistency into a single 0–1 quality map. That map can then multiply into the risk score (`adjusted_risk = risk × confidence`) to produce a naturally attenuated decision layer where noisy regions self-downrank.

### 8.6 Dashboard and reporting UI

A static map is a starting point. A living dashboard — where district officers can click a canal, see its risk score, and compare month-to-month — is what turns the technology into a workflow. The existing TiTiler + Leaflet prototype serves individual COGs. Production use needs user accounts, saved views, change alerts, and export to report templates.

---

## Part 9 — The Restoration Use Case in Concrete Terms

To make this tangible, consider the following scenario for a district forestry office in Central Kalimantan.

1. The office opens PeatGuard's monthly risk map for its jurisdiction in ArcGIS Pro.
2. Only the `canal_risk` and `canal_risk_confidence` layers are turned on, plus the world-topographic basemap.
3. Five "critical" red clusters pop out. The officer zooms into each and switches on `canal_mask` — confirming that the red is indeed tracing linear canal features, not blob-shaped noise.
4. The officer switches on `subsidence_velocity` and `subsidence_class` over one of the clusters. The pixels along the canal are classified "active drying" or "severe"; the pixels far from the canal are "stable". This is what drainage-induced subsidence should look like.
5. The officer switches on `deforestation_year` and sees that most of the red cluster was cleared in 2014–2018 — a young enough drainage that aggressive subsidence is expected.
6. The officer makes a call: block the two canals inside this cluster in the next quarter's work plan. The restoration team is given a shapefile of the canal centreline, extracted from PeatGuard's canal_mask with a one-line geoprocessing tool.
7. Six months later, the same analysis is run for the same AOI. The risk map shows the blocked canals fading from red to yellow, because the subsidence has slowed. This is a closing loop: the pipeline is both the planning tool and the monitoring tool.

None of the above requires the officer to understand SBAS, connectivity-component thresholds, or Hooijer's drainage equation. PeatGuard's value is that it produces decision layers that are usable by someone who does not need to know any of the science underneath.

---

## Part 10 — Acknowledgements and Positioning

PeatGuard is a project by Tommy Quak (National University of Singapore, Geography Department) for the 2026 Hult Prize challenge. The scientific foundation rests on two decades of peer-reviewed tropical peat research, principally by Aljosja Hooijer and colleagues at Deltares; on the open SAR data archives operated by NASA Alaska Satellite Facility and ESA Copernicus; and on the open-source software ecosystem — ISCE2 (JPL), MintPy (Zhang et al.), SNAPHU (Chen & Zebker), PyAPS (JPL), and the dozens of Python geospatial libraries (rasterio, scikit-image, numpy, h5py).

The pipeline code is open-source and available at github.com/tommyquak/peatguard-v3. The methodology is documented in `PeatGuard_Methodology_Review.md` in the repository. The full data-processing choices, including every threshold and weight, are specified in `config/default.yaml` and overridable at runtime.

**PeatGuard is positioned as a decision-support system, not an MRV system.** It will tell a restoration agency where to work first. It will *not*, in its current form, produce carbon credits. Both positions are scientifically honest; both are defensible; the scope of each is explicitly documented in Sections 7.5 and 8.4 of this report.

If the agency, donor, or policymaker reading this wants to extend PeatGuard toward MRV, the roadmap is (1) L-band data, (2) ground-GPS reference points, (3) seasonal decomposition, (4) an external verifier. None of those are software changes; all are institutional partnerships. The software is the smallest part of the problem.

---

*End of report. Word count ≈ 7,800. For an executive summary, read Part 1. For an audit, read Parts 5 and 7. For implementation details, the companion file `PeatGuard_Methodology_Review.md` carries the full code-level audit.*
