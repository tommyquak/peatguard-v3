# PeatGuard v3 - Complete Development Context

## What This Project Is
Satellite-based peatland subsidence monitoring pipeline for West Kalimantan, Indonesia.
Uses Sentinel-1 SAR data to detect ground sinking near drainage canals, producing risk maps
that prioritize where to block canals for peatland restoration.

The pipeline is FUNCTIONAL end-to-end and has produced 11 GeoTIFF products in GCS.
Tommy is an NUS Geography student building this for the Hult Prize competition.

## Repository Layout
```
peatguard/peatguard/              <-- THIS IS THE BUILD CONTEXT (cd here for gcloud builds)
  Dockerfile                       # conda-forge mambaforge + ISCE2 + MintPy + SNAPHU
  pyproject.toml                   # Package definition
  cloud/
    cloudbuild.yaml                # Cloud Build config (docker build + push to Artifact Registry)
    cloudrun-job.yaml              # Cloud Run job template
  config/
    default.yaml                   # Master config (AOI, sentinel1, processing params)
    kapuas.yaml                    # Site override
  src/peatguard/
    cli.py                         # Click CLI: download, process, timeseries, analyze, run
    config.py                      # Pydantic v2 config models
    catalog.py                     # SQLite processing state
    data/default.yaml              # Embedded default config
    pipeline/
      orchestrator.py              # THE MAIN FILE - all stage logic, GCS upload, cleanup
    ingest/
      search.py                    # ASF DAAC Sentinel-1 search
      download.py                  # ASF/Earthdata download
      orbit.py                     # ESA STEP precise orbit download
    insar/
      topsapp.py                   # ISCE2 topsApp XML generation + execution
      unwrap.py                    # Standalone SNAPHU unwrapping
      pairs.py                     # SBAS pair network generation
    timeseries/
      mintpy_prep.py               # Custom HDF5 prep (bypasses prep_isce.py) + MintPy config
      sbas.py                      # MintPy smallbaselineApp runner
      velocity.py                  # HDF5 -> COG GeoTIFF velocity export with georeferencing
    backscatter/
      calibrate.py                 # GRD sigma0 calibration with GCP preservation
      speckle.py                   # Lee Sigma speckle filter
      terrain_correct.py           # GCP-based terrain correction via GDAL Warp
      composite.py                 # Temporal median composite
    analysis/
      subsidence_class.py          # Velocity -> 4-class severity map
      canal_detect.py              # VV backscatter threshold -> canal mask + distance
      risk_score.py                # Combined subsidence + canal proximity risk (0-1)
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
Current Image Tag: v29-autoref (also tagged :latest)
```

### Cloud Run Jobs (all in asia-southeast1)
| Job | Command | CPU | RAM | Timeout | Purpose |
|-----|---------|-----|-----|---------|---------|
| peatguard-ingest | `peatguard download --start 2024-01-01 --end 2024-12-31 --level SLC` | 4 | 8Gi | 2h | Download SLC+GRD from ASF |
| peatguard-insar | `peatguard process --mode insar --workers 2` | 8 | 32Gi | 6h | ISCE2 topsApp per pair |
| peatguard-backscatter | `peatguard process --mode backscatter` | 8 | 32Gi | 2h | GRD calibration + composite |
| peatguard-timeseries | `peatguard timeseries` | 8 | 32Gi | 6h | MintPy SBAS inversion |
| peatguard-analyze | `peatguard analyze` | 4 | 16Gi | 30m | Classification + canal + risk |

All jobs use env var: `PEATGUARD_STORAGE__GCS_BUCKET=peatguard-data`

### Build & Deploy Workflow
```bash
cd peatguard/peatguard   # MUST be in this dir (cloudbuild.yaml uses . as context)
gcloud builds submit --config cloud/cloudbuild.yaml --substitutions=SHORT_SHA=vXX-tag --project peatguard
gcloud run jobs update JOB_NAME --region asia-southeast1 --project peatguard --image asia-southeast1-docker.pkg.dev/peatguard/peatguard/pipeline:vXX-tag
gcloud run jobs execute JOB_NAME --region asia-southeast1 --project peatguard
```

## Pipeline Stages & Current State

### Stage 1: Data Ingestion (COMPLETE)
- 14 Sentinel-1A IW SLC scenes (Jan-Dec 2024) in `gs://peatguard-data/raw/slc/`
- 14 Sentinel-1A IW GRD scenes in `gs://peatguard-data/raw/grd/`
- Downloaded via ASF DAAC search API

