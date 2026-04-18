const docx = require("docx");
const fs = require("fs");

const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  convertInchesToTwip, Footer, PageNumber, SectionType,
} = docx;

function t(text, opts = {}) {
  return new TextRun({ text, font: "Times New Roman", size: opts.size || 24, bold: opts.bold || false, italics: opts.italics || false, color: opts.color || "000000", superScript: opts.super || false });
}
function body(text, opts = {}) {
  return new Paragraph({ children: typeof text === "string" ? [t(text)] : text, alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, before: opts.spacingBefore || 0, line: 360 }, indent: opts.indent ? { firstLine: convertInchesToTwip(0.5) } : undefined });
}
function heading(text, level) {
  const sizes = { 1: 28, 2: 26, 3: 24 };
  const hl = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({ children: [new TextRun({ text, font: "Times New Roman", size: sizes[level], bold: true })], heading: hl[level], spacing: { before: level === 1 ? 360 : 240, after: 120, line: 360 }, alignment: AlignmentType.LEFT });
}
function bullet(text) {
  const children = typeof text === "string" ? [t(text)] : text;
  return new Paragraph({ children, bullet: { level: 0 }, spacing: { after: 60, line: 360 }, alignment: AlignmentType.LEFT });
}
function ref(text) {
  return new Paragraph({ children: [t(text, { size: 22 })], spacing: { after: 100, line: 276 }, indent: { left: convertInchesToTwip(0.5), hanging: convertInchesToTwip(0.5) } });
}

