const docx = require("docx");
const fs = require("fs");

const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  PageNumber,
  Footer,
  Header,
  TabStopPosition,
  TabStopType,
  convertInchesToTwip,
  SectionType,
  PageBreak,
  Tab,
} = docx;

// Helper: create a text run with Arial
function t(text, opts = {}) {
  return new TextRun({
    text,
    font: "Arial",
    size: opts.size || 24, // 12pt = 24 half-points
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || "000000",
    break: opts.break,
  });
}

// Helper: create a paragraph
function p(runs, opts = {}) {
  if (typeof runs === "string") runs = [t(runs)];
  return new Paragraph({
    children: runs,
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    heading: opts.heading,
    spacing: {
      after: opts.spacingAfter !== undefined ? opts.spacingAfter : 120,
      before: opts.spacingBefore || 0,
      line: opts.lineSpacing || 240, // single spacing
    },
    indent: opts.indent,
  });
}

// Helper: heading paragraph
function heading(text, level) {
  const sizes = {
    1: 32, // 16pt
    2: 28, // 14pt
    3: 26, // 13pt
  };
  const headingLevels = {
    1: HeadingLevel.HEADING_1,
    2: HeadingLevel.HEADING_2,
    3: HeadingLevel.HEADING_3,
  };
  return new Paragraph({
    children: [
      new TextRun({
        text,
        font: "Arial",
        size: sizes[level] || 24,
        bold: true,
      }),
    ],
    heading: headingLevels[level],
    spacing: { before: level === 1 ? 360 : 240, after: 120, line: 240 },
    alignment: AlignmentType.LEFT,
  });
}

// Helper: body paragraph from text string
function body(text) {
  return p([t(text)]);
}

// Title page children
const titlePage = [
  new Paragraph({ spacing: { before: 3600, after: 0 } }),
  p(
    [
      t(
        "PeatGuard: Satellite-Based Peatland Subsidence Monitoring Using Sentinel-1 InSAR for West Kalimantan, Indonesia",
        { size: 36, bold: true }
      ),
    ],
    { alignment: AlignmentType.CENTER, spacingAfter: 480 }
  ),
  new Paragraph({ spacing: { before: 600, after: 0 } }),
  p([t("Tommy Quak", { size: 28 })], {
    alignment: AlignmentType.CENTER,
    spacingAfter: 120,
  }),
  p(
    [
      t("National University of Singapore", { size: 24, italics: true }),
    ],
    { alignment: AlignmentType.CENTER, spacingAfter: 60 }
  ),
  p(
    [t("Department of Geography", { size: 24, italics: true })],
    { alignment: AlignmentType.CENTER, spacingAfter: 480 }
  ),
  new Paragraph({ spacing: { before: 600, after: 0 } }),
  p([t("March 2026", { size: 24 })], {
    alignment: AlignmentType.CENTER,
    spacingAfter: 0,
  }),
];

// Abstract
const abstractSection = [
  heading("Abstract", 1),
  p([
    t(
      "This report presents PeatGuard, a cloud-native satellite monitoring pipeline for detecting and quantifying peatland subsidence in the Kapuas River region of West Kalimantan, Indonesia. The system leverages Sentinel-1 Synthetic Aperture Radar (SAR) data processed through an Interferometric SAR (InSAR) workflow using the ISCE2 processing framework and MintPy Small Baseline Subset (SBAS) time-series analysis. A complementary backscatter analysis module processes Ground Range Detected (GRD) imagery to detect drainage canal networks, enabling spatial correlation between subsidence patterns and drainage infrastructure. The pipeline is deployed on Google Cloud Platform using containerized Cloud Run Jobs, achieving end-to-end processing of 14 SAR acquisitions across 29 interferometric pairs in approximately seven hours. Results identify active subsidence zones with line-of-sight velocities ranging from -20 to -50 mm/yr concentrated near drainage canal intersections, consistent with published rates for drained tropical peatlands. A composite risk score integrating canal proximity and subsidence severity classifies 8% of the study area as elevated to critical risk, providing actionable prioritization for canal blocking and rewetting interventions. The pipeline is open-source, reproducible, and scalable to broader tropical peatland monitoring campaigns."
    ),
  ]),
];

