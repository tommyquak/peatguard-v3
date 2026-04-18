const docx = require("docx");
const fs = require("fs");

const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  convertInchesToTwip,
  Footer,
  PageNumber,
  Table,
  TableRow,
  TableCell,
  WidthType,
} = docx;

function t(text, opts = {}) {
  return new TextRun({
    text,
    font: "Arial",
    size: opts.size || 24,
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || "000000",
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    children: [t(text)],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, before: opts.spacingBefore || 0, line: 276 },
  });
}

function heading(text, level) {
  const sizes = { 1: 32, 2: 28, 3: 26 };
  const headingLevels = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: sizes[level] || 24, bold: true })],
    heading: headingLevels[level],
    spacing: { before: level === 1 ? 360 : 240, after: 120, line: 240 },
    alignment: AlignmentType.LEFT,
  });
}

function bullet(text, level = 0) {
  const children = typeof text === "string" ? [t(text)] : text;
  return new Paragraph({
    children,
    bullet: { level },
    spacing: { after: 60, line: 276 },
    alignment: AlignmentType.LEFT,
  });
}

function labeledPara(label, text) {
  return new Paragraph({
    children: [t(label, { bold: true }), t(text)],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, line: 276 },
  });
}

function makeCell(text, opts = {}) {
  return new TableCell({
    children: [new Paragraph({ children: [t(text, { size: 20, bold: opts.bold })], spacing: { after: 40 } })],
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
  });
}

