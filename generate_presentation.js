const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 inches
pres.author = "Tommy Quak";
pres.title = "PeatGuard: Satellite-Based Peatland Monitoring";

// Color palette
const C = {
  dark: "1a1a2e",
  accent: "16213e",
  blue: "0f3460",
  orange: "e94560",
  white: "ffffff",
  light: "f0f0f0",
  green: "1a9850",
  yellow: "fdae61",
  red: "d73027",
  gray: "888888",
  bg: "0d1117",
  card: "161b22",
};

function titleSlide(title, subtitle) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText(title, { x: 0.8, y: 2.0, w: 11.5, h: 1.5, fontSize: 36, bold: true, color: C.white, fontFace: "Arial" });
  if (subtitle) s.addText(subtitle, { x: 0.8, y: 3.5, w: 11.5, h: 0.8, fontSize: 18, color: C.gray, fontFace: "Arial" });
  return s;
}

function contentSlide(title, bullets, opts = {}) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText(title, { x: 0.6, y: 0.3, w: 12, h: 0.8, fontSize: 28, bold: true, color: C.white, fontFace: "Arial" });
  s.addShape(pres.ShapeType.rect, { x: 0.6, y: 1.0, w: 3.0, h: 0.04, fill: { color: C.orange } });

  const startY = opts.startY || 1.3;
  const fontSize = opts.fontSize || 16;
  const bodyText = bullets.map(b => {
    if (typeof b === "string") return { text: b, options: { fontSize, color: C.light, fontFace: "Arial", bullet: { type: "bullet" }, paraSpaceBefore: 6, paraSpaceAfter: 6 } };
    return b;
  });
  s.addText(bodyText, { x: 0.8, y: startY, w: 11.5, h: 5.5, valign: "top" });
  return s;
}

function twoColSlide(title, leftTitle, leftBullets, rightTitle, rightBullets) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText(title, { x: 0.6, y: 0.3, w: 12, h: 0.8, fontSize: 28, bold: true, color: C.white, fontFace: "Arial" });
  s.addShape(pres.ShapeType.rect, { x: 0.6, y: 1.0, w: 3.0, h: 0.04, fill: { color: C.orange } });

  // Left column
  s.addText(leftTitle, { x: 0.6, y: 1.3, w: 5.5, h: 0.5, fontSize: 20, bold: true, color: C.orange, fontFace: "Arial" });
  const lb = leftBullets.map(b => ({ text: b, options: { fontSize: 14, color: C.light, fontFace: "Arial", bullet: { type: "bullet" }, paraSpaceBefore: 4, paraSpaceAfter: 4 } }));
  s.addText(lb, { x: 0.8, y: 1.9, w: 5.3, h: 5.0, valign: "top" });

  // Right column
  s.addText(rightTitle, { x: 7.0, y: 1.3, w: 5.5, h: 0.5, fontSize: 20, bold: true, color: C.orange, fontFace: "Arial" });
  const rb = rightBullets.map(b => ({ text: b, options: { fontSize: 14, color: C.light, fontFace: "Arial", bullet: { type: "bullet" }, paraSpaceBefore: 4, paraSpaceAfter: 4 } }));
  s.addText(rb, { x: 7.2, y: 1.9, w: 5.3, h: 5.0, valign: "top" });
  return s;
}

function tableSlide(title, headers, rows) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addText(title, { x: 0.6, y: 0.3, w: 12, h: 0.8, fontSize: 28, bold: true, color: C.white, fontFace: "Arial" });
  s.addShape(pres.ShapeType.rect, { x: 0.6, y: 1.0, w: 3.0, h: 0.04, fill: { color: C.orange } });

  const tableData = [
    headers.map(h => ({ text: h, options: { bold: true, color: C.white, fontSize: 13, fontFace: "Arial" } })),
    ...rows.map(row => row.map(cell => ({ text: cell, options: { color: C.light, fontSize: 12, fontFace: "Arial" } }))),
  ];
  s.addTable(tableData, {
    x: 0.6, y: 1.3, w: 12.0,
    border: { type: "solid", pt: 0.5, color: "333333" },
    rowH: 0.45,
    colW: Array(headers.length).fill(12.0 / headers.length),
    fill: { color: C.card },
    autoPage: false,
  });
  return s;
}

