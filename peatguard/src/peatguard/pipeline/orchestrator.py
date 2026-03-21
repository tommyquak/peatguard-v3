"""Pipeline orchestrator with DAG-based execution.

Manages the execution of pipeline stages with dependency tracking,
parallel execution of independent tasks, and resume from failure.
The orchestrator is aware of task dependencies and can run
InSAR pairs in parallel while ensuring MintPy waits for all
pairs to complete.
"""

from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from peatguard.catalog import Catalog, ProcessingStatus
from peatguard.config import PeatGuardConfig, load_config

logger = logging.getLogger(__name__)


def run_download_stage(
    config: PeatGuardConfig,
    catalog: Catalog,
    start_date: str,
    end_date: str,
    processing_level: str = "SLC",
    max_scenes: Optional[int] = None,
) -> list[Path]:
    """Stage 1: Search and download Sentinel-1 scenes.

    Args:
        config: Pipeline configuration.
        catalog: Processing catalog.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        processing_level: SLC or GRD_HD.
        max_scenes: Maximum scenes to download.

    Returns:
        List of downloaded file paths.
    """
    from peatguard.ingest.download import download_scenes
    from peatguard.ingest.search import build_acquisition_stack

    logger.info("=== Stage 1: Data Download (%s) ===", processing_level)

    scenes = build_acquisition_stack(
        config, start_date, end_date, processing_level, max_scenes
    )

    if not scenes:
        logger.warning("No scenes found")
        return []

    download_dir = config.storage.output_dir / "raw" / processing_level.lower()
    return download_scenes(scenes, download_dir, catalog=catalog)


