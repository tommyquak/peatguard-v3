const docx = require("docx");
const fs = require("fs");

const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  convertInchesToTwip, Footer, PageNumber, Table, TableRow, TableCell,
  WidthType, BorderStyle, SectionType,
} = docx;

function t(text, opts = {}) {
  return new TextRun({ text, font: "Arial", size: opts.size || 24, bold: opts.bold || false, italics: opts.italics || false, color: opts.color || "000000" });
}
function body(text, opts = {}) {
  return new Paragraph({ children: typeof text === "string" ? [t(text)] : text, alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, before: opts.spacingBefore || 0, line: 300 }, indent: opts.indent ? { firstLine: convertInchesToTwip(0.4) } : undefined });
}
function heading(text, level) {
  const sizes = { 1: 30, 2: 26, 3: 24 };
  const hl = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({ children: [new TextRun({ text, font: "Arial", size: sizes[level], bold: true })], heading: hl[level], spacing: { before: level === 1 ? 360 : 200, after: 120, line: 300 }, alignment: AlignmentType.LEFT });
}
function bullet(text) {
  const children = typeof text === "string" ? [t(text)] : text;
  return new Paragraph({ children, bullet: { level: 0 }, spacing: { after: 60, line: 300 } });
}
function labelPara(label, text) {
  return new Paragraph({ children: [t(label, { bold: true }), t(text)], alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 300 } });
}
function monoBlock(lines) {
  return lines.map(line => new Paragraph({
    children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "333333" })],
    spacing: { after: 20, line: 240 },
    indent: { left: convertInchesToTwip(0.3) },
  }));
}
function makeCell(text, opts = {}) {
  return new TableCell({
    children: [new Paragraph({ children: [t(text, { size: 20, bold: opts.bold })], spacing: { after: 30 } })],
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    borders: { top: { style: BorderStyle.SINGLE, size: 1, color: "cccccc" }, bottom: { style: BorderStyle.SINGLE, size: 1, color: "cccccc" }, left: { style: BorderStyle.SINGLE, size: 1, color: "cccccc" }, right: { style: BorderStyle.SINGLE, size: 1, color: "cccccc" } },
  });
}
function makeRow(cells, opts = {}) { return new TableRow({ children: cells.map(c => makeCell(c, opts)) }); }