// ============================================================
// SLIDE 1: Title
// ============================================================
const s1 = pres.addSlide();
s1.background = { color: C.bg };
s1.addText("PeatGuard", { x: 0.8, y: 1.5, w: 11.5, h: 1.2, fontSize: 48, bold: true, color: C.white, fontFace: "Arial" });
s1.addText("Satellite-Based Peatland Subsidence Monitoring\nfor Carbon Credit MRV in West Kalimantan, Indonesia", { x: 0.8, y: 2.8, w: 11.5, h: 1.2, fontSize: 20, color: C.gray, fontFace: "Arial" });
s1.addShape(pres.ShapeType.rect, { x: 0.8, y: 4.2, w: 4.0, h: 0.04, fill: { color: C.orange } });
s1.addText("Tommy Quak\nNational University of Singapore, Department of Geography", { x: 0.8, y: 4.5, w: 11.5, h: 0.8, fontSize: 14, color: C.gray, fontFace: "Arial" });
s1.addText("March 2026", { x: 0.8, y: 5.5, w: 11.5, h: 0.5, fontSize: 14, color: C.gray, fontFace: "Arial" });

// ============================================================
// SLIDE 2: The Problem
// ============================================================
contentSlide("The Problem: Tropical Peatland Carbon Crisis", [
  "Indonesia's 20.6M hectares of peatland store 88.6 Gt carbon -- equivalent to a decade of global fossil fuel emissions (Page et al., 2011)",
  "Drainage for oil palm has converted 5.1M hectares, releasing 0.9-1.4 Gt CO2/year (Hooijer et al., 2010)",
  "Drainage triggers irreversible peat oxidation and compaction, manifesting as measurable land surface subsidence",
  "Subsidence rates: 40-60 mm/yr in first 5 years, declining to 20-30 mm/yr over decades (Hooijer et al., 2012)",
  "Carbon credit market opportunity: USD 5.78B for peatland rewetting under Verra VCS VM0007",
  "Challenge: How to measure, report, and verify peat degradation at landscape scale for carbon credits?",
]);

// ============================================================
// SLIDE 3: Our Approach -- Why InSAR?
// ============================================================
twoColSlide(
  "Why InSAR? Rationale for Sensor Selection",
  "Why Sentinel-1 C-band SAR",
  [
    "Only satellite technique measuring mm-level ground displacement from space",
    "All-weather, day-night: critical for tropical Kalimantan (200+ cloud days/yr)",
    "Free and open data (Copernicus Programme) -- ensures reproducibility and continuity",
    "12-day repeat cycle provides sufficient temporal sampling for SBAS time-series",
    "Subsidence IS the physical signal of peat carbon loss -- direct measurement, not a proxy",
  ],
  "Why NOT optical / hyperspectral",
  [
    "Optical sensors (Sentinel-2, Landsat) cannot measure ground displacement",
    "NDVI detects vegetation stress but not the subsidence that drives it",
    "Hyperspectral (PRISMA, EnMAP) identifies surface chemistry, not vertical motion",
    "Cloud cover in Kalimantan blocks optical sensors >200 days/yr",
    "Optical data used for validation (Hansen GFC, NDVI) not primary measurement",
  ]
);

// ============================================================
// SLIDE 4: System Architecture
// ============================================================
contentSlide("System Architecture: Cloud-Native InSAR Pipeline", [
  "5-stage pipeline deployed on Google Cloud Platform (Cloud Run Jobs):",
  "  Stage 1: Data Ingestion -- 14 Sentinel-1 SLC + 14 GRD scenes from ASF DAAC (Jan-Dec 2024)",
  "  Stage 2: InSAR Processing -- ISCE2 topsApp, 29 SBAS pairs, SNAPHU MCF unwrapping, ionospheric correction",
  "  Stage 3: Time-Series Analysis -- MintPy SBAS inversion, ERA5 tropospheric correction, MintPy geocoding",
  "  Stage 4: Backscatter Processing -- GRD calibration, Lee Sigma speckle filter, terrain correction, temporal median",
  "  Stage 5: Analysis -- Canal detection, water masking, classification, risk scoring, carbon loss, Hansen integration",
  "",
  "Fully containerised (Docker), automated monthly (Cloud Scheduler + Workflows), open-source on GitHub",
]);