function makeRow(cells, opts = {}) {
  return new TableRow({ children: cells.map((c) => makeCell(c, opts)) });
}

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: Scientific Methodology and Validation Report",
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: convertInchesToTwip(1), right: convertInchesToTwip(1), bottom: convertInchesToTwip(1), left: convertInchesToTwip(1) },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 20 })] })],
        }),
      },
      children: [
        // Title page
        new Paragraph({ spacing: { before: 3600 } }),
        new Paragraph({
          children: [t("PeatGuard: Scientific Methodology and Validation Report", { size: 36, bold: true })],
          alignment: AlignmentType.CENTER,
          spacing: { after: 240 },
        }),
        new Paragraph({
          children: [t("Satellite-Based Peatland Subsidence Monitoring for Carbon Credit MRV", { size: 26, italics: true, color: "444444" })],
          alignment: AlignmentType.CENTER,
          spacing: { after: 480 },
        }),
        new Paragraph({ children: [t("Prepared for Third-Party Audit", { size: 24, color: "444444" })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
        new Paragraph({ children: [t("Tommy Quak", { size: 28 })], alignment: AlignmentType.CENTER, spacing: { after: 60 } }),
        new Paragraph({ children: [t("National University of Singapore, Department of Geography", { size: 24, italics: true })], alignment: AlignmentType.CENTER, spacing: { after: 480 } }),
        new Paragraph({ children: [t("March 2026", { size: 24 })], alignment: AlignmentType.CENTER }),

        // 1. Executive Summary
        heading("1. Executive Summary", 1),
        body("This document describes the scientific methodology, data sources, processing chain, calibration approach, error budget, and validation strategy employed by the PeatGuard satellite monitoring system for detecting and quantifying peatland subsidence in the Kapuas River region of West Kalimantan, Indonesia. The system is designed to support Measurement, Reporting, and Verification (MRV) requirements under the Verra Verified Carbon Standard (VCS) VM0007 methodology for peatland rewetting credits."),
        body("The pipeline processes Sentinel-1 C-band Synthetic Aperture Radar (SAR) data through an Interferometric SAR (InSAR) workflow using the ISCE2 processing framework and MintPy Small Baseline Subset (SBAS) time-series analysis. Complementary backscatter analysis detects drainage canal networks. A composite risk score integrates subsidence velocity, canal proximity, and peat depth to prioritize restoration zones. Carbon loss is estimated using the empirical relationship established by Hooijer et al. (2012)."),
        body("All processing is cloud-native, containerized, and reproducible. The pipeline is open-source and deployed on Google Cloud Platform. This report provides the scientific justification for each processing decision and quantifies the associated uncertainties."),

        // 2. Study Area
        heading("2. Study Area and Context", 1),
        body("The study area is located within the Kapuas River peatland complex in West Kalimantan, Indonesia, bounded by 114.277 to 114.431 degrees East and 2.511 to 2.611 degrees South. The area covers approximately 18,700 hectares of tropical peatland, including oil palm plantations, degraded peat forest, intact peat swamp forest, and a dense network of drainage canals."),
        body("Peat deposits in the region reach depths exceeding 10 meters, formed over millennia under waterlogged conditions (Jaenicke et al. 2008). The landscape has been extensively drained for oil palm cultivation, with a systematic grid of canals visible in both optical and SAR imagery. Drainage lowers the water table, triggering irreversible peat oxidation and physical compaction that manifests as measurable land surface subsidence."),
        body("The study area was selected because it represents a typical degraded tropical peatland where canal blocking interventions are feasible and carbon credit revenue could fund restoration. The village head of Teluk Bayur (Pak Agus) and former BRGM official (Mr Rifqi Marisel) have confirmed local interest in peatland restoration activities."),

        // 3. Data Sources
        heading("3. Data Sources and Justification", 1),

        heading("3.1 Primary: Sentinel-1 SAR", 2),
        body("Sentinel-1A Interferometric Wide (IW) mode Single Look Complex (SLC) data was selected as the primary measurement source for the following reasons:"),
        bullet("All-weather, day-night acquisition capability essential for tropical equatorial monitoring where persistent cloud cover precludes optical approaches"),
        bullet("Free and open data policy under the Copernicus Programme ensures long-term data continuity and reproducibility"),
        bullet("12-day repeat cycle provides sufficient temporal sampling for SBAS time-series analysis"),
        bullet("C-band radar (5.546 cm wavelength) is sensitive to millimeter-level ground displacement through interferometric phase measurement"),
        bullet("IW2 subswath provides optimal coverage of the study area with consistent burst overlap across acquisitions"),

        labeledPara("Acquisition parameters: ", "14 Sentinel-1A IW SLC scenes spanning January 2024 to December 2024, VV polarization, IW2 subswath, descending orbit. Additionally, 14 corresponding GRD scenes were acquired for backscatter analysis."),

        heading("3.2 Copernicus GLO-30 Digital Elevation Model", 2),
        body("The Copernicus Global 30-meter DEM, derived from the TanDEM-X mission, is used for topographic phase removal during interferometric processing. The flat terrain of the peatland (typically less than 10 meters above sea level) means that DEM errors contribute negligibly to the velocity estimate. Topographic residual correction is therefore disabled in the time-series analysis, which is standard practice for flat terrain (Yunjun et al. 2019)."),

        heading("3.3 ERA5 Atmospheric Reanalysis", 2),
        body("ERA5 hourly data on pressure levels from the ECMWF Copernicus Climate Data Store is used for tropospheric delay correction via the PyAPS module within MintPy. Tropical Kalimantan experiences high atmospheric water vapor variability that causes 5 to 20 millimeters of equivalent phase delay per SAR acquisition. Without correction, this introduces systematic velocity biases of 5 to 15 mm/yr. ERA5 data is downloaded for each of the 15 unique acquisition dates and applied during the time-series inversion."),
        labeledPara("Justification: ", "ERA5 tropospheric correction is the standard approach for InSAR time-series analysis in tropical environments (Jolivet et al. 2014). The correction removes the spatially and temporally correlated component of tropospheric delay that would otherwise alias into the velocity estimate."),

        heading("3.4 WRI/GFW Indonesia Peatlands", 2),
        body("Peat extent polygons from the World Resources Institute Global Forest Watch database are used to delineate peatland areas within the study region. The dataset is derived from the Indonesian Ministry of Agriculture peat mapping programme and provides the spatial boundary within which subsidence rates are interpreted as peat-related carbon loss."),
        labeledPara("Limitation: ", "The WRI peat boundary has positional accuracy on the order of hundreds of meters. Peat depth is estimated from the distance-to-edge dome model (Page et al. 2006) rather than measured directly. The depth classification (shallow, moderate, deep) should be treated as an approximate indicator."),

        heading("3.5 Hansen Global Forest Change", 2),
        body("The Hansen et al. (2013) Global Forest Change dataset provides the year of forest loss at 30-meter resolution from 2001 to 2023. This is used to determine the time elapsed since each area was cleared for drainage-based agriculture, which directly relates to the expected subsidence rate via the Hooijer et al. (2012) temporal decay relationship. Recently cleared areas (0 to 5 years) are expected to show the highest subsidence rates."),

        heading("3.6 OpenStreetMap Waterways", 2),
        body("Canal and waterway features from OpenStreetMap are downloaded via the Overpass API and used as an independent validation dataset for the SAR-based canal detection. Comparison metrics (precision, recall, F1 score) quantify the detection accuracy against community-mapped drainage infrastructure."),

        // 4. Processing Methodology
        heading("4. Processing Methodology", 1),

        heading("4.1 InSAR Processing (ISCE2)", 2),
        body("Interferometric processing follows the ISCE2 topsApp workflow designed for Sentinel-1 TOPS mode data (Rosen et al. 2012). A Small Baseline Subset (SBAS) network of 29 interferometric pairs with temporal baselines of 12 to 48 days was constructed. Of these, 16 pairs were successfully processed; the remaining 13 failed due to insufficient burst overlap in the subswath, a geometric limitation of the TOPS acquisition mode."),
        labeledPara("Multilooking: ", "3 looks in azimuth by 9 looks in range, producing approximately 42 by 21 meter ground resolution. This averaging reduces phase noise by a factor of approximately 5.2 (square root of 27 looks) while maintaining sufficient spatial resolution for canal-scale features."),
        labeledPara("Phase filtering: ", "Goldstein adaptive filter with alpha = 0.8 (Goldstein and Werner 1998). This suppresses high-frequency phase noise while preserving fringe continuity."),
        labeledPara("Phase unwrapping: ", "SNAPHU Minimum Cost Flow algorithm (Chen and Zebker 2002). MCF is well-suited to the relatively smooth displacement fields expected in subsidence monitoring and produces fewer unwrapping errors than branch-cut methods in low-coherence tropical environments."),
        labeledPara("Ionospheric correction: ", "Split-spectrum method enabled in ISCE2 (do_ion = True). This is important for equatorial data where ionospheric phase contributions can reach 2 to 5 mm/yr equivalent velocity bias."),

        heading("4.2 Time-Series Analysis (MintPy SBAS)", 2),
        body("Time-series displacement analysis uses the Miami InSAR Time-Series Software in Python (MintPy), implementing the SBAS approach (Berardino et al. 2002). The interferometric network is inverted to estimate cumulative displacement at each acquisition date, from which a linear velocity is estimated by regression."),
        labeledPara("Coherence threshold: ", "0.3 minimum temporal coherence for pixel inclusion in the network. Pixels below this threshold are excluded as unreliable. This is a standard value for C-band InSAR in tropical environments."),
        labeledPara("Reference point: ", "Automatically selected as the highest-coherence pixel within the processed frame. The reference pixel defines the zero-velocity datum; all velocities are relative to this point."),
        labeledPara("Tropospheric correction: ", "ERA5 via PyAPS (Python-based Atmospheric Phase Screen). Pressure-level data for each acquisition date is used to compute and remove the tropospheric delay phase screen from each interferogram before inversion."),
        labeledPara("Orbital ramp removal: ", "Linear deramping applied to remove residual orbital phase contributions."),
        labeledPara("Geocoding: ", "MintPy geocoding enabled with bilinear interpolation to properly transform velocity products from radar coordinates to geographic (EPSG:4326) coordinates using the full geometry lookup tables."),

        heading("4.3 LOS-to-Vertical Velocity Conversion", 2),
        body("MintPy outputs Line-of-Sight (LOS) displacement velocity. For subsidence monitoring, the vertical component is required. The conversion assumes purely vertical motion (no horizontal displacement), which is appropriate for peat compaction and oxidation processes:"),
        body("    V_vertical = V_LOS / cos(theta)"),
        body("where theta is the radar incidence angle. For Sentinel-1 IW2 at mid-swath, theta is approximately 37 degrees, giving a conversion factor of 1.25. A constant incidence angle is used rather than per-pixel values to avoid amplification artifacts at geocoded geometry edges."),
        labeledPara("Justification: ", "Peatland subsidence is a predominantly vertical process driven by peat oxidation and compaction. Horizontal tectonic motion in the Sundaland block is less than 1 mm/yr (Simons et al. 2007) and is negligible relative to the subsidence signal."),

        heading("4.4 Backscatter Processing", 2),
        body("Ground Range Detected (GRD) data is calibrated to radar backscatter coefficient (sigma-nought) using the radiometric calibration look-up tables from the Sentinel-1 product annotations. Speckle noise is reduced using the Lee Sigma filter with a 7 by 7 pixel window (Lee 1983). Geometric terrain correction is applied using GDAL Warp with a GCP-based Thin Plate Spline transformation. A temporal median composite from 14 calibrated scenes produces a stable backscatter reference image."),

        heading("4.5 Canal Detection", 2),
        body("Drainage canals are detected using a dual-method approach combining absolute backscatter thresholding and ridge detection:"),
        bullet([t("Threshold method: ", { bold: true }), t("The 10th percentile of the backscatter distribution identifies water-filled features with very low radar return (specular reflection). This captures wide, water-filled primary canals.")]),
        bullet([t("Ridge detection: ", { bold: true }), t("The Sato ridge filter (multi-scale, sigmas 1 to 3) detects narrow linear features that create local backscatter minima but do not reach the absolute threshold. This captures secondary drainage ditches at sub-pixel to near-pixel width.")]),
        body("The two detection masks are combined by union, followed by morphological cleanup (closing with disk radius 2, removal of connected components smaller than 10 pixels, slight dilation for width recovery). A Euclidean distance transform produces a continuous canal proximity surface in meters."),

        heading("4.6 Water Body Detection", 2),
        body("Open water bodies are identified from the VV backscatter composite using a threshold of -18 dB. Water surfaces produce specular reflection resulting in very low radar return. Connected components smaller than 25 pixels (2,500 square meters) are removed to exclude isolated noise detections. Morphological closing with radius 3 fills small gaps within water bodies. Water pixels are excluded from subsidence classification and risk scoring to prevent false degradation detections."),

        // 5. Risk Score Calibration
        heading("5. Risk Score and Carbon Loss Calibration", 1),

        heading("5.1 Composite Risk Score", 2),
        body("The degradation risk score (0 to 1) integrates two components with weights derived from the relative reliability of each measurement:"),
        body("    R = 0.45 * R_proximity + 0.55 * R_subsidence"),
        labeledPara("Proximity risk: ", "Linear decay with distance from the nearest canal, reaching zero at 1200 meters. This follows the Dupuit equation approximation for water table drawdown in tropical peat (Hooijer et al. 2012, Jaenicke et al. 2010). The 1200-meter influence radius reflects the observed extent of drainage effects in Indonesian peatlands."),
        labeledPara("Subsidence risk: ", "Linear normalization of the vertical velocity, saturating at -40 mm/yr. This threshold captures actively draining peat within the first decade following drainage (Hooijer et al. 2012)."),
        labeledPara("Weight rationale: ", "The subsidence component receives higher weight (0.55) because it is a direct measurement of ongoing peat loss. Canal proximity is an indirect proxy for drainage intensity and receives lower weight (0.45). The weights sum to 1.0."),

        heading("5.2 Peat Depth Weighting", 2),
        body("The risk score is further weighted by estimated peat depth from the WRI peat extent data:"),
        bullet("Non-peat areas: weight 0.0 (excluded from risk assessment)"),
        bullet("Shallow peat (less than 2 meters): weight 0.6"),
        bullet("Moderate peat (2 to 4 meters): weight 0.8"),
        bullet("Deep peat (greater than 4 meters): weight 1.0"),
        body("The depth-weighted risk score (peat_risk) directs restoration resources toward areas where the greatest carbon stock is at risk. Deeper peat contains more carbon per unit area and represents a larger emission reduction potential from rewetting."),

        heading("5.3 Carbon Loss Estimation", 2),
        body("Carbon dioxide emission rates are estimated from the vertical subsidence velocity using the empirical conversion factor established by Hooijer et al. (2012):"),
        body("    CO2_loss (tCO2/ha/yr) = |V_vertical (mm/yr)| x 0.5"),
        body("This factor of 0.5 tonnes CO2 per hectare per year per millimeter of annual subsidence is derived from the relationship between subsidence rate, peat bulk density (approximately 0.1 g/cm3 for tropical peat), and carbon content (approximately 55% by dry weight). The factor is conservative; some studies report values of 0.7 to 1.0 for freshly drained peat where primary consolidation contributes to higher initial subsidence rates."),
        labeledPara("Quality filter: ", "Carbon loss is computed only for pixels with temporal coherence greater than 0.5 and where the water mask indicates non-water land surface. A 5 by 5 pixel median filter (with global-median fill for nodata pixels) smooths the velocity before conversion to reduce pixel-level noise."),

        heading("5.4 Temporal Risk Adjustment", 2),
        body("The Hansen Global Forest Change dataset provides the year of clearing for each pixel. A temporal risk adjustment factor modulates the base risk score based on the time elapsed since drainage:"),
        bullet("0 to 5 years since clearing: factor 1.2 (rapid subsidence phase per Hooijer et al. 2012)"),
        bullet("5 to 15 years: factor 1.0 (ongoing but declining rate)"),
        bullet("Greater than 15 years: factor 0.8 (long-term slow subsidence)"),
        bullet("Intact forest (never cleared): factor 0.6"),
        body("This temporal adjustment reflects the well-documented decline in peat subsidence rate with time after drainage onset."),

        // 6. Classification
        heading("6. Subsidence Classification", 1),
        body("Vertical velocity is classified into six categories based on thresholds informed by peatland literature. Natural peat accumulation is approximately 1 mm/yr (Page et al. 2011), so any subsidence exceeding approximately 5 mm/yr on peat indicates net carbon loss."),

        new Table({
          rows: [
            makeRow(["Class", "Velocity Range (mm/yr)", "Interpretation"], { bold: true }),
            makeRow(["1 - Severe", "< -50", "Heavily drained peat, maximum carbon loss"]),
            makeRow(["2 - Active drying", "-50 to -20", "Ongoing drainage impact, significant carbon loss"]),
            makeRow(["3 - Moderate drying", "-20 to -5", "Slow but ongoing carbon loss"]),
            makeRow(["4 - Stable", "-5 to +5", "Within natural variability envelope"]),
            makeRow(["5 - Rebound/Noise", "> +5", "Possible rewetting rebound or measurement noise"]),
            makeRow(["6 - Water", "N/A", "Open water body (excluded from analysis)"]),
          ],
          width: { size: 100, type: WidthType.PERCENTAGE },
        }),

        // 7. Error Budget
        heading("7. Error Budget", 1),
        body("The following table summarizes the estimated magnitude of each error source and the mitigation applied:"),

        new Table({
          rows: [
            makeRow(["Error Source", "Estimated Magnitude", "Mitigation", "Status"], { bold: true }),
            makeRow(["Tropospheric delay", "5-15 mm/yr", "ERA5 correction via PyAPS", "Corrected"]),
            makeRow(["Ionospheric delay", "2-5 mm/yr", "Split-spectrum (ISCE2 do_ion)", "Corrected"]),
            makeRow(["Reference point bias", "3-8 mm/yr", "Auto-selected high-coherence pixel", "Mitigated"]),
            makeRow(["Temporal decorrelation", "2-10 mm/yr", "Coherence masking (threshold 0.3)", "Partially mitigated"]),
            makeRow(["Phase unwrapping errors", "0-28 mm/yr per event", "SNAPHU MCF + SBAS network redundancy", "Mitigated"]),
            makeRow(["LOS-to-vertical assumption", "0-3 mm/yr", "Constant incidence angle (37 deg)", "Applied"]),
            makeRow(["Georeferencing", "~100 m (with geocoding)", "MintPy geocoding with lookup tables", "Corrected"]),
            makeRow(["Seasonal aliasing", "5-15 mm/yr", "1-year observation span", "Not yet corrected"]),
            makeRow(["Total RSS (corrected)", "~8-12 mm/yr", "", ""]),
          ],
          width: { size: 100, type: WidthType.PERCENTAGE },
        }),

        body("The total root-sum-square uncertainty of approximately 8 to 12 mm/yr represents the estimated accuracy of the velocity measurement after all corrections are applied. For the observed mean subsidence rate of approximately -26 mm/yr, this represents a relative uncertainty of 30 to 46 percent. The spatial pattern of subsidence (where rates are higher vs lower) is more reliable than the absolute velocity values because many error sources (atmospheric, reference point, orbital ramp) affect the entire image uniformly.", { spacingBefore: 120 }),

        // 8. Validation
        heading("8. Validation Strategy", 1),

        heading("8.1 Internal Consistency Checks", 2),
        bullet("Velocity vs canal distance correlation: statistically significant negative correlation (r = -0.40, p < 0.001) confirms that subsidence rates are spatially related to drainage infrastructure"),
        bullet("Velocity vs VV backscatter correlation: positive correlation (r = 0.27, p < 0.001) indicating that areas with lower backscatter (cleared, drained land) show more subsidence"),
        bullet("Mean velocity (-26.1 mm/yr vertical) is consistent with published rates for drained tropical peatlands (Hooijer et al. 2012: 20-50 mm/yr)"),

        heading("8.2 External Validation Datasets", 2),
        bullet("OpenStreetMap waterways: precision, recall, and F1 score computed against community-mapped canal features"),
        bullet("Hansen Global Forest Change: clearing year cohort analysis verifies that recently cleared areas show higher subsidence rates than old clearings"),
        bullet("WRI peat extent: spatial overlap confirms that subsidence is concentrated within mapped peatland boundaries"),

        heading("8.3 Limitations and Caveats", 2),
        bullet("No ground truth measurements (GPS, leveling, piezometer data) are available within the study area. All validation is against independent remote sensing datasets, not in-situ measurements."),
        bullet("C-band radar decorrelates under dense tropical forest canopy, meaning approximately 38 percent of pixels show measurement noise rather than reliable velocity estimates. These pixels are not excluded from the current analysis."),
        bullet("The 1-year observation period (2024) provides minimal temporal sampling. Seasonal effects (wet/dry cycle) may alias into the annual velocity estimate by 5 to 15 mm/yr."),
        bullet("Peat depth is estimated from the distance-to-edge dome model, not measured. The depth classes should be treated as approximate indicators for prioritization, not quantitative measurements."),
        bullet("The carbon loss conversion factor (0.5 tCO2/ha/yr per mm/yr subsidence) is an empirical average from Hooijer et al. (2012). Actual conversion varies with peat type, drainage age, and compaction state."),

        // 9. Reproducibility
        heading("9. Reproducibility and Transparency", 1),
        body("The complete processing pipeline is open-source and available at https://github.com/tommyquak/peatguard-v3. All processing is containerized using Docker with explicit dependency versions (ISCE2, MintPy, SNAPHU, GDAL, rasterio) ensuring bitwise reproducibility across environments. Processing is orchestrated through Google Cloud Run Jobs with defined resource allocations (8 CPU, 32 GB RAM per InSAR job). Configuration is managed through versioned YAML files with Pydantic validation."),
        body("All intermediate and final products are stored as Cloud-Optimized GeoTIFFs in Google Cloud Storage (gs://peatguard-data/products/) and can be independently downloaded and verified. A machine-readable pipeline quality report (pipeline_report.json) accompanies each processing run with complete statistics and metadata."),

        // 10. References
        heading("10. References", 1),
        body("Berardino, P., G. Fornaro, R. Lanari, and E. Sansosti. 2002. A New Algorithm for Surface Deformation Monitoring Based on Small Baseline Differential SAR Interferograms. IEEE Trans. Geosci. Remote Sens. 40(11): 2375-2383."),
        body("Chen, C. W. and H. A. Zebker. 2002. Phase Unwrapping for Large SAR Interferograms: Statistical Segmentation and Generalized Network Models. IEEE Trans. Geosci. Remote Sens. 40(8): 1709-1719."),
        body("Goldstein, R. M. and C. L. Werner. 1998. Radar Interferogram Filtering for Geophysical Applications. Geophysical Research Letters 25(21): 4035-4038."),
        body("Hansen, M. C. et al. 2013. High-Resolution Global Maps of 21st-Century Forest Cover Change. Science 342(6160): 850-853."),
        body("Hooijer, A. et al. 2012. Subsidence and Carbon Loss in Drained Tropical Peatlands. Biogeosciences 9(3): 1053-1071."),
        body("Jaenicke, J. et al. 2008. Determination of the Amount of Carbon Stored in Indonesian Peatlands. Geoderma 147(3-4): 151-158."),
        body("Jolivet, R. et al. 2014. Improving InSAR Geodesy Using Global Atmospheric Models. J. Geophys. Res. Solid Earth 119(3): 2324-2341."),
        body("Lee, J.-S. 1983. Digital Image Smoothing and the Sigma Filter. Computer Vision, Graphics, and Image Processing 24(2): 255-269."),
        body("Page, S. E., J. O. Rieley, and C. J. Banks. 2011. Global and Regional Importance of the Tropical Peatland Carbon Pool. Global Change Biology 17(2): 798-818."),
        body("Page, S. E. et al. 2006. Peatland Carbon Stocks and Carbon Loss from Drainage-Associated Fire in Southeast Asia. Proc. International Peat Congress."),
        body("Rosen, P. A. et al. 2012. The InSAR Scientific Computing Environment. In 9th European Conference on Synthetic Aperture Radar, 730-733."),
        body("Simons, W. J. F. et al. 2007. A Decade of GPS in Southeast Asia: Resolving Sundaland Motion and Boundaries. J. Geophys. Res. 112: B06420."),
        body("Yunjun, Z., H. Fattahi, and F. Amelung. 2019. Small Baseline InSAR Time Series Analysis: Unwrapping Error Correction and Noise Reduction. Computers and Geosciences 133: 104331."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Scientific_Methodology_Report.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Report generated: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
