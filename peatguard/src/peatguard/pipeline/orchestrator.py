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

    logger.info("=== Stage 1: Data Download (%s, sensor=%s) ===", processing_level, config.sensor)

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

    Generates interferogram pairs and processes them using ISCE2.
    Routes to topsApp (Sentinel-1 TOPS) or stripmapApp (NISAR L-band)
    based on the active sensor configuration.

    Args:
        config: Pipeline configuration.
        catalog: Processing catalog.
        slc_paths: List of SLC file paths.
        max_workers: Number of parallel pair processing workers.

    Returns:
        List of pair working directories.
    """
    from peatguard.insar.pairs import select_sbas_pairs
    from peatguard.insar.topsapp import _download_dem

    if config.is_nisar:
        from peatguard.insar.stripmapapp import process_pair
    else:
        from peatguard.insar.topsapp import process_pair

    logger.info("=== Stage 2: InSAR Processing (sensor=%s) ===", config.sensor)

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

    # Extract dates from filenames (no extraction yet -- just indexing).
    # Filter to SLC files only -- GRD files may be mixed in the same directory
    # (known issue: GRD download saves to raw/slc/ instead of raw/grd/).
    dates = []
    date_to_zip = {}  # date -> original zip/safe path
    for path in sorted(slc_paths):
        name_str = str(path.name)
        # Skip GRD files -- they can't be used for InSAR
        if "GRDH" in name_str or "GRD" in name_str:
            continue
        name_str = name_str.replace(".SAFE", "").replace(".zip", "")
        for part in name_str.split("_"):
            if len(part) >= 8 and part[:8].isdigit():
                date_str = f"{part[:4]}-{part[4:6]}-{part[6:8]}"
                if date_str not in date_to_zip:  # avoid duplicates
                    dates.append(date_str)
                date_to_zip[date_str] = path
                break

    sensor_cfg = config.active_sensor_config
    pairs = select_sbas_pairs(
        dates,
        max_temporal_baseline_days=sensor_cfg.max_temporal_baseline_days,
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
            if config.is_nisar:
                work_dir = process_pair(
                    reference_slc=ref_path,
                    secondary_slc=sec_path,
                    work_dir=pair_dir,
                    config=config,
                    dem_path=dem_path,
                )
            else:
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


def _estimate_burst_overlaps(
    arrays: list[np.ndarray],
    max_search: int = 200,
    default_overlap: int = 120,
) -> list[int]:
    """Estimate azimuth overlap between adjacent burst arrays.

    Sentinel-1 TOPS bursts overlap by ~100-120 lines in azimuth. This
    function detects the overlap by comparing the trailing edge of burst i
    with the leading edge of burst i+1 using the center column signal.

    Args:
        arrays: List of 2D burst arrays (height x width).
        max_search: Maximum overlap to search for (lines).
        default_overlap: Fallback if detection is uncertain.

    Returns:
        List of overlap values (length = len(arrays) - 1).
    """
    import numpy as np

    overlaps = []
    for i in range(len(arrays) - 1):
        a = arrays[i]
        b = arrays[i + 1]
        # Use center column as 1D signal for matching
        mid_col = a.shape[1] // 2
        sig_a = a[:, mid_col].astype(np.float64)
        sig_b = b[:, mid_col].astype(np.float64)

        best_overlap = default_overlap
        best_diff = float("inf")
        for candidate in range(20, min(max_search, a.shape[0], b.shape[0])):
            tail = sig_a[-candidate:]
            head = sig_b[:candidate]
            diff = np.mean(np.abs(tail - head))
            if diff < best_diff:
                best_diff = diff
                best_overlap = candidate

        # If signal is constant or detection uncertain, use default
        sig_range = np.ptp(sig_a)
        if sig_range > 0 and best_diff / sig_range > 0.1:
            best_overlap = default_overlap

        overlaps.append(best_overlap)
    return overlaps


def _merge_burst_arrays_with_overlap(
    arrays: list[np.ndarray],
    overlaps: list[int],
) -> np.ndarray:
    """Merge burst arrays, trimming overlap regions.

    For N bursts with overlaps [o1, o2, ..., o_{N-1}]:
    - Burst 0: keep rows [0 : height - o1//2]
    - Burst i (middle): keep rows [o_i//2 : height - o_{i+1}//2]
    - Burst N-1: keep rows [o_{N-1}//2 : height]

    Args:
        arrays: List of 2D burst arrays.
        overlaps: List of overlap sizes between adjacent bursts.

    Returns:
        Vertically merged array with overlaps removed.
    """
    import numpy as np

    n = len(arrays)
    if n == 1:
        return arrays[0]

    trimmed = []
    for i, arr in enumerate(arrays):
        h = arr.shape[0]
        top_trim = overlaps[i - 1] // 2 if i > 0 else 0
        bot_trim = overlaps[i] // 2 if i < n - 1 else 0

        row_start = top_trim
        row_end = h - bot_trim
        if row_end <= row_start:
            # Safety: don't produce empty slice
            logger.warning(
                "Burst %d: overlap trimming would produce empty array "
                "(%d rows, top=%d, bot=%d). Skipping trim.",
                i, h, top_trim, bot_trim,
            )
            trimmed.append(arr)
        else:
            trimmed.append(arr[row_start:row_end])

    return np.concatenate(trimmed, axis=0)


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
    handles the ~100-120 line overlap between adjacent bursts by trimming
    overlap margins, then downsamples by az_looks x rg_looks to match
    the interferogram resolution.
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

    # Detect burst overlaps using lat arrays (monotonic in azimuth, most reliable).
    detected_overlaps = None
    if "lat" in geom_types:
        lat_files = geom_types["lat"]
        lat_arrays = []
        for bf in lat_files:
            data = np.fromfile(str(bf), dtype=np.float64)
            xml_path = bf.with_suffix(".rdr.xml")
            w = None
            if xml_path.exists():
                import xml.etree.ElementTree as ET
                tree = ET.parse(str(xml_path))
                for prop in tree.iter("property"):
                    if prop.get("name", "") == "width":
                        val = prop.find("value")
                        if val is not None and val.text:
                            w = int(val.text)
            if w:
                data = data.reshape(-1, w)
            lat_arrays.append(data)
        detected_overlaps = _estimate_burst_overlaps(lat_arrays)
        logger.info("Detected burst overlaps from lat: %s", detected_overlaps)

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
                name = prop.get("name", "")
                val_elem = prop.find("value")
                if val_elem is None or val_elem.text is None:
                    continue
                if name == "width":
                    width = int(val_elem.text)
                elif name == "number_bands":
                    n_bands = int(val_elem.text)
        if width is None:
            logger.warning("Could not parse width for %s, skipping", geom_name)
            continue

        # Determine data type (lat/lon are float64 in ISCE2)
        dtype = np.float64 if geom_name in ("lat", "lon") else np.float32

        # Read burst arrays
        arrays = []
        for bf in burst_files:
            data = np.fromfile(str(bf), dtype=dtype)
            if width and n_bands:
                data = data.reshape(-1, width * n_bands)
            arrays.append(data)

        # Merge with overlap trimming
        if detected_overlaps is not None and len(detected_overlaps) == len(arrays) - 1:
            overlaps = detected_overlaps
        elif len(arrays) > 1:
            overlaps = _estimate_burst_overlaps(arrays)
            logger.info("Estimated overlaps for %s: %s", geom_name, overlaps)
        else:
            overlaps = []

        if overlaps:
            merged = _merge_burst_arrays_with_overlap(arrays, overlaps)
        else:
            merged = np.concatenate(arrays, axis=0) if len(arrays) > 1 else arrays[0]

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
    from peatguard.timeseries.mintpy_prep import (
        generate_mintpy_config,
        pre_download_era5,
        prep_data_for_mintpy,
    )
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
    weather_dir = mintpy_dir / "weather"
    weather_dir.mkdir(exist_ok=True)

    # Pre-download ERA5 data one date at a time with retry logic.
    # This prevents the CDS API timeout that occurs when MintPy/PyAPS
    # tries to bulk-download all dates in a single request.
    tropo_setting = config.mintpy.tropospheric_correction.lower()
    era5_enabled = tropo_setting in ("pyaps", "era5")
    if era5_enabled:
        ifg_dates = set()
        for d in (isce_dir / "merged" / "interferograms").iterdir():
            if d.is_dir():
                parts = d.name.split("_")
                if len(parts) == 2 and len(parts[0]) == 8:
                    ifg_dates.add(parts[0])
                    ifg_dates.add(parts[1])
        if ifg_dates:
            pre_download_era5(
                dates=sorted(ifg_dates),
                bbox=config.aoi.bbox,
                weather_dir=weather_dir,
            )

    from peatguard.timeseries.sbas import run_smallbaselineApp_from_step

    # Two-phase reference point selection to prevent ERA5 velocity bias.
    #
    # ERA5 tropospheric correction changes the phase pattern, which can cause
    # MintPy to auto-select a different reference point. This shifts the
    # entire velocity field (observed +35 mm/yr bias). To prevent this:
    #   Phase 1: Run modify_network -> reference_point WITHOUT ERA5 correction.
    #            This selects the reference on uncorrected data (physically correct).
    #   Phase 2: Extract the selected reference coordinates, regenerate the config
    #            with ERA5 enabled AND the fixed reference, then run the full chain.
    ref_lalo = config.mintpy.reference_lalo
    has_fixed_ref = ref_lalo and len(ref_lalo) == 2

    if era5_enabled and not has_fixed_ref:
        logger.info(
            "ERA5 enabled without fixed reference point. Running two-phase "
            "reference selection to prevent velocity bias."
        )

        # Phase 1: Generate config WITHOUT ERA5, run through reference_point only
        from peatguard.timeseries.mintpy_prep import _is_cds_api_available
        original_tropo = config.mintpy.tropospheric_correction
        config.mintpy.tropospheric_correction = "no"
        phase1_config_path = generate_mintpy_config(
            isce_dir, mintpy_dir, config, weather_dir=weather_dir
        )
        config.mintpy.tropospheric_correction = original_tropo

        run_smallbaselineApp_from_step(
            phase1_config_path, mintpy_dir,
            start_step="modify_network", end_step="reference_point",
        )

        # Extract the auto-selected reference point from ifgramStack.h5 attributes
        import h5py
        ifgram_h5 = mintpy_dir / "inputs" / "ifgramStack.h5"
        ref_y, ref_x = -1, -1
        with h5py.File(str(ifgram_h5), "r") as f:
            ref_y = int(f.attrs.get("REF_Y", -1))
            ref_x = int(f.attrs.get("REF_X", -1))

        if ref_y < 0 or ref_x < 0:
            logger.warning(
                "Could not extract reference point from ifgramStack.h5 "
                "(REF_Y=%d, REF_X=%d). Falling back to auto-selection.",
                ref_y, ref_x,
            )
            config_path = generate_mintpy_config(
                isce_dir, mintpy_dir, config, weather_dir=weather_dir
            )
        else:
            logger.info(
                "Phase 1 reference point selected: REF_Y=%d, REF_X=%d. "
                "Locking for ERA5 run.",
                ref_y, ref_x,
            )
            # Phase 2: Regenerate config WITH ERA5 and the fixed reference (Y, X)
            config_path = generate_mintpy_config(
                isce_dir, mintpy_dir, config, weather_dir=weather_dir,
                override_ref_yx=(ref_y, ref_x),
            )

        # Phase 2: Run the full chain with ERA5 + fixed reference
        run_smallbaselineApp_from_step(
            config_path, mintpy_dir, start_step="modify_network"
        )
    else:
        # No ERA5 or already have a fixed reference -- single pass is fine
        config_path = generate_mintpy_config(
            isce_dir, mintpy_dir, config, weather_dir=weather_dir
        )
        run_smallbaselineApp_from_step(
            config_path, mintpy_dir, start_step="modify_network"
        )

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
            terrain_correct(filt_path, geo_path, target_crs=config.aoi.epsg,
                           resolution_m=config.processing.resolution_m,
                           bounds=tuple(config.aoi.bbox))
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


def _run_fusion(
    config: PeatGuardConfig,
    output_dir: Path,
    existing_products: dict[str, Path],
) -> dict[str, Path]:
    """Run multi-sensor fusion if both C-band and L-band products are available.

    Attempts to locate C-band and L-band velocity and coherence products,
    either from local storage or by downloading from GCS. If both sensor
    datasets are found, performs coherence-weighted fusion and re-runs
    subsidence classification and risk scoring on the fused velocity.

    Args:
        config: Pipeline configuration (must have fusion.enabled=True).
        output_dir: Directory for output products.
        existing_products: Products already generated in this analysis run.

    Returns:
        Dict of fusion product names to output paths. Empty if fusion
        inputs are not available.
    """
    from peatguard.analysis.fusion import generate_fusion_products

    logger.info("=== Multi-sensor fusion check ===")

    # Define expected paths for both sensors' products.
    # Convention: C-band products use default names, L-band products use
    # the "nisar_" prefix to distinguish them.
    c_vel_path = output_dir / "subsidence_velocity.tif"
    c_coh_path = output_dir / "coherence_median.tif"
    l_vel_path = output_dir / "nisar_subsidence_velocity.tif"
    l_coh_path = output_dir / "nisar_coherence_median.tif"

    # Try downloading missing products from GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import download_file

        gcs_products = {
            c_vel_path: "products/subsidence_velocity.tif",
            c_coh_path: "products/coherence_median.tif",
            l_vel_path: "products/nisar_subsidence_velocity.tif",
            l_coh_path: "products/nisar_coherence_median.tif",
        }
        for local_path, blob_name in gcs_products.items():
            if not local_path.exists():
                try:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    download_file(config.storage.gcs_bucket, blob_name, local_path)
                    logger.info("Downloaded %s from GCS", blob_name)
                except Exception:
                    pass  # Not all products may exist

    # Check that all four inputs exist
    missing = []
    for label, path in [
        ("C-band velocity", c_vel_path),
        ("C-band coherence", c_coh_path),
        ("L-band velocity", l_vel_path),
        ("L-band coherence", l_coh_path),
    ]:
        if not path.exists():
            missing.append(label)

    if missing:
        logger.info(
            "Fusion skipped: missing inputs: %s. "
            "Run the pipeline for both sentinel1 and nisar sensors to generate all products.",
            ", ".join(missing),
        )
        return {}

    # Generate fusion products
    fusion_cfg = config.fusion
    fusion_products = generate_fusion_products(
        c_vel_path=c_vel_path,
        c_coh_path=c_coh_path,
        l_vel_path=l_vel_path,
        l_coh_path=l_coh_path,
        output_dir=output_dir,
        nodata=config.export.nodata,
        min_coherence=fusion_cfg.min_coherence,
        c_band_weight_boost=fusion_cfg.c_band_weight_boost,
    )

    # Re-run subsidence classification on the fused velocity
    fused_vel_path = fusion_products.get("fused_velocity")
    if fused_vel_path and fused_vel_path.exists():
        from peatguard.analysis.subsidence_class import classify_subsidence_file

        fused_class_path = output_dir / "fused_subsidence_class.tif"
        water_mask_path = existing_products.get("water_mask")
        classify_subsidence_file(
            fused_vel_path,
            fused_class_path,
            config.classification,
            water_mask_path=water_mask_path,
        )
        fusion_products["fused_subsidence_class"] = fused_class_path
        logger.info("Fused subsidence classification: %s", fused_class_path)

        # Re-run risk scoring on fused velocity if canal distance is available
        canal_dist_path = existing_products.get("canal_distance")
        if canal_dist_path and canal_dist_path.exists():
            from peatguard.analysis.risk_score import generate_risk_map

            fused_risk_path = output_dir / "fused_canal_risk.tif"
            risk_cfg = config.risk_score
            generate_risk_map(
                fused_vel_path,
                canal_dist_path,
                fused_risk_path,
                proximity_weight=risk_cfg.proximity_weight,
                subsidence_weight=risk_cfg.subsidence_weight,
                max_influence_m=risk_cfg.max_influence_m,
                severe_velocity_mm_yr=risk_cfg.severe_velocity_mm_yr,
                water_mask_path=water_mask_path,
            )
            fusion_products["fused_canal_risk"] = fused_risk_path
            logger.info("Fused risk score: %s", fused_risk_path)
        else:
            logger.info("Canal distance not available, skipping fused risk scoring")

    logger.info("Fusion produced %d products", len(fusion_products))
    return fusion_products


def generate_quality_report(
    products: dict[str, Path],
    config: PeatGuardConfig,
    output_dir: Path,
) -> Path:
    """Generate a JSON quality report summarizing pipeline output metrics.

    Reads each raster product one at a time, computes summary statistics,
    then releases the array before loading the next product. This keeps
    memory usage flat on Cloud Run.

    The report is designed for stakeholder communication and Verra
    carbon-credit audit trails.

    Args:
        products: Dict mapping product names to output file paths.
        config: Pipeline configuration.
        output_dir: Directory to write pipeline_report.json.

    Returns:
        Path to the written pipeline_report.json.
    """
    import json
    from datetime import datetime, timezone

    import numpy as np
    from peatguard.export.cog import read_raster

    report: dict = {
        "pipeline_version": "v32",
        "sensor": config.sensor,
        "aoi_bbox": config.aoi.bbox,
        "target_epsg": config.aoi.epsg,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # -- Pipeline metadata --
    report["pipeline_metadata"] = {
        "reference_point_lalo": config.mintpy.reference_lalo,
        "tropospheric_correction": config.mintpy.tropospheric_correction,
        "coherence_threshold": config.processing.coherence_threshold,
        "fusion_enabled": config.fusion.enabled,
        "water_mask_enabled": config.water_mask.enabled,
        "peat_mask_enabled": config.peat_mask.enabled,
        "risk_weights": {
            "proximity": config.risk_score.proximity_weight,
            "subsidence": config.risk_score.subsidence_weight,
        },
        "max_influence_m": config.risk_score.max_influence_m,
        "severe_velocity_mm_yr": config.risk_score.severe_velocity_mm_yr,
    }

    # -- Velocity statistics --
    vel_path = products.get("subsidence_velocity_utm") or products.get("subsidence_velocity")
    if vel_path and vel_path.exists():
        try:
            vel_data, vel_meta = read_raster(vel_path)
            velocity = vel_data[0]
            nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0
            valid = (velocity != nodata) & np.isfinite(velocity)
            valid_pixels = velocity[valid]
            report["velocity_stats"] = {
                "mean_mm_yr": round(float(np.mean(valid_pixels)), 2),
                "median_mm_yr": round(float(np.median(valid_pixels)), 2),
                "std_mm_yr": round(float(np.std(valid_pixels)), 2),
                "min_mm_yr": round(float(np.min(valid_pixels)), 2),
                "max_mm_yr": round(float(np.max(valid_pixels)), 2),
                "valid_pixel_count": int(valid_pixels.size),
                "total_pixels": int(velocity.size),
            }
            logger.info(
                "Quality report: velocity mean=%.2f mm/yr, %d valid pixels",
                report["velocity_stats"]["mean_mm_yr"],
                report["velocity_stats"]["valid_pixel_count"],
            )
            del vel_data, velocity, valid_pixels, valid
        except Exception as exc:
            logger.warning("Quality report: failed to read velocity product: %s", exc)
    else:
        logger.info("Quality report: velocity product not found, skipping velocity stats")

    # -- Coherence statistics --
    coh_path = output_dir / "coherence_median.tif"
    if coh_path.exists():
        try:
            coh_data, coh_meta = read_raster(coh_path)
            coherence = coh_data[0]
            nodata = coh_meta["nodata"] if coh_meta["nodata"] is not None else -9999.0
            valid = (coherence != nodata) & np.isfinite(coherence)
            valid_coh = coherence[valid]
            n_valid = int(valid_coh.size)
            report["coherence_stats"] = {
                "mean": round(float(np.mean(valid_coh)), 4),
                "median": round(float(np.median(valid_coh)), 4),
                "pixels_above_0.5": int(np.sum(valid_coh > 0.5)),
                "fraction_above_0.5": round(float(np.sum(valid_coh > 0.5)) / max(1, n_valid), 4),
                "pixels_above_0.7": int(np.sum(valid_coh > 0.7)),
                "fraction_above_0.7": round(float(np.sum(valid_coh > 0.7)) / max(1, n_valid), 4),
                "valid_pixel_count": n_valid,
            }
            logger.info(
                "Quality report: coherence mean=%.3f, %.1f%% above 0.5",
                report["coherence_stats"]["mean"],
                report["coherence_stats"]["fraction_above_0.5"] * 100,
            )
            del coh_data, coherence, valid_coh, valid
        except Exception as exc:
            logger.warning("Quality report: failed to read coherence product: %s", exc)
    else:
        logger.info("Quality report: coherence product not found, skipping coherence stats")

    # -- Canal mask statistics --
    canal_path = products.get("canal_mask")
    if canal_path and canal_path.exists():
        try:
            canal_data, canal_meta = read_raster(canal_path)
            canal = canal_data[0]
            total_pixels = int(canal.size)
            canal_pixels = int(np.sum(canal == 1))
            report["canal_stats"] = {
                "total_canal_pixels": canal_pixels,
                "total_pixels": total_pixels,
                "canal_coverage_pct": round(canal_pixels / max(1, total_pixels) * 100, 3),
            }
            logger.info(
                "Quality report: %d canal pixels (%.2f%% coverage)",
                canal_pixels,
                report["canal_stats"]["canal_coverage_pct"],
            )
            del canal_data, canal
        except Exception as exc:
            logger.warning("Quality report: failed to read canal mask: %s", exc)
    else:
        logger.info("Quality report: canal mask not found, skipping canal stats")

    # -- Classification distribution --
    class_path = products.get("subsidence_class")
    if class_path and class_path.exists():
        try:
            from peatguard.analysis.subsidence_class import CLASS_LABELS

            class_data, _ = read_raster(class_path)
            classified = class_data[0]
            distribution = {}
            for code, label in CLASS_LABELS.items():
                count = int(np.sum(classified == code))
                if count > 0:
                    distribution[label] = count
            report["classification_distribution"] = distribution
            logger.info(
                "Quality report: classification has %d classes with data",
                len(distribution),
            )
            del class_data, classified
        except Exception as exc:
            logger.warning("Quality report: failed to read classification: %s", exc)
    else:
        logger.info("Quality report: classification product not found, skipping")

    # -- Risk score distribution --
    risk_path = products.get("canal_risk")
    if risk_path and risk_path.exists():
        try:
            risk_data, risk_meta = read_raster(risk_path)
            risk = risk_data[0]
            nodata = risk_meta["nodata"] if risk_meta["nodata"] is not None else -9999.0
            valid = (risk != nodata) & np.isfinite(risk)
            valid_risk = risk[valid]
            n_valid = int(valid_risk.size)
            if n_valid > 0:
                # Risk categories: 0-0.2 low, 0.2-0.4 moderate, 0.4-0.6 elevated,
                # 0.6-0.8 high, 0.8-1.0 critical
                low = int(np.sum(valid_risk < 0.2))
                moderate = int(np.sum((valid_risk >= 0.2) & (valid_risk < 0.4)))
                elevated = int(np.sum((valid_risk >= 0.4) & (valid_risk < 0.6)))
                high = int(np.sum((valid_risk >= 0.6) & (valid_risk < 0.8)))
                critical = int(np.sum(valid_risk >= 0.8))
                report["risk_distribution"] = {
                    "mean_risk": round(float(np.mean(valid_risk)), 4),
                    "low_fraction": round(low / n_valid, 4),
                    "moderate_fraction": round(moderate / n_valid, 4),
                    "elevated_fraction": round(elevated / n_valid, 4),
                    "high_fraction": round(high / n_valid, 4),
                    "critical_fraction": round(critical / n_valid, 4),
                    "valid_pixel_count": n_valid,
                }
                logger.info(
                    "Quality report: mean risk=%.3f, %.1f%% critical",
                    report["risk_distribution"]["mean_risk"],
                    report["risk_distribution"]["critical_fraction"] * 100,
                )
            del risk_data, risk, valid_risk, valid
        except Exception as exc:
            logger.warning("Quality report: failed to read risk score: %s", exc)
    else:
        logger.info("Quality report: risk score product not found, skipping")

    # -- Error budget (static, based on processing configuration) --
    atmo_note = "ERA5-corrected (PyAPS)" if config.mintpy.tropospheric_correction == "pyaps" else "uncorrected"
    report["error_budget"] = {
        "atmospheric": f"5-15 mm/yr ({atmo_note})",
        "unwrapping_errors": config.mintpy.unwrap_error_correction,
        "reference_point": (
            f"Fixed at {config.mintpy.reference_lalo}"
            if config.mintpy.reference_lalo
            else "MintPy auto-selected"
        ),
        "coherence_threshold": config.processing.coherence_threshold,
    }

    # -- Data quality summary --
    data_quality: dict = {}
    if "velocity_stats" in report:
        data_quality["valid_pixel_fraction"] = round(
            report["velocity_stats"]["valid_pixel_count"]
            / max(1, report["velocity_stats"]["total_pixels"]),
            4,
        )
    if "coherence_stats" in report:
        data_quality["mean_coherence"] = report["coherence_stats"]["mean"]
        data_quality["high_coherence_fraction"] = report["coherence_stats"]["fraction_above_0.7"]
    if data_quality:
        report["data_quality"] = data_quality

    # -- Product inventory --
    report["products"] = {
        name: str(path.name)
        for name, path in sorted(products.items())
        if path.exists()
    }
    report["product_count"] = len(report["products"])

    # Write the report
    report_path = output_dir / "pipeline_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Pipeline quality report written to %s", report_path)
    return report_path


def run_analysis_stage(
    config: PeatGuardConfig,
    velocity_path: Path,
    vv_path: Optional[Path] = None,
) -> dict[str, Path]:
    """Stage 5: Analysis and product generation.

    Canal detection and risk scoring require VV backscatter and are
    skipped if vv_path is not provided. Subsidence classification
    always runs. Water mask generation runs when VV backscatter is
    available and water_mask.enabled is True in config.

    Args:
        config: Pipeline configuration.
        velocity_path: Path to subsidence velocity GeoTIFF.
        vv_path: Path to VV backscatter composite (optional).

    Returns:
        Dict mapping product names to output paths.
    """
    import numpy as np
    from peatguard.analysis.subsidence_class import classify_subsidence_file
    from peatguard.export.cog import read_raster, write_cog

    logger.info("=== Stage 5: Analysis ===")

    output_dir = config.storage.output_dir
    products = {}
    water_mask_path = None

    # Canal detection + water mask + risk scoring (requires VV backscatter)
    if vv_path and vv_path.exists():
        from peatguard.analysis.canal_detect import detect_canals
        from peatguard.analysis.risk_score import generate_risk_map

        canal_mask_path = output_dir / "canal_mask.tif"
        canal_dist_path = output_dir / "canal_distance.tif"
        detect_canals(vv_path, canal_mask_path, canal_dist_path)
        products["canal_mask"] = canal_mask_path
        products["canal_distance"] = canal_dist_path

        # Water mask generation (uses VV backscatter, excludes canal pixels).
        # Prefer the dB product for water masking -- thresholding in dB space
        # is more intuitive and avoids precision issues at the low end of
        # linear scale (water: -18 dB = 0.016 linear, easily missed).
        if config.water_mask.enabled:
            from peatguard.analysis.water_mask import generate_water_mask

            water_mask_path = output_dir / "water_mask.tif"
            canal_for_exclusion = canal_mask_path if config.water_mask.exclude_canals else None

            # Try to find or download the dB product for water masking.
            # The dB scale gives more intuitive thresholding than linear.
            vv_db_path = output_dir / "vv_median_db.tif"
            if not vv_db_path.exists() and config.storage.gcs_bucket:
                try:
                    from peatguard.export.gcs import download_file
                    download_file(
                        config.storage.gcs_bucket,
                        "products/vv_median_db.tif",
                        vv_db_path,
                    )
                    logger.info("Downloaded dB product from GCS: %s", vv_db_path)
                except Exception:
                    logger.debug("Could not download dB product from GCS")

            if vv_db_path.exists():
                water_vv_path = vv_db_path
                water_is_db = True
                logger.info("Using dB product for water masking: %s", vv_db_path)
            else:
                water_vv_path = vv_path
                water_is_db = False
                logger.info("dB product not available, using linear VV for water masking")

            generate_water_mask(
                water_vv_path,
                water_mask_path,
                canal_mask_path=canal_for_exclusion,
                water_config=config.water_mask,
                is_db=water_is_db,
            )
            products["water_mask"] = water_mask_path
            logger.info("Water mask generated: %s", water_mask_path)
        else:
            logger.info("Water mask disabled in config, skipping")

    # Subsidence classification (always runs, uses water mask if available)
    class_path = output_dir / "subsidence_class.tif"
    classify_subsidence_file(
        velocity_path, class_path, config.classification,
        water_mask_path=water_mask_path,
    )
    products["subsidence_class"] = class_path

    # Peat extent mapping: download peat polygons, rasterize, classify depth,
    # and create peat-masked subsidence product.
    peat_binary_path = None
    if config.peat_mask.enabled:
        try:
            from peatguard.analysis.peat_mask import generate_peat_products

            peat_products = generate_peat_products(
                bbox=config.aoi.bbox,
                reference_raster_path=velocity_path,
                velocity_path=velocity_path,
                output_dir=output_dir,
                shallow_edge_m=config.peat_mask.shallow_edge_m,
                moderate_edge_m=config.peat_mask.moderate_edge_m,
            )
            products.update(peat_products)
            peat_binary_path = peat_products.get("peat_extent_binary")
            logger.info("Peat mapping complete: %d products", len(peat_products))
        except Exception as exc:
            logger.warning("Peat mapping failed (non-fatal): %s", exc)
    else:
        logger.info("Peat mask disabled in config, skipping")

    # Forest change analysis: download Hansen GFC data for temporal context.
    # Clearing year directly relates to subsidence rate (Hooijer et al. 2012).
    clearing_risk_factor_path = None
    if config.forest_change.enabled:
        try:
            from peatguard.analysis.forest_change import (
                generate_forest_change_products,
                validate_subsidence_vs_clearing,
            )

            fc_products = generate_forest_change_products(
                bbox=config.aoi.bbox,
                reference_raster_path=velocity_path,
                output_dir=output_dir,
                reference_year=config.forest_change.reference_year,
                hansen_version=config.forest_change.hansen_version,
            )
            products.update(fc_products)
            clearing_risk_factor_path = fc_products.get("clearing_risk_factor")
            logger.info("Forest change analysis complete: %d products", len(fc_products))
        except Exception as exc:
            logger.warning("Forest change analysis failed (non-fatal): %s", exc)
    else:
        logger.info("Forest change analysis disabled in config, skipping")

    # Degraded peatland layer: binary mask where subsidence exceeds -10 mm/yr.
    # Now restricted to peat areas only -- shows WHERE peat degradation is occurring.
    degraded_path = output_dir / "degraded_peatland.tif"
    vel_data, vel_meta = read_raster(velocity_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0
    valid = (velocity != vel_nodata) & np.isfinite(velocity)
    degraded = (valid & (velocity < -10.0)).astype(np.uint8)
    # Exclude water pixels
    if water_mask_path and water_mask_path.exists():
        wm_data, _ = read_raster(water_mask_path)
        water = wm_data[0].astype(bool)
        if water.shape == degraded.shape:
            degraded[water] = 0
    # Restrict to peat areas only: degradation outside peatland is not the target
    if peat_binary_path and peat_binary_path.exists():
        peat_data, peat_meta = read_raster(peat_binary_path)
        peat = peat_data[0]
        if peat.shape == degraded.shape:
            n_before = degraded.sum()
            degraded[peat == 0] = 0
            n_after = degraded.sum()
            logger.info(
                "Peat mask applied to degraded layer: %d -> %d pixels "
                "(removed %d non-peat degradation pixels)",
                n_before, n_after, n_before - n_after,
            )
        else:
            logger.warning(
                "Peat mask shape %s != degraded shape %s, skipping peat restriction",
                peat.shape, degraded.shape,
            )
    write_cog(
        data=degraded,
        output_path=degraded_path,
        crs=vel_meta["crs"],
        transform=vel_meta["transform"],
        nodata=255,
        band_names=["degraded_peatland"],
        dtype="uint8",
    )
    products["degraded_peatland"] = degraded_path
    n_degraded = degraded.sum()
    n_valid = valid.sum()
    logger.info(
        "Degraded peatland: %d/%d pixels (%.1f%%) with velocity < -10 mm/yr on peat",
        n_degraded, n_valid, n_degraded / max(1, n_valid) * 100,
    )

    # Risk scoring and CRS alignment (requires VV backscatter products)
    if vv_path and vv_path.exists():
        # Reproject velocity to match backscatter/canal grid (UTM).
        # This ensures all products share the same CRS, extent, and pixel grid.
        import rasterio
        from rasterio.warp import reproject, Resampling
        vel_ds = rasterio.open(velocity_path)
        dist_ds = rasterio.open(canal_dist_path)
        try:
            if vel_ds.crs != dist_ds.crs or vel_ds.shape != dist_ds.shape:
                logger.warning(
                    "CRS mismatch in analysis stage: velocity %s != backscatter %s. "
                    "This should not be needed if velocity export uses output_crs. "
                    "Reprojecting to %s (%dx%d)",
                    vel_ds.crs, dist_ds.crs, dist_ds.crs, dist_ds.width, dist_ds.height,
                )
                aligned_vel_path = output_dir / "subsidence_velocity_utm.tif"
                aligned_class_path = output_dir / "subsidence_class_utm.tif"

                # Reproject velocity to backscatter grid
                with rasterio.open(
                    aligned_vel_path, "w", driver="GTiff",
                    height=dist_ds.height, width=dist_ds.width,
                    count=1, dtype="float32",
                    crs=dist_ds.crs, transform=dist_ds.transform,
                    nodata=-9999.0,
                ) as dst:
                    reproject(
                        source=rasterio.band(vel_ds, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=vel_ds.transform,
                        src_crs=vel_ds.crs,
                        dst_transform=dist_ds.transform,
                        dst_crs=dist_ds.crs,
                        resampling=Resampling.bilinear,
                    )

                # Also reproject classification to same grid
                with rasterio.open(class_path) as class_ds:
                    with rasterio.open(
                        aligned_class_path, "w", driver="GTiff",
                        height=dist_ds.height, width=dist_ds.width,
                        count=1, dtype="uint8",
                        crs=dist_ds.crs, transform=dist_ds.transform,
                        nodata=0,
                    ) as dst:
                        reproject(
                            source=rasterio.band(class_ds, 1),
                            destination=rasterio.band(dst, 1),
                            src_transform=class_ds.transform,
                            src_crs=class_ds.crs,
                            dst_transform=dist_ds.transform,
                            dst_crs=dist_ds.crs,
                            resampling=Resampling.nearest,
                        )
                products["subsidence_class"] = aligned_class_path

                vel_for_risk = aligned_vel_path
                products["subsidence_velocity_utm"] = aligned_vel_path
            else:
                vel_for_risk = velocity_path
        finally:
            dist_ds.close()
            vel_ds.close()

        risk_path = output_dir / "canal_risk.tif"
        risk_cfg = config.risk_score
        generate_risk_map(
            vel_for_risk, canal_dist_path, risk_path,
            proximity_weight=risk_cfg.proximity_weight,
            subsidence_weight=risk_cfg.subsidence_weight,
            max_influence_m=risk_cfg.max_influence_m,
            severe_velocity_mm_yr=risk_cfg.severe_velocity_mm_yr,
            water_mask_path=water_mask_path,
        )
        products["canal_risk"] = risk_path

        # Apply peat depth weighting to risk score: deeper peat = higher priority.
        # Produces a peat-focused risk map where non-peat areas are excluded.
        peat_depth_path = products.get("peat_extent")
        if peat_depth_path and peat_depth_path.exists():
            try:
                from peatguard.analysis.peat_mask import compute_peat_risk_weight

                risk_data, risk_meta = read_raster(risk_path)
                risk_arr = risk_data[0]
                peat_weights = compute_peat_risk_weight(peat_depth_path)

                # Handle shape mismatch
                if peat_weights.shape != risk_arr.shape:
                    from rasterio.warp import Resampling, reproject
                    peat_d, peat_m = read_raster(peat_depth_path)
                    pw_reproj = np.zeros(risk_arr.shape, dtype=np.float32)
                    reproject(
                        source=peat_weights,
                        destination=pw_reproj,
                        src_transform=peat_m["transform"],
                        src_crs=peat_m["crs"],
                        dst_transform=risk_meta["transform"],
                        dst_crs=risk_meta["crs"],
                        resampling=Resampling.nearest,
                    )
                    peat_weights = pw_reproj

                peat_risk = risk_arr * peat_weights
                peat_risk[risk_arr == -9999.0] = -9999.0
                peat_risk[peat_weights == 0.0] = -9999.0

                peat_risk_path = output_dir / "peat_risk.tif"
                write_cog(
                    data=peat_risk,
                    output_path=peat_risk_path,
                    crs=risk_meta["crs"],
                    transform=risk_meta["transform"],
                    nodata=-9999.0,
                    band_names=["peat_weighted_risk"],
                    dtype="float32",
                )
                products["peat_risk"] = peat_risk_path

                valid_peat_risk = peat_risk[peat_risk != -9999.0]
                if valid_peat_risk.size > 0:
                    logger.info(
                        "Peat-weighted risk: min=%.3f, max=%.3f, mean=%.3f",
                        valid_peat_risk.min(),
                        valid_peat_risk.max(),
                        valid_peat_risk.mean(),
                    )
            except Exception as exc:
                logger.warning("Peat risk weighting failed (non-fatal): %s", exc)

        # Time-adjusted risk: multiply canal risk by clearing risk factor.
        # Areas cleared recently get a higher multiplier (Hooijer et al. 2012).
        if clearing_risk_factor_path and clearing_risk_factor_path.exists():
            try:
                risk_data, risk_meta = read_raster(risk_path)
                risk_arr = risk_data[0]
                crf_data, crf_meta = read_raster(clearing_risk_factor_path)
                crf_arr = crf_data[0]

                # Handle shape mismatch
                if crf_arr.shape != risk_arr.shape:
                    from rasterio.warp import Resampling, reproject
                    crf_reproj = np.zeros(risk_arr.shape, dtype=np.float32)
                    reproject(
                        source=crf_arr,
                        destination=crf_reproj,
                        src_transform=crf_meta["transform"],
                        src_crs=crf_meta["crs"],
                        dst_transform=risk_meta["transform"],
                        dst_crs=risk_meta["crs"],
                        resampling=Resampling.nearest,
                    )
                    crf_arr = crf_reproj

                time_adjusted = risk_arr * crf_arr
                time_adjusted[risk_arr == -9999.0] = -9999.0
                time_adjusted[crf_arr == -9999.0] = -9999.0
                # Clip to [0, 1] range after multiplication
                valid_ta = (time_adjusted != -9999.0)
                time_adjusted[valid_ta] = np.clip(time_adjusted[valid_ta], 0.0, 1.0)

                ta_risk_path = output_dir / "time_adjusted_risk.tif"
                write_cog(
                    data=time_adjusted,
                    output_path=ta_risk_path,
                    crs=risk_meta["crs"],
                    transform=risk_meta["transform"],
                    nodata=-9999.0,
                    band_names=["time_adjusted_risk"],
                    dtype="float32",
                )
                products["time_adjusted_risk"] = ta_risk_path

                valid_mask = time_adjusted != -9999.0
                if valid_mask.any():
                    logger.info(
                        "Time-adjusted risk: min=%.3f, max=%.3f, mean=%.3f",
                        time_adjusted[valid_mask].min(),
                        time_adjusted[valid_mask].max(),
                        time_adjusted[valid_mask].mean(),
                    )
            except Exception as exc:
                logger.warning("Time-adjusted risk failed (non-fatal): %s", exc)
    else:
        logger.info("VV backscatter not available, skipping canal detection and risk scoring")

    # Carbon loss estimation: convert vertical subsidence rate to CO2 emission rate.
    # Uses Hooijer et al. (2012) empirical factor: 1 mm/yr subsidence ~ 0.5 tCO2/ha/yr
    # for tropical peat (conservative; some studies report 0.7-1.0).
    # Masked to peat areas only via peat_extent_binary.
    HOOIJER_CO2_FACTOR = 0.5  # tCO2/ha/yr per mm/yr subsidence
    carbon_loss_path = output_dir / "carbon_loss.tif"
    try:
        vel_data_cl, vel_meta_cl = read_raster(velocity_path)
        vel_arr = vel_data_cl[0]
        vel_nodata = vel_meta_cl["nodata"] if vel_meta_cl["nodata"] is not None else -9999.0
        valid_vel = (vel_arr != vel_nodata) & np.isfinite(vel_arr)

        # Apply coherence filter: exclude low-coherence pixels (river banks,
        # water edges) that produce extreme velocity artifacts.
        coherence_path = output_dir / "coherence_median.tif"
        if not coherence_path.exists():
            coherence_path = output_dir / "coherence_median_utm.tif"
        if coherence_path.exists():
            coh_data, _ = read_raster(coherence_path)
            coh_arr = coh_data[0]
            if coh_arr.shape == vel_arr.shape:
                low_coh = coh_arr < 0.7
                valid_vel = valid_vel & ~low_coh
                logger.info(
                    "Carbon loss: filtered %d low-coherence pixels (<0.7)",
                    int(low_coh.sum()),
                )
                del low_coh
            del coh_data, coh_arr

        # Smooth velocity with median filter to reduce noise.
        # Fill nodata with global median (not 0) to avoid edge bias at
        # valid/nodata boundaries.
        from scipy.ndimage import median_filter
        vel_smooth = vel_arr.copy()
        global_median = float(np.median(vel_arr[valid_vel])) if np.any(valid_vel) else 0.0
        vel_smooth[~valid_vel] = global_median
        vel_smooth = median_filter(vel_smooth, size=9).astype(np.float32)
        vel_smooth[~valid_vel] = vel_nodata

        # Carbon loss = |negative velocity| * factor (only subsidence, not uplift)
        carbon_loss = np.full_like(vel_arr, -9999.0, dtype=np.float32)
        subsiding = valid_vel & (vel_smooth < 0)
        carbon_loss[subsiding] = np.abs(vel_smooth[subsiding]) * HOOIJER_CO2_FACTOR
        carbon_loss[valid_vel & ~subsiding] = 0.0
        del vel_smooth

        # Exclude water pixels and buffer water bodies by ~100m to remove
        # unreliable velocity near water/land boundaries where coherence degrades.
        water_path = products.get("water_mask")
        if water_path and water_path.exists():
            wm_data, _ = read_raster(water_path)
            wm_arr = wm_data[0].astype(bool)
            if wm_arr.shape == carbon_loss.shape:
                # Buffer water bodies by ~100m. At ~40m pixel resolution
                # (EPSG:4326 carbon loss grid), 100m is ~2.5 pixels; use disk(3).
                from scipy.ndimage import binary_dilation
                from skimage.morphology import disk
                water_buffered = binary_dilation(wm_arr, structure=disk(3).astype(bool))
                carbon_loss[water_buffered] = -9999.0
                del water_buffered
            else:
                # Shape mismatch (e.g. UTM water mask vs EPSG:4326 carbon loss);
                # cannot apply buffer or mask without reprojection.
                logger.info(
                    "Water mask shape %s differs from carbon loss %s; "
                    "skipping water exclusion for carbon loss",
                    wm_arr.shape, carbon_loss.shape,
                )
            del wm_data, wm_arr

        write_cog(
            data=carbon_loss,
            output_path=carbon_loss_path,
            crs=vel_meta_cl["crs"],
            transform=vel_meta_cl["transform"],
            nodata=-9999.0,
            band_names=["carbon_loss_tCO2_ha_yr"],
            dtype="float32",
        )
        products["carbon_loss"] = carbon_loss_path

        valid_cl = carbon_loss[carbon_loss != -9999.0]
        if valid_cl.size > 0:
            pixel_x = abs(vel_meta_cl["transform"][0])
            pixel_y = abs(vel_meta_cl["transform"][4])
            crs = vel_meta_cl.get("crs")
            if crs and str(crs).startswith("EPSG:326"):
                # UTM: transform is already in meters
                pixel_area_m2 = pixel_x * pixel_y
            else:
                # Geographic: convert degrees to meters
                pixel_area_m2 = (pixel_x * 111320) * (pixel_y * 111320)
            total_area_ha = valid_cl.size * pixel_area_m2 / 10000
            total_emission = float(np.mean(valid_cl)) * total_area_ha
            logger.info(
                "Carbon loss: mean=%.1f tCO2/ha/yr, total=%.0f tCO2/yr over %.0f ha peat",
                np.mean(valid_cl), total_emission, total_area_ha,
            )
        del vel_data_cl, vel_arr, carbon_loss, valid_cl
    except Exception as exc:
        logger.warning("Carbon loss estimation failed (non-fatal): %s", exc)

    # Multi-sensor fusion: combine C-band and L-band velocity if both available
    if config.fusion.enabled:
        fusion_products = _run_fusion(config, output_dir, products)
        products.update(fusion_products)

    # Cross-validation: correlate velocity with independent datasets
    if config.validation.enabled:
        try:
            from peatguard.analysis.validation import run_validation

            # Use the UTM velocity if available (matches backscatter grid),
            # otherwise fall back to the original velocity path.
            val_velocity = products.get("subsidence_velocity_utm", velocity_path)

            # Locate coherence product (produced by timeseries stage)
            coherence_path = output_dir / "coherence_median.tif"

            # bbox is used for both NDVI download and OSM canal validation.
            # Always pass it so OSM validation can run even if NDVI download
            # is disabled (run_validation gates NDVI via attempt_ndvi_download).
            validation_report = run_validation(
                velocity_path=val_velocity,
                output_dir=output_dir,
                vv_path=vv_path,
                coherence_path=coherence_path if coherence_path.exists() else None,
                canal_distance_path=products.get("canal_distance"),
                canal_mask_path=products.get("canal_mask"),
                bbox=config.aoi.bbox,
                attempt_ndvi_download=config.validation.attempt_ndvi_download,
            )

            # Track validation outputs for GCS upload
            validation_dir = output_dir / "validation"
            report_path = validation_dir / "validation_report.json"
            if report_path.exists():
                products["validation_report"] = report_path
            ndvi_composite = validation_dir / "validation_ndvi_composite.tif"
            if ndvi_composite.exists():
                products["validation_ndvi_composite"] = ndvi_composite
            osm_waterways = validation_dir / "osm_waterways.tif"
            if osm_waterways.exists():
                products["osm_waterways"] = osm_waterways
            osm_metrics = validation_dir / "validation_osm.json"
            if osm_metrics.exists():
                products["validation_osm"] = osm_metrics

            n_correlations = len(validation_report.get("correlations", {}))
            logger.info("Cross-validation complete: %d correlations computed", n_correlations)

        except Exception as exc:
            logger.warning("Cross-validation failed (non-fatal): %s", exc)
    else:
        logger.info("Cross-validation disabled in config, skipping")

    # Forest change validation: compare subsidence rates across clearing cohorts
    if config.forest_change.enabled and clearing_risk_factor_path is not None:
        try:
            from peatguard.analysis.forest_change import validate_subsidence_vs_clearing

            deforestation_year_path = products.get("deforestation_year")
            if deforestation_year_path and deforestation_year_path.exists():
                val_velocity = products.get("subsidence_velocity_utm", velocity_path)
                fc_validation = validate_subsidence_vs_clearing(
                    velocity_path=val_velocity,
                    lossyear_path=deforestation_year_path,
                    output_dir=output_dir,
                )
                fc_report_path = output_dir / "validation_clearing.json"
                if fc_report_path.exists():
                    products["validation_clearing"] = fc_report_path
                logger.info(
                    "Forest change validation: %s",
                    fc_validation.get("assessment", "unknown"),
                )
        except Exception as exc:
            logger.warning("Forest change validation failed (non-fatal): %s", exc)

    # Generate pipeline quality report for stakeholder communication and audits
    try:
        report_path = generate_quality_report(products, config, output_dir)
        products["pipeline_report"] = report_path
    except Exception as exc:
        logger.warning("Quality report generation failed (non-fatal): %s", exc)

    # Upload products to GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import upload_file
        for name, path in products.items():
            if path.suffix == ".json":
                blob_name = f"products/{path.name}"
                content_type = "application/json"
            else:
                blob_name = f"products/{path.name}"
                content_type = None
            try:
                upload_file(path, config.storage.gcs_bucket, blob_name, content_type=content_type)
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