// ============================================================
// SLIDE 5: Key Scientific Decisions
// ============================================================
tableSlide(
  "Key Scientific Decisions and Rationale",
  ["Decision", "Choice", "Rationale", "Reference"],
  [
    ["Subswath", "IW2 (not IW3)", "IW3 gave 45% pair failure; IW2 provides full AOI burst coverage", "ASF burst analysis"],
    ["Multilooking", "3 az x 9 range", "Reduces phase noise 5.2x while preserving canal-scale features (~42x21m)", "Standard for S-1 IW"],
    ["Unwrapping", "SNAPHU MCF", "Minimum cost flow handles smooth deformation fields in low-coherence tropics", "Chen & Zebker 2002"],
    ["Atmos. correction", "ERA5 via PyAPS", "Removes 5-15 mm/yr tropospheric bias; two-phase reference selection", "Jolivet et al. 2014"],
    ["LOS-to-vertical", "cos(37) factor 1.25x", "Peat subsidence is purely vertical; Sundaland horiz. motion <1 mm/yr", "Simons et al. 2007"],
    ["Coherence mask", "0.5 threshold", "Excludes noisy forest pixels; 0.3 too permissive for tropical C-band", "Hoyt et al. 2020"],
    ["Canal detection", "10th pctl threshold", "Captures water-filled canals via specular reflection; 9.1% coverage", "Validated vs OSM"],
    ["Risk weights", "0.45 prox + 0.55 sub", "Direct measurement (subsidence) weighted higher than proxy (canal distance)", "Hooijer et al. 2012"],
    ["Carbon factor", "0.5 tCO2/ha/yr/mm", "Conservative estimate from Hooijer; some studies report 0.7-1.0", "Hooijer et al. 2012"],
  ]
);

// ============================================================
// SLIDE 6: Atmospheric Correction Detail
// ============================================================
contentSlide("ERA5 Tropospheric Correction: Why It Matters", [
  "Problem: Tropical water vapour causes 5-20 mm equivalent phase delay per acquisition",
  "Without correction: velocity bias of 5-15 mm/yr (up to 50% of the subsidence signal)",
  "",
  "Solution: Two-phase ERA5 reference selection strategy:",
  "  Phase 1: Run MintPy WITHOUT ERA5 to select reference point on uncorrected data",
  "  Phase 2: Lock reference point, re-run WITH ERA5 atmospheric correction",
  "",
  "Why two phases? ERA5 changes the phase pattern, which can shift the auto-selected reference",
  "point to subsiding ground, introducing a +35 mm/yr false positive bias",
  "",
  "Result: ERA5 correction removes atmospheric noise while preserving the correct velocity datum",
  "15/15 acquisition dates corrected using ECMWF ERA5 pressure-level reanalysis (Hersbach et al., 2020)",
]);

// ============================================================
// SLIDE 7: Results
// ============================================================
tableSlide(
  "Results: Subsidence and Carbon Loss",
  ["Metric", "Value", "Interpretation"],
  [
    ["Mean vertical velocity", "-26 mm/yr", "Consistent with Hooijer (2012): 20-50 mm/yr for drained peat"],
    ["Severe subsidence (<-50)", "30% of area", "Heavily drained peat near primary canals"],
    ["Active drying (-50 to -20)", "11% of area", "Ongoing drainage impact, significant CO2 loss"],
    ["Moderate drying (-20 to -5)", "6% of area", "Slow but measurable carbon loss"],
    ["Stable (-5 to +5)", "4% of area", "Within natural variability"],
    ["Canal network coverage", "9.1%", "Detected via VV backscatter thresholding"],
    ["Water bodies detected", "1.1%", "Kapuas River and ponds (VV dB < -18)"],
    ["Mean risk score", "0.48", "Moderate-to-elevated across drained landscape"],
    ["Peat extent coverage", "~60% of AOI", "From WRI/GFW Indonesia peatland dataset"],
  ]
);

// ============================================================
// SLIDE 8: Carbon Loss
// ============================================================
contentSlide("Carbon Loss Estimation", [
  "Conversion: CO2 loss (tCO2/ha/yr) = |subsidence velocity (mm/yr)| x 0.5",
  "Based on Hooijer et al. (2012) empirical relationship for Indonesian tropical peat",
  "Conservative factor (0.5); literature range is 0.5-1.0 depending on drainage age",
  "",
  "Quality filters applied before carbon estimation:",
  "  - Coherence > 0.5 (excludes unreliable pixels under forest canopy)",
  "  - Water mask applied (excludes rivers and ponds)",
  "  - 5x5 median filter (reduces pixel-level noise)",
  "",
  "Carbon-loss-backed visualization thresholds:",
  "  0-1 tCO2/ha/yr: Natural variability",
  "  1-5: Drainage-affected",
  "  5-10: Active degradation",
  "  10-20: Severe degradation",
  "  >20: Critical emission hotspot",
]);

