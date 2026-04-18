# PeatGuard

Satellite-based peatland subsidence monitoring pipeline for identifying degraded peatlands and prioritizing restoration in tropical regions.

## Overview

PeatGuard uses Sentinel-1 SAR satellite imagery to measure ground subsidence rates over peatlands. Peat soils subside (sink) when drained for agriculture or logging -- this subsidence directly correlates with carbon loss and fire risk. By mapping where and how fast the ground is sinking, PeatGuard helps conservation teams identify which areas need urgent rewetting and canal blocking.

### What it produces

| Product | File | Description |
|---------|------|-------------|
| Subsidence Velocity | `subsidence_velocity.tif` | Annual ground movement rate (mm/yr). Negative = sinking. |
| Severity Classification | `subsidence_class.tif` | 4-class map: Severe / Active Drying / Stable / Noise |
| Canal Network | `canal_mask.tif` | Detected drainage canals from radar backscatter |
| Degradation Risk | `canal_risk.tif` | Combined canal proximity + subsidence risk score (0-1) |
| Coherence | `coherence_median.tif` | Data quality indicator (higher = more reliable) |

All outputs are Cloud-Optimized GeoTIFFs (COG) in EPSG:4326, directly loadable in ArcGIS Pro, QGIS, or web map viewers.

### Classification thresholds

| Class | Rate (mm/yr) | Interpretation |
|-------|-------------|----------------|
| Severe | < -50 | Heavily drained peat, rapid carbon loss |
| Active Drying | -50 to -20 | Ongoing drainage, intervention needed |
| Stable | -20 to 0 | Intact or successfully rewetted peat |
| Noise/Uplift | > 0 | Measurement noise or peat rebound |

## Architecture

```
Sentinel-1 SLC (ASF DAAC)
        |
        v
  [1] ISCE2 topsApp ---- InSAR coregistration, interferogram, SNAPHU MCF unwrapping
        |
        v
  [2] MintPy SBAS ------- Time-series inversion (25 interferogram pairs -> velocity)
        |
        v
  [3] Velocity Export --- COG GeoTIFF with georeferencing from radar geometry
        |
        v
  [4] Classification ---- Threshold-based severity mapping
        |
Sentinel-1 GRD (ASF DAAC)
        |
        v
  [5] Backscatter ------- Calibration, speckle filter, terrain correction, median composite
        |
        v
  [6] Canal Detection --- Dark-pixel thresholding + morphological cleanup
        |
        v
  [7] Risk Scoring ------ Weighted combination of subsidence + canal proximity
```

## Deployment

The pipeline runs on **Google Cloud Platform** as Cloud Run Jobs:

| Job | Purpose | Resources |
|-----|---------|-----------|
| `peatguard-ingest` | Download Sentinel-1 scenes from ASF | 2 CPU, 8 GB |
| `peatguard-insar` | ISCE2 InSAR + SNAPHU unwrapping | 8 CPU, 32 GB |
| `peatguard-timeseries` | MintPy SBAS + velocity export | 8 CPU, 32 GB |
| `peatguard-analyze` | Classification + canal detection + risk | 2 CPU, 8 GB |

### Prerequisites

- GCP project with Cloud Run, Cloud Build, Artifact Registry, and Cloud Storage enabled
- ASF Earthdata credentials (stored as Secret Manager secret `earthdata-netrc`)
- Service account with Storage Admin and Cloud Run Invoker roles

### Build and deploy

```bash
# Build the Docker image
gcloud builds submit --config cloud/cloudbuild.yaml \
  --substitutions=SHORT_SHA=v1 --project YOUR_PROJECT

# Create Cloud Run jobs (see cloud/cloudrun-job.yaml for full config)
gcloud run jobs create peatguard-insar \
  --image REGION-docker.pkg.dev/PROJECT/peatguard/pipeline:latest \
  --region REGION --cpu 8 --memory 32Gi --task-timeout 21600 \
  --set-env-vars PEATGUARD_STORAGE__GCS_BUCKET=YOUR_BUCKET \
  --args="process,--mode,insar,--workers,2"
```

### Run the pipeline

```bash
# 1. Download Sentinel-1 SLC scenes
gcloud run jobs execute peatguard-ingest

# 2. Process InSAR pairs (with resume capability)
gcloud run jobs execute peatguard-insar

# 3. Run MintPy time-series analysis
gcloud run jobs execute peatguard-timeseries

# 4. Classification and analysis
gcloud run jobs execute peatguard-analyze
```

## Configuration

Edit `config/default.yaml` or create a site-specific config:

```yaml
aoi:
  bbox: [114.304, -2.611, 114.404, -2.511]  # [west, south, east, north]
  epsg: 32649  # UTM Zone 49S

sentinel1:
  platform: SENTINEL-1
  beam_mode: IW
  subswath: IW2
  polarization: VV

processing:
  az_looks: 3       # Azimuth multilooking
  rg_looks: 9       # Range multilooking
  resolution_m: 10  # Output resolution for backscatter
```

## Study Area

The initial deployment covers the **Kapuas River peatland** in West Kalimantan, Indonesia -- one of the largest tropical peatland complexes in Southeast Asia. This area has experienced significant drainage-driven subsidence due to canal construction for palm oil plantations and logging concessions.

## Tech Stack

- **InSAR Processing**: ISCE2 (topsApp) with SNAPHU MCF phase unwrapping
- **Time-Series**: MintPy (Small Baseline Subset / SBAS inversion)
- **Geospatial**: rasterio, GDAL, numpy
- **Cloud**: Google Cloud Run Jobs, Cloud Storage, Cloud Build
- **Container**: Docker with conda-forge (ISCE2 + MintPy + GDAL)

## License

MIT