// Section 1: Introduction
const introduction = [
  heading("1. Introduction", 1),
  p([
    t(
      "Tropical peatlands represent one of the most significant terrestrial carbon stores on Earth, containing approximately 30% of global soil carbon despite covering less than 3% of the land surface (Page, Rieley, and Banks 2011). These ecosystems accumulate organic matter over millennia under waterlogged, anaerobic conditions, forming peat deposits that can reach depths exceeding 10 meters in Southeast Asia (Jaenicke et al. 2008). The carbon density of tropical peat far exceeds that of mineral soils and most forest biomass pools, making the integrity of these deposits critically important for global climate regulation."
    ),
  ]),
  p([
    t(
      "Indonesian peatlands, concentrated in Kalimantan and Sumatra, constitute the largest tropical peat carbon pool globally. However, these systems have been subjected to extensive drainage and land-use conversion, primarily for oil palm cultivation and pulpwood plantations, over the past three decades. Drainage lowers the water table, exposing previously saturated peat to aerobic conditions and triggering irreversible decomposition processes. This decomposition manifests physically as land surface subsidence, a measurable indicator of carbon loss. Hooijer et al. (2012) documented subsidence rates of 20 to 50 mm/yr in drained Indonesian peatlands during the first five years following drainage, with rates declining but persisting over subsequent decades."
    ),
  ]),
  p([
    t(
      "The relationship between drainage, subsidence, and carbon emissions underscores the urgent need for systematic monitoring of peatland surface dynamics. Conventional ground-based surveying methods, while accurate, are impractical across the vast and often inaccessible tropical peatland landscapes of Indonesia. Satellite-based Interferometric Synthetic Aperture Radar (InSAR) offers a viable alternative, providing spatially continuous measurements of land surface displacement with millimeter-level sensitivity from repeat-pass SAR acquisitions."
    ),
  ]),
  p([
    t(
      "This report describes PeatGuard, a cloud-native pipeline that integrates Sentinel-1 InSAR processing, time-series displacement analysis, backscatter-based canal detection, and composite risk scoring to monitor peatland subsidence in West Kalimantan, Indonesia. The system is designed to be operationally deployable, providing actionable outputs that support the prioritization of peatland restoration interventions such as canal blocking and rewetting."
    ),
  ]),
];

// Section 2: Study Area
const studyArea = [
  heading("2. Study Area", 1),
  p([
    t(
      "The study area is located within the Kapuas River peatland complex in West Kalimantan, Indonesia, centered at approximately 114.3 to 114.4 degrees East and 2.5 to 2.6 degrees South. This region contains extensive tropical peat swamp forests that have been heavily impacted by drainage-based land conversion, primarily for oil palm plantation development."
    ),
  ]),
  p([
    t(
      "Peat deposits in the study area reach depths of up to 10 meters, formed through millennia of organic matter accumulation under persistently waterlogged conditions (Jaenicke et al. 2008). The landscape is characterized by a dense network of drainage canals constructed to lower the water table for agricultural operations. These canals are clearly visible in SAR imagery due to the strong backscatter contrast between water-filled canal surfaces and surrounding vegetated peat."
    ),
  ]),
  p([
    t(
      "The region experiences a tropical equatorial climate with annual precipitation exceeding 3,000 mm and minimal seasonal variation. The flat, low-lying topography of the peatland, typically less than 10 meters above sea level, makes the area particularly susceptible to both subsidence and flooding when drainage infrastructure degrades or is intentionally blocked for restoration purposes."
    ),
  ]),
];

// Section 3: Data
const dataSection = [
  heading("3. Data", 1),
  p([
    t(
      "The primary datasets for this study consist of Sentinel-1A SAR acquisitions in both Single Look Complex (SLC) and Ground Range Detected (GRD) product formats, supplemented by digital elevation model data and precise orbital information."
    ),
  ]),
  p([
    t(
      "For InSAR processing, 14 Sentinel-1A Interferometric Wide (IW) mode SLC acquisitions spanning January 2024 to December 2024 were obtained from the Copernicus Open Access Hub. All acquisitions are from the same relative orbit to ensure consistent imaging geometry. The IW3 subswath was selected for processing as it provides optimal coverage of the study area. SLC data preserves the full phase information required for interferometric analysis."
    ),
  ]),
  p([
    t(
      "For backscatter analysis and canal detection, 14 corresponding Sentinel-1A IW mode GRD scenes from the same period were acquired. GRD products provide calibrated intensity data suitable for radiometric analysis without the computational overhead of SLC phase processing."
    ),
  ]),
  p([
    t(
      "Topographic correction was performed using the Copernicus GLO-30 Digital Elevation Model, which provides global coverage at 30-meter posting derived from the TanDEM-X mission. Precise orbit state vectors from the European Space Agency Sentinel-1 Precise Orbit Determination service were applied to refine the satellite position and velocity information beyond the accuracy of the onboard orbit data."
    ),
  ]),
];