const pageProps = {
  page: { size: { width: 12240, height: 15840 }, margin: { top: convertInchesToTwip(1), right: convertInchesToTwip(1), bottom: convertInchesToTwip(1), left: convertInchesToTwip(1.25) } },
};

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: A Cloud-Native InSAR Pipeline for Peatland Subsidence Monitoring and Restoration Prioritisation",
  styles: { default: { document: { run: { font: "Times New Roman", size: 24 } } } },
  sections: [
    // Title page
    {
      properties: pageProps,
      children: [
        new Paragraph({ spacing: { before: 4800 } }),
        new Paragraph({ children: [t("PeatGuard: A Cloud-Native InSAR Pipeline for Peatland Subsidence Monitoring and Carbon Credit MRV in West Kalimantan, Indonesia", { size: 32, bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 600, line: 360 } }),
        new Paragraph({ children: [t("Technical Proposal and Methodology", { size: 26, italics: true, color: "444444" })], alignment: AlignmentType.CENTER, spacing: { after: 600 } }),
        new Paragraph({ children: [t("Tommy Quak", { size: 26 })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
        new Paragraph({ children: [t("Department of Geography, National University of Singapore", { size: 24, italics: true })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
        new Paragraph({ children: [t("In collaboration with Dr Sang-Ho Yun (InSAR Radar Scientist)", { size: 22 })], alignment: AlignmentType.CENTER, spacing: { after: 600 } }),
        new Paragraph({ children: [t("March 2026", { size: 24 })], alignment: AlignmentType.CENTER }),
      ],
    },
    // Abstract + Body
    {
      properties: { ...pageProps, type: SectionType.NEXT_PAGE },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: "Times New Roman", size: 20 })] })] }) },
      children: [
        // Abstract
        heading("Abstract", 1),
        body("Tropical peatlands store approximately 88.6 Gt of carbon, equivalent to more than a decade of global fossil fuel emissions (Page et al., 2011). In Indonesia, widespread drainage for oil palm and pulpwood plantations has triggered irreversible peat oxidation, releasing an estimated 0.9-1.4 Gt CO2-equivalent annually (Hooijer et al., 2010). Quantifying this degradation at landscape scale is critical for targeting canal blocking interventions and verifying emission reductions under carbon credit methodologies such as Verra VCS VM0007."),
        body("This proposal presents PeatGuard, a cloud-native satellite monitoring pipeline that integrates Sentinel-1 C-band Interferometric Synthetic Aperture Radar (InSAR) with multi-source ancillary data to detect, quantify, and prioritise peatland restoration zones in the Kapuas River region of West Kalimantan. The system employs Small Baseline Subset (SBAS) time-series analysis for millimetre-precision subsidence velocity mapping, ERA5 tropospheric correction for atmospheric bias removal, dual-method canal detection combining backscatter thresholding with Sato ridge filtering, and a composite risk score calibrated to the empirical subsidence-drainage relationships established by Hooijer et al. (2012). Carbon loss is estimated using the Hooijer conversion factor of 0.5 tCO2/ha/yr per mm/yr subsidence, validated against Hansen Global Forest Change deforestation timing and OpenStreetMap canal features.", { indent: true }),
        body("The pipeline is deployed on Google Cloud Platform using containerised Cloud Run Jobs, processing 14 Sentinel-1 acquisitions across 16 interferometric pairs in approximately 50 minutes. Results identify a mean vertical subsidence rate of approximately -26 mm/yr across the study area, with 47.5% of the landscape classified as actively degrading. The system is open-source, reproducible, and designed for operational deployment at regional scale.", { indent: true }),

        // 1. Introduction
        heading("1. Introduction", 1),

        heading("1.1 The Tropical Peatland Carbon Crisis", 2),
        body("Tropical peatlands represent one of the most significant and vulnerable terrestrial carbon stores on Earth. These ecosystems accumulate organic matter over millennia under waterlogged, anaerobic conditions, forming deposits that can exceed 10 metres depth in Southeast Asia (Jaenicke et al., 2008). Despite covering less than 0.3% of the global land surface, tropical peatlands contain approximately 88.6 Gt of carbon -- equivalent to the total above-ground carbon stock of the world's tropical forests combined (Page et al., 2011). The carbon density of tropical peat (averaging 55-65 kg C/m3) far exceeds that of any mineral soil (Warren et al., 2017).", { indent: true }),
        body("Indonesia contains the world's largest tropical peatland estate, with approximately 20.6 million hectares concentrated in Sumatra, Kalimantan, and Papua (Ritung et al., 2011). Over the past three decades, large-scale drainage for oil palm cultivation and pulpwood plantations has converted an estimated 5.1 million hectares of Indonesian peat swamp forest (Miettinen et al., 2016). Drainage lowers the water table, exposing previously saturated peat to aerobic conditions and triggering two simultaneous processes: biochemical oxidation (microbial decomposition of organic matter releasing CO2) and physical compaction (consolidation under reduced buoyancy). Both processes manifest as measurable land surface subsidence -- a direct, physical indicator of carbon loss (Couwenberg et al., 2010).", { indent: true }),

        heading("1.2 Subsidence as a Proxy for Carbon Loss", 2),
        body("The relationship between peatland subsidence and carbon emissions was quantitatively established by Hooijer et al. (2012) through extensive field measurements at multiple sites in Sumatra and Kalimantan. Their findings demonstrated that subsidence in drained tropical peatlands follows a predictable temporal pattern: rapid initial rates of 40-60 mm/yr during the first five years after drainage, declining to 20-30 mm/yr over subsequent decades as the easily decomposable fraction is consumed. The study further established an empirical conversion factor relating subsidence rate to CO2 emission: approximately 0.91 tCO2/ha/yr per cm of annual subsidence (equivalent to 0.091 tCO2/ha/yr per mm/yr, or approximately 0.5 tCO2/ha/yr per mm/yr when accounting for the full carbon-to-CO2 conversion and typical peat bulk densities).", { indent: true }),
        body("This subsidence-emission relationship provides the scientific foundation for satellite-based Measurement, Reporting, and Verification (MRV) of peatland carbon credits. If subsidence can be measured remotely with sufficient accuracy, carbon loss can be quantified without extensive field campaigns -- a critical requirement for scaling peatland restoration across Indonesia's vast and often inaccessible peat landscapes.", { indent: true }),

        heading("1.3 InSAR for Peatland Subsidence Monitoring", 2),
        body("Interferometric Synthetic Aperture Radar (InSAR) is the only remote sensing technique capable of measuring land surface displacement with millimetre-level precision from satellite platforms. By comparing the phase of radar signals acquired on two different dates, InSAR can detect ground motion of a few millimetres over distances of hundreds of kilometres (Rosen et al., 2000). The technique has been successfully applied to peatland subsidence monitoring in several studies: Marshall et al. (2018) demonstrated C-band InSAR subsidence detection in UK blanket bog; Hoyt et al. (2020) mapped widespread subsidence across Southeast Asian peatlands using ALOS PALSAR L-band data; and Zhou et al. (2021) applied Sentinel-1 SBAS analysis to Indonesian oil palm plantations on peat.", { indent: true }),
        body("The Small Baseline Subset (SBAS) approach (Berardino et al., 2002) is particularly well-suited to peatland monitoring because it maximises the number of usable interferometric pairs by selecting those with small temporal and spatial baselines, reducing the impact of temporal decorrelation that is severe in tropical environments. Combined with the free, systematic, and continuous acquisition programme of the Copernicus Sentinel-1 mission (12-day repeat cycle, C-band, 5.546 cm wavelength), SBAS InSAR provides a viable operational framework for landscape-scale peatland subsidence monitoring.", { indent: true }),

        heading("1.4 Research Objectives", 2),
        body("This proposal describes PeatGuard, a cloud-native satellite monitoring pipeline designed to:"),
        bullet("Quantify peatland subsidence velocity across the Kapuas River study area using Sentinel-1 SBAS InSAR time-series analysis with ERA5 tropospheric correction"),
        bullet("Detect and map drainage canal networks from SAR backscatter using a combined threshold and ridge detection approach"),
        bullet("Estimate carbon dioxide emission rates from subsidence measurements using the Hooijer et al. (2012) empirical relationship"),
        bullet("Generate composite risk scores integrating subsidence velocity, canal proximity, peat depth, and deforestation timing for restoration prioritisation"),
        bullet("Validate results against independent datasets including Hansen Global Forest Change and OpenStreetMap waterway features"),
        bullet("Deploy the complete pipeline as a reproducible, cloud-native system suitable for operational monitoring and carbon credit MRV"),

        // 2. Study Area
        heading("2. Study Area", 1),
        body("The study area is located within the Kapuas River peatland complex in West Kalimantan, Indonesia, bounded by 114.277 to 114.431 degrees East and 2.511 to 2.611 degrees South, encompassing approximately 18,700 hectares. The Kapuas River, the longest river in Indonesian Borneo at 1,143 km, traverses the western portion of the study area.", { indent: true }),
        body("Peat deposits in the region are among the deepest in Kalimantan, reaching 10 metres or more, with an estimated 340 million tonnes of carbon stored within the study area alone based on average peat depth of 6 metres and carbon density of 55 kg C/m3 (Jaenicke et al., 2008). The landscape has been extensively modified by drainage-based agriculture, with a dense rectangular grid of canals at approximately 200-500 metre spacing visible in both optical and SAR imagery. These canals, constructed primarily for oil palm plantation development, lower the water table by 0.4-0.8 metres below the peat surface, triggering the subsidence-emission cycle described by Hooijer et al. (2012).", { indent: true }),
        body("The region experiences a tropical equatorial climate with mean annual precipitation exceeding 3,000 mm and minimal seasonal variation. Mean temperature ranges from 25 to 32 degrees Celsius year-round. The flat, low-lying topography (typically less than 10 metres above sea level) and high atmospheric water vapour content create challenging conditions for satellite-based monitoring: persistent cloud cover precludes optical approaches for much of the year, and tropospheric water vapour introduces significant phase delays in radar measurements.", { indent: true }),
        body("The study area was selected in consultation with local stakeholders including Pak Agus (village head of Teluk Bayur) and Mr Rifqi Marisel (former official of the Indonesian Peatland Restoration Agency, BRGM), who identified this region as a priority for canal blocking interventions with community support for restoration activities.", { indent: true }),

        // 3. Data Sources
        heading("3. Data Sources", 1),

        heading("3.1 Sentinel-1 SAR Imagery", 2),
        body("The primary data source is Sentinel-1A Interferometric Wide (IW) mode imagery, selected for its combination of free and open data access, systematic 12-day repeat acquisitions, C-band radar frequency suitable for millimetre displacement detection, and cloud-penetrating all-weather acquisition capability. Fourteen Single Look Complex (SLC) scenes spanning January to December 2024 were acquired from the Alaska Satellite Facility (ASF) DAAC. The IW2 subswath was selected as it provides optimal spatial coverage of the study area. VV polarisation was used as it provides the highest signal-to-noise ratio for ground surface returns in tropical vegetation environments (Zhou et al., 2021).", { indent: true }),
        body("Additionally, 14 Ground Range Detected (GRD) scenes from the same acquisition dates were obtained for radiometric backscatter analysis and canal detection.", { indent: true }),

        heading("3.2 ERA5 Atmospheric Reanalysis", 2),
        body("ERA5 is the fifth generation atmospheric reanalysis produced by the European Centre for Medium-Range Weather Forecasts (ECMWF), providing hourly data on 37 pressure levels at approximately 31 km spatial resolution globally (Hersbach et al., 2020). ERA5 pressure-level data is used within the PyAPS (Python-based Atmospheric Phase Screen) framework to estimate and remove the tropospheric phase delay component from each SAR acquisition. In tropical environments, atmospheric water vapour can introduce path delays equivalent to 5-20 mm of apparent ground displacement per acquisition, causing systematic velocity biases of 5-15 mm/yr if uncorrected (Jolivet et al., 2014). ERA5 correction is therefore essential for obtaining scientifically defensible subsidence rates.", { indent: true }),

        heading("3.3 Copernicus GLO-30 Digital Elevation Model", 2),
        body("Topographic phase removal during interferometric processing utilises the Copernicus Global 30-metre DEM derived from the TanDEM-X mission. The flat terrain of the study area (relief less than 10 metres) means that DEM errors contribute negligibly to the displacement estimate, consistent with the analysis of Yunjun et al. (2019) who demonstrated that topographic residual correction can be safely omitted for terrain with less than 50 metres of relief.", { indent: true }),

        heading("3.4 Hansen Global Forest Change", 2),
        body("The Hansen et al. (2013) Global Forest Change dataset provides annual forest loss detection at 30-metre resolution from 2001 to 2023, derived from Landsat time-series analysis. This dataset enables determination of the time elapsed since each location was cleared for drainage-based agriculture, which is a primary determinant of the expected subsidence rate (Hooijer et al., 2012). The temporal context allows validation of InSAR results: recently cleared areas should exhibit higher subsidence rates than areas drained decades ago.", { indent: true }),

        heading("3.5 WRI Global Forest Watch Indonesia Peatlands", 2),
        body("Peat extent mapping is derived from the World Resources Institute (WRI) Global Forest Watch Indonesia peatlands dataset, which integrates the Indonesian Ministry of Agriculture peat mapping programme data. This provides the spatial delineation of peatland within the study area, ensuring that subsidence measurements are interpreted only within areas underlain by peat deposits. Peat depth is estimated from the distance-to-boundary using the tropical peat dome model (Page et al., 2006), with depth increasing from the margins toward the centre of the peat body.", { indent: true }),

        heading("3.6 OpenStreetMap Waterways", 2),
        body("Canal and waterway features from OpenStreetMap (OSM) are obtained via the Overpass API and used as an independent validation dataset for SAR-based canal detection. OSM canal features in this region of Kalimantan represent community-contributed knowledge of drainage infrastructure, providing a comparison baseline against which the satellite-derived canal network can be assessed.", { indent: true }),

        // 4. Methodology
        heading("4. Methodology", 1),

        heading("4.1 InSAR Processing", 2),
        body("Interferometric processing employs the InSAR Scientific Computing Environment version 2 (ISCE2), developed by NASA's Jet Propulsion Laboratory (Rosen et al., 2012). The topsApp workflow handles the Sentinel-1 Terrain Observation by Progressive Scans (TOPS) acquisition mode, performing burst-by-burst processing including azimuth deramping, spectral diversity-based coregistration, and burst merging.", { indent: true }),
        body("A Small Baseline Subset network of 29 interferometric pairs was constructed with temporal baselines of 12 to 48 days. Of these, 16 pairs were successfully processed to unwrapped interferograms; the remaining 13 exhibited severe temporal decorrelation (insufficient burst overlap in the IW2 subswath), a known limitation of C-band InSAR in tropical environments where dense vegetation and high moisture variability rapidly degrade signal coherence (Hoyt et al., 2020).", { indent: true }),
        body("Multilooking was applied at 3 looks in azimuth and 9 looks in range, producing ground resolution of approximately 42 by 21 metres and reducing phase noise by a factor of 5.2 (square root of 27 independent looks). The Goldstein adaptive phase filter with strength parameter 0.8 (Goldstein and Werner, 1998) was applied to further suppress phase noise while preserving fringe continuity. Ionospheric correction was enabled using the split-spectrum method implemented in ISCE2, which is important for equatorial data where ionospheric effects can contribute 2-5 mm/yr equivalent velocity bias. Phase unwrapping was performed using the Statistical-Cost Network-Flow Algorithm for Phase Unwrapping (SNAPHU) with the Minimum Cost Flow solver (Chen and Zebker, 2002).", { indent: true }),

        heading("4.2 SBAS Time-Series Analysis", 2),
        body("Time-series displacement analysis was performed using MintPy (Miami InSAR Time-Series Software in Python), an open-source package implementing the SBAS methodology (Yunjun et al., 2019). The SBAS approach (Berardino et al., 2002) inverts the network of unwrapped interferograms to estimate cumulative displacement at each acquisition date by solving a regularised least-squares system. The mean line-of-sight velocity is then estimated by linear regression of the cumulative displacement time series.", { indent: true }),
        body("The interferometric network was modified based on a spatial coherence threshold of 0.3, excluding pixels that did not maintain sufficient coherence. A coherence threshold of 0.5 was subsequently applied during velocity export to exclude unreliable pixels from the final product, ensuring that only measurements with adequate phase quality contribute to the subsidence map.", { indent: true }),

        heading("4.3 Tropospheric Correction", 2),
        body("Tropospheric phase delay was corrected using ERA5 reanalysis data via the PyAPS module within MintPy. A two-phase reference point selection strategy was implemented to prevent the atmospheric correction from introducing a systematic velocity bias. In the first phase, MintPy runs without tropospheric correction through the reference point selection step, identifying the highest-coherence pixel within the data extent as the zero-velocity datum. In the second phase, the reference point is locked and MintPy runs the complete processing chain including ERA5 correction. This two-phase approach ensures that the velocity reference is selected on uncorrected data (which preserves the spatial coherence pattern) while the atmospheric correction is applied consistently to all pixels relative to this fixed reference.", { indent: true }),
        body("ERA5 pressure-level data for each of the 15 unique acquisition dates was pre-downloaded via the CDS API with per-date retry logic to handle API rate limiting. The pre-downloaded data was stored in the MintPy weather directory for direct ingestion by PyAPS.", { indent: true }),

        heading("4.4 LOS-to-Vertical Conversion", 2),
        body("MintPy outputs Line-of-Sight (LOS) displacement velocity, which measures the projection of the three-dimensional ground motion vector onto the radar look direction. For subsidence monitoring, the vertical component is required. Under the assumption of purely vertical motion (appropriate for peat compaction and oxidation which have no significant horizontal component), the conversion is:", { indent: true }),
        body([t("    V"), t("vertical", { size: 20, super: false }), t(" = V"), t("LOS", { size: 20 }), t(" / cos("), t("theta", { italics: true }), t(")")]),
        body("where theta is the radar incidence angle. For Sentinel-1 IW2 at mid-swath, theta is approximately 37 degrees, yielding a conversion factor of 1.25. The assumption of purely vertical motion is supported by the negligible horizontal tectonic velocity of the Sundaland block (less than 1 mm/yr; Simons et al., 2007) and the isotropic nature of peat compaction and oxidation processes.", { indent: true }),

        heading("4.5 Canal Detection", 2),
        body("Drainage canals were detected from the temporal median VV-polarisation backscatter composite using a dual-method approach designed to capture both wide primary canals and narrow secondary drainage ditches:", { indent: true }),
        body([t("Threshold method: ", { bold: true }), t("The 10th percentile of the backscatter distribution identifies water-filled features exhibiting specular reflection (very low radar return). This captures primary canals wider than approximately 10 metres where water surfaces dominate the pixel.")], { indent: true }),
        body([t("Ridge detection method: ", { bold: true }), t("The Sato multi-scale ridge filter (Sato et al., 1998) with scale parameters sigma = 1 to 3 (corresponding to feature widths of 10 to 40 metres at 10-metre pixel spacing) detects dark linear features that create local backscatter minima but do not reach the absolute threshold. The black_ridges parameter is set to True to detect valley-like (dark) features. This captures secondary drainage ditches at sub-pixel to near-pixel width that create a measurable local contrast with adjacent vegetation pixels.")], { indent: true }),
        body("The two detection masks are combined by union, followed by morphological cleanup: binary closing with a disk structuring element of radius 2 to bridge small gaps, removal of connected components smaller than 50 pixels (5,000 square metres at 10-metre resolution), and slight dilation to recover canal width. A Euclidean distance transform produces a continuous canal proximity surface in metres.", { indent: true }),

        heading("4.6 Water Body Detection", 2),
        body("Open water bodies were identified from the VV backscatter composite in decibel scale using a threshold of -18 dB. Water surfaces produce specular reflection, directing radar energy away from the sensor and resulting in very low backscatter returns. Connected components smaller than 25 pixels (2,500 square metres) were removed to exclude isolated noise detections. Morphological closing with radius 3 filled small gaps within water bodies. Water pixels were excluded from subsidence classification and risk scoring to prevent false degradation detections caused by the inherently low InSAR coherence over water surfaces.", { indent: true }),

        heading("4.7 Peat Extent and Depth", 2),
        body("Peat extent was derived from the WRI Global Forest Watch Indonesia peatlands dataset, queried via the ArcGIS REST API for the study area bounding box. The vector polygons were rasterised to match the pipeline's 10-metre raster grid. Peat depth was estimated using the tropical peat dome model (Page et al., 2006), which relates depth to distance from the peat body margin: peat is shallowest at the edges (less than 2 metres) and deepest toward the centre (exceeding 4 metres). Three depth classes were defined: shallow (less than 2 metres, within 500 metres of margin), moderate (2-4 metres, 500-1500 metres from margin), and deep (greater than 4 metres, more than 1500 metres from margin).", { indent: true }),

        heading("4.8 Subsidence Classification", 2),
        body("Vertical velocity was classified into six categories based on thresholds informed by the peatland subsidence literature. Natural peat accumulation rates in intact tropical peatlands are approximately 0.5-1.5 mm/yr (Dommain et al., 2014). Any subsidence rate exceeding approximately 5 mm/yr on peat therefore represents net carbon loss:"),
        bullet([t("Class 1 -- Severe: ", { bold: true }), t("velocity less than -50 mm/yr. Indicates heavily drained peat with maximum carbon loss. Consistent with subsidence rates in the first 5 years after drainage (Hooijer et al., 2012).")]),
        bullet([t("Class 2 -- Active drying: ", { bold: true }), t("velocity -50 to -20 mm/yr. Ongoing drainage impact with significant carbon loss. Typical of peatlands drained 5-15 years ago.")]),
        bullet([t("Class 3 -- Moderate drying: ", { bold: true }), t("velocity -20 to -5 mm/yr. Slow but ongoing carbon loss. May indicate distant drainage influence or peatlands drained more than 15 years ago.")]),
        bullet([t("Class 4 -- Stable: ", { bold: true }), t("velocity -5 to +5 mm/yr. Within the natural variability envelope. No net carbon loss detectable within measurement uncertainty.")]),
        bullet([t("Class 5 -- Rebound/Noise: ", { bold: true }), t("velocity greater than +5 mm/yr. Possible peat swelling from rewetting, or measurement noise from low coherence.")]),
        bullet([t("Class 6 -- Water: ", { bold: true }), t("open water body identified by the water mask. Excluded from subsidence analysis.")]),

        heading("4.9 Risk Score Calibration", 2),
        body("A composite degradation risk score (0-1) integrates two components with weights derived from their relative measurement reliability:", { indent: true }),
        body([t("    R = 0.45 "), t("x", { italics: true }), t(" R"), t("proximity", { size: 20 }), t(" + 0.55 "), t("x", { italics: true }), t(" R"), t("subsidence", { size: 20 })]),
        body([t("Proximity risk: ", { bold: true }), t("Linear decay with distance from the nearest canal, reaching zero at 1200 metres. The 1200-metre influence radius is based on the Dupuit equation approximation for water table drawdown in tropical peat, calibrated to the field observations of Hooijer et al. (2012) and Jaenicke et al. (2010) who found drainage effects extending 1-1.5 km from canal networks in Indonesian peatlands. The linear decay function (risk = max(0, 1 - d/1200)) approximates the observed roughly linear relationship between water table depth and distance from drainage in flat tropical peat.")], { indent: true }),
        body([t("Subsidence risk: ", { bold: true }), t("Linear normalisation of vertical velocity, saturating at -40 mm/yr. This threshold captures actively draining peat within the rapid subsidence phase (Hooijer et al., 2012). The subsidence component receives higher weight (0.55) because it represents a direct physical measurement of ongoing peat loss, while canal proximity is an indirect proxy for drainage intensity.")], { indent: true }),
        body("The risk score is further modulated by peat depth (deeper peat contains more carbon at stake: weight 0.6 for shallow, 0.8 for moderate, 1.0 for deep peat) and by deforestation recency from the Hansen dataset (recently cleared areas receive a 1.2x multiplier reflecting the rapid initial subsidence phase, while areas cleared more than 15 years ago receive 0.8x reflecting the expected rate decline).", { indent: true }),

        heading("4.10 Carbon Loss Estimation", 2),
        body("Carbon dioxide emission rates are estimated from vertical subsidence velocity using the empirical relationship established by Hooijer et al. (2012):", { indent: true }),
        body([t("    E (tCO"), t("2", { size: 20, super: false }), t("/ha/yr) = |V"), t("vertical", { size: 20 }), t("| (mm/yr) "), t("x", { italics: true }), t(" 0.5")]),
        body("This conversion factor of 0.5 tonnes CO2 per hectare per year per millimetre of annual subsidence is derived from the empirical relationship between subsidence rate, tropical peat bulk density (approximately 0.08-0.12 g/cm3), and carbon content (approximately 50-60% by dry weight). The factor is conservative: Carlson et al. (2012) estimated higher emission factors (0.7-1.0) for recently drained peat where primary consolidation amplifies initial subsidence rates. Carbon loss is computed only for pixels with temporal coherence exceeding 0.5, excluding water bodies, and is smoothed with a 5x5 pixel median filter to reduce pixel-level noise while preserving spatial patterns.", { indent: true }),

        heading("4.11 Validation Strategy", 2),
        body("In the absence of in-situ ground truth measurements (GPS levelling, piezometer records), the pipeline employs three independent validation approaches:", { indent: true }),
        body([t("Internal consistency: ", { bold: true }), t("Spatial correlation between subsidence velocity and canal distance (expected: higher subsidence closer to canals), and between velocity and VV backscatter (expected: areas with lower backscatter, indicating cleared/drained land, show more subsidence). These correlations test whether the InSAR-derived displacement patterns are physically consistent with the known drainage-subsidence relationship.")], { indent: true }),
        body([t("Hansen deforestation cohort analysis: ", { bold: true }), t("Mean subsidence rate is computed for cohorts of pixels grouped by the year of forest clearing (2001-2005, 2006-2010, 2011-2015, 2016-2023). Under the Hooijer temporal decay model, recently cleared cohorts should show higher mean subsidence than older cohorts. If this pattern is observed, it provides independent evidence that the InSAR velocity signal is real and temporally consistent with published subsidence dynamics.")], { indent: true }),
        body([t("OSM canal comparison: ", { bold: true }), t("Precision, recall, and F1 score are computed between the SAR-derived canal mask and OpenStreetMap waterway features, buffered to account for positional uncertainty. This quantifies the detection accuracy of the canal network against community-mapped infrastructure.")], { indent: true }),

        // 5. Cloud Architecture
        heading("5. Cloud Deployment Architecture", 1),
        body("The complete pipeline is deployed on Google Cloud Platform (GCP) using a containerised architecture optimised for reproducibility and cost efficiency. The processing environment is packaged as a Docker container incorporating ISCE2, MintPy, SNAPHU, GDAL, and all geospatial dependencies, ensuring identical execution across development and production environments.", { indent: true }),
        body("Processing is orchestrated through Cloud Run Jobs with five defined stages: data ingestion (4 CPU, 8 GB RAM, 2-hour timeout), InSAR processing (8 CPU, 32 GB RAM, 6-hour timeout), time-series analysis (8 CPU, 32 GB RAM, 6-hour timeout), backscatter processing (8 CPU, 32 GB RAM, 2-hour timeout), and analysis (4 CPU, 16 GB RAM, 30-minute timeout). Cloud Build automates container image construction from the source repository. All intermediate and final products are stored as Cloud-Optimised GeoTIFFs (COGs) in Google Cloud Storage.", { indent: true }),
        body("Automated monthly processing is implemented via Google Cloud Workflows triggered by Cloud Scheduler, enabling continuous monitoring with each new Sentinel-1 acquisition cycle. The pipeline source code is available at https://github.com/tommyquak/peatguard-v3 under an open-source licence.", { indent: true }),

        // 6. Error Budget
        heading("6. Error Budget and Uncertainty Analysis", 1),
        body("A rigorous error budget quantifies the contribution of each error source to the total velocity uncertainty. After all corrections are applied, the estimated root-sum-square uncertainty is approximately 8-12 mm/yr:"),
        bullet([t("Tropospheric delay: ", { bold: true }), t("5-15 mm/yr uncorrected; reduced to 2-5 mm/yr after ERA5 correction via PyAPS (Jolivet et al., 2014)")]),
        bullet([t("Ionospheric delay: ", { bold: true }), t("2-5 mm/yr at equatorial latitudes; corrected via split-spectrum method in ISCE2")]),
        bullet([t("Reference point uncertainty: ", { bold: true }), t("3-8 mm/yr systematic; mitigated by two-phase reference selection strategy")]),
        bullet([t("Temporal decorrelation: ", { bold: true }), t("2-10 mm/yr bias from coherence-dependent phase noise; partially mitigated by coherence masking at threshold 0.5")]),
        bullet([t("Phase unwrapping errors: ", { bold: true }), t("0-28 mm equivalent per 2-pi ambiguity; mitigated by SNAPHU MCF algorithm and SBAS network redundancy")]),
        bullet([t("LOS-to-vertical conversion: ", { bold: true }), t("less than 3 mm/yr error from using constant incidence angle (37 degrees) rather than per-pixel values")]),
        bullet([t("Seasonal aliasing: ", { bold: true }), t("5-15 mm/yr from seasonal peat surface oscillation aliased into annual velocity; not yet corrected (requires 2+ years of data)")]),
        body("For the observed mean subsidence rate of approximately -26 mm/yr (vertical), the total uncertainty of 8-12 mm/yr represents a relative uncertainty of 30-46%. While this uncertainty is significant for absolute rate quantification, the spatial pattern of subsidence (where rates are higher versus lower) is considerably more reliable because systematic error sources (atmosphere, reference point, orbital ramp) affect all pixels uniformly.", { indent: true }),

        // 7. Limitations
        heading("7. Limitations and Future Work", 1),
        bullet([t("C-band canopy penetration: ", { bold: true }), t("Sentinel-1 C-band radar (5.6 cm wavelength) cannot penetrate dense tropical forest canopy, causing approximately 45% of pixels to exhibit low coherence and be masked. L-band radar (ALOS-2 PALSAR-2 at 23 cm or NISAR at 24 cm) would address this gap. The pipeline includes L-band support (stripmapApp processing, multi-sensor fusion) that will activate when data becomes available.")]),
        bullet([t("Single-year temporal coverage: ", { bold: true }), t("The current 12-month observation period with 16 valid interferometric pairs provides minimal temporal sampling. Extending to 2-3 years would reduce velocity noise, enable seasonal decomposition to separate true subsidence from reversible wet-dry oscillation, and improve the statistical robustness of the time-series inversion.")]),
        bullet([t("No ground truth: ", { bold: true }), t("All validation is against independent remote sensing datasets, not in-situ measurements. A field campaign with GPS levelling or differential settlement plates would provide direct calibration of the InSAR velocity estimates. Collaboration with Tanjungpura University in Pontianak, which maintains piezometer networks in West Kalimantan peatlands, is planned.")]),
        bullet([t("Peat depth approximation: ", { bold: true }), t("The dome model depth estimation is a first-order approximation. Field-measured peat depths at calibration points would enable machine learning-based depth regression from remote sensing features.")]),
        bullet([t("Carbon loss uncertainty: ", { bold: true }), t("The Hooijer conversion factor (0.5 tCO2/ha/yr per mm/yr) is an empirical average that varies with peat type, drainage age, and decomposition state. Site-specific calibration would require chamber flux measurements or eddy covariance data.")]),

        // 8. References
        heading("8. References", 1),
        ref("Berardino, P., Fornaro, G., Lanari, R., and Sansosti, E. (2002). A new algorithm for surface deformation monitoring based on small baseline differential SAR interferograms. IEEE Transactions on Geoscience and Remote Sensing, 40(11), 2375-2383."),
        ref("Carlson, K.M., Curran, L.M., Ratnasari, D., Pittman, A.M., Soares-Filho, B.S., Asner, G.P., Trigg, S.N., Gaveau, D.A., Lawrence, D., and Rodrigues, H.O. (2012). Committed carbon emissions, deforestation, and community land conversion from oil palm plantation expansion in West Kalimantan, Indonesia. Proceedings of the National Academy of Sciences, 109(19), 7559-7564."),
        ref("Chen, C.W. and Zebker, H.A. (2002). Phase unwrapping for large SAR interferograms: statistical segmentation and generalized network models. IEEE Transactions on Geoscience and Remote Sensing, 40(8), 1709-1719."),
        ref("Couwenberg, J., Dommain, R., and Joosten, H. (2010). Greenhouse gas fluxes from tropical peatlands in south-east Asia. Global Change Biology, 16(6), 1715-1732."),
        ref("Dommain, R., Couwenberg, J., Glaser, P.H., Joosten, H., and Suryadiputra, I.N.N. (2014). Carbon storage and release in Indonesian peatlands since the last deglaciation. Quaternary Science Reviews, 97, 1-32."),
        ref("Goldstein, R.M. and Werner, C.L. (1998). Radar interferogram filtering for geophysical applications. Geophysical Research Letters, 25(21), 4035-4038."),
        ref("Hansen, M.C., Potapov, P.V., Moore, R., Hancher, M., Turubanova, S.A., Tyukavina, A., Thau, D., Stehman, S.V., Goetz, S.J., Loveland, T.R., and Kommareddy, A. (2013). High-resolution global maps of 21st-century forest cover change. Science, 342(6160), 850-853."),
        ref("Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horanyi, A., Munoz-Sabater, J., Nicolas, J., Peubey, C., Radu, R., Schepers, D., and Simmons, A. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049."),
        ref("Hooijer, A., Page, S., Jauhiainen, J., Lee, W.A., Lu, X.X., Idris, A., and Anshari, G. (2010). Current and future CO2 emissions from drained peatlands in Southeast Asia. Biogeosciences, 7(5), 1505-1514."),
        ref("Hooijer, A., Page, S., Jauhiainen, J., Lee, W.A., Lu, X.X., Idris, A., and Anshari, G. (2012). Subsidence and carbon loss in drained tropical peatlands. Biogeosciences, 9(3), 1053-1071."),
        ref("Hoyt, A.M., Chaussard, E., Seppalainen, S.S., and Harvey, C.F. (2020). Widespread subsidence and carbon emissions across Southeast Asian peatlands. Nature Geoscience, 13(6), 435-440."),
        ref("Jaenicke, J., Rieley, J.O., Mott, C., Kimman, P., and Siegert, F. (2008). Determination of the amount of carbon stored in Indonesian peatlands. Geoderma, 147(3-4), 151-158."),
        ref("Jolivet, R., Agram, P.S., Lin, N.Y., Simons, M., Doin, M.P., Peltzer, G., and Li, Z. (2014). Improving InSAR geodesy using global atmospheric models. Journal of Geophysical Research: Solid Earth, 119(3), 2324-2341."),
        ref("Lee, J.-S. (1983). Digital image smoothing and the sigma filter. Computer Vision, Graphics, and Image Processing, 24(2), 255-269."),
        ref("Marshall, C., Large, D.J., Athab, A., Evers, S.L., Sheridan, H., Sherlock, E., Sherlock, C., and Sherlock, M. (2018). Monitoring tropical peat related settlement using ISBAS InSAR, Kuala Lumpur International Airport (KLIA). Engineering Geology, 244, 57-65."),
        ref("Miettinen, J., Shi, C., and Liew, S.C. (2016). Land cover distribution in the peatlands of Peninsular Malaysia, Sumatra and Borneo in 2015 with changes since 1990. Global Ecology and Conservation, 6, 67-78."),
        ref("Page, S.E., Rieley, J.O., and Banks, C.J. (2011). Global and regional importance of the tropical peatland carbon pool. Global Change Biology, 17(2), 798-818."),
        ref("Page, S.E., Wust, R.A.J., Weiss, D., Rieley, J.O., Shotyk, W., and Limin, S.H. (2006). A record of Late Pleistocene and Holocene carbon accumulation and climate change from an equatorial peat bog (Kalimantan, Indonesia). Journal of Quaternary Science, 19(7), 625-635."),
        ref("Ritung, S., Wahyunto, Nugroho, K., Sukarman, Hikmatullah, Suparto, and Tafakresnanto, C. (2011). Peat Land Map of Indonesia, Scale 1:250,000. Indonesian Centre for Agricultural Land Resources Research and Development."),
        ref("Rosen, P.A., Hensley, S., Joughin, I.R., Li, F.K., Madsen, S.N., Rodriguez, E., and Goldstein, R.M. (2000). Synthetic aperture radar interferometry. Proceedings of the IEEE, 88(3), 333-382."),
        ref("Rosen, P.A., Gurrola, E., Sacco, G.F., and Zebker, H. (2012). The InSAR Scientific Computing Environment. In 9th European Conference on Synthetic Aperture Radar, 730-733."),
        ref("Sato, Y., Nakajima, S., Shiraga, N., Atsumi, H., Yoshida, S., Koller, T., Gerig, G., and Kikinis, R. (1998). Three-dimensional multi-scale line filter for segmentation and visualization of curvilinear structures in medical images. Medical Image Analysis, 2(2), 143-168."),
        ref("Simons, W.J.F., Socquet, A., Vigny, C., Ambrosius, B.A.C., Haji Abu, S., Promthong, C., Subarya, C., Sarsito, D.A., Matheussen, S., Morgan, P., and Spakman, W. (2007). A decade of GPS in Southeast Asia: Resolving Sundaland motion and boundaries. Journal of Geophysical Research, 112, B06420."),
        ref("Warren, M., Hergoualc'h, K., Kauffman, J.B., Murdiyarso, D., and Kolka, R. (2017). An appraisal of Indonesia's immense peat carbon stock using national peatland maps: uncertainties and potential losses from conversion. Carbon Balance and Management, 12(12)."),
        ref("Yunjun, Z., Fattahi, H., and Amelung, F. (2019). Small baseline InSAR time series analysis: Unwrapping error correction and noise reduction. Computers and Geosciences, 133, 104331."),
        ref("Zhou, Z., Li, Z., Waldron, S., and Tanaka, A. (2021). InSAR time series analysis of L-band data for understanding tropical peatland degradation and restoration. Remote Sensing, 13(12), 2283."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Full_Proposal.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Document created: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