const pageProps = {
  page: { size: { width: 12240, height: 15840 }, margin: { top: convertInchesToTwip(0.8), right: convertInchesToTwip(0.8), bottom: convertInchesToTwip(0.8), left: convertInchesToTwip(1) } },
};

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: Process Flow and Technical Justification",
  sections: [
    // Title page
    {
      properties: pageProps,
      children: [
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({ children: [t("PeatGuard", { size: 44, bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 60 } }),
        new Paragraph({ children: [t("Process Flow and Technical Justification", { size: 28, color: "555555" })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
        new Paragraph({ children: [t("Complete Pipeline Architecture, Data Flow, and Scientific Rationale", { size: 22, italics: true, color: "777777" })], alignment: AlignmentType.CENTER, spacing: { after: 600 } }),
        new Paragraph({ children: [t("Tommy Quak | National University of Singapore", { size: 22 })], alignment: AlignmentType.CENTER, spacing: { after: 60 } }),
        new Paragraph({ children: [t("Department of Geography", { size: 20, italics: true, color: "666666" })], alignment: AlignmentType.CENTER, spacing: { after: 300 } }),
        new Paragraph({ children: [t("April 2026", { size: 22 })], alignment: AlignmentType.CENTER }),
      ],
    },
    // Main content
    {
      properties: { ...pageProps, type: SectionType.NEXT_PAGE },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18 })] })] }) },
      children: [
        // 1. Pipeline Overview
        heading("1. Pipeline Overview", 1),
        body("PeatGuard is a five-stage satellite processing pipeline that transforms raw Sentinel-1 SAR acquisitions into actionable peatland restoration priority maps. Each stage is a containerised Cloud Run Job on Google Cloud Platform, executing sequentially with products stored in Google Cloud Storage between stages."),

        heading("1.1 End-to-End Process Flow", 2),
        body("The pipeline processes data through the following stages:"),
        ...monoBlock([
          "STAGE 1: DATA INGESTION",
          "  Input:  ASF DAAC search API (Sentinel-1 catalogue)",
          "  Action: Download 14 SLC + 14 GRD scenes (Jan-Dec 2024)",
          "  Output: gs://peatguard-data/raw/slc/*.zip, raw/grd/*.zip",
          "  Time:   ~2 hours | CPU: 4 | RAM: 8 GB",
          "",
          "STAGE 2: InSAR PROCESSING",
          "  Input:  14 SLC scenes from GCS",
          "  Action: ISCE2 topsApp per pair (29 SBAS pairs, 16 succeed)",
          "  Output: gs://peatguard-data/interferograms/*/merged/",
          "          (filt_topophase.unw, phsig.cor, geom_reference/)",
          "  Time:   ~6 hours | CPU: 8 | RAM: 32 GB",
          "",
          "STAGE 3: TIME-SERIES ANALYSIS",
          "  Input:  16 unwrapped interferograms + geometry from GCS",
          "  Action: MintPy SBAS inversion -> velocity estimation",
          "  Output: gs://peatguard-data/products/subsidence_velocity.tif",
          "          + coherence_median.tif, velocity_uncertainty.tif",
          "  Time:   ~30 min | CPU: 8 | RAM: 32 GB",
          "",
          "STAGE 4: BACKSCATTER PROCESSING",
          "  Input:  14 GRD scenes from GCS",
          "  Action: Calibrate -> speckle filter -> terrain correct -> composite",
          "  Output: gs://peatguard-data/products/vv_median.tif, vv_median_db.tif",
          "  Time:   ~20 min | CPU: 8 | RAM: 32 GB",
          "",
          "STAGE 5: ANALYSIS",
          "  Input:  Velocity + VV backscatter + ancillary data",
          "  Action: Canal detection, water masking, classification,",
          "          risk scoring, carbon loss, peat mapping, validation",
          "  Output: 20+ products in gs://peatguard-data/products/",
          "  Time:   ~3 min | CPU: 4 | RAM: 16 GB",
        ]),

        // 2. Stage 1
        heading("2. Stage 1: Data Ingestion", 1),
        labelPara("Purpose: ", "Acquire Sentinel-1 SAR imagery from the Alaska Satellite Facility Distributed Active Archive Center."),
        labelPara("Justification: ", "Sentinel-1 is the only freely available SAR satellite with systematic 12-day repeat acquisitions suitable for InSAR time-series analysis. ASF DAAC provides the most complete and accessible archive."),

        heading("2.1 Search and Selection", 2),
        body("The ASF search API is queried for Sentinel-1A IW-mode SLC and GRD products intersecting the study area bounding box. Scenes are filtered by:"),
        bullet("Platform: SENTINEL-1 (Sentinel-1A only, consistent imaging geometry)"),
        bullet("Beam mode: IW (Interferometric Wide, 250 km swath)"),
        bullet("Polarisation: VV (highest ground-surface sensitivity for tropical peat)"),
        bullet("Processing level: SLC for InSAR, GRD_HD for backscatter"),
        bullet("Relative orbit: single orbit track selected (orbit 105, descending)"),
        bullet("Temporal range: January 2024 to December 2024"),

        heading("2.2 Orbit Selection Rationale", 2),
        body("Orbit 105 (descending) provides the most acquisitions (20+ scenes/year) over the study area. The IW3 subswath covers the AOI at far range. Descending orbit acquires at approximately 22:00 UTC (06:00 local), which minimises atmospheric convective activity relative to the afternoon ascending pass.", { indent: true }),

        // 3. Stage 2
        heading("3. Stage 2: InSAR Processing", 1),
        labelPara("Purpose: ", "Generate interferograms measuring the phase difference between repeat-pass SAR acquisitions, from which ground displacement is derived."),

        heading("3.1 SBAS Pair Network", 2),
        body("An SBAS (Small Baseline Subset) network connects acquisitions with temporal baselines of 12 to 48 days. Of 29 possible pairs, 16 produce coherent interferograms. The 13 failures occur at the IW3 swath edge where burst overlap is inconsistent across acquisitions."),
        labelPara("Justification: ", "SBAS maximises the number of usable interferometric pairs by selecting small temporal baselines, which is critical in tropical environments where long baselines decorrelate rapidly. The 12-48 day range balances coherence preservation with deformation sensitivity."),

        heading("3.2 ISCE2 topsApp Processing", 2),
        body("Each interferometric pair is processed through the ISCE2 topsApp workflow:"),

        new Table({ rows: [
          makeRow(["Step", "Algorithm", "Parameters", "Justification"], { bold: true }),
          makeRow(["Coregistration", "Spectral diversity + ESD", "Default", "Sub-pixel alignment of TOPS burst seams"]),
          makeRow(["DEM download", "Copernicus GLO-30", "30m, auto from AWS", "Free, global, sufficient for flat peatland"]),
          makeRow(["Topographic phase", "Radar-coded DEM", "GLO-30 elevation", "Removes topographic contribution to phase"]),
          makeRow(["Ionospheric", "Split-spectrum", "do_ion = True", "Removes 2-5 mm/yr equatorial iono bias"]),
          makeRow(["Multilooking", "Block averaging", "3 az x 9 rg", "Reduces noise 5.2x, resolution ~42x21m"]),
          makeRow(["Phase filtering", "Goldstein adaptive", "alpha = 0.8", "Suppresses noise, preserves fringes"]),
          makeRow(["Unwrapping", "SNAPHU MCF", "Cost mode: DEFO", "Handles smooth subsidence fields"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),

        heading("3.3 Memory Management", 2),
        body("Cloud Run uses RAM-backed filesystem (32 GB shared between process memory and disk). The pipeline processes one pair at a time: download SLC from GCS, extract IW3 bursts, run topsApp, upload merged products to GCS, delete the pair directory. This per-pair cleanup keeps peak RAM usage under 20 GB."),

        // 4. Stage 3
        heading("4. Stage 3: Time-Series Analysis", 1),
        labelPara("Purpose: ", "Invert the network of unwrapped interferograms to estimate cumulative displacement and mean velocity at each pixel."),

        heading("4.1 Custom HDF5 Preparation", 2),
        body("MintPy's standard prep_isce.py fails on our data because GCS-reconstructed interferograms lack full ISCE2 XML metadata. A custom prep_data_for_mintpy() function reads ISCE2 binary files directly and creates the required ifgramStack.h5 and geometryRadar.h5 with hardcoded Sentinel-1 SAR parameters (wavelength, orbit height, pixel sizes)."),
        labelPara("Justification: ", "This bypass is necessary because the per-pair download-process-upload-delete pattern means the full ISCE2 directory structure is never present in a single location. The custom prep preserves all information MintPy needs while accommodating the cloud-native processing pattern."),

        heading("4.2 MintPy SBAS Configuration", 2),
        new Table({ rows: [
          makeRow(["Parameter", "Value", "Justification"], { bold: true }),
          makeRow(["Processor", "ISCE", "Matches our interferogram format"]),
          makeRow(["Network coherence", "0.3 minimum", "Standard for tropical C-band InSAR"]),
          makeRow(["Reference point", "Auto-selected (max coherence)", "No known stable structures in peat landscape"]),
          makeRow(["Tropospheric correction", "Disabled (ERA5 under calibration)", "ERA5 implementation has naming mismatch with PyAPS; correction shifts velocity baseline. Documented as 5-15 mm/yr uncertainty."]),
          makeRow(["Topographic residual", "Disabled", "Peatland relief < 10m; DEM error negligible"]),
          makeRow(["Orbital ramp", "Linear deramp", "Removes residual orbit errors"]),
          makeRow(["Unwrap error correction", "Disabled (MCF)", "Bridging fails with fragmented connected components in tropical peat"]),
          makeRow(["Geocoding", "Disabled", "Export handles georeferencing via affine approximation from geometry lookup tables"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),

        heading("4.3 LOS-to-Vertical Conversion", 2),
        body("MintPy outputs Line-of-Sight velocity. Conversion to vertical uses a constant incidence angle of 37 degrees (IW3 mid-swath):"),
        ...monoBlock(["V_vertical = V_LOS / cos(37 deg) = V_LOS x 1.25"]),
        labelPara("Justification: ", "Peat subsidence is purely vertical (no horizontal component). The constant angle avoids amplification artifacts from geocoded geometry edge pixels. Uncertainty from incidence angle variation across the swath is less than 3 mm/yr."),

        heading("4.4 Velocity Export", 2),
        body("The velocity is clipped to the AOI with a reduced western buffer (0.02 degrees vs 0.1 degrees elsewhere) to exclude the noisy IW3 swath edge. Values are clamped to [-200, +200] mm/yr to remove extreme unwrapping errors. A coherence mask at 0.5 excludes unreliable pixels. Products are exported as Cloud-Optimised GeoTIFFs in both EPSG:4326 (native) and EPSG:32649 (UTM Zone 49S)."),

        // 5. Stage 4
        heading("5. Stage 4: Backscatter Processing", 1),
        labelPara("Purpose: ", "Generate a stable VV backscatter composite for canal detection and water masking."),

        heading("5.1 Processing Chain", 2),
        body("Each of 14 GRD scenes is processed through:"),
        bullet([t("Radiometric calibration: ", { bold: true }), t("Annotation LUT-based conversion to sigma-nought (radar backscatter coefficient)")]),
        bullet([t("Speckle filtering: ", { bold: true }), t("Lee Sigma filter, 7x7 window. Preserves edges (canal boundaries) while smoothing homogeneous areas.")]),
        bullet([t("Terrain correction: ", { bold: true }), t("GCP-based Thin Plate Spline warp to UTM (EPSG:32649), 10m pixel spacing.")]),
        bullet([t("Temporal composite: ", { bold: true }), t("Median of 14 calibrated scenes. Robust to outliers (rain events, RFI). Produces stable reference image with reduced speckle.")]),

        // 6. Stage 5
        heading("6. Stage 5: Analysis", 1),
        labelPara("Purpose: ", "Integrate velocity, backscatter, and ancillary data into actionable restoration products."),

        heading("6.1 Canal Detection", 2),
        body("Drainage canals are detected from the VV backscatter composite using the 10th percentile threshold. Water-filled canals produce specular reflection (very low radar return) distinguishing them from vegetation."),
        new Table({ rows: [
          makeRow(["Parameter", "Value", "Justification"], { bold: true }),
          makeRow(["Threshold", "10th percentile", "Adaptive to scene statistics; captures water-filled features"]),
          makeRow(["Min component size", "50 pixels (5000 sq m)", "Removes speckle noise and isolated dark features"]),
          makeRow(["Morphological closing", "Disk radius 2", "Bridges small gaps between canal segments"]),
          makeRow(["Dilation", "Disk radius 1", "Recovers canal width lost by thresholding"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),
        labelPara("Coverage: ", "~9.1% of study area, consistent with expected plantation drainage network density."),

        heading("6.2 Water Body Detection", 2),
        body("Open water is detected from the VV dB backscatter using a threshold of -18 dB. The dB product is downloaded from GCS at runtime if not available locally. Connected components smaller than 25 pixels are removed. Canal exclusion is disabled because the broad canal detection overlaps with water features."),
        labelPara("Justification: ", "VV dB thresholding at -18 dB captures the Kapuas River and major ponds while avoiding over-masking of wet peat. The -18 dB threshold represents specular reflection from smooth water surfaces, well below typical vegetation backscatter (-5 to -10 dB)."),

        heading("6.3 Subsidence Classification", 2),
        body("Vertical velocity is classified into six categories based on peatland literature:"),
        new Table({ rows: [
          makeRow(["Class", "Velocity (mm/yr)", "Scientific Basis"], { bold: true }),
          makeRow(["1 - Severe", "< -50", "Hooijer (2012): first 5 years post-drainage"]),
          makeRow(["2 - Active drying", "-50 to -20", "Hooijer (2012): ongoing drainage 5-15 years"]),
          makeRow(["3 - Moderate drying", "-20 to -5", "Slow carbon loss above natural accumulation rate"]),
          makeRow(["4 - Stable", "-5 to +5", "Natural peat accumulation ~1 mm/yr (Page et al. 2011)"]),
          makeRow(["5 - Rebound/Noise", "> +5", "Possible rewetting or measurement noise"]),
          makeRow(["6 - Water", "N/A", "Excluded by water mask"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),

        heading("6.4 Risk Score", 2),
        body("The composite risk score integrates canal proximity and subsidence velocity:"),
        ...monoBlock([
          "R = 0.45 x R_proximity + 0.55 x R_subsidence",
          "",
          "R_proximity = max(0, 1 - distance/1200)    [Dupuit, Hooijer 2012]",
          "R_subsidence = clip(-velocity/40, 0, 1)     [Hooijer 2012]",
        ]),
        body("A 9x9 pixel median filter is applied to the velocity before risk computation to suppress pixel-level noise. NoData pixels are filled with the global velocity median to avoid edge bias in the filter."),
        labelPara("Weight justification: ", "The subsidence component (0.55) receives higher weight because it is a direct physical measurement. Canal proximity (0.45) is an indirect proxy for drainage intensity."),

        heading("6.5 Carbon Loss Estimation", 2),
        ...monoBlock(["CO2_loss (tCO2/ha/yr) = |V_vertical| (mm/yr) x 0.5"]),
        body("Quality filters applied before carbon estimation:"),
        bullet("Coherence > 0.7 (excludes unreliable forest/water-edge pixels)"),
        bullet("Water body buffer: 100m exclusion zone around detected water"),
        bullet("9x9 median spatial filter (reduces pixel-level noise)"),
        bullet("Positive velocity pixels set to 0 (no carbon loss for uplift/noise)"),
        labelPara("Conversion factor: ", "0.5 tCO2/ha/yr per mm/yr subsidence (Hooijer et al. 2012). Conservative estimate; literature range 0.5-1.0."),

        heading("6.6 Peat Extent and Depth", 2),
        body("Peat polygons from WRI/GFW Indonesia Peatlands dataset are rasterised to the pipeline grid. Peat depth is estimated from the distance-to-edge dome model (Page et al. 2006):"),
        bullet("Shallow (< 2m): within 500m of peat boundary"),
        bullet("Moderate (2-4m): 500-1500m from boundary"),
        bullet("Deep (> 4m): beyond 1500m from boundary"),
        body("Products: peat_extent_binary.tif, peat_extent.tif (depth classes), peat_subsidence.tif (velocity masked to peat), peat_risk.tif (risk weighted by depth)."),

        heading("6.7 Hansen Forest Change Integration", 2),
        body("The Hansen GFC dataset provides the year of forest loss (2001-2023) at 30m resolution. This enables temporal context:"),
        bullet("Clearing risk factor: 1.2x for 0-5 years (rapid subsidence phase)"),
        bullet("1.0x for 5-15 years, 0.8x for 15+ years (declining rate per Hooijer 2012)"),
        bullet("0.6x for intact forest (possible but undetectable with C-band)"),
        body("Products: deforestation_year.tif, time_since_clearing.tif, clearing_risk_factor.tif, time_adjusted_risk.tif."),

        heading("6.8 Validation", 2),
        body("Three independent validation approaches:"),
        bullet([t("Internal consistency: ", { bold: true }), t("Velocity vs canal distance correlation (expected: r < -0.3), velocity vs VV backscatter correlation (expected: r > 0.2)")]),
        bullet([t("OSM canal comparison: ", { bold: true }), t("Precision, recall, F1 against OpenStreetMap waterway features downloaded via Overpass API")]),
        bullet([t("Hansen cohort analysis: ", { bold: true }), t("Mean subsidence rate by clearing-year cohort (recently cleared should show highest rates)")]),

        // 7. Error Budget
        heading("7. Error Budget", 1),
        new Table({ rows: [
          makeRow(["Source", "Magnitude", "Mitigation", "Residual"], { bold: true }),
          makeRow(["Tropospheric delay", "5-15 mm/yr", "Documented uncertainty (ERA5 under calibration)", "5-15 mm/yr"]),
          makeRow(["Ionospheric delay", "2-5 mm/yr", "Split-spectrum correction", "< 1 mm/yr"]),
          makeRow(["Reference point", "3-8 mm/yr", "Auto-selected max coherence", "3-8 mm/yr"]),
          makeRow(["Decorrelation bias", "2-10 mm/yr", "Coherence mask (0.5 for velocity, 0.7 for carbon)", "2-5 mm/yr"]),
          makeRow(["Unwrapping errors", "0-28 mm/yr", "SNAPHU MCF + SBAS network", "0-5 mm/yr"]),
          makeRow(["LOS-to-vertical", "< 3 mm/yr", "Constant incidence (37 deg)", "< 3 mm/yr"]),
          makeRow(["Georeferencing", "~1-3 km", "Affine from lat/lon lookup", "~1-3 km"]),
          makeRow(["Seasonal aliasing", "5-15 mm/yr", "Not corrected (1-year span)", "5-15 mm/yr"]),
          makeRow(["Total RSS", "~10-20 mm/yr", "", "Relative patterns more reliable than absolute values"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),

        // 8. Products
        heading("8. Output Products", 1),
        new Table({ rows: [
          makeRow(["Product", "Format", "CRS", "Description"], { bold: true }),
          makeRow(["subsidence_velocity.tif", "COG float32", "EPSG:4326", "Vertical velocity (mm/yr)"]),
          makeRow(["subsidence_velocity_utm.tif", "COG float32", "EPSG:32649", "Velocity reprojected to UTM"]),
          makeRow(["coherence_median.tif", "COG float32", "EPSG:4326", "Temporal coherence (0-1)"]),
          makeRow(["velocity_uncertainty.tif", "COG float32", "EPSG:4326", "Velocity std dev"]),
          makeRow(["vv_median.tif", "COG float32", "EPSG:32649", "VV backscatter (linear)"]),
          makeRow(["vv_median_db.tif", "COG float32", "EPSG:32649", "VV backscatter (dB)"]),
          makeRow(["canal_mask.tif", "COG uint8", "EPSG:32649", "Binary canal network"]),
          makeRow(["canal_distance.tif", "COG float32", "EPSG:32649", "Distance to nearest canal (m)"]),
          makeRow(["water_mask.tif", "COG uint8", "EPSG:32649", "Binary water bodies"]),
          makeRow(["subsidence_class_utm.tif", "COG uint8", "EPSG:32649", "6-class severity"]),
          makeRow(["canal_risk.tif", "COG float32", "EPSG:32649", "Combined risk (0-1)"]),
          makeRow(["carbon_loss.tif", "COG float32", "EPSG:4326", "CO2 loss (tCO2/ha/yr)"]),
          makeRow(["degraded_peatland.tif", "COG uint8", "EPSG:4326", "Binary degradation on peat"]),
          makeRow(["peat_extent.tif", "COG uint8", "EPSG:32649", "Peat depth classes"]),
          makeRow(["peat_risk.tif", "COG float32", "EPSG:32649", "Depth-weighted risk"]),
          makeRow(["deforestation_year.tif", "COG uint8", "EPSG:32649", "Hansen loss year (1-23)"]),
          makeRow(["time_adjusted_risk.tif", "COG float32", "EPSG:32649", "Temporally adjusted risk"]),
          makeRow(["pipeline_report.json", "JSON", "N/A", "Quality metrics and statistics"]),
          makeRow(["validation_report.json", "JSON", "N/A", "Correlation statistics"]),
        ], width: { size: 100, type: WidthType.PERCENTAGE } }),

        // 9. Known Limitations
        heading("9. Known Limitations and Documented Decisions", 1),

        heading("9.1 Atmospheric Correction", 2),
        body("ERA5 tropospheric correction via PyAPS is implemented but produces a velocity baseline shift due to a file naming mismatch between the pre-download module and PyAPS expectations. The pre-download creates files named ERA5_{SNWE}_{date}_{hour}.grb while PyAPS expects ERA-5_{date}_{hour}.grb. This has been fixed in code (v52+) but requires validation through a full reprocessing run. Until validated, products are generated without atmospheric correction, with the 5-15 mm/yr uncertainty documented in the error budget."),

        heading("9.2 Subswath Edge Coverage", 2),
        body("The study area at 114.354E sits at the western edge of the IW3 subswath for orbit 105. This causes 13 of 29 interferometric pairs to fail (insufficient burst overlap) and produces degraded data quality at the left (western) edge of the velocity map. The western buffer has been reduced from 0.1 to 0.02 degrees to minimise the inclusion of noisy edge pixels. A future dual-subswath approach (IW2+IW3) would provide complete coverage."),

        heading("9.3 Velocity Noise", 2),
        body("The velocity standard deviation (~80-90 mm/yr) significantly exceeds the subsidence signal (~25-35 mm/yr), giving a signal-to-noise ratio of approximately 0.3-0.4. This is typical for C-band InSAR in tropical peatland where temporal decorrelation is severe. Individual pixel values are unreliable; only spatial patterns and statistical averages are scientifically meaningful. Coherence-based masking (0.5 for velocity export, 0.7 for carbon loss estimation) and spatial median filtering (9x9) mitigate this limitation."),

        heading("9.4 Forest Canopy Penetration", 2),
        body("C-band radar (5.6 cm wavelength) cannot penetrate dense tropical forest canopy. Approximately 45% of pixels have low temporal coherence and are flagged as 'rebound/noise' in the classification. L-band SAR (ALOS-2 PALSAR-2 at 23 cm or NISAR at 24 cm) would address this gap. The pipeline includes L-band support (stripmapApp processing, multi-sensor fusion module) that will activate when data becomes available."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Process_Flow.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Document created: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