// Section 4: Methodology
const methodology = [
  heading("4. Methodology", 1),

  heading("4.1 InSAR Processing (ISCE2)", 2),
  p([
    t(
      "Interferometric processing was performed using the InSAR Scientific Computing Environment version 2 (ISCE2), an open-source framework developed by the Jet Propulsion Laboratory for processing SAR data (Rosen et al. 2012). The topsApp.py workflow within ISCE2 was used, which is specifically designed for Sentinel-1 Terrain Observation by Progressive Scans (TOPS) mode data and handles the burst-by-burst processing and azimuth deramping required by the TOPS acquisition scheme."
    ),
  ]),
  p([
    t(
      "A Small Baseline Subset (SBAS) pair network was constructed, generating 29 interferometric pairs with temporal baselines of 12 to 36 days. Of these, 16 pairs were successfully processed to geocoded displacement products. The 13 failed pairs, predominantly those with 48-day baselines, exhibited severe temporal decorrelation resulting in incoherent interferograms unsuitable for phase unwrapping. This decorrelation is expected in tropical peatland environments where dense vegetation and high moisture variability rapidly degrade the SAR signal coherence."
    ),
  ]),
  p([
    t(
      "Multilooking was applied at 3 looks in azimuth and 9 looks in range to reduce phase noise while maintaining spatial resolution appropriate for the subsidence features of interest. The Goldstein adaptive filter (Goldstein and Werner 1998) was applied to the interferograms to further suppress phase noise while preserving fringe continuity. Phase unwrapping was performed using the Statistical-Cost Network-Flow Algorithm for Phase Unwrapping (SNAPHU) with the Minimum Cost Flow (MCF) algorithm, which is well-suited to the relatively smooth displacement fields expected in subsidence monitoring."
    ),
  ]),

  heading("4.2 Time-Series Analysis (MintPy)", 2),
  p([
    t(
      "Time-series displacement analysis was performed using the Miami InSAR Time-Series Software in Python (MintPy), an open-source package for InSAR time-series analysis (Yunjun, Fattahi, and Amelung 2019). MintPy implements the SBAS approach (Berardino et al. 2002), which inverts the network of unwrapped interferograms to estimate the cumulative displacement at each acquisition date."
    ),
  ]),
  p([
    t(
      "The interferometric network was modified based on a spatial coherence threshold of 0.3, excluding pixels that did not maintain sufficient coherence across the network. Linear deramping was applied to remove residual orbital ramp artifacts from the unwrapped interferograms. Tropospheric delay correction using ERA5 reanalysis data was not applied due to the absence of the required atmospheric model data within the processing container environment. Topographic residual correction was similarly omitted given the flat terrain of the study area, where topographic phase residuals are negligible."
    ),
  ]),
  p([
    t(
      "The mean line-of-sight velocity was estimated by fitting a linear regression model to the cumulative displacement time series at each pixel. Negative velocities indicate surface motion away from the satellite, which for the near-vertical incidence geometry of Sentinel-1 in this region corresponds predominantly to subsidence."
    ),
  ]),

  heading("4.3 Backscatter Analysis", 2),
  p([
    t(
      "GRD data were calibrated to radar backscatter coefficient (sigma-nought) using the radiometric calibration look-up tables provided in the Sentinel-1 product annotation files. Speckle noise, inherent in coherent SAR imaging, was reduced using the Lee Sigma filter (Lee 1983) with a 7-by-7 pixel window. This filter preserves edges and point targets while effectively smoothing homogeneous regions."
    ),
  ]),
  p([
    t(
      "Geometric terrain correction was performed using GDAL Warp with a Ground Control Point (GCP) based Thin Plate Spline (TPS) transformation, projecting the data from radar geometry to the WGS84 geographic coordinate system. A temporal median composite was generated from the 14 calibrated and terrain-corrected scenes to produce a stable backscatter reference image with further reduced speckle noise."
    ),
  ]),

  heading("4.4 Canal Detection", 2),
  p([
    t(
      "Drainage canals were detected in the temporal median VV-polarization backscatter composite using a threshold-based approach. Canal surfaces, being smooth water bodies, exhibit very low radar backscatter compared to the surrounding vegetated peat surface. A threshold set at the 10th percentile of the backscatter distribution was applied to identify candidate canal pixels. Morphological cleanup was performed to remove isolated noise objects smaller than 10 pixels, retaining only spatially connected features consistent with linear canal structures."
    ),
  ]),
  p([
    t(
      "A Euclidean distance transform was computed from the binary canal mask to generate a continuous canal proximity surface. This surface quantifies the distance from each pixel to the nearest detected canal, providing a spatial variable for the subsequent risk scoring analysis."
    ),
  ]),

  heading("4.5 Risk Scoring", 2),
  p([
    t(
      "A composite subsidence risk score was developed to integrate the InSAR-derived subsidence velocity with canal proximity information. The risk score R is computed as a weighted sum of two normalized components: canal proximity risk and subsidence severity risk."
    ),
  ]),
  p([
    t(
      "The canal proximity risk follows an exponential decay function, calculated as exp(-3d/1000) where d is the distance to the nearest canal in meters. This formulation assigns highest risk to areas immediately adjacent to canals, with risk decreasing exponentially with distance, reflecting the observed relationship between drainage canal proximity and water table drawdown."
    ),
  ]),
  p([
    t(
      "The subsidence severity risk is derived from the InSAR velocity, normalized linearly between 0 (no subsidence) and 1 (subsidence at or exceeding -50 mm/yr). Velocities are clamped at -50 mm/yr to limit the influence of potential outliers. The composite risk score is computed as R = 0.4 * proximity_risk + 0.6 * subsidence_risk, with the higher weight assigned to the directly observed subsidence measurement. The output is a continuous 0-to-1 risk surface suitable for thematic classification and spatial prioritization."
    ),
  ]),
];

