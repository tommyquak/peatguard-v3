# PeatGuard v3 - Complete Development Context

## What This Project Is
Multi-sensor satellite-based peatland subsidence monitoring pipeline for West Kalimantan, Indonesia.
Uses Sentinel-1 C-band and NISAR L-band SAR data to detect ground sinking near drainage canals,
producing risk maps that prioritize where to block canals for peatland restoration.

The pipeline is FUNCTIONAL end-to-end with 11+ GeoTIFF products in GCS.
Tommy is an NUS Geography student building this for the Hult Prize competition.

## Repository Layout
```
peatguard/peatguard/              <-- THIS IS THE BUILD CONTEXT (cd here for gcloud builds)
  Dockerfile                       # conda-forge mambaforge + ISCE2 + MintPy + SNAPHU + PyAPS
  pyproject.toml                   # Package definition
  docker-compose.yaml              # Local dev: pipeline, jupyter, dashboard services
  cloud/
    cloudbuild.yaml                # Cloud Build config (docker build + push to Artifact Registry)
    cloudrun-job.yaml              # Cloud Run job definitions (all 5 stages)
    Dockerfile.dashboard           # Lightweight TiTiler dashboard container
    workflow.yaml                  # Cloud Workflows: sequential pipeline orchestration
    scheduler.yaml                 # Cloud Scheduler config (monthly trigger)
    scheduler-setup.sh             # Setup/manage script for scheduling infrastructure
  config/
    default.yaml                   # Master config (AOI, sentinel1, nisar, processing params)
    kapuas.yaml                    # Site override
    nisar.yaml                     # NISAR L-band sensor override
  src/peatguard/
    cli.py                         # Click CLI: download, process, timeseries, analyze, fuse, dashboard, schedule
    config.py                      # Pydantic v2 config models (all sections)
    catalog.py                     # SQLite processing state
    data/default.yaml              # Embedded default config
    pipeline/
      orchestrator.py              # THE MAIN FILE - all stage logic, GCS upload, cleanup, fusion
    ingest/
      search.py                    # ASF DAAC search (Sentinel-1 + NISAR)
      download.py                  # ASF/Earthdata download
      orbit.py                     # ESA STEP precise orbit download
    insar/
      topsapp.py                   # ISCE2 topsApp for Sentinel-1 TOPS mode
      stripmapapp.py               # ISCE2 stripmapApp for NISAR L-band stripmap mode
      unwrap.py                    # Standalone SNAPHU unwrapping
      pairs.py                     # SBAS pair network generation
    timeseries/
      mintpy_prep.py               # Custom HDF5 prep + MintPy config (sensor-aware SAR params)
      sbas.py                      # MintPy smallbaselineApp runner
      velocity.py                  # HDF5 -> COG GeoTIFF velocity export + UTM reprojection
    backscatter/
      calibrate.py                 # GRD sigma0 calibration with GCP preservation
      speckle.py                   # Lee Sigma speckle filter
      terrain_correct.py           # GCP-based terrain correction via GDAL Warp
      composite.py                 # Temporal median composite
    analysis/
      subsidence_class.py          # Velocity -> 5-class severity map (includes water class)
      canal_detect.py              # VV backscatter threshold -> canal mask + distance
      risk_score.py                # Calibrated subsidence + canal proximity risk (Hooijer et al.)
      water_mask.py                # VV backscatter water body detection
      fusion.py                    # Multi-sensor C+L band coherence-weighted velocity fusion
    dashboard/
      app.py                       # FastAPI + TiTiler tile server for COG visualization
      templates/index.html         # Leaflet.js map frontend
    export/
      cog.py                       # Cloud-Optimized GeoTIFF writer (read_raster, write_cog)
      gcs.py                       # GCS upload/download/list/sync utilities
      metadata.py                  # Product metadata
  tests/                           # Pytest suite
```

## GCP Infrastructure
```
Project ID:        peatguard (265643957903)
Region:            asia-southeast1
Service Account:   peatguard-sa@peatguard.iam.gserviceaccount.com
GCS Bucket:        peatguard-data
Artifact Registry: asia-southeast1-docker.pkg.dev/peatguard/peatguard/pipeline
Current Image Tag: v29-autoref (needs rebuild for new features)
```

