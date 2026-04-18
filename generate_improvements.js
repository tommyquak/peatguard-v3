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
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
} = docx;

function t(text, opts = {}) {
  return new TextRun({
    text,
    font: "Arial",
    size: opts.size || 24,
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || "000000",
    break: opts.break,
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

function codePara(text) {
  return new Paragraph({
    children: [
      new TextRun({
        text,
        font: "Courier New",
        size: 20,
        color: "333333",
      }),
    ],
    spacing: { after: 80, line: 240 },
    indent: { left: convertInchesToTwip(0.5) },
  });
}

function makeTableCell(text, opts = {}) {
  return new TableCell({
    children: [
      new Paragraph({
        children: [t(text, { size: 20, bold: opts.bold || false })],
        spacing: { after: 40 },
      }),
    ],
    width: opts.width
      ? { size: opts.width, type: WidthType.PERCENTAGE }
      : undefined,
  });
}

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: Plans for Improvement",
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: {
            top: convertInchesToTwip(1),
            right: convertInchesToTwip(1),
            bottom: convertInchesToTwip(1),
            left: convertInchesToTwip(1),
          },
        },
      },
      children: [
        // Title
        new Paragraph({
          children: [
            new TextRun({
              text: "PeatGuard: Plans for Improvement",
              font: "Arial",
              size: 40,
              bold: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 60, line: 240 },
        }),
        new Paragraph({
          children: [
            new TextRun({
              text: "Improving Clarity and Confidence of Peatland Restoration Zone Detection",
              font: "Arial",
              size: 26,
              color: "444444",
              italics: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 120, line: 240 },
        }),
        new Paragraph({
          children: [
            new TextRun({ text: "Tommy Quak", font: "Arial", size: 28, color: "444444" }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 60, line: 240 },
        }),
        new Paragraph({
          children: [
            new TextRun({ text: "March 2026", font: "Arial", size: 28, color: "444444" }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 360, line: 240 },
        }),

        // Objective
        heading("Objective", 1),
        body(
          "This document identifies nine improvements to the PeatGuard satellite monitoring pipeline, each designed to increase the clarity and confidence of peatland restoration zone detection. Improvements are assessed by scientific impact, implementation effort, and data availability, then organized into three implementation phases. Phase 1 improvements use only existing pipeline outputs. Phase 2 improvements each require one additional freely available dataset. Phase 3 requires future temporal data from post-intervention monitoring."
        ),

        // 1. Confidence Mapping
        heading("1. Confidence Mapping", 1),
        labeledPara("Impact: ", "High"),
        labeledPara("Effort: ", "Low"),
        labeledPara("Data required: ", "None (all inputs already exist in the pipeline)"),

        heading("Problem", 2),
        body(
          "The pipeline produces velocity and risk maps but provides no per-pixel confidence indicator. A stakeholder examining the risk map cannot distinguish between a high-confidence measurement over cleared land and a noisy estimate at the edge of forest cover. The velocity uncertainty file exists but is not used in classification or risk scoring."
        ),

        heading("Proposed Solution", 2),
        body("Create a composite confidence layer (0 to 1) combining four existing metrics:"),
        bullet("Temporal coherence (already computed): higher coherence indicates more reliable phase measurement"),
        bullet("Velocity uncertainty (already computed): lower uncertainty indicates better-constrained velocity estimate"),
        bullet("Number of valid interferograms per pixel: more contributing pairs reduce random error"),
        bullet("Spatial consistency: agreement with neighboring pixels, measured as the inverse of local standard deviation of velocity within a 5-by-5 window"),
        body("The composite confidence is computed as a weighted sum:"),
        codePara("confidence = w1*coherence + w2*(1 - norm_uncertainty) + w3*norm_n_pairs + w4*spatial_consistency"),

        heading("Integration", 2),
        bullet("Weight the risk score by confidence: adjusted_risk = risk * confidence"),
        bullet("Export confidence as a separate GeoTIFF product for the dashboard"),
        bullet("Classification can use confidence to downgrade low-confidence severe pixels to an 'uncertain' category"),
        bullet("In the dashboard, display confidence as a semi-transparent overlay on the risk map"),

        // 2. Seasonal Decomposition
        heading("2. Seasonal Decomposition", 1),
        labeledPara("Impact: ", "High"),
        labeledPara("Effort: ", "Medium"),
        labeledPara("Data required: ", "Existing data; benefits from extending to 2+ years of acquisitions"),

        heading("Problem", 2),
        body(
          "Tropical peatlands expand and contract seasonally with wet and dry cycles. A single linear velocity estimated over one year conflates true subsidence (irreversible peat oxidation and compaction) with seasonal oscillation (reversible water table fluctuation). This introduces 5 to 15 mm/yr of apparent velocity variation depending on which part of the seasonal cycle the time series begins and ends. The current pipeline fits only a linear model to the displacement time series."
        ),

        heading("Proposed Solution", 2),
        body("Enable MintPy's periodic signal estimation to decompose the displacement time series into three components:"),
        bullet([t("Linear trend: ", { bold: true }), t("the true irreversible subsidence rate, which is the signal of interest for restoration prioritization")]),
        bullet([t("Seasonal amplitude: ", { bold: true }), t("the magnitude of annual surface oscillation, which indicates water table responsiveness")]),
        bullet([t("Seasonal phase: ", { bold: true }), t("the timing of peak and trough relative to the monsoon calendar")]),
        body("MintPy supports this natively with a single configuration parameter:"),
        codePara("mintpy.timeseries.periodicSignal = 365.25"),
        body("The seasonal amplitude is itself a useful product: areas with high seasonal amplitude have responsive water tables and may be the most amenable to rewetting interventions."),

        // 3. Land Cover Stratification
        heading("3. Land Cover Stratification", 1),
        labeledPara("Impact: ", "High"),
        labeledPara("Effort: ", "Medium"),
        labeledPara("Data required: ", "Sentinel-2 cloud-free composite (free, Copernicus Open Access Hub)"),

        heading("Problem", 2),
        body(
          "The risk score treats all land equally, but subsidence interpretation differs fundamentally by land cover type. Oil palm plantation on peat has expected ongoing subsidence that is difficult to halt without land use change. Degraded peat forest with active drainage impact is the primary target for canal blocking. Intact peat swamp forest showing any subsidence is alarming and indicates encroaching drainage. Recently cleared areas exhibit the highest subsidence rates in the first five years after drainage. Without land cover context, a measurement of -30 mm/yr over a mature plantation receives the same risk score as -30 mm/yr under degraded forest, even though the restoration priority and feasibility differ substantially."
        ),

        heading("Proposed Solution", 2),
        body("Derive a land cover map from Sentinel-2 optical imagery using NDVI thresholding and temporal signature analysis:"),
        bullet("Water: NDVI less than 0"),
        bullet("Bare or cleared land: NDVI 0 to 0.3"),
        bullet("Plantation: NDVI 0.3 to 0.6, with regular grid spatial pattern"),
        bullet("Degraded forest: NDVI 0.4 to 0.7, irregular spatial pattern"),
        bullet("Intact forest: NDVI greater than 0.7"),
        body("Integrate land cover into a restoration priority score:"),
        codePara("restoration_priority = risk_score * land_cover_weight * peat_depth_factor"),
        body("Where land_cover_weight is highest for degraded forest (most restorable, highest conservation value) and lowest for active plantation concessions (legally constrained, restoration requires concession holder cooperation)."),

        // 4. Peat Depth Integration
        heading("4. Peat Depth Integration", 1),
        labeledPara("Impact: ", "High"),
        labeledPara("Effort: ", "Low"),
        labeledPara("Data required: ", "CIFOR Indonesian Peat Map (free download from cifor.org)"),

        heading("Problem", 2),
        body(
          "The risk score does not account for peat depth. A subsiding area underlain by 10 meters of peat contains far more carbon at risk than a 2-meter peat area with the same subsidence rate. Restoration prioritization should weight by the total carbon stock that would be lost without intervention, not just the rate of loss."
        ),

        heading("Proposed Solution", 2),
        body("Overlay the CIFOR Indonesian Peat Map, which provides peat extent polygons and depth estimates across Indonesia. Rasterize to the pipeline grid and create a peat depth factor:"),
        bullet("No peat: 0.0 (exclude from restoration priority)"),
        bullet("Shallow peat (less than 2 meters): 0.5"),
        bullet("Moderate peat (2 to 4 meters): 0.8"),
        bullet("Deep peat (greater than 4 meters): 1.0"),
        body("Multiply this factor into the risk score to create a carbon-weighted priority map that directs restoration resources to where the most carbon is at stake."),

        // 5. Spatial Coherence Filtering
        heading("5. Spatial Coherence Filtering", 1),
        labeledPara("Impact: ", "Medium"),
        labeledPara("Effort: ", "Low"),
        labeledPara("Data required: ", "None (applied to existing classification output)"),

        heading("Problem", 2),
        body(
          "Isolated single pixels classified as severe subsidence surrounded by stable pixels are almost certainly noise from unwrapping errors or atmospheric residuals. These noisy pixels erode confidence in the results and can mislead restoration planning by directing attention to scattered point artifacts rather than coherent degradation zones."
        ),

        heading("Proposed Solution", 2),
        body("Apply a spatial consistency filter after classification:"),
        bullet("For each pixel, check whether more than 50% of neighbors within a 5-by-5 window share the same or adjacent severity class"),
        bullet("Isolated severe pixels surrounded by stable pixels are downgraded to the majority class"),
        bullet("Alternatively, require a minimum connected area of 1 hectare for each severity class to be reported as a distinct zone"),
        body("This approach is analogous to the morphological cleanup already applied to the canal mask and water mask products."),

        // 6. Cross-Validation with Optical Time Series
        heading("6. Cross-Validation with Optical Time Series", 1),
        labeledPara("Impact: ", "Medium"),
        labeledPara("Effort: ", "Medium"),
        labeledPara("Data required: ", "Sentinel-2 NDVI time series (free, Copernicus Open Access Hub or Google Earth Engine)"),

        heading("Problem", 2),
        body(
          "The InSAR-derived subsidence velocity has no independent validation in the study area. There are no ground truth measurements (GPS, leveling surveys, or piezometer records) available. Without cross-validation, the results depend entirely on the InSAR processing chain and its assumptions, and there is no way to distinguish real subsidence from systematic processing artifacts."
        ),

        heading("Proposed Solution", 2),
        body("Use Sentinel-2 NDVI time series as an independent degradation indicator:"),
        bullet("Peat degradation causes vegetation stress, which manifests as NDVI decline over time"),
        bullet("Canal construction is visible as abrupt NDVI drops at construction date"),
        bullet("Water table rise after rewetting should produce NDVI recovery"),
        body("Compute the spatial correlation between InSAR subsidence velocity and NDVI trend:"),
        bullet("Areas of high subsidence should correlate with NDVI decline"),
        bullet("Areas near canals should show lower mean NDVI than areas far from canals"),
        bullet("Report the Pearson correlation coefficient as a pipeline-level quality metric"),
        body("If InSAR subsidence and NDVI decline are spatially correlated (r greater than 0.5), this provides independent evidence that the subsidence signal is real and driven by peat degradation rather than atmospheric or processing artifacts. This correlation statistic can be included in Verra audit documentation."),

        // 7. Error Budget
        heading("7. Error Budget and Sensitivity Analysis", 1),
        labeledPara("Impact: ", "Medium"),
        labeledPara("Effort: ", "Low"),
        labeledPara("Data required: ", "None (computed from existing uncertainty products and literature values)"),

        heading("Problem", 2),
        body(
          "When presenting results to Verra auditors or carbon credit investors, the question 'how accurate is this?' currently has no quantitative answer. The velocity is reported as a point estimate without systematic error characterization. This undermines confidence in the results regardless of their actual quality."
        ),

        heading("Proposed Solution", 2),
        body("Compute and report an explicit error budget quantifying each error source:"),
        bullet("Tropospheric delay: 5-15 mm/yr (now corrected via ERA5)"),
        bullet("Ionospheric delay: 2-5 mm/yr (now corrected via split-spectrum)"),
        bullet("Reference point uncertainty: 3-8 mm/yr (mitigated with fixed reference)"),
        bullet("Temporal decorrelation bias: 2-10 mm/yr (partially mitigated by coherence masking)"),
        bullet("Phase unwrapping errors: 0-28 mm/yr per event (mitigated by MCF algorithm and SBAS network)"),
        bullet("Georeferencing error: 1-3 km spatial (known limitation)"),
        bullet("Seasonal aliasing: 5-15 mm/yr (not yet corrected, see Improvement 2)"),
        bullet([t("Total root-sum-square (corrected sources): approximately 8-12 mm/yr", { bold: true })]),
        body("Embed this error budget in product metadata and display it in the dashboard legend. A measurement reported as -30 plus or minus 10 mm/yr is far more useful for decision-making than -30 mm/yr alone."),

        // 8. Restoration Effectiveness Monitoring
        heading("8. Restoration Effectiveness Monitoring", 1),
        labeledPara("Impact: ", "High"),
        labeledPara("Effort: ", "High"),
        labeledPara("Data required: ", "Post-intervention Sentinel-1 acquisitions and intervention dates from field teams"),

        heading("Problem", 2),
        body(
          "The current pipeline detects where restoration is needed but cannot verify whether restoration interventions (canal blocking) are working. This is the critical gap for carbon credit MRV under Verra VCS VM0007: the methodology requires quantitative evidence that interventions are reducing greenhouse gas emissions from peat decomposition."
        ),

        heading("Proposed Solution", 2),
        body("Implement a before-and-after comparison capability:"),
        bullet("Split the displacement time series at the intervention date"),
        bullet("Estimate separate velocities for pre-intervention and post-intervention periods"),
        bullet("Compute a restoration effectiveness metric: effectiveness = velocity_post minus velocity_pre"),
        bullet("Positive effectiveness values indicate subsidence is slowing (intervention working)"),
        body("Complementary indicators of successful canal blocking:"),
        bullet("VV backscatter decrease near blocked canals (indicating rising water table)"),
        bullet("Coherence decrease in rewetted areas (indicating changing surface scattering conditions)"),
        bullet("These SAR-based indicators can be computed without ground visits"),
        body("This capability requires pre-intervention baseline data (the current pipeline output) and post-intervention acquisitions, which will accumulate automatically through the monthly scheduling system. Intervention dates and locations should be provided by the field team (Pak Agus, Teluk Bayur village head)."),

        // 9. Coherence as Land Cover Proxy
        heading("9. Coherence as Land Cover Proxy", 1),
        labeledPara("Impact: ", "Low"),
        labeledPara("Effort: ", "Very low"),
        labeledPara("Data required: ", "Already computed (coherence_median.tif)"),

        heading("Problem", 2),
        body(
          "No land cover information is currently used in the analysis pipeline. Obtaining optical imagery for a proper land cover classification requires a separate data pipeline and cloud-free compositing, which adds complexity."
        ),

        heading("Proposed Solution", 2),
        body("InSAR temporal coherence is already a reliable land cover indicator in tropical peatlands:"),
        bullet("High coherence (greater than 0.6): bare soil, urban structures, bridges, cleared land"),
        bullet("Moderate coherence (0.3 to 0.6): plantation canopy, sparse vegetation"),
        bullet("Low coherence (less than 0.3): dense forest, water bodies"),
        body("Export the coherence map with a simple three-class land cover proxy classification. This is a free byproduct of existing InSAR processing that requires zero additional computation or data acquisition. It provides an immediate, approximate land cover context until a proper Sentinel-2 classification is implemented in Phase 2."),

        // Implementation Priority
        heading("Implementation Priority", 1),
        body("The nine improvements are organized into three phases based on data dependencies and implementation complexity:"),

        heading("Phase 1: Existing Data Only (1-2 days)", 2),
        bullet([t("Confidence mapping", { bold: true }), t(" -- composite per-pixel quality indicator from coherence, uncertainty, pair count, and spatial consistency")]),
        bullet([t("Spatial coherence filtering", { bold: true }), t(" -- remove isolated noise pixels from classification")]),
        bullet([t("Coherence as land cover proxy", { bold: true }), t(" -- three-class land cover from existing coherence product")]),
        bullet([t("Error budget", { bold: true }), t(" -- quantified accuracy statement for stakeholder communication")]),

        heading("Phase 2: One Free Dataset Each (1-2 weeks)", 2),
        bullet([t("Peat depth integration", { bold: true }), t(" -- CIFOR peat map for carbon-weighted restoration priority")]),
        bullet([t("Seasonal decomposition", { bold: true }), t(" -- separate true subsidence from seasonal oscillation (MintPy native)")]),
        bullet([t("Land cover stratification", { bold: true }), t(" -- Sentinel-2 NDVI-based classification for context-aware risk scoring")]),
        bullet([t("Optical cross-validation", { bold: true }), t(" -- NDVI trend correlation as independent quality metric")]),

        heading("Phase 3: Future Temporal Data (ongoing)", 2),
        bullet([t("Restoration effectiveness monitoring", { bold: true }), t(" -- before/after velocity comparison for Verra MRV compliance")]),

        body(
          "Phase 1 improvements can be implemented immediately using only existing pipeline outputs. Phase 2 improvements each require downloading one additional freely available dataset (CIFOR peat map or Sentinel-2 imagery). Phase 3 requires accumulation of post-intervention satellite acquisitions over time, which the automated monthly scheduling system will handle.",
          { spacingBefore: 120 }
        ),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Improvement_Plans.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Document created: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