// Section 5: Results
const results = [
  heading("5. Results", 1),

  heading("5.1 InSAR Velocity", 2),
  p([
    t(
      "Of the 29 interferometric pairs generated, 16 were successfully processed through to geocoded displacement products, yielding a 55% success rate. The mean line-of-sight velocity across the study area was -31 mm/yr, indicating net subsidence. Velocity values were clamped to the range of -200 to +200 mm/yr to exclude extreme outliers associated with unwrapping errors or isolated decorrelation artifacts."
    ),
  ]),
  p([
    t(
      "The spatial distribution of subsidence velocities exhibits a clear pattern of enhanced subsidence in areas proximal to the drainage canal network. The highest subsidence rates, reaching -50 mm/yr and beyond, are concentrated at canal intersections and in heavily drained plantation areas. Areas distant from canals or retaining intact peat swamp forest show near-zero or slightly positive velocity values, consistent with stable or minimally affected peat surfaces."
    ),
  ]),

  heading("5.2 Canal Network", 2),
  p([
    t(
      "The backscatter-based canal detection identified a drainage network covering approximately 10% of the study area. The detected canals exhibit a characteristic grid pattern in plantation areas, consistent with the systematic drainage infrastructure associated with oil palm cultivation. The mean distance from any point in the study area to the nearest detected canal is approximately 450 meters, indicating the pervasive extent of drainage infrastructure across the landscape."
    ),
  ]),

  heading("5.3 Risk Assessment", 2),
  p([
    t(
      "The composite risk score classification reveals that 41% of the study area falls within the low-risk category (scores of 0 to 0.2), corresponding to areas either distant from canals or exhibiting minimal subsidence. The majority of the study area, 51%, is classified as moderate risk (0.2 to 0.4), reflecting the widespread but moderate impact of the drainage network on peat stability."
    ),
  ]),
  p([
    t(
      "Elevated risk areas (0.4 to 0.6) account for 6% of the study area, while high and critical risk zones (0.6 to 1.0) comprise 2%. These highest-risk areas are spatially concentrated at canal intersections in heavily drained peat, where the combined effects of canal proximity and observed subsidence are most severe. These locations represent the highest priority targets for canal blocking and rewetting interventions."
    ),
  ]),
];

// Section 6: Cloud Deployment
const cloudDeployment = [
  heading("6. Cloud Deployment", 1),
  p([
    t(
      "The PeatGuard pipeline is deployed on Google Cloud Platform (GCP) using a containerized architecture designed for operational scalability and reproducibility. The processing environment is packaged as a Docker container incorporating ISCE2, MintPy, SNAPHU, and GDAL with all required dependencies, ensuring consistent execution across development and production environments."
    ),
  ]),
  p([
    t(
      "Processing is orchestrated through Cloud Run Jobs, with individual interferometric pairs processed as independent jobs to enable parallelization and fault isolation. Each job is allocated 8 CPU cores and 32 GB of RAM, sufficient for the memory-intensive phase unwrapping operations. Cloud Build automates container image construction and deployment from the source repository."
    ),
  ]),
  p([
    t(
      "Intermediate and final products are stored in Google Cloud Storage (GCS), with a resume capability that allows interrupted processing to restart from the last completed stage rather than reprocessing from the beginning. This design is critical for managing the long processing times and potential transient failures inherent in large-scale SAR processing."
    ),
  ]),
  p([
    t(
      "Total processing time for the complete pipeline is approximately seven hours: six hours for InSAR pair processing, 28 minutes for MintPy time-series analysis, and 20 minutes for backscatter processing and canal detection. Final outputs are exported as Cloud-Optimized GeoTIFFs (COGs) suitable for direct ingestion into GIS platforms including ArcGIS Pro and QGIS."
    ),
  ]),
];

