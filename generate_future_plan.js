const docx = require("docx");
const fs = require("fs");

const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  ExternalHyperlink,
  convertInchesToTwip,
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

// Helper: body paragraph
function body(text, opts = {}) {
  return new Paragraph({
    children: [t(text)],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, before: opts.spacingBefore || 0, line: 276 },
  });
}

// Helper: bold label + normal text paragraph
function labeledPara(label, text, opts = {}) {
  return new Paragraph({
    children: [t(label, { bold: true }), t(text)],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, before: opts.spacingBefore || 0, line: 276 },
  });
}

// Helper: heading paragraph
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

// Helper: bullet point
function bullet(text, level = 0) {
  const children = typeof text === "string" ? [t(text)] : text;
  return new Paragraph({
    children,
    bullet: { level },
    spacing: { after: 60, line: 276 },
    alignment: AlignmentType.LEFT,
  });
}

// Helper: bullet with bold prefix
function bulletLabeled(label, text, level = 0) {
  return new Paragraph({
    children: [t(label, { bold: true }), t(text)],
    bullet: { level },
    spacing: { after: 60, line: 276 },
    alignment: AlignmentType.LEFT,
  });
}

// Helper: hyperlink in a bullet
function bulletWithLink(prefix, url, suffix, level = 0) {
  return new Paragraph({
    children: [
      t(prefix),
      new ExternalHyperlink({
        children: [
          new TextRun({
            text: url,
            font: "Arial",
            size: 24,
            color: "0563C1",
            underline: {},
          }),
        ],
        link: url,
      }),
      t(suffix),
    ],
    bullet: { level },
    spacing: { after: 60, line: 276 },
    alignment: AlignmentType.LEFT,
  });
}

// Empty paragraph spacer
function spacer() {
  return new Paragraph({ children: [], spacing: { after: 120 } });
}