### Cloud Run Jobs (all in asia-southeast1)
| Job | Command | CPU | RAM | Timeout | Purpose |
|-----|---------|-----|-----|---------|---------|
| peatguard-ingest | `peatguard download --start 2024-01-01 --end 2024-12-31 --level SLC` | 4 | 8Gi | 2h | Download SLC+GRD from ASF |
| peatguard-insar | `peatguard process --mode insar --workers 2` | 8 | 32Gi | 6h | ISCE2 topsApp/stripmapApp per pair |
| peatguard-backscatter | `peatguard process --mode backscatter` | 8 | 32Gi | 2h | GRD calibration + composite |
| peatguard-timeseries | `peatguard timeseries` | 8 | 32Gi | 6h | MintPy SBAS inversion |
| peatguard-analyze | `peatguard analyze` | 4 | 16Gi | 30m | Classification + canal + risk + water mask + fusion |

All jobs use env var: `PEATGUARD_STORAGE__GCS_BUCKET=peatguard-data`
Timeseries job also needs: `CDS_API_KEY=<key>` for ERA5 tropospheric correction.

### Automated Scheduling
Cloud Scheduler triggers Cloud Workflow monthly (1st of month, 06:00 WIB).
Workflow runs: ingest -> (insar + backscatter parallel) -> timeseries -> analyze.
Setup: `bash cloud/scheduler-setup.sh`. Manage: `--status`, `--pause`, `--resume`, `--run-now`.
CLI: `peatguard schedule [--status]`.

### Build & Deploy Workflow
```bash
cd peatguard/peatguard   # MUST be in this dir (cloudbuild.yaml uses . as context)
gcloud builds submit --config cloud/cloudbuild.yaml --substitutions=SHORT_SHA=vXX-tag --project peatguard
gcloud run jobs update JOB_NAME --region asia-southeast1 --project peatguard --image asia-southeast1-docker.pkg.dev/peatguard/peatguard/pipeline:vXX-tag
gcloud run jobs execute JOB_NAME --region asia-southeast1 --project peatguard
```

## Multi-Sensor Support

### Sentinel-1 (C-band, default)
- Wavelength: 5.6 cm, IW TOPS mode, VV polarization
- High coherence over cleared land, plantations, urban areas
- Decorrelates under dense tropical forest canopy
- Processing: ISCE2 topsApp, 3x9 multilooking

### NISAR (L-band, opt-in)
- Wavelength: 24 cm, stripmap mode, HH polarization
- Penetrates forest canopy -- measures subsidence under intact peat forest
- 12-day repeat cycle, free from ASF DAAC
- Processing: ISCE2 stripmapApp, 5x11 multilooking
- Enable: set `sensor: nisar` in config or use `config/nisar.yaml` override

### Multi-Sensor Fusion
When both C-band and L-band products exist, fusion produces a unified velocity map:
- Coherence-weighted average: `(coh_c * vel_c + coh_l * vel_l) / (coh_c + coh_l)`
- Where only one sensor is valid, uses that sensor's measurement
- Produces: fused_velocity.tif, fused_coherence.tif, sensor_coverage.tif
- Enable: set `fusion.enabled: true` in config
- CLI: `peatguard fuse`

## Pipeline Stages & Current State

### Stage 1: Data Ingestion (COMPLETE)
- 14 Sentinel-1A IW SLC scenes (Jan-Dec 2024) in `gs://peatguard-data/raw/slc/`
- 14 Sentinel-1A IW GRD scenes in `gs://peatguard-data/raw/grd/`
- ASF DAAC search supports both Sentinel-1 and NISAR

### Stage 2: InSAR Processing (COMPLETE)
- 29 SBAS pairs generated, 16 successfully processed with unwrapped phase
- Routes to topsApp (Sentinel-1) or stripmapApp (NISAR) based on sensor config
- Ionospheric correction enabled (split-spectrum, `do_ion=True`)
- Per-pair GCS upload + aggressive cleanup keeps RAM flat
- Burst overlap detection + trimming for clean geometry merge

### Stage 3: Time-Series (COMPLETE)
- Custom HDF5 prep with sensor-aware SAR parameters (C-band or L-band)
- ERA5 tropospheric correction via PyAPS (requires CDS API key)
- Fixed reference point from config (deterministic velocity baseline)
- Velocity exported in both EPSG:4326 (native) and UTM (reprojected)