### Stage 2: InSAR Processing (COMPLETE)
- 29 SBAS pairs generated, 16 successfully processed with unwrapped phase
- 13 pairs failed (mostly 48-day baselines, insufficient burst overlap in IW3)
- Uses ISCE2 topsApp: startup -> unwrap (SNAPHU MCF)
- 3x9 multilooking (azimuth x range)
- Per-pair GCS upload + aggressive cleanup keeps RAM flat
- GCS resume logic: checks for `filt_topophase.unw` to skip completed pairs
- Products in `gs://peatguard-data/interferograms/{YYYY-MM-DD_YYYY-MM-DD}/merged/`

### Stage 3: Time-Series (COMPLETE)
- Custom HDF5 prep (`prep_data_for_mintpy`) bypasses `prep_isce.py` entirely
  because reconstructed-from-GCS data lacks full ISCE2 metadata (HEIGHT, STARTING_RANGE etc.)
- Reads ISCE2 binary files directly, creates ifgramStack.h5 + geometryRadar.h5
- Hardcoded Sentinel-1 SAR parameters (wavelength, orbit height, pixel sizes)
- MintPy config disables: tropospheric correction (no ERA5 creds), DEM error correction
  (flat peatland), unwrap error correction (MCF handles it), geocoding (handled in export)
- Reference point: auto-select with minCoherence=0.7
- Velocity clipped to AOI + 0.1 degree buffer
- Georeferencing derived from burst-merged lat/lon lookup tables, fallback to AOI bbox
- Products: subsidence_velocity.tif, velocity_uncertainty.tif, coherence_median.tif

### Stage 4: Backscatter (COMPLETE)
- 14 GRDs processed: calibrate (sigma0) -> Lee Sigma speckle filter -> terrain correct -> composite
- CRITICAL: must use v19-upload image or earlier for backscatter (v20+ OOM on GRD 2 due to
  conda snaphu package bloating the image). Or use v21+ which builds SNAPHU from ISCE2 contrib.
- GCP-based georeferencing from GRD SAFE annotation files
- Output in UTM (EPSG:32750), 10m resolution
- Products: vv_median.tif, vv_median_db.tif

### Stage 5: Analysis (COMPLETE)
- Downloads velocity + VV composite from GCS
- Reprojects canal products to match velocity CRS
- Subsidence classification (4 classes: severe/active/stable/uplift)
- Canal detection (VV backscatter 10th percentile threshold)
- Risk score: 0.4*proximity + 0.6*subsidence severity
- Products: subsidence_class.tif, canal_mask.tif, canal_distance.tif, canal_risk.tif

## GCS Products (gs://peatguard-data/products/)
| File | Size | CRS | Description |
|------|------|-----|-------------|
| subsidence_velocity.tif | 3.4 MB | EPSG:4326 | Velocity mm/yr, AOI-clipped |
| subsidence_velocity_utm.tif | 46 MB | EPSG:32750 | Velocity reprojected to UTM |
| velocity_uncertainty.tif | 3.3 MB | EPSG:4326 | Velocity std dev |
| coherence_median.tif | 3.2 MB | EPSG:4326 | Temporal coherence (0-1) |
| subsidence_class.tif | 78 KB | EPSG:4326 | 4-class severity (uint8) |
| subsidence_class_utm.tif | 11.5 MB | EPSG:32750 | Classification in UTM |
| vv_median.tif | 41 MB | EPSG:32750 | VV backscatter composite (linear) |
| vv_median_db.tif | 31 MB | EPSG:32750 | VV backscatter composite (dB) |
| canal_mask.tif | 345 KB | EPSG:32750 | Binary canal network |
| canal_distance.tif | 24 MB | EPSG:32750 | Distance to nearest canal (m) |
| canal_risk.tif | 30 MB | EPSG:32750 | Combined risk score (0-1) |

## Known Issues & Limitations (as of March 22, 2026)

### Must Fix
1. **Reference point instability**: Auto-selection gives different points per run, shifting
   velocity baseline. Need to set fixed reference on known stable ground (GPS station or
   persistent scatterer). Current workaround: minCoherence=0.7 for auto-select.
2. **No atmospheric correction**: ERA5 tropospheric correction disabled (no CDS API key in
   container). Causes 5-15 mm/yr bias. Fix: register at cds.climate.copernicus.eu, add
   CDS_API_KEY as Cloud Run secret, set mintpy.troposphericDelay.method=pyaps.
3. **Approximate georeferencing**: Velocity uses affine approximation from burst-merged lat/lon.
   Positional accuracy ~1-3 km. Need proper geocoding (either in MintPy or post-processing).

### Should Fix
4. **CRS mismatch between products**: Velocity is EPSG:4326, backscatter is EPSG:32750.
   Analysis reprojects on the fly but this is fragile. Should standardize to one CRS.
