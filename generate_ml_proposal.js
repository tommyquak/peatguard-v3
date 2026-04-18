const docx = require("docx");
const fs = require("fs");

const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  convertInchesToTwip, Footer, PageNumber, Table, TableRow, TableCell, WidthType,
} = docx;

function t(text, opts = {}) {
  return new TextRun({ text, font: "Arial", size: opts.size || 24, bold: opts.bold || false, italics: opts.italics || false, color: opts.color || "000000" });
}
function body(text, opts = {}) {
  return new Paragraph({ children: [t(text)], alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, before: opts.spacingBefore || 0, line: 276 } });
}
function heading(text, level) {
  const sizes = { 1: 32, 2: 28, 3: 26 };
  const hl = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({ children: [new TextRun({ text, font: "Arial", size: sizes[level], bold: true })], heading: hl[level], spacing: { before: level === 1 ? 360 : 240, after: 120, line: 240 }, alignment: AlignmentType.LEFT });
}
function bullet(text, level = 0) {
  const children = typeof text === "string" ? [t(text)] : text;
  return new Paragraph({ children, bullet: { level }, spacing: { after: 60, line: 276 }, alignment: AlignmentType.LEFT });
}
function labeledPara(label, text) {
  return new Paragraph({ children: [t(label, { bold: true }), t(text)], alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 276 } });
}
function makeCell(text, opts = {}) {
  return new TableCell({ children: [new Paragraph({ children: [t(text, { size: 20, bold: opts.bold })], spacing: { after: 40 } })], width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined });
}
function makeRow(cells, opts = {}) { return new TableRow({ children: cells.map(c => makeCell(c, opts)) }); }

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: Machine Learning Integration Proposal",
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: convertInchesToTwip(1), right: convertInchesToTwip(1), bottom: convertInchesToTwip(1), left: convertInchesToTwip(1) } },
    },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 20 })] })] }) },
    children: [
      // Title
      new Paragraph({ spacing: { before: 2400 } }),
      new Paragraph({ children: [t("Machine Learning Integration Proposal", { size: 40, bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
      new Paragraph({ children: [t("PeatGuard Satellite Monitoring Pipeline", { size: 28, color: "444444" })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
      new Paragraph({ children: [t("Tommy Quak -- National University of Singapore", { size: 24, color: "444444" })], alignment: AlignmentType.CENTER, spacing: { after: 60 } }),
      new Paragraph({ children: [t("March 2026", { size: 24, color: "444444" })], alignment: AlignmentType.CENTER, spacing: { after: 600 } }),

      // 1. Context
      heading("1. Context and Motivation", 1),
      body("The PeatGuard pipeline currently uses physics-based and rule-based algorithms for all processing stages: InSAR displacement measurement (ISCE2/MintPy), backscatter thresholding for canal detection, empirical conversion factors for carbon loss estimation, and literature-calibrated thresholds for classification and risk scoring. These approaches are transparent, reproducible, and defensible for third-party auditing."),
      body("This proposal evaluates where machine learning could improve detection accuracy, reduce noise, or extract information that physics-based methods cannot. Each candidate application is assessed for realistic benefit, data requirements, implementation effort, and whether it improves or undermines auditability. The goal is to identify high-value ML applications while avoiding complexity that does not measurably improve restoration zone detection."),

      // 2. Honest Assessment
      heading("2. Honest Assessment: Where ML Helps vs Where It Does Not", 1),
      body("Machine learning is not universally beneficial. For PeatGuard, the core measurement (InSAR subsidence velocity) is a physics-based computation that ML cannot improve -- it depends on the radar wavelength, satellite geometry, and atmospheric conditions, not on learned patterns. Similarly, the carbon loss conversion factor is an empirical physical relationship that ML has no advantage over."),
      body("ML adds genuine value in three scenarios: (1) pattern recognition tasks where human-defined rules are insufficient, such as distinguishing canals from other dark features in SAR imagery; (2) multivariate integration where non-linear interactions between features carry information, such as combining velocity, coherence, backscatter, and peat depth into a restoration priority; and (3) unsupervised discovery of spatial patterns that are not visible through threshold-based analysis."),
      body("ML does NOT help when: the problem is well-solved by physics (InSAR inversion), labeled training data does not exist (supervised classification without ground truth), or the added complexity undermines the interpretability required for carbon credit auditing."),

      // 3. Candidate Applications
      heading("3. Candidate Applications", 1),

      // 3.1 Canal Segmentation
      heading("3.1 Canal Network Segmentation (U-Net)", 2),
      labeledPara("Benefit: ", "HIGH -- addresses the primary detection quality issue"),
      labeledPara("Data requirement: ", "Moderate -- needs 500-1000 labeled image patches"),
      labeledPara("Implementation effort: ", "2-3 weeks"),

      heading("Problem", 3),
      body("The current canal detection uses VV backscatter thresholding combined with a Sato ridge filter. This approach has two persistent issues: false positives from dark non-canal features (shadows, wet soil, vegetation boundaries) and false negatives from narrow canals (2-5 meters wide) that do not produce sufficient backscatter contrast at 10-meter pixel spacing. The canal mask coverage is 19.8%, which is higher than the expected 5-10% for the canal network alone, indicating substantial noise."),

      heading("Proposed Approach", 3),
      body("Train a U-Net semantic segmentation model on VV backscatter patches to classify each pixel as canal or non-canal. U-Net is the standard architecture for geospatial segmentation because its encoder-decoder structure with skip connections preserves spatial detail while learning contextual features."),
      bullet("Input: 64x64 pixel patches from the VV median composite (10m resolution, covering 640x640 meter areas)"),
      bullet("Output: Binary mask (canal / non-canal) at same resolution"),
      bullet("Architecture: U-Net with ResNet-18 encoder (pretrained on ImageNet), 4 downsampling levels"),
      bullet("Training data sources:"),
      bullet("  (a) Manual digitization of canals on Google Earth high-resolution optical imagery for 50-100 patches", 1),
      bullet("  (b) OSM waterway features rasterized to 10m grid as weak labels for an additional 200-300 patches", 1),
      bullet("  (c) The existing threshold+ridge detection as pseudo-labels for bootstrapping, with manual correction of obvious errors", 1),
      bullet("Loss function: Binary cross-entropy with dice loss (handles class imbalance, canals are ~5-10% of pixels)"),
      bullet("Augmentation: Random rotation (canals run in multiple orientations), flip, brightness/contrast jitter"),
      bullet("Framework: PyTorch with segmentation-models-pytorch library"),

      heading("Expected Improvement", 3),
      bullet("Precision: ~90% (vs ~60% current, reducing false canal detections by 3x)"),
      bullet("Recall: ~80% (vs ~50% current, detecting more narrow canals)"),
      bullet("The model learns spatial context (canal grid pattern, linear continuity) that thresholding cannot capture"),

      heading("Limitations", 3),
      bullet("Requires labeled training data creation (2-3 days of manual work)"),
      bullet("The 10-meter resolution limit means canals narrower than ~4 meters are still fundamentally undetectable regardless of method"),
      bullet("Model performance degrades outside the training distribution (different peatland regions may need retraining)"),
      bullet("Adds a deep learning dependency (PyTorch) to a pipeline that currently requires only numpy/scipy/scikit-image"),

      // 3.2 Unsupervised Clustering
      heading("3.2 Unsupervised Degradation Zone Clustering", 2),
      labeledPara("Benefit: ", "MEDIUM -- reveals natural spatial patterns without requiring labels"),
      labeledPara("Data requirement: ", "None (uses existing products)"),
      labeledPara("Implementation effort: ", "2-3 days"),

      heading("Problem", 3),
      body("The current risk score is a weighted sum of two variables (canal proximity and subsidence velocity). This assumes a linear, additive relationship and ignores potentially informative features like coherence (land cover proxy), backscatter intensity (vegetation density), deforestation timing, and peat depth. A pixel with moderate subsidence but very recent clearing may be more urgent for intervention than a pixel with high subsidence but old clearing (where most carbon has already been lost)."),

      heading("Proposed Approach", 3),
      body("Apply K-means or Gaussian Mixture Model (GMM) clustering on the multi-feature space to discover natural groupings of peatland condition. Each pixel is represented by a feature vector:"),
      bullet("Subsidence velocity (mm/yr)"),
      bullet("Temporal coherence (0-1)"),
      bullet("VV backscatter (dB)"),
      bullet("Canal distance (meters)"),
      bullet("Time since clearing (years, from Hansen GFC)"),
      bullet("Peat depth class (0-3)"),
      body("Standardize all features to zero mean and unit variance. Run K-means with k=5 to 8 clusters. Interpret clusters post-hoc based on their feature centroids. Expected cluster types:"),
      bullet("Cluster A: High subsidence, close to canals, recently cleared -- URGENT restoration"),
      bullet("Cluster B: Moderate subsidence, far from canals, old clearing -- MONITORING"),
      bullet("Cluster C: Low coherence, intact forest, no clearing -- PROTECTION"),
      bullet("Cluster D: High backscatter, urban/road features -- EXCLUDE"),
      bullet("Cluster E: Very low backscatter, water -- WATER BODIES"),

      heading("Expected Improvement", 3),
      bullet("Reveals non-linear feature interactions that the weighted sum risk score misses"),
      bullet("Produces interpretable restoration priority zones that can be labeled and mapped"),
      bullet("No training data needed -- fully unsupervised"),
      bullet("Computationally trivial (scikit-learn K-means on ~11M pixels with 6 features takes seconds)"),
      bullet("Can be validated by overlaying on optical basemap and checking if clusters correspond to visible land cover types"),

      heading("Limitations", 3),
      bullet("Cluster interpretation requires domain expertise (what does each cluster mean for restoration?)"),
      bullet("The number of clusters (k) is a subjective choice"),
      bullet("Results are sensitive to feature scaling and selection"),

      // 3.3 Supervised Restoration Priority
      heading("3.3 Supervised Restoration Priority Model (Future)", 2),
      labeledPara("Benefit: ", "HIGH -- but requires ground truth data we do not currently have"),
      labeledPara("Data requirement: ", "Expert-labeled locations (100-200 points)"),
      labeledPara("Implementation effort: ", "1-2 weeks after data collection"),

      heading("Problem", 3),
      body("The current risk score treats all subsidence equally regardless of context. In reality, restoration priority depends on factors that are difficult to capture in a simple formula: accessibility (can restoration teams reach the site?), community willingness (does the landowner cooperate?), downstream impact (does blocking this canal affect downstream water supply?), and intervention feasibility (is the canal blockable with local materials?). These factors require local knowledge that cannot be derived from satellite imagery alone."),

      heading("Proposed Approach", 3),
      body("Train a Random Forest or Gradient Boosted Trees (XGBoost) model to predict restoration priority from a combination of remote sensing features and expert labels:"),
      bullet("Features: all remote sensing products (velocity, coherence, backscatter, canal distance, peat depth, deforestation year) plus derived features (velocity trend, seasonal amplitude if available)"),
      bullet("Labels: 100-200 locations labeled by Pak Agus (Teluk Bayur village head), Mr Rifqi Marisel (ex-BRGM), and/or Dr Sang-Ho Yun as one of: 'high priority', 'medium priority', 'low priority', 'not suitable for restoration'"),
      bullet("Training: 5-fold cross-validation, class-weighted to handle imbalanced labels"),
      bullet("Output: per-pixel restoration priority score (0-1) with feature importance ranking"),

      heading("Why Random Forest over Deep Learning", 3),
      bullet("Works with small training datasets (100-200 labeled points)"),
      bullet("Produces feature importance rankings (interpretable for auditors)"),
      bullet("No GPU required, trains in seconds"),
      bullet("Handles mixed feature types (continuous velocity, categorical peat depth)"),
      bullet("Less prone to overfitting on small datasets than neural networks"),

      heading("Expected Improvement", 3),
      bullet("Captures non-linear interactions between features that the weighted sum misses"),
      bullet("Incorporates local expert knowledge into the satellite-based assessment"),
      bullet("Feature importance reveals which factors drive restoration priority (scientifically informative)"),
      bullet("Produces a defensible, data-driven priority map rather than a rule-based approximation"),

      heading("Limitations", 3),
      bullet("Requires field visits or expert interviews to create training labels"),
      bullet("Model is specific to this AOI -- generalization to other peatlands needs retraining"),
      bullet("Introduces a 'black box' element that may concern Verra auditors (mitigated by feature importance transparency)"),

      // 3.4 Applications Evaluated and Rejected
      heading("3.4 Applications Evaluated and Rejected", 2),

      new Table({
        rows: [
          makeRow(["Application", "Why Rejected"], { bold: true }),
          makeRow(["ML for InSAR velocity estimation", "MintPy SBAS is physics-based and well-validated. ML cannot improve on the phase-to-displacement conversion. Would undermine scientific defensibility."]),
          makeRow(["ML atmospheric correction", "ERA5 correction is physics-based and standard. Our ERA5 issue was implementation (reference point), not the correction method. ML alternative would need massive training data."]),
          makeRow(["Deep learning phase unwrapping", "Research-stage only. SNAPHU MCF is proven. Risk of introducing subtle errors that are difficult to detect."]),
          makeRow(["ML water body detection", "VV threshold at -18 dB works once properly implemented. Adding a segmentation model for a binary classification that a single threshold handles is unnecessary complexity."]),
          makeRow(["ML subsidence classification", "Thresholds are from peer-reviewed literature (Hooijer 2012). ML would just learn the same thresholds from the data. No added value."]),
          makeRow(["SAR super-resolution", "Requires paired high-res/low-res training data we don't have. Enhancement is learned, not physics-based, risking artifacts. Research only."]),
          makeRow(["ML peat depth estimation", "Requires field-measured peat depth calibration data. Without ground truth, any ML model is unconstrained. The dome model, while crude, is at least physically motivated."]),
        ],
        width: { size: 100, type: WidthType.PERCENTAGE },
      }),

      // 4. Implementation Roadmap
      heading("4. Implementation Roadmap", 1),

      heading("Phase 1: Unsupervised Clustering (Immediate, 2-3 days)", 2),
      body("Implement K-means clustering on the existing multi-feature product stack. No new data collection needed. Produces a degradation_zones.tif product with 5-8 natural clusters. Validate by visual comparison with optical basemap. This is the lowest-effort, highest-insight ML addition."),
      bullet("Add src/peatguard/analysis/clustering.py"),
      bullet("Features: velocity, coherence, VV backscatter, canal distance, peat depth, deforestation year"),
      bullet("Output: degradation_zones.tif (uint8, cluster labels) + cluster_centroids.json"),
      bullet("Dependencies: scikit-learn (already available via conda)"),

      heading("Phase 2: U-Net Canal Segmentation (2-3 weeks)", 2),
      body("Create training labels by manually digitizing canals on 50-100 Google Earth patches within the AOI. Supplement with OSM waterway data. Train a U-Net model on VV backscatter patches. Deploy as an optional canal detection backend that can be toggled via config."),
      bullet("Add src/peatguard/analysis/canal_unet.py"),
      bullet("Training: Google Colab or local GPU (free tier sufficient for small dataset)"),
      bullet("Model file: canal_unet.pth (~10 MB, stored in GCS)"),
      bullet("Inference: ~30 seconds on CPU for the full AOI (no GPU needed at inference time)"),
      bullet("Dependencies: torch, segmentation-models-pytorch (add to pip requirements)"),

      heading("Phase 3: Supervised Restoration Priority (1-2 months)", 2),
      body("Requires field data collection. During a visit to Teluk Bayur village, work with Pak Agus and local restoration practitioners to label 100-200 locations by restoration priority. Train a Random Forest model. This produces the most actionable output for actual restoration planning."),
      bullet("Data collection: 1-2 day field visit with GPS-enabled tablet"),
      bullet("Training: scikit-learn RandomForestClassifier, 5-fold CV"),
      bullet("Output: restoration_priority.tif + feature_importance.json"),

      // 5. Cost-Benefit Summary
      heading("5. Cost-Benefit Summary", 1),

      new Table({
        rows: [
          makeRow(["Application", "Effort", "Benefit", "Data Needed", "Auditability", "Recommend"], { bold: true }),
          makeRow(["Unsupervised clustering", "2-3 days", "New insights, no labels", "None (existing products)", "High (interpretable clusters)", "YES -- immediate"]),
          makeRow(["U-Net canal segmentation", "2-3 weeks", "Cleaner canal detection", "500+ labeled patches", "Medium (model is a black box)", "YES -- if time allows"]),
          makeRow(["Supervised restoration priority", "1-2 months", "Actionable priority map", "100-200 expert labels", "Medium-High (feature importance)", "YES -- for production"]),
          makeRow(["ML atmospheric correction", "Months", "Marginal improvement", "Large training corpus", "Low (replaces physics)", "NO"]),
          makeRow(["ML InSAR/classification", "Weeks", "No improvement", "Not applicable", "Low (unnecessary)", "NO"]),
        ],
        width: { size: 100, type: WidthType.PERCENTAGE },
      }),

      // 6. Recommendation
      heading("6. Recommendation", 1),
      body("For the Hult Prize pitch timeline, implement Phase 1 only (unsupervised clustering). It requires no new data, takes 2-3 days, and produces a novel degradation zone map that demonstrates ML capability without undermining the physics-based foundation. The clustering output can be presented as 'AI-assisted restoration zone identification' which is accurate and compelling."),
      body("For production deployment, all three phases are recommended in sequence. The U-Net canal segmentation (Phase 2) addresses the most persistent data quality issue in the pipeline. The supervised restoration priority model (Phase 3) produces the most actionable output for field teams and carbon credit verification."),
      body("The physics-based core (InSAR velocity, ERA5 correction, Hooijer carbon factors) should remain unchanged. ML supplements the interpretation and classification layers, not the fundamental measurement. This hybrid approach -- physics for measurement, ML for interpretation -- is the most defensible and effective architecture for satellite-based environmental monitoring."),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  const outPath = "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_ML_Proposal.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Document created: " + outPath);
  console.log("File size: " + (buffer.length / 1024).toFixed(1) + " KB");
});