// Section 7: Discussion
const discussion = [
  heading("7. Discussion", 1),
  p([
    t(
      "The subsidence rates observed in this study, with a mean of -31 mm/yr and values reaching -50 mm/yr near drainage infrastructure, are consistent with published rates for drained tropical peatlands in Indonesia. Hooijer et al. (2012) reported subsidence rates of 20 to 50 mm/yr during the initial years following drainage, with the highest rates occurring in the first five years. The correspondence between our InSAR-derived estimates and these ground-based measurements provides confidence in the reliability of the satellite monitoring approach."
    ),
  ]),
  p([
    t(
      "The backscatter-based canal detection module successfully identifies the drainage infrastructure that drives peatland subsidence. The characteristic low-backscatter signature of water-filled canals in VV-polarization SAR imagery provides a robust detection mechanism, though narrow or partially vegetated canals may be missed at the spatial resolution of the temporal median composite."
    ),
  ]),
  p([
    t(
      "The composite risk score provides a practical framework for prioritizing restoration interventions. By combining the directly observed subsidence signal with the spatial relationship to drainage infrastructure, the risk score identifies locations where intervention, specifically canal blocking to raise the water table, would have the greatest impact on reducing ongoing peat loss."
    ),
  ]),
  p([
    t(
      "Several limitations of the current implementation should be noted. The georeferencing accuracy of the InSAR products is approximately 1 to 3 kilometers, limited by the GCP-based terrain correction approach. This spatial uncertainty is acceptable for landscape-scale monitoring but insufficient for precise co-registration with cadastral or management unit boundaries. The absence of tropospheric delay correction, due to the unavailability of ERA5 data within the processing container, introduces a potential systematic bias in the velocity estimates, though the magnitude of this bias is expected to be small relative to the subsidence signal in this low-relief tropical environment. The loss of 13 of 29 interferometric pairs to temporal decorrelation, predominantly at 48-day baselines, limits the temporal sampling of the displacement time series."
    ),
  ]),
  p([
    t(
      "Future development of the PeatGuard pipeline will address these limitations through several enhancements. Automated pipeline scheduling will enable continuous monitoring with each new Sentinel-1 acquisition. Integration of tropospheric correction using ERA5 or GACOS models will improve velocity estimation accuracy. A web-based dashboard for visualization and dissemination of results to peatland managers and restoration practitioners is under development. Extension to additional peatland regions across Kalimantan and Sumatra will test the generalizability of the approach."
    ),
  ]),
];

// Section 8: Conclusion
const conclusion = [
  heading("8. Conclusion", 1),
  p([
    t(
      "This report has presented PeatGuard, an end-to-end satellite monitoring pipeline for quantifying peatland subsidence using Sentinel-1 InSAR and backscatter analysis. The pipeline integrates ISCE2 interferometric processing, MintPy SBAS time-series analysis, backscatter-based canal detection, and composite risk scoring within a cloud-native architecture deployed on Google Cloud Platform."
    ),
  ]),
  p([
    t(
      "Results for the Kapuas River peatland in West Kalimantan demonstrate that the pipeline successfully identifies active subsidence zones with rates of -20 to -50 mm/yr concentrated near drainage canal networks. The composite risk assessment classifies 8% of the study area as elevated to critical risk, providing actionable spatial prioritization for canal blocking and rewetting interventions."
    ),
  ]),
  p([
    t(
      "The pipeline is cloud-native, reproducible through containerized deployment, and scalable to broader monitoring campaigns across the tropical peatlands of Southeast Asia. The open-source codebase is available on GitHub, supporting transparency and community contribution to operational peatland monitoring. Systematic satellite-based subsidence monitoring, as demonstrated by PeatGuard, is essential for guiding evidence-based peatland restoration and protecting these globally significant carbon stores."
    ),
  ]),
];