// ============================================================
// SLIDE 9: Error Budget
// ============================================================
tableSlide(
  "Error Budget: Quantified Uncertainty",
  ["Error Source", "Magnitude", "Mitigation", "Status"],
  [
    ["Tropospheric delay", "5-15 mm/yr", "ERA5 correction (PyAPS)", "Corrected"],
    ["Ionospheric delay", "2-5 mm/yr", "Split-spectrum (ISCE2)", "Corrected"],
    ["Reference point", "3-8 mm/yr", "Two-phase selection", "Mitigated"],
    ["Temporal decorrelation", "2-10 mm/yr", "Coherence mask (0.5)", "Partially mitigated"],
    ["Unwrapping errors", "0-28 mm/yr per event", "SNAPHU MCF + SBAS network", "Mitigated"],
    ["LOS-to-vertical", "<3 mm/yr", "Constant incidence (37 deg)", "Applied"],
    ["Georeferencing", "~100 m", "MintPy geocoding", "Corrected"],
    ["Seasonal aliasing", "5-15 mm/yr", "1-year span (limitation)", "Not yet corrected"],
    ["Total RSS", "~8-12 mm/yr", "", "30-46% relative uncertainty"],
  ]
);

// ============================================================
// SLIDE 10: Validation
// ============================================================
twoColSlide(
  "Validation Strategy",
  "Internal Consistency",
  [
    "Velocity vs canal distance: r = -0.40 (p < 0.001) -- subsidence correlates with drainage proximity",
    "Velocity vs VV backscatter: r = 0.27 (p < 0.001) -- cleared areas show more subsidence",
    "Mean velocity (-26 mm/yr) matches published rates for drained Indonesian peat",
    "Classification distribution is physically plausible (47% subsiding, 4% stable)",
  ],
  "External Datasets",
  [
    "Hansen GFC: clearing-year cohort analysis validates temporal subsidence pattern",
    "OSM waterways: precision/recall against community-mapped canal features",
    "WRI peat extent: subsidence concentrated within mapped peatland boundaries",
    "Limitation: No ground truth (GPS, levelling, piezometers) available in study area",
  ]
);

// ============================================================
// SLIDE 11: Limitations
// ============================================================
contentSlide("Honest Limitations", [
  "C-band cannot penetrate forest canopy: ~45% of pixels are low-coherence (masked at 0.5)",
  "  - This means we cannot measure subsidence under intact peat forest",
  "  - L-band (ALOS-2 or NISAR) would address this gap",
  "",
  "Single-year temporal coverage (2024): seasonal aliasing adds 5-15 mm/yr uncertainty",
  "  - Extending to 2+ years enables seasonal decomposition",
  "",
  "No in-situ ground truth: all validation is against remote sensing datasets",
  "  - Planned: collaboration with Tanjungpura University for piezometer data",
  "",
  "Peat depth is estimated (dome model), not measured",
  "  - CIFOR peat map provides extent; depth classification is approximate",
  "",
  "Carbon loss factor (0.5 tCO2/ha/yr per mm/yr) is an empirical average, not site-specific",
]);

// ============================================================
// SLIDE 12: Future Work
// ============================================================
twoColSlide(
  "Future Development Roadmap",
  "Phase 1: Immediate (1-2 weeks)",
  [
    "Extend to 2+ years of data (2023-2024) for seasonal decomposition and noise reduction",
    "Apply for ALOS-2 L-band data (JAXA EORC, free for NUS students)",
    "Add Sentinel-2 NDVI composite for land cover classification",
    "Implement unsupervised K-means clustering for degradation zone mapping",
    "Confidence mapping: per-pixel quality indicator from coherence + uncertainty",
  ],
  "Phase 2: Medium-term (1-3 months)",
  [
    "ALOS-2 L-band InSAR for forest-penetrating subsidence (fills 45% canopy gap)",
    "Multi-sensor C+L band fusion: coherence-weighted velocity combining both wavelengths",
    "NISAR integration when data becomes available (free, open access)",
    "U-Net canal segmentation trained on Google Earth + OSM labels",
    "Supervised restoration priority model (Random Forest with expert labels from field visits)",
    "Before/after monitoring for canal blocking effectiveness (Verra MRV requirement)",
    "Web dashboard deployment (TiTiler + Leaflet for live monitoring)",
  ]
);