### Stage 4: Backscatter (COMPLETE)
- 14 GRDs processed: calibrate -> speckle filter -> terrain correct -> composite
- Output in UTM (EPSG:32649), 10m resolution
- Products: vv_median.tif, vv_median_db.tif

### Stage 5: Analysis (COMPLETE)
- Water mask from VV backscatter (prevents false subsidence over water bodies)
- Subsidence classification (5 classes: severe/active/stable/uplift/water)
- Canal detection (VV backscatter 10th percentile threshold)
- Risk score: calibrated 0.45*proximity + 0.55*subsidence (Hooijer et al. 2012)
  - Linear proximity decay over 1200m (Dupuit equation approximation)
  - Severe threshold: -40 mm/yr
- Optional multi-sensor fusion when both C-band and L-band products available

## Web Dashboard
TiTiler-based COG tile server with Leaflet.js frontend.
- Visualizes all products with appropriate colormaps
- Layer toggles, legends, click-to-query pixel values
- Run: `peatguard dashboard --port 8080`
- Deploy: `cloud/Dockerfile.dashboard` -> Cloud Run service

## Config Sections (config.py / default.yaml)
| Section | Purpose |
|---------|---------|
| `sensor` | Active sensor: "sentinel1" or "nisar" |
| `aoi` | Bounding box, target EPSG (32649 = UTM 49S) |
| `sentinel1` | C-band platform, polarization, subswath, baselines |
| `nisar` | L-band platform, wavelength, pixel sizes, orbit height |
| `processing` | Resolution, coherence threshold, speckle filter, do_ion |
| `classification` | Subsidence velocity thresholds (mm/yr) |
| `water_mask` | VV threshold, min size, closing radius, canal exclusion |
| `risk_score` | Calibrated weights, influence radius, severe velocity |
| `fusion` | Enabled flag, C-band weight boost, min coherence |
| `export` | COG blocksize, compression, overview levels |
| `storage` | Output/scratch dirs, GCS bucket/prefix |
| `mintpy` | Reference point, tropospheric correction, network modification |

## Critical Implementation Details

### orchestrator.py is the heart of the pipeline
- `run_insar_stage()`: Routes to topsApp (Sentinel-1) or stripmapApp (NISAR).
  Downloads SLC per-pair from GCS, processes, uploads, deletes. GCS resume logic.
- `_merge_burst_geometry()`: Detects burst overlaps via lat signal matching,
  trims overlap margins before concatenation, then multilooks by 3x9.
- `run_timeseries_stage()`: ERA5 tropospheric correction + fixed reference point.
  Sensor-aware SAR parameters in HDF5 metadata via `_get_sar_params()`.
- `run_analysis_stage()`: Water mask -> classification -> canal detect -> risk score.
  Optional fusion when both sensor products exist and fusion.enabled=True.

### mintpy_prep.py sensor-aware HDF5 creation
`_get_sar_params(config)` returns wavelength, orbit height, pixel sizes, PRF etc.
based on `config.sensor`. Replaces hardcoded Sentinel-1 values.
`_ensure_cdsapirc()` writes ~/.cdsapirc from CDS_API_KEY env var for ERA5.

### velocity.py CRS standardization
Exports native EPSG:4326 velocity, then reprojects to config's `aoi.epsg` (UTM 49S).
Both products are kept: `subsidence_velocity.tif` (4326) and `subsidence_velocity_utm.tif`.

### Risk score calibration (Hooijer et al. 2012)
- Linear proximity decay: `risk = max(0, 1 - d/1200)` (Dupuit equation)
- Severe threshold: -40 mm/yr (captures actively draining peat)
- Weights: 0.45 proximity + 0.55 subsidence
- Water pixels excluded via water mask

## Conventions
- No emojis in code or output
- Use logging (not print) for all output
- All geospatial outputs must be COG format (DEFLATE, 512 tiles, overviews)
- Config via Pydantic models + YAML, env var overrides with PEATGUARD_ prefix (double underscore separator)
- Always check downstream requirements before modifying upstream
- Aggressive cleanup of intermediates in Cloud Run (32GB RAM shared with filesystem)
- Build from peatguard/peatguard/ directory (that's where Dockerfile + cloudbuild.yaml are)
- CLI file globs use *.zip (not S1*.zip) for multi-sensor compatibility

## GitHub
Repository: https://github.com/tommyquak/peatguard-v3.git
Branch: main
Remote: origin