5. **Burst geometry merge quality**: Per-burst concatenation doesn't handle overlap regions
   correctly (just stacks vertically, trims to interferogram height). Causes geometry
   discontinuities at burst boundaries.
6. **Backscatter OOM with v20+ images**: The conda-forge snaphu package or pip snaphu
   increases baseline memory, causing OOM on GRD 2. v19-upload and v21+ (ISCE2 contrib
   SNAPHU) work. If rebuilding, ensure SNAPHU doesn't pull heavy transitive deps.
7. **No ionospheric correction**: ISCE2 supports split-spectrum via `do_ion=True` in
   topsApp XML. Should enable for equatorial data.

### Nice to Have
8. **Risk score calibration**: Weights (0.4/0.6) and decay function are arbitrary. Should
   calibrate against Hooijer et al. 2012 water table-subsidence relationship.
9. **Web dashboard**: COG GeoTIFFs can be served via TiTiler for web map display.
10. **NISAR L-band integration**: NISAR data is now available (Feb 2026, free from ASF).
    L-band penetrates forest canopy. ISCE2 supports NISAR natively.
11. **Automated scheduling**: Cloud Scheduler -> Cloud Run for monthly reprocessing.

## Critical Implementation Details

### orchestrator.py is the heart of the pipeline
- `run_insar_stage()`: Downloads SLC per-pair from GCS, runs topsApp, uploads merged/
  outputs, deletes pair dir. GCS resume via filt_topophase.unw existence check.
- `_upload_pair_to_gcs()`: Recursive upload of merged/ tree including geom_reference/
- `_merge_burst_geometry()`: Concatenates per-burst hgt/lat/lon/los files, multilooks by 3x9
- `_download_interferograms_from_gcs()`: Downloads pairs, restructures YYYY-MM-DD to
  YYYYMMDD for MintPy, downloads+merges burst geometry from first available pair
- `run_timeseries_stage()`: Downloads ifgs, calls prep_data_for_mintpy (custom HDF5),
  runs smallbaselineApp --start modify_network, exports velocity COGs
- `run_backscatter_stage()`: Per-GRD calibrate->speckle->terrain_correct, then composite
- `run_analysis_stage()`: Downloads velocity+VV from GCS, runs classification+canal+risk

### mintpy_prep.py custom HDF5 creation
MintPy's prep_isce.py fails because our GCS-reconstructed data lacks full ISCE2 XML metadata.
`prep_data_for_mintpy()` reads ISCE2 binary files directly and creates ifgramStack.h5 +
geometryRadar.h5 with hardcoded Sentinel-1 SAR parameters (wavelength, height, pixel sizes).
The `_read_isce_xml_dims()` helper parses width/length/bands from ISCE2 XML sidecars.

### velocity.py georeferencing chain
`_get_transform()` tries 3 sources in order:
1. MintPy geocoded attributes (X_FIRST/Y_FIRST/X_STEP/Y_STEP) -- only if MintPy geocoded
2. Lat/lon arrays from geometryRadar.h5 -- uses from_bounds() approximation
3. Config AOI bbox as last resort
Then clips to AOI + 0.1 degree buffer.

### topsapp.py key settings
- `snaphu_mcf` unwrapper (faster than statistical cost, handles most unwrap errors)
- `end_step="unwrap"` (no geocoding -- left to MintPy/export)
- `az_looks=3, rg_looks=9` (reduces peak memory ~27x vs full resolution)
- `do_unwrap=True` always (MintPy needs unwrapped phase)
- Generates topsApp.xml from template with config values

### Cloud Run memory management
- RAM-backed filesystem: disk usage = memory usage
- Per-pair download -> process -> upload -> delete pattern
- Delete ALL completed pair directories after each pair
- Remove SLC ZIPs immediately after extraction
- Skip VH polarization TIFFs during extraction (3 files, ~2GB saved)
- gc.collect() after each pair and each GRD

## Conventions
- No emojis in code or output
- Use logging (not print) for all output
- All geospatial outputs must be COG format (DEFLATE, 512 tiles, overviews)
- Config via Pydantic models + YAML, env var overrides with PEATGUARD_ prefix
- Always check downstream requirements before modifying upstream (e.g., MintPy needs
  unwrapped phase -- don't run topsApp without unwrapping)
- Aggressive cleanup of intermediates in Cloud Run (32GB RAM shared with filesystem)
- Build from peatguard/peatguard/ directory (that's where Dockerfile + cloudbuild.yaml are)

## GitHub
Repository: https://github.com/tommyquak/peatguard-v3.git
Branch: main
Remote: origin