// ============================================================
// SLIDE 13: ML Opportunities
// ============================================================
tableSlide(
  "Machine Learning: Where It Helps vs Where It Doesn't",
  ["Application", "ML Benefit", "Status", "Recommendation"],
  [
    ["K-means degradation zones", "Discovers natural spatial patterns, no labels needed", "Ready to implement", "YES -- immediate"],
    ["U-Net canal segmentation", "Learns grid patterns, reduces false positives", "Needs training labels", "YES -- 2-3 weeks"],
    ["Random Forest restoration priority", "Multivariate feature fusion with expert knowledge", "Needs field data", "YES -- with field visit"],
    ["InSAR velocity estimation", "Cannot improve physics-based measurement", "N/A", "NO -- use MintPy"],
    ["Atmospheric correction", "Cannot improve ERA5 physics-based approach", "N/A", "NO -- use ERA5"],
    ["Subsidence classification", "Would just re-learn the Hooijer thresholds", "N/A", "NO -- use thresholds"],
  ]
);

// ============================================================
// SLIDE 14: Technology Stack
// ============================================================
contentSlide("Technology Stack", [
  "InSAR Processing: ISCE2 (JPL) -- topsApp for Sentinel-1 TOPS, stripmapApp for NISAR L-band",
  "Time-Series: MintPy (University of Miami) -- SBAS inversion, ERA5 via PyAPS, geocoding",
  "Unwrapping: SNAPHU (Stanford) -- Minimum Cost Flow algorithm",
  "Geospatial: GDAL, rasterio, geopandas, scikit-image, scipy",
  "Cloud: Google Cloud Platform -- Cloud Run Jobs, Cloud Storage, Cloud Build, Workflows, Scheduler",
  "Container: Docker (mambaforge + conda-forge for reproducible geospatial environment)",
  "Config: Pydantic v2 models + YAML, environment variable overrides",
  "Data: ASF DAAC (Sentinel-1), CDS (ERA5), Hansen GFC, WRI peatlands, OSM waterways",
  "Output: Cloud-Optimised GeoTIFFs (COG) compatible with ArcGIS Pro, QGIS, web tile servers",
  "",
  "Open source: github.com/tommyquak/peatguard-v3",
]);

// ============================================================
// SLIDE 15: Closing
// ============================================================
const sEnd = pres.addSlide();
sEnd.background = { color: C.bg };
sEnd.addText("PeatGuard", { x: 0.8, y: 1.5, w: 11.5, h: 1.0, fontSize: 44, bold: true, color: C.white, fontFace: "Arial" });
sEnd.addShape(pres.ShapeType.rect, { x: 0.8, y: 2.6, w: 4.0, h: 0.04, fill: { color: C.orange } });
sEnd.addText([
  { text: "Satellite monitoring for peatland restoration and carbon credit MRV\n\n", options: { fontSize: 18, color: C.gray, fontFace: "Arial" } },
  { text: "Key numbers:\n", options: { fontSize: 16, bold: true, color: C.orange, fontFace: "Arial" } },
  { text: "47.5% of study area shows active subsidence\n", options: { fontSize: 16, color: C.light, fontFace: "Arial" } },
  { text: "Mean vertical subsidence: -26 mm/yr (ERA5-corrected)\n", options: { fontSize: 16, color: C.light, fontFace: "Arial" } },
  { text: "9.1% canal network detected from SAR backscatter\n", options: { fontSize: 16, color: C.light, fontFace: "Arial" } },
  { text: "19 GeoTIFF products deployed to cloud in <1 hour\n\n", options: { fontSize: 16, color: C.light, fontFace: "Arial" } },
  { text: "Tommy Quak | NUS Geography | github.com/tommyquak/peatguard-v3", options: { fontSize: 14, color: C.gray, fontFace: "Arial" } },
], { x: 0.8, y: 3.0, w: 11.5, h: 4.0, valign: "top" });

// Generate
const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Scientific_Presentation.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("Presentation created: " + outPath);
});