const doc = new Document({
  creator: "Tommy Quak",
  title: "PeatGuard: Future Development Plan",
  description: "Future development plan for PeatGuard InSAR peatland monitoring system",
  sections: [
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
      children: [
        // Title
        new Paragraph({
          children: [
            new TextRun({
              text: "PeatGuard: Future Development Plan",
              font: "Arial",
              size: 40, // 20pt
              bold: true,
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 120, line: 240 },
        }),
        // Author
        new Paragraph({
          children: [
            new TextRun({
              text: "Tommy Quak",
              font: "Arial",
              size: 28,
              color: "444444",
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 60, line: 240 },
        }),
        // Date
        new Paragraph({
          children: [
            new TextRun({
              text: "March 2026",
              font: "Arial",
              size: 28,
              color: "444444",
            }),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 360, line: 240 },
        }),

        // ========== Section 1: Atmospheric Correction ==========
        heading("1. Atmospheric Correction (Highest Priority)", 1),

        heading("Problem", 2),
        body(
          "Tropical Kalimantan has high atmospheric water vapor causing 5-20 mm equivalent phase delays. Without correction, velocity estimates have 5-15 mm/yr systematic bias, causing results to vary between runs."
        ),

        heading("Solution: ERA5 via CDS API", 2),
        bulletWithLink(
          "Register at Copernicus Climate Data Store (",
          "https://cds.climate.copernicus.eu",
          ") - free account"
        ),
        bullet("Obtain CDS API key"),
        bullet("Add as Cloud Run secret environment variable"),
        bullet("Enable in MintPy config: mintpy.troposphericDelay.method = pyaps", 0),
        bullet(
          "MintPy has built-in ERA5 support via PyAPS (Python-based Atmospheric Phase Screen)"
        ),
        bullet("This single fix removes 5-15 mm/yr of atmospheric noise"),

        heading("Additional: Ionospheric Correction", 2),
        bullet([
          t("Add to topsApp XML config: "),
          t('<property name="do ion">True</property>', { italics: true }),
        ]),
        bullet("ISCE2 handles this automatically with split-spectrum method"),
        bullet("Important for equatorial regions like Kalimantan"),

        // ========== Section 2: L-band SAR ==========
        heading("2. L-band SAR for Forest Penetration (High Priority)", 1),

        heading("Problem", 2),
        body(
          "Sentinel-1 C-band (5.6 cm wavelength) bounces off tropical canopy, not the ground. Only measures subsidence in cleared/sparse vegetation areas. Intact peat forest shows low coherence and gets masked out."
        ),

        heading("Solution: ALOS-2 PALSAR-2", 2),
        bullet("JAXA L-band SAR satellite, 23 cm wavelength penetrates tropical canopy"),
        bullet("Free for research/educational users"),
        bulletWithLink(
          "Apply at ",
          "https://www.eorc.jaxa.jp/ALOS-2/en/calval/calval_index.htm",
          ""
        ),
        bullet("NUS students qualify through university research agreement"),
        bullet("Application process takes 2-4 weeks"),
        bullet(
          "ISCE2 pipeline supports ALOS-2 with minor config changes (sensor name, subswath settings)"
        ),

        heading("Future: NISAR", 2),
        bullet("NASA-ISRO L-band + S-band SAR, launched January 2025"),
        bullet("ALL data is free and open access (no application needed)"),
        bullet("12-day repeat cycle, global coverage"),
        bullet("Data expected mid-2025 after commissioning phase"),
        bullet("Will be the gold standard for forest deformation monitoring"),

        labeledPara(
          "NUS Resource: ",
          "Check with CRISP (Centre for Remote Imaging, Sensing and Processing) for existing ALOS-2 data or institutional access agreements.",
          { spacingBefore: 120 }
        ),

        // ========== Section 3: Reference Point Stabilization ==========
        heading("3. Reference Point Stabilization (High Priority)", 1),

        heading("Problem", 2),
        body(
          "MintPy auto-selects the highest-coherence pixel as velocity reference. Different selections shift the entire velocity field, causing contradictory results between runs. Ideally the reference should be on stable bedrock, but peatlands lack exposed bedrock."
        ),

        heading("Solutions", 2),

        labeledPara(
          "1. GNSS/GPS Station Reference: ",
          "Check BIG (Badan Informasi Geospasial) CORS network for stations in West Kalimantan. If a station with known vertical velocity exists within the SAR frame, use its coordinates as the fixed reference point."
        ),
        labeledPara(
          "2. Persistent Scatterer on Stable Structure: ",
          "Identify a bridge, mosque, or government building in a nearby town (e.g., Sintang, Sanggau) on non-peat substrate. These show consistently high coherence and minimal subsidence."
        ),
        labeledPara(
          "3. Multi-Reference Averaging: ",
          "Process with several candidate reference points and average the velocity fields. This reduces bias from any single point."
        ),
        labeledPara(
          "4. External Velocity Model: ",
          "Use ITRF2014 geodetic velocity model to correct for tectonic motion. The Sundaland block has near-zero vertical motion away from subduction zones."
        ),

        // ========== Section 4: Risk Score Calibration ==========
        heading("4. Risk Score Calibration (Medium Priority)", 1),

        heading("Problem", 2),
        body(
          "The 60% subsidence / 40% canal proximity weighting has no empirical basis. The exponential decay parameters for proximity risk are not calibrated against field measurements."
        ),

        heading("Solutions", 2),
        labeledPara(
          "1. Literature-Based Calibration: ",
          "Hooijer et al. (2012) established that subsidence rate is approximately linear with water table depth. Canal proximity maps to water table depth via the Dupuit equation (groundwater hydraulics). These relationships provide a physics-based decay function."
        ),
        labeledPara(
          "2. Optical Cross-Validation: ",
          "Download Sentinel-2 NDVI time series (free from Copernicus Open Access Hub) or use Google Earth Engine. Deforested/drained areas show NDVI decline that should correlate spatially with subsidence patterns."
        ),
        labeledPara(
          "3. GEDI LiDAR Validation: ",
          "NASA's GEDI mission provides free canopy height data. Canopy height changes correlate with peat condition and can validate degradation patterns."
        ),

        // ========== Section 5: Ground Truth Validation ==========
        heading("5. Ground Truth Validation (Medium Priority)", 1),

        heading("Problem", 2),
        body(
          "No comparison against field measurements (GPS/leveling, manual canal digitization, peat depth surveys). Cannot quantify accuracy without validation."
        ),

        heading("Free Validation Datasets", 2),
        bullet("CIFOR Indonesian Peat Map (cifor.org): peat extent and depth"),
        bullet(
          "Global Forest Watch (globalforestwatch.org): deforestation timing and extent"
        ),
        bullet("OpenStreetMap: canal network digitization for comparison"),
        bullet(
          "GEDI LiDAR canopy height (NASA DAAC): forest condition and degradation"
        ),
        bullet(
          "Bappenas Peat Moratorium Map (Indonesian government): protected peat areas"
        ),
        bullet("MERIT DEM: high-resolution elevation for peat surface topography"),

        heading("Field Collaboration", 2),
        bullet(
          "NUS Geography department likely has contacts with Indonesian research institutions"
        ),
        bullet(
          "Tanjungpura University in Pontianak (West Kalimantan capital) has an active peatland research group with ground monitoring wells"
        ),
        bullet(
          "A collaboration would provide actual subsidence measurements for validation"
        ),

        // ========== Section 6: Implementation Timeline ==========
        heading("6. Implementation Timeline", 1),

        heading("Phase 1 (Immediate, 1-2 days)", 2),
        bullet("Register for CDS API key"),
        bullet("Enable ERA5 tropospheric correction in pipeline"),
        bullet("Enable ionospheric correction in topsApp config"),

        heading("Phase 2 (Short-term, 1-2 weeks)", 2),
        bullet("Apply for ALOS-2 PALSAR-2 data through NUS"),
        bullet(
          "Download CIFOR peat map and Sentinel-2 NDVI for validation overlay"
        ),
        bullet(
          "Identify and set fixed reference point from GPS station or persistent scatterer"
        ),

        heading("Phase 3 (Medium-term, 1-2 months)", 2),
        bullet(
          "Process ALOS-2 L-band InSAR for forest-penetrating subsidence measurement"
        ),
        bullet(
          "Calibrate risk score using Hooijer et al. water table-subsidence relationship"
        ),
        bullet("Cross-validate with optical imagery and GEDI LiDAR"),

        heading("Phase 4 (Longer-term, 2-4 months)", 2),
        bullet("Integrate NISAR data when available"),
        bullet(
          "Establish field validation partnership with Tanjungpura University"
        ),
        bullet(
          "Develop automated monitoring dashboard with scheduled pipeline runs"
        ),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(
    "/Users/tommyquak/Desktop/PeatGuard/PeatGuard_Future_Plan.docx",
    buffer
  );
  console.log("Document created: PeatGuard_Future_Plan.docx");
});