def run_insar_stage(
    config: PeatGuardConfig,
    catalog: Catalog,
    slc_paths: list[Path],
    max_workers: int = 2,
) -> list[Path]:
    """Stage 2: InSAR processing for all pairs.

    Generates interferogram pairs and processes them in parallel
    using ISCE2 topsApp.

    Args:
        config: Pipeline configuration.
        catalog: Processing catalog.
        slc_paths: List of SLC file paths.
        max_workers: Number of parallel pair processing workers.

    Returns:
        List of pair working directories.
    """
    from peatguard.insar.pairs import select_sbas_pairs
    from peatguard.insar.topsapp import _download_dem, process_pair

    logger.info("=== Stage 2: InSAR Processing ===")

    # Download DEM once (shared across all pairs). Uses Copernicus GLO-30
    # from AWS (no auth required) with rasterio fallback.
    dem_dir = config.storage.scratch_dir / "dem"
    dem_dir.mkdir(parents=True, exist_ok=True)
    dem_path = dem_dir / "dem.wgs84"
    dem_xml = Path(str(dem_path) + ".xml")
    if not dem_xml.exists():
        logger.info("Downloading shared DEM for AOI: %s", config.aoi.bbox)
        try:
            _download_dem(config.aoi.bbox, dem_dir)
        except Exception as exc:
            logger.error("DEM download failed: %s", exc)
            raise
    else:
        logger.info("DEM already exists: %s", dem_path)

    # Lazy extraction helper: extracts SLCs on-demand per pair to avoid
    # filling the RAM-backed tmpfs (32GB container can't hold all 16 SLCs).
    # Only the 2 SLCs needed for the current pair are extracted at a time.
    import shutil
    import zipfile

    fuse_mount = Path("/mnt/gcs")
    use_fuse = fuse_mount.exists()
    local_safe_dir = config.storage.scratch_dir / "safe"
    local_safe_dir.mkdir(parents=True, exist_ok=True)
    _extracted_cache: dict[str, Path] = {}  # date -> SAFE path

    def _ensure_zip_downloaded(zip_path: Path) -> Path:
        """Download a ZIP from GCS if it does not exist locally."""
        if zip_path.exists() and zip_path.stat().st_size > 0:
            return zip_path

        if config.storage.gcs_bucket:
            from peatguard.export.gcs import download_file

            blob_name = f"raw/slc/{zip_path.name}"
            logger.info("Downloading %s from GCS", zip_path.name)
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            download_file(
                bucket_name=config.storage.gcs_bucket,
                blob_name=blob_name,
                local_path=zip_path,
            )
            logger.info("Downloaded %s (%d MB)", zip_path.name, zip_path.stat().st_size // (1024 * 1024))
        return zip_path

    def _ensure_safe_extracted(zip_path: Path) -> Path:
        """Download (if needed) and extract a single SLC ZIP, returning the SAFE path.

        Uses a cache to avoid re-extracting within the same run.
        Downloads from GCS on-demand to avoid filling disk with all SLCs.
        """
        if not str(zip_path).endswith(".zip"):
            return zip_path

        zip_stem = zip_path.stem
        safe_name = zip_stem + ".SAFE" if not zip_stem.endswith(".SAFE") else zip_stem

        # Already extracted this run
        local_safe = local_safe_dir / safe_name
        if local_safe.exists() and any(local_safe.iterdir()):
            return local_safe

        # Download from GCS if not available locally
        zip_path = _ensure_zip_downloaded(zip_path)

        logger.info("Extracting %s", zip_path.name)
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            # Get actual SAFE name from ZIP contents
            safe_dirs = [n for n in zf.namelist() if n.endswith(".SAFE/")]
            if safe_dirs:
                safe_name = safe_dirs[0].rstrip("/")
                local_safe = local_safe_dir / safe_name

            # Selective extraction: skip VH measurement TIFFs to save ~50%
            # disk space. ISCE2 only needs VV for InSAR processing.
            # Keep: all annotations, calibration, manifest, support, and VV TIFFs.
            members = zf.namelist()
            skip_vh = [m for m in members if "/measurement/" in m and "-vh-" in m]
            extract_members = [m for m in members if m not in skip_vh]
            logger.info("  Extracting %d of %d files (skipping %d VH TIFFs)",
                        len(extract_members), len(members), len(skip_vh))
            zf.extractall(str(local_safe_dir), members=extract_members)

        # Delete the ZIP immediately after extraction to free disk/RAM
        # (Cloud Run filesystem is RAM-backed, so this is critical)
        if zip_path.exists():
            logger.info("  Removing ZIP to free memory: %s (%.1f GB)", zip_path.name, zip_path.stat().st_size / (1024**3))
            zip_path.unlink()

        logger.info("  Extracted: %s", safe_name)
        return local_safe

    # Build date -> zip_path mapping without extracting yet
    logger.info("Building SLC date index from %d files", len(slc_paths))

    # Extract dates from filenames (no extraction yet -- just indexing)
    dates = []
    date_to_zip = {}  # date -> original zip/safe path
    for path in sorted(slc_paths):
        name_str = str(path.name).replace(".SAFE", "").replace(".zip", "")
        for part in name_str.split("_"):
            if len(part) >= 8 and part[:8].isdigit():
                date_str = f"{part[:4]}-{part[4:6]}-{part[6:8]}"
                dates.append(date_str)
                date_to_zip[date_str] = path
                break

    pairs = select_sbas_pairs(
        dates,
        max_temporal_baseline_days=config.sentinel1.max_temporal_baseline_days,
    )

    # Register pairs in catalog (best-effort; may fail in ephemeral containers
    # where scenes table is empty due to separate ingest job)
    for pair in pairs:
        try:
            catalog.add_interferogram(
                reference_scene_id=pair.reference_date,
                secondary_scene_id=pair.secondary_date,
                temporal_baseline_days=pair.temporal_baseline_days,
            )
        except Exception:
            logger.debug("Could not register pair %s in catalog (expected in cloud mode)", pair.pair_id)

    # Process pairs sequentially with aggressive cleanup.
    # Cloud Run filesystem is RAM-backed (32GB total), so we must keep
    # only the 2 SAFEs needed for the current pair on disk at any time.
    # After each pair completes, upload merged outputs to GCS, then delete
    # the entire pair directory to reclaim RAM.
    work_dirs = []
    completed_pair_ids = []

    def _upload_pair_to_gcs(pair_id: str, pair_dir: Path) -> None:
        """Upload merged interferogram outputs and geometry to GCS.

        Recursively walks the merged/ directory tree to capture all files
        including geometry subdirectories. Also uploads top-level XML
        config files from the pair directory.
        """
        if not config.storage.gcs_bucket:
            return
        from peatguard.export.gcs import upload_file
        merged_dir = pair_dir / "merged"
        if not merged_dir.exists():
            logger.warning("No merged directory for %s, skipping GCS upload", pair_id)
            return
        gcs_prefix = f"interferograms/{pair_id}"
        uploaded = 0

        # Log directory structure for debugging geometry issues
        subdirs = [d.name for d in merged_dir.iterdir() if d.is_dir()]
        if subdirs:
            logger.info("Subdirectories in merged/: %s", subdirs)

        # Recursively upload all files under merged/
        for fpath in merged_dir.rglob("*"):
            if fpath.is_file():
                rel = fpath.relative_to(merged_dir)
                blob_name = f"{gcs_prefix}/merged/{rel}"
                try:
                    upload_file(fpath, config.storage.gcs_bucket, blob_name)
                    uploaded += 1
                except Exception as exc:
                    logger.warning("Failed to upload %s: %s", rel, exc)

        # Also check for geom_reference at pair level (topsApp variant)
        geom_dir = pair_dir / "geom_reference"
        if geom_dir.exists() and geom_dir.is_dir():
            geom_count = 0
            for fpath in geom_dir.rglob("*"):
                if fpath.is_file():
                    rel = fpath.relative_to(geom_dir)
                    blob_name = f"{gcs_prefix}/merged/geom_reference/{rel}"
                    try:
                        upload_file(fpath, config.storage.gcs_bucket, blob_name)
                        uploaded += 1
                        geom_count += 1
                    except Exception as exc:
                        logger.warning("Failed to upload geom %s: %s", rel, exc)
            if geom_count:
                logger.info("Uploaded %d geometry files from pair-level geom_reference", geom_count)

        # Upload top-level XML sidecar files
        for xml_file in pair_dir.glob("*.xml"):
            blob_name = f"{gcs_prefix}/{xml_file.name}"
            try:
                upload_file(xml_file, config.storage.gcs_bucket, blob_name)
                uploaded += 1
            except Exception as exc:
                logger.warning("Failed to upload %s: %s", xml_file.name, exc)
        logger.info("Uploaded %d files for %s to gs://%s/%s",
                     uploaded, pair_id, config.storage.gcs_bucket, gcs_prefix)

    # Check GCS for already-completed pairs (enables resume after timeout/restart).
    # A pair is considered complete if its unwrapped phase exists in GCS.
    already_done = set()
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import list_blobs
        for pair in pairs:
            check_prefix = f"interferograms/{pair.pair_id}/merged/filt_topophase.unw"
            existing = list_blobs(config.storage.gcs_bucket, check_prefix)
            if existing:
                already_done.add(pair.pair_id)
        if already_done:
            logger.info("Found %d pairs already in GCS, will skip them", len(already_done))

    logger.info("Processing %d pairs sequentially with on-demand extraction (%d to skip)",
                len(pairs), len(already_done))
    for i, pair in enumerate(pairs):
        logger.info("[%d/%d] Processing pair: %s", i + 1, len(pairs), pair.pair_id)

        # Skip pairs already uploaded to GCS from a previous run
        if pair.pair_id in already_done:
            logger.info("[%d/%d] Skipping %s (already in GCS)", i + 1, len(pairs), pair.pair_id)
            continue

        # AGGRESSIVE CLEANUP: before each pair, remove ALL SAFEs except
        # the two needed for this pair.
        current_dates = {pair.reference_date, pair.secondary_date}
        for safe_path in list(local_safe_dir.iterdir()):
            if not safe_path.is_dir():
                continue
            name_str = safe_path.name.replace(".SAFE", "")
            safe_date = None
            for part in name_str.split("_"):
                if len(part) >= 8 and part[:8].isdigit():
                    safe_date = f"{part[:4]}-{part[4:6]}-{part[6:8]}"
                    break
            if safe_date and safe_date not in current_dates:
                logger.info("  Pre-cleanup: removing %s", safe_path.name)
                shutil.rmtree(str(safe_path), ignore_errors=True)

        # Delete ALL completed pair directories entirely (not just trim).
        # Their merged outputs are already in GCS.
        insar_root = config.storage.scratch_dir / "insar"
        for prev_id in completed_pair_ids:
            prev_dir = insar_root / prev_id
            if prev_dir.exists():
                shutil.rmtree(str(prev_dir), ignore_errors=True)
                logger.info("  Pre-cleanup: deleted entire %s directory", prev_id)

        # Also remove any stale ZIP files that weren't cleaned up
        slc_dir = config.storage.scratch_dir / "raw" / "slc"
        if slc_dir.exists():
            for zip_file in slc_dir.glob("*.zip"):
                logger.info("  Pre-cleanup: removing stale ZIP %s", zip_file.name)
                zip_file.unlink(missing_ok=True)

        # Extract and process
        ref_path = _ensure_safe_extracted(date_to_zip[pair.reference_date])
        sec_path = _ensure_safe_extracted(date_to_zip[pair.secondary_date])
        pair_dir = config.storage.scratch_dir / "insar" / pair.pair_id

        try:
            catalog.update_interferogram_status(pair.pair_id, ProcessingStatus.PROCESSING)
        except Exception:
            pass

        try:
            work_dir = process_pair(
                reference_safe=ref_path,
                secondary_safe=sec_path,
                work_dir=pair_dir,
                config=config,
                dem_path=dem_path,
            )

            # Upload merged outputs to GCS immediately after success
            _upload_pair_to_gcs(pair.pair_id, work_dir)
            completed_pair_ids.append(pair.pair_id)
            work_dirs.append(work_dir)

            try:
                catalog.update_interferogram_status(
                    pair.pair_id, ProcessingStatus.COMPLETED, output_dir=str(work_dir))
            except Exception:
                pass
            logger.info("[%d/%d] Completed pair: %s", i + 1, len(pairs), pair.pair_id)
        except Exception as exc:
            logger.error("[%d/%d] Failed pair %s: %s", i + 1, len(pairs), pair.pair_id, exc)
            # Still clean up the failed pair directory to free RAM
            if pair_dir.exists():
                shutil.rmtree(str(pair_dir), ignore_errors=True)
                logger.info("  Cleaned up failed pair directory: %s", pair.pair_id)
            try:
                catalog.update_interferogram_status(
                    pair.pair_id, ProcessingStatus.FAILED, error_message=str(exc))
            except Exception:
                pass

    logger.info("InSAR processing complete: %d/%d pairs", len(work_dirs), len(pairs))
    return work_dirs


def _merge_burst_geometry(
    burst_dir: Path,
    output_dir: Path,
    az_looks: int = 3,
    rg_looks: int = 9,
) -> None:
    """Merge per-burst geometry and multilook to match interferogram size.

    topsApp produces per-burst geometry (hgt_01.rdr, hgt_02.rdr, etc.)
    in geom_reference/IW*/. MintPy expects merged, multilooked files
    (hgt.rdr, lat.rdr, lon.rdr) in geom_reference/.

    Each per-burst file is a strip in the azimuth direction. Merging
    concatenates them vertically, then downsamples by az_looks x rg_looks
    to match the interferogram resolution.
    """
    import numpy as np

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find per-burst geometry files (e.g. hgt_01.rdr, hgt_02.rdr, ...)
    geom_types = {}  # e.g. {"hgt": [Path("hgt_01.rdr"), ...], "lat": [...]}
    for rdr_file in sorted(burst_dir.glob("*.rdr")):
        stem = rdr_file.stem  # e.g. "hgt_01"
        if "_" not in stem:
            continue
        geom_name = stem.rsplit("_", 1)[0]  # e.g. "hgt"
        geom_types.setdefault(geom_name, []).append(rdr_file)

    for geom_name, burst_files in sorted(geom_types.items()):
        output_file = output_dir / f"{geom_name}.rdr"
        if output_file.exists():
            continue

        # Read XML of first burst to get width
        xml_path = burst_files[0].with_suffix(".rdr.xml")
        width = None
        n_bands = 1
        if xml_path.exists():
            import xml.etree.ElementTree as ET
            tree = ET.parse(str(xml_path))
            for prop in tree.iter("property"):
                if prop.get("name") == "width":
                    width = int(prop.find("value").text)
                elif prop.get("name") == "number_bands":
                    n_bands = int(prop.find("value").text)

        # Determine data type (lat/lon are float64 in ISCE2)
        dtype = np.float64 if geom_name in ("lat", "lon") else np.float32

        # Concatenate bursts vertically
        arrays = []
        for bf in burst_files:
            data = np.fromfile(str(bf), dtype=dtype)
            if width and n_bands:
                data = data.reshape(-1, width * n_bands)
            arrays.append(data)

        merged = np.concatenate(arrays, axis=0)
        full_h, full_w_bands = merged.shape

        # Multilook (block-average) to match interferogram resolution
        ml_h = full_h // az_looks
        ml_w = (full_w_bands // n_bands) // rg_looks
        if n_bands > 1:
            # Handle multi-band (e.g. los.rdr with inc+az)
            band_w = full_w_bands // n_bands
            ml_bands = []
            for b in range(n_bands):
                band = merged[:, b * band_w:(b + 1) * band_w]
                band_trimmed = band[:ml_h * az_looks, :ml_w * rg_looks]
                band_ml = band_trimmed.reshape(ml_h, az_looks, ml_w, rg_looks).mean(axis=(1, 3))
                ml_bands.append(band_ml.astype(np.float32))
            multilooked = np.column_stack(ml_bands)
        else:
            trimmed = merged[:ml_h * az_looks, :ml_w * rg_looks]
            multilooked = trimmed.reshape(ml_h, az_looks, ml_w, rg_looks).mean(axis=(1, 3))
            multilooked = multilooked.astype(np.float32)

        multilooked.tofile(str(output_file))
        out_w = ml_w * n_bands if n_bands > 1 else ml_w
        logger.info("Merged+multilooked %d bursts -> %s (%dx%d, %dx%d looks)",
                     len(burst_files), output_file.name,
                     ml_h, ml_w, az_looks, rg_looks)

        # Create minimal XML sidecar
        xml_content = f"""<imageFile>
    <property name="width"><value>{ml_w}</value></property>
    <property name="length"><value>{ml_h}</value></property>
    <property name="number_bands"><value>{n_bands}</value></property>
    <property name="scheme"><value>BIL</value></property>
    <property name="data_type"><value>FLOAT</value></property>
    <property name="byte_order"><value>l</value></property>
</imageFile>"""
        output_file.with_suffix(".rdr.xml").write_text(xml_content)


def _download_interferograms_from_gcs(config: PeatGuardConfig, isce_dir: Path) -> int:
    """Download interferogram outputs from GCS and restructure for MintPy.

    MintPy expects:
        isce_dir/merged/interferograms/{YYYYMMDD_YYYYMMDD}/filt_topophase.unw
        isce_dir/merged/geom_reference/hgt.rdr

    GCS has:
        interferograms/{YYYY-MM-DD_YYYY-MM-DD}/merged/filt_topophase.unw
        interferograms/{YYYY-MM-DD_YYYY-MM-DD}/merged/geom_reference/IW2/hgt_01.rdr

    Returns:
        Number of pairs downloaded.
    """
    from peatguard.export.gcs import download_file, list_blobs

    logger.info("Downloading interferograms from GCS for MintPy")

    # List all pair directories in GCS
    all_blobs = list_blobs(config.storage.gcs_bucket, "interferograms/")
    if not all_blobs:
        raise RuntimeError("No interferograms found in GCS")

    # Identify completed pairs (those with unwrapped phase)
    pair_ids = set()
    for blob in all_blobs:
        parts = blob.split("/")
        if len(parts) >= 4 and parts[2] == "merged" and parts[3] == "filt_topophase.unw":
            pair_ids.add(parts[1])

    logger.info("Found %d unwrapped pairs in GCS", len(pair_ids))

    # Create MintPy-expected directory structure
    ifg_root = isce_dir / "merged" / "interferograms"
    geom_root = isce_dir / "merged" / "geom_reference"
    ifg_root.mkdir(parents=True, exist_ok=True)
    geom_root.mkdir(parents=True, exist_ok=True)

    geom_downloaded = False
    downloaded_pairs = 0

    for pair_id in sorted(pair_ids):
        # Convert YYYY-MM-DD_YYYY-MM-DD to YYYYMMDD_YYYYMMDD for MintPy
        mintpy_pair_id = pair_id.replace("-", "")
        pair_dir = ifg_root / mintpy_pair_id
        pair_dir.mkdir(parents=True, exist_ok=True)

        # Download interferogram files for this pair (skip geom subdirs)
        pair_blobs = [b for b in all_blobs if b.startswith(f"interferograms/{pair_id}/merged/")
                      and "/geom_reference/" not in b]
        for blob in pair_blobs:
            filename = blob.split("/")[-1]
            local_path = pair_dir / filename
            if not local_path.exists():
                download_file(config.storage.gcs_bucket, blob, local_path)

        # Also copy los.rdr into geom_reference (MintPy expects it there)
        los_src = pair_dir / "los.rdr"
        los_dst = geom_root / "los.rdr"
        if los_src.exists() and not los_dst.exists():
            import shutil as _shutil
            _shutil.copy2(str(los_src), str(los_dst))
            # Also copy XML sidecar
            los_xml_src = pair_dir / "los.rdr.xml"
            if los_xml_src.exists():
                _shutil.copy2(str(los_xml_src), str(geom_root / "los.rdr.xml"))

        # Download per-burst geometry from first pair and merge for MintPy
        if not geom_downloaded:
            geom_blobs = [b for b in all_blobs
                          if b.startswith(f"interferograms/{pair_id}/merged/geom_reference/")]
            if geom_blobs:
                # Download per-burst geometry files
                local_geom_staging = isce_dir / "_geom_staging"
                local_geom_staging.mkdir(parents=True, exist_ok=True)
                for blob in geom_blobs:
                    # Preserve subdirectory structure
                    rel_path = blob.split("geom_reference/", 1)[1]
                    local_path = local_geom_staging / rel_path
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    if not local_path.exists():
                        download_file(config.storage.gcs_bucket, blob, local_path)

                # Find the IW subswath directory and merge bursts
                for iw_dir in sorted(local_geom_staging.glob("IW*")):
                    if iw_dir.is_dir():
                        logger.info("Merging per-burst geometry from %s", iw_dir.name)
                        _merge_burst_geometry(iw_dir, geom_root)
                        break

                geom_downloaded = True
                logger.info("Downloaded and merged geometry from pair %s", pair_id)
            else:
                logger.warning("No geometry blobs found for pair %s", pair_id)

        downloaded_pairs += 1

    logger.info("Downloaded %d pairs to %s", downloaded_pairs, isce_dir)
    return downloaded_pairs


def run_timeseries_stage(
    config: PeatGuardConfig,
    isce_dir: Path,
) -> Path:
    """Stage 3: MintPy SBAS time-series analysis.

    Downloads interferograms from GCS (if running in Cloud Run),
    restructures them for MintPy, and runs the SBAS inversion.

    Args:
        config: Pipeline configuration.
        isce_dir: Root ISCE2 output directory.

    Returns:
        Path to the MintPy working directory.
    """
    from peatguard.timeseries.mintpy_prep import generate_mintpy_config, prep_data_for_mintpy
    from peatguard.timeseries.sbas import run_sbas_inversion
    from peatguard.timeseries.velocity import export_velocity

    logger.info("=== Stage 3: Time-Series Analysis ===")

    # Download interferograms from GCS if the local directory is empty
    ifg_dir = isce_dir / "merged" / "interferograms"
    if not ifg_dir.exists() or not any(ifg_dir.iterdir()):
        if config.storage.gcs_bucket:
            _download_interferograms_from_gcs(config, isce_dir)
        else:
            raise RuntimeError(
                f"No interferograms found at {ifg_dir} and no GCS bucket configured"
            )

    mintpy_dir = config.storage.scratch_dir / "mintpy"
    mintpy_dir.mkdir(parents=True, exist_ok=True)

    # Prepare HDF5 stack files directly (avoids prep_isce.py metadata issues
    # when data is reconstructed from GCS rather than a single topsApp run)
    ifgram_file, geom_file = prep_data_for_mintpy(isce_dir, mintpy_dir, config)

    # Generate MintPy config and run smallbaselineApp with --start to skip
    # load_data (we already created the HDF5 files directly)
    config_path = generate_mintpy_config(isce_dir, mintpy_dir, config)

    from peatguard.timeseries.sbas import run_smallbaselineApp_from_step
    run_smallbaselineApp_from_step(config_path, mintpy_dir, start_step="modify_network")

    # Export velocity products as COG GeoTIFFs
    velocity_products = export_velocity(mintpy_dir, config.storage.output_dir, config)
    logger.info("Velocity products: %s", list(velocity_products.keys()))

    # Upload products to GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import upload_file
        for name, path in velocity_products.items():
            blob_name = f"products/{path.name}"
            try:
                upload_file(path, config.storage.gcs_bucket, blob_name)
                logger.info("Uploaded %s to gs://%s/%s", name, config.storage.gcs_bucket, blob_name)
            except Exception as exc:
                logger.warning("Failed to upload %s: %s", name, exc)

    return mintpy_dir


def run_backscatter_stage(
    config: PeatGuardConfig,
    grd_paths: list[Path],
) -> Path:
    """Stage 4: GRD backscatter processing.

    Args:
        config: Pipeline configuration.
        grd_paths: List of GRD file paths.

    Returns:
        Path to the median composite GeoTIFF.
    """
    from peatguard.backscatter.calibrate import calibrate_grd
    from peatguard.backscatter.composite import create_temporal_composite
    from peatguard.backscatter.speckle import apply_speckle_filter
    from peatguard.backscatter.terrain_correct import terrain_correct, to_decibels

    logger.info("=== Stage 4: Backscatter Processing ===")

    scratch = config.storage.scratch_dir / "backscatter"
    geocoded_paths = []

    for i, grd_path in enumerate(grd_paths, 1):
        logger.info("Processing GRD %d/%d: %s", i, len(grd_paths), grd_path.name)
        stem = grd_path.stem

        # Download from GCS if the file doesn't exist locally (on-demand)
        if not grd_path.exists() and config.storage.gcs_bucket:
            from peatguard.export.gcs import download_file, list_blobs
            # Search both raw/grd/ and raw/slc/ for this file
            for prefix in ["raw/grd/", "raw/slc/"]:
                blobs = list_blobs(config.storage.gcs_bucket, prefix + grd_path.name)
                if blobs:
                    grd_path.parent.mkdir(parents=True, exist_ok=True)
                    download_file(config.storage.gcs_bucket, blobs[0], grd_path)
                    logger.info("Downloaded %s from GCS (%s)", grd_path.name, prefix)
                    break

        cal_path = scratch / "calibrated" / f"{stem}_sigma0.tif"
        filt_path = scratch / "filtered" / f"{stem}_filtered.tif"
        geo_path = scratch / "geocoded" / f"{stem}_geocoded.tif"

        try:
            calibrate_grd(grd_path, cal_path, polarization=config.sentinel1.polarization.lower())
            apply_speckle_filter(cal_path, filt_path, window_size=config.processing.speckle_window_size)
            terrain_correct(filt_path, geo_path, target_crs=config.aoi.epsg, resolution_m=config.processing.resolution_m)
            geocoded_paths.append(geo_path)
        except Exception as exc:
            logger.error("Failed to process GRD %s: %s", grd_path.name, exc)
        finally:
            # Aggressively clean up ALL intermediates to free RAM-backed disk
            import gc
            for p in [grd_path, cal_path, filt_path]:
                if p.exists():
                    p.unlink(missing_ok=True)
            # Remove extracted SAFE directory and temp extraction dirs
            safe_dir = grd_path.with_suffix(".SAFE")
            if safe_dir.exists():
                shutil.rmtree(str(safe_dir), ignore_errors=True)
            for tmp_dir in grd_path.parent.glob("_*_tmp"):
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
            gc.collect()
            logger.info("Cleaned up intermediates for GRD %d/%d", i, len(grd_paths))

    # Create median composite
    composite_path = config.storage.output_dir / "vv_median.tif"
    create_temporal_composite(geocoded_paths, composite_path, method="median", config=config)

    # Also produce dB version
    db_path = config.storage.output_dir / "vv_median_db.tif"
    to_decibels(composite_path, db_path)

    # Upload composites to GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import upload_file
        for path in [composite_path, db_path]:
            if path.exists():
                blob_name = f"products/{path.name}"
                try:
                    upload_file(path, config.storage.gcs_bucket, blob_name)
                    logger.info("Uploaded %s to gs://%s/%s", path.name, config.storage.gcs_bucket, blob_name)
                except Exception as exc:
                    logger.warning("Failed to upload %s: %s", path.name, exc)

    return composite_path


def run_analysis_stage(
    config: PeatGuardConfig,
    velocity_path: Path,
    vv_path: Optional[Path] = None,
) -> dict[str, Path]:
    """Stage 5: Analysis and product generation.

    Canal detection and risk scoring require VV backscatter and are
    skipped if vv_path is not provided. Subsidence classification
    always runs.

    Args:
        config: Pipeline configuration.
        velocity_path: Path to subsidence velocity GeoTIFF.
        vv_path: Path to VV backscatter composite (optional).

    Returns:
        Dict mapping product names to output paths.
    """
    from peatguard.analysis.subsidence_class import classify_subsidence_file

    logger.info("=== Stage 5: Analysis ===")

    output_dir = config.storage.output_dir
    products = {}

    # Subsidence classification (always runs)
    class_path = output_dir / "subsidence_class.tif"
    classify_subsidence_file(velocity_path, class_path, config.classification)
    products["subsidence_class"] = class_path

    # Canal detection + risk scoring (requires VV backscatter)
    if vv_path and vv_path.exists():
        from peatguard.analysis.canal_detect import detect_canals
        from peatguard.analysis.risk_score import generate_risk_map

        canal_mask_path = output_dir / "canal_mask.tif"
        canal_dist_path = output_dir / "canal_distance.tif"
        detect_canals(vv_path, canal_mask_path, canal_dist_path)
        products["canal_mask"] = canal_mask_path
        products["canal_distance"] = canal_dist_path

        # Reproject canal distance to match velocity grid (CRS may differ:
        # backscatter is typically UTM, velocity is WGS84 from radar coords)
        import rasterio
        from rasterio.warp import reproject, Resampling
        vel_ds = rasterio.open(velocity_path)
        dist_ds = rasterio.open(canal_dist_path)
        if vel_ds.crs != dist_ds.crs or vel_ds.shape != dist_ds.shape:
            logger.info("Reprojecting canal distance from %s to %s", dist_ds.crs, vel_ds.crs)
            aligned_dist_path = output_dir / "canal_distance_aligned.tif"
            with rasterio.open(
                aligned_dist_path, "w", driver="GTiff",
                height=vel_ds.height, width=vel_ds.width,
                count=1, dtype="float32",
                crs=vel_ds.crs, transform=vel_ds.transform,
                nodata=-9999.0,
            ) as dst:
                reproject(
                    source=rasterio.band(dist_ds, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=dist_ds.transform,
                    src_crs=dist_ds.crs,
                    dst_transform=vel_ds.transform,
                    dst_crs=vel_ds.crs,
                    resampling=Resampling.bilinear,
                )
            dist_ds.close()
            vel_ds.close()
            canal_dist_for_risk = aligned_dist_path
        else:
            dist_ds.close()
            vel_ds.close()
            canal_dist_for_risk = canal_dist_path

        risk_path = output_dir / "canal_risk.tif"
        generate_risk_map(velocity_path, canal_dist_for_risk, risk_path)
        products["canal_risk"] = risk_path
    else:
        logger.info("VV backscatter not available, skipping canal detection and risk scoring")

    # Upload products to GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import upload_file
        for name, path in products.items():
            blob_name = f"products/{path.name}"
            try:
                upload_file(path, config.storage.gcs_bucket, blob_name)
                logger.info("Uploaded %s to gs://%s/%s", name, config.storage.gcs_bucket, blob_name)
            except Exception as exc:
                logger.warning("Failed to upload %s: %s", name, exc)

    logger.info("Analysis complete: %d products generated", len(products))
    return products


def run_full_pipeline(
    config_path: Optional[Path] = None,
    override_path: Optional[Path] = None,
    start_date: str = "2015-01-01",
    end_date: str = "2016-12-31",
    max_workers: int = 2,
) -> None:
    """Run the complete PeatGuard pipeline end-to-end.

    Args:
        config_path: Path to config YAML.
        override_path: Path to config override YAML.
        start_date: Data search start date.
        end_date: Data search end date.
        max_workers: Parallel workers for InSAR processing.
    """
    config = load_config(config_path, override_path)
    catalog = Catalog(config.storage.catalog_db)

    # Ensure output dirs exist
    config.storage.output_dir.mkdir(parents=True, exist_ok=True)
    config.storage.scratch_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting PeatGuard pipeline")
    logger.info("AOI: %s, EPSG: %d", config.aoi.bbox, config.aoi.epsg)

    # Download SLC and GRD
    slc_paths = run_download_stage(config, catalog, start_date, end_date, "SLC")
    grd_paths = run_download_stage(config, catalog, start_date, end_date, "GRD_HD")

    # InSAR processing (parallel pairs)
    insar_dirs = run_insar_stage(config, catalog, slc_paths, max_workers)

    # MintPy time-series
    isce_root = config.storage.scratch_dir / "insar"
    mintpy_dir = run_timeseries_stage(config, isce_root)

    # Export velocity products
    from peatguard.timeseries.velocity import export_velocity

    velocity_products = export_velocity(mintpy_dir, config.storage.output_dir, config)

    # Backscatter processing (independent of InSAR)
    vv_path = run_backscatter_stage(config, grd_paths)

    # Analysis
    velocity_path = velocity_products.get("subsidence_velocity", config.storage.output_dir / "subsidence_velocity.tif")
    run_analysis_stage(config, velocity_path, vv_path)

    # Upload to GCS if configured
    if config.storage.gcs_bucket:
        from datetime import date

        from peatguard.export.gcs import upload_products

        upload_products(config.storage.output_dir, config.storage, date.today().isoformat())

    logger.info("Pipeline complete. Products in: %s", config.storage.output_dir)
