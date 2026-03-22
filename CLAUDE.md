# PeatGuard v3 - Development Guide

## Project
Satellite-based peatland subsidence monitoring using Sentinel-1 InSAR.
5-stage pipeline: Ingest → InSAR (ISCE2) → Time-Series (MintPy) → Backscatter → Analysis.
Deployed on GCP Cloud Run. Outputs are COG GeoTIFFs for ArcGIS dashboard.

## Repository Layout
```
peatguard/
  src/peatguard/         # Main Python package
    cli.py               # Click CLI (download, process, timeseries, analyze, run)
    config.py            # Pydantic config models
    catalog.py           # SQLite processing state tracker
    pipeline/
      orchestrator.py    # DAG-based stage orchestrator (main entrypoint)
    ingest/              # ASF search + Earthdata download
    insar/               # ISCE2 topsApp, SNAPHU unwrap, pairs
    timeseries/          # MintPy SBAS, HDF5 prep, velocity export
    backscatter/         # GRD calibrate, speckle, terrain correct, composite
    analysis/            # Canal detection, subsidence classification, risk scoring
    export/              # COG writer, GCS upload, metadata
  config/
    default.yaml         # Master config
    kapuas.yaml          # Site-specific override
  cloud/                 # Cloud Run, Cloud Build, Workflows configs
  tests/                 # Pytest suite
  Dockerfile             # conda-forge + ISCE2 + SNAPHU + MintPy
```

## Tech Stack
- Python 3.11, ISCE2, MintPy, SNAPHU, rasterio, GDAL
- Pydantic v2 for config, Click for CLI, SQLite for catalog
- GCS for storage, Cloud Run Jobs for execution
- COG (DEFLATE, 512 tiles, overviews) output format

## Commands
```bash
cd peatguard
pip install -e .                     # Install package (editable)
pytest tests/ -v                     # Run tests
pytest tests/test_analysis.py -v     # Run specific test module
docker build -t peatguard .          # Build container
peatguard run --start 2024-01-01 --end 2024-12-31  # Full pipeline
```

## Known Issues (priority order)
1. CRITICAL: pyproject.toml may need path fixes for editable install
2. HIGH: GRD download saves to wrong GCS prefix (raw/slc/ instead of raw/grd/)
   - Fix in ingest/download.py:182 — pass gcs_prefix based on processing_level
3. HIGH: Backscatter stage OOM — needs per-scene download-process-delete pattern
   - Fix in pipeline/orchestrator.py run_backscatter_stage()
4. MEDIUM: Cloud Run job parallelism config doesn't match sequential implementation
5. MEDIUM: Bare `except Exception: pass` in orchestrator.py (lines 344, 364, 376)
6. Wrong subswath (IW2 vs IW1) for Kapuas AOI — needs verification
7. Water body false positives — need water mask or higher coherence threshold
8. Approximate georeferencing (~1-3km error) — need proper geocoding step

## Conventions
- No emojis in code or comments
- Use logging (not print) for all output
- All geospatial outputs must be COG format
- Config via Pydantic models + YAML files
- Aggressive cleanup of intermediates (Cloud Run RAM constraint)
- Check downstream stage requirements before modifying upstream outputs