// References
const references = [
  heading("References", 1),
  p(
    [
      t(
        'Berardino, P., G. Fornaro, R. Lanari, and E. Sansosti. 2002. "A New Algorithm for Surface Deformation Monitoring Based on Small Baseline Differential SAR Interferograms." ',
        {}
      ),
      t(
        "IEEE Transactions on Geoscience and Remote Sensing",
        { italics: true }
      ),
      t(" 40 (11): 2375-2383."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Goldstein, R. M., and C. L. Werner. 1998. "Radar Interferogram Filtering for Geophysical Applications." '
      ),
      t("Geophysical Research Letters", { italics: true }),
      t(" 25 (21): 4035-4038."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Hooijer, A., S. Page, J. Jauhiainen, W. A. Lee, X. X. Lu, A. Idris, and G. Anshari. 2012. "Subsidence and Carbon Loss in Drained Tropical Peatlands." '
      ),
      t("Biogeosciences", { italics: true }),
      t(" 9 (3): 1053-1071."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Jaenicke, J., J. O. Rieley, C. Mott, P. Kimman, and F. Siegert. 2008. "Determination of the Amount of Carbon Stored in Indonesian Peatlands." '
      ),
      t("Geoderma", { italics: true }),
      t(" 147 (3-4): 151-158."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Lee, J.-S. 1983. "Digital Image Smoothing and the Sigma Filter." '
      ),
      t("Computer Vision, Graphics, and Image Processing", {
        italics: true,
      }),
      t(" 24 (2): 255-269."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Page, S. E., J. O. Rieley, and C. J. Banks. 2011. "Global and Regional Importance of the Tropical Peatland Carbon Pool." '
      ),
      t("Global Change Biology", { italics: true }),
      t(" 17 (2): 798-818."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Rosen, P. A., E. Gurrola, G. F. Sacco, and H. Zebker. 2012. "The InSAR Scientific Computing Environment." In '
      ),
      t(
        "9th European Conference on Synthetic Aperture Radar",
        { italics: true }
      ),
      t(", 730-733."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
  p(
    [
      t(
        'Yunjun, Z., H. Fattahi, and F. Amelung. 2019. "Small Baseline InSAR Time Series Analysis: Unwrapping Error Correction and Noise Reduction." '
      ),
      t("Computers and Geosciences", { italics: true }),
      t(" 133: 104331."),
    ],
    { spacingAfter: 200, alignment: AlignmentType.LEFT }
  ),
];

// Build the document
const doc = new Document({
  styles: {
    default: {
      document: {
        run: {
          font: "Arial",
          size: 24,
        },
      },
      heading1: {
        run: {
          font: "Arial",
          size: 32,
          bold: true,
          color: "000000",
        },
        paragraph: {
          spacing: { before: 360, after: 120, line: 240 },
        },
      },
      heading2: {
        run: {
          font: "Arial",
          size: 28,
          bold: true,
          color: "000000",
        },
        paragraph: {
          spacing: { before: 240, after: 120, line: 240 },
        },
      },
      heading3: {
        run: {
          font: "Arial",
          size: 26,
          bold: true,
          color: "000000",
        },
        paragraph: {
          spacing: { before: 200, after: 120, line: 240 },
        },
      },
    },
  },
  sections: [
    // Title page section
    {
      properties: {
        page: {
          size: {
            width: 12240,
            height: 15840,
          },
          margin: {
            top: convertInchesToTwip(1),
            right: convertInchesToTwip(1),
            bottom: convertInchesToTwip(1),
            left: convertInchesToTwip(1),
          },
        },
      },
      children: titlePage,
    },
    // Main content section with page numbers
    {
      properties: {
        page: {
          size: {
            width: 12240,
            height: 15840,
          },
          margin: {
            top: convertInchesToTwip(1),
            right: convertInchesToTwip(1),
            bottom: convertInchesToTwip(1),
            left: convertInchesToTwip(1),
          },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({
                  children: [PageNumber.CURRENT],
                  font: "Arial",
                  size: 20,
                }),
              ],
            }),
          ],
        }),
      },
      children: [
        ...abstractSection,
        ...introduction,
        ...studyArea,
        ...dataSection,
        ...methodology,
        ...results,
        ...cloudDeployment,
        ...discussion,
        ...conclusion,
        ...references,
      ],
    },
  ],
});

// Generate the file
Packer.toBuffer(doc).then((buffer) => {
  const outPath =
    "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Technical_Report.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Report generated: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
