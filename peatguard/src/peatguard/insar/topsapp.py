"""ISCE2 topsApp wrapper for Sentinel-1 TOPS InSAR processing.

Wraps ISCE2's topsApp.py to handle the complete Sentinel-1 TOPS
InSAR workflow: split, orbit correction, coregistration, interferogram
generation, and debursting. This replaces 6+ separate SNAP GPT calls
and XML graph files with a single configured ISCE2 run.

ISCE2 topsApp expects an XML configuration file specifying the
reference and secondary SLC paths, DEM, and processing parameters.
This module generates that configuration and manages the run.
"""

from __future__ import annotations

import logging
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Optional

from peatguard.config import PeatGuardConfig

logger = logging.getLogger(__name__)


def _download_dem(bbox: list[float], dem_dir: Path) -> Path:
    """Download and prepare a DEM for ISCE2 processing.

    Downloads Copernicus GLO-30 DEM tiles from AWS open data (no auth
    required) using rasterio, then converts to ISCE2's native binary
    format with XML sidecar.

    Args:
        bbox: [west, south, east, north] in decimal degrees.
        dem_dir: Directory to store the DEM files.

    Returns:
        Path to the DEM file (dem.wgs84).
    """
    import math

    import numpy as np
    import rasterio
    from rasterio.merge import merge

    west, south, east, north = bbox

    # Expand bbox by 0.15 degrees (~17km) for processing margin
    south_exp = south - 0.15
    north_exp = north + 0.15
    west_exp = west - 0.15
    east_exp = east + 0.15

    dem_wgs84 = dem_dir / "dem.wgs84"

    # Build tile list for Copernicus GLO-30 DEM on AWS (free, no auth)
    # Tile naming: Copernicus_DSM_COG_10_{N|S}{lat}_00_{E|W}{lon}_00_DEM
    # Each tile covers 1x1 degree. lat/lon refer to the SW corner.
    lat_min = math.floor(south_exp)
    lat_max = math.ceil(north_exp)
    lon_min = math.floor(west_exp)
    lon_max = math.ceil(east_exp)

    tile_urls = []
    for lat in range(lat_min, lat_max):
        for lon in range(lon_min, lon_max):
            lat_prefix = "N" if lat >= 0 else "S"
            lon_prefix = "E" if lon >= 0 else "W"
            tile_name = (
                f"Copernicus_DSM_COG_10_{lat_prefix}{abs(lat):02d}_00_"
                f"{lon_prefix}{abs(lon):03d}_00_DEM"
            )
            tile_url = (
                f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/"
                f"{tile_name}/{tile_name}.tif"
            )
            tile_urls.append(tile_url)

    logger.info(
        "Downloading Copernicus GLO-30 DEM (%d tiles) for bbox "
        "[%.3f, %.3f, %.3f, %.3f]",
        len(tile_urls), west_exp, south_exp, east_exp, north_exp,
    )

    datasets = []
    for url in tile_urls:
        try:
            ds = rasterio.open(url)
            datasets.append(ds)
            logger.debug("Opened DEM tile: %s", url)
        except Exception as exc:
            logger.warning("Could not open DEM tile: %s (%s)", url, exc)

    if not datasets:
        raise RuntimeError(
            f"No Copernicus DEM tiles found for bbox "
            f"[{west_exp}, {south_exp}, {east_exp}, {north_exp}]"
        )

    mosaic, out_transform = merge(
        datasets, bounds=(west_exp, south_exp, east_exp, north_exp)
    )
    for ds in datasets:
        ds.close()

    # ISCE2 expects the DEM as a flat binary file (BIL, int16, little-endian)
    # with an XML sidecar describing the geometry.
    dem_data = mosaic[0].astype(np.int16)
    height, width = dem_data.shape

    # Write binary
    dem_data.tofile(str(dem_wgs84))

    # Compute pixel spacing from the actual transform
    delta_lon = out_transform.a   # positive (east)
    delta_lat = out_transform.e   # negative (south)
    start_lon = out_transform.c   # west edge
    start_lat = out_transform.f   # north edge
    end_lon = start_lon + delta_lon * width
    end_lat = start_lat + delta_lat * height

    # ISCE2 XML sidecar
    xml_content = f"""<imageFile>
    <property name="DATA_TYPE">SHORT</property>
    <property name="BYTE_ORDER">l</property>
    <property name="FILE_NAME">{dem_wgs84}</property>
    <property name="IMAGE_TYPE">dem</property>
    <property name="LENGTH">{height}</property>
    <property name="NUMBER_BANDS">1</property>
    <property name="SCHEME">BIL</property>
    <property name="WIDTH">{width}</property>
    <component name="coordinate1">
        <property name="delta">{delta_lon}</property>
        <property name="endingValue">{end_lon}</property>
        <property name="size">{width}</property>
        <property name="startingValue">{start_lon}</property>
    </component>
    <component name="coordinate2">
        <property name="delta">{delta_lat}</property>
        <property name="endingValue">{end_lat}</property>
        <property name="size">{height}</property>
        <property name="startingValue">{start_lat}</property>
    </component>
</imageFile>"""
    xml_path = Path(str(dem_wgs84) + ".xml")
    xml_path.write_text(xml_content)

    logger.info("DEM prepared: %s (%d x %d pixels)", dem_wgs84, width, height)
    return dem_wgs84


# Template for ISCE2 topsApp XML configuration.
# The {dem_property} placeholder is filled conditionally -- when a DEM path
# is provided we emit the demFilename property; when omitted ISCE2 uses its
# internal DEM downloader which fetches SRTM tiles automatically.
_TOPSAPP_XML_TEMPLATE = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <topsApp>
        <component name="topsinsar">
            <property name="Sensor name">SENTINEL1</property>
            <component name="reference">
                <property name="safe">['{reference_safe}']</property>
                <property name="orbit directory">{orbit_dir}</property>
                <property name="output directory">{work_dir}/reference</property>
            </component>
            <component name="secondary">
                <property name="safe">['{secondary_safe}']</property>
                <property name="orbit directory">{orbit_dir}</property>
                <property name="output directory">{work_dir}/secondary</property>
            </component>
            <property name="swaths">[{swath_list}]</property>
            <property name="region of interest">[{roi_south}, {roi_north}, {roi_west}, {roi_east}]</property>
            {dem_property}
            <property name="do unwrap">{do_unwrap_str}</property>
            <property name="unwrapper name">snaphu_mcf</property>
            <property name="do ESD">True</property>
            <property name="azimuth looks">{az_looks}</property>
            <property name="range looks">{rg_looks}</property>
            <property name="filter strength">{filter_strength}</property>
            <property name="do ion">{do_ion_str}</property>
            <property name="geocode list">['merged/filt_topophase.unw',
                'merged/filt_topophase.unw.conncomp',
                'merged/phsig.cor',
                'merged/filt_topophase.flat',
                'merged/los.rdr',
                'merged/topophase.cor']</property>
            <property name="geocode bounding box">[{south}, {north}, {west}, {east}]</property>
        </component>
    </topsApp>
""")


def generate_topsapp_config(
    reference_safe: Path,
    secondary_safe: Path,
    work_dir: Path,
    config: PeatGuardConfig,
    orbit_dir: Optional[Path] = None,
    dem_path: Optional[Path] = None,
    az_looks: int = 3,
    rg_looks: int = 9,
) -> Path:
    """Generate an ISCE2 topsApp XML configuration file.

    Args:
        reference_safe: Path to the reference (master) SLC .SAFE or .zip.
        secondary_safe: Path to the secondary (slave) SLC .SAFE or .zip.
        work_dir: Working directory for ISCE2 outputs.
        config: Pipeline configuration.
        orbit_dir: Directory containing precise orbit files.
        dem_path: Path to the DEM file. Auto-downloaded if None.
        az_looks: Azimuth multilooking factor.
        rg_looks: Range multilooking factor.

    Returns:
        Path to the generated topsApp.xml file.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    if orbit_dir is None:
        orbit_dir = work_dir / "orbits"
        orbit_dir.mkdir(exist_ok=True)

    # Build DEM property conditionally. When a valid DEM path is provided
    # and the file + XML sidecar exist, include it in the config. Otherwise
    # omit it so ISCE2 auto-downloads SRTM via its internal demdb module.
    dem_property = ""
    if dem_path is not None and Path(str(dem_path) + ".xml").exists():
        dem_property = f'<property name="demFilename">{dem_path}</property>'
        logger.info("Using pre-downloaded DEM: %s", dem_path)
    else:
        logger.info("No DEM provided -- ISCE2 will auto-download SRTM tiles")

    west, south, east, north = config.aoi.bbox

    # Expand region of interest by 0.5 degrees to ensure ISCE2 captures
    # enough bursts per swath. Small AOIs cause runTopo to produce a 1D
    # bounding box array, triggering an IndexError. The geocode bounding
    # box still uses the tight AOI for final output clipping.
    roi_margin = 0.5
    roi_south = south - roi_margin
    roi_north = north + roi_margin
    roi_west = west - roi_margin
    roi_east = east + roi_margin

    # Use single subswath (IW2) to reduce memory usage significantly.
    # The AOI bounding box + ROI already limits which bursts are processed.
    # IW2 covers the Kapuas River area in West Kalimantan.
    # Config stores "IW2", ISCE2 expects integer 2.
    subswath_str = config.sentinel1.subswath  # e.g. "IW2"
    swath_num = int(subswath_str.replace("IW", ""))
    swath_list = str(swath_num)

    xml_content = _TOPSAPP_XML_TEMPLATE.format(
        reference_safe=str(reference_safe),
        secondary_safe=str(secondary_safe),
        orbit_dir=str(orbit_dir),
        work_dir=str(work_dir),
        dem_property=dem_property,
        do_unwrap_str="True",
        roi_south=roi_south,
        roi_north=roi_north,
        roi_west=roi_west,
        roi_east=roi_east,
        south=south,
        north=north,
        west=west,
        east=east,
        az_looks=az_looks,
        rg_looks=rg_looks,
        filter_strength=config.processing.goldstein_alpha,
        do_ion_str=str(config.processing.do_ion),
        swath_list=swath_list,
    )

    config_path = work_dir / "topsApp.xml"
    config_path.write_text(xml_content)
    logger.info("Generated topsApp config: %s", config_path)
    return config_path


def run_topsapp(
    work_dir: Path,
    steps: Optional[list[str]] = None,
    end_step: Optional[str] = None,
    start_step: Optional[str] = None,
) -> None:
    """Execute ISCE2 topsApp.py processing.

    Runs the configured topsApp workflow, optionally restricted to
    specific processing steps. Steps are executed in ISCE2's defined
    order: startup, preprocess, computeBaselines, verifyDEM,
    topo, subsetoverlaps, coarseoffsets, coarseresamp, overlapifg,
    prepesd, esd, rangecoreg, fineoffsets, fineresamp, ion,
    burstifg, mergebursts, filter, unwrap, unwrap2stage, geocode.

    Args:
        work_dir: Working directory containing topsApp.xml.
        steps: Specific steps to run. Runs all if None.
        end_step: Stop after this step.
        start_step: Start from this step.
    """
    import shutil

    # Locate the topsApp executable -- conda-forge installs it in the
    # conda bin directory, but the script name varies between installations.
    topsapp_bin = shutil.which("topsApp.py") or shutil.which("topsApp")
    if topsapp_bin:
        cmd = [topsapp_bin]
    else:
        # Fallback: invoke via Python module path
        cmd = ["python", "-m", "isce.applications.topsApp"]

    # ISCE2 topsApp uses --start=STEP and --end=STEP syntax (= required)
    if start_step:
        cmd.append(f"--start={start_step}")
    if end_step:
        cmd.append(f"--end={end_step}")

    logger.info("Running topsApp in %s (cmd: %s)", work_dir, cmd[0])
    if start_step or end_step:
        logger.info("  Steps: %s -> %s", start_step or "startup", end_step or "geocode")

    env = os.environ.copy()
    # ISCE2 needs these environment variables
    isce_home = os.environ.get("ISCE_HOME", "")
    if isce_home:
        env["PATH"] = f"{isce_home}/bin:{env.get('PATH', '')}"
    # Ensure PROJ can find its data files (critical in containers)
    if "PROJ_LIB" not in env:
        import sysconfig
        conda_prefix = os.environ.get("CONDA_PREFIX", "/opt/conda")
        env["PROJ_LIB"] = f"{conda_prefix}/share/proj"
        env["PROJ_DATA"] = env["PROJ_LIB"]

    result = subprocess.run(
        cmd,
        cwd=str(work_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    # Always log output for debugging
    if result.stdout:
        logger.info("topsApp STDOUT:\n%s", result.stdout[-3000:])
    if result.stderr:
        logger.info("topsApp STDERR:\n%s", result.stderr[-3000:])

    if result.returncode != 0:
        # Log the XML config for debugging
        xml_path = work_dir / "topsApp.xml"
        if xml_path.exists():
            logger.error("topsApp.xml contents:\n%s", xml_path.read_text())
        raise RuntimeError(f"topsApp.py failed with return code {result.returncode}")

    logger.info("topsApp completed successfully")


def process_pair(
    reference_safe: Path,
    secondary_safe: Path,
    work_dir: Path,
    config: PeatGuardConfig,
    orbit_dir: Optional[Path] = None,
    dem_path: Optional[Path] = None,
    do_unwrap: bool = True,
) -> Path:
    """Process a single interferometric pair end-to-end with ISCE2.

    This is the main entry point for single-pair InSAR processing.
    It generates the topsApp configuration and runs all steps from
    startup through unwrapping (SNAPHU). Geocoding is left to MintPy.

    Args:
        reference_safe: Path to reference SLC.
        secondary_safe: Path to secondary SLC.
        work_dir: Working directory for this pair.
        config: Pipeline configuration.
        orbit_dir: Directory with orbit files.
        dem_path: DEM file path.
        do_unwrap: Whether to run ISCE2's built-in unwrapping.

    Returns:
        Path to the work directory containing ISCE2 outputs.
    """
    logger.info(
        "Processing pair: %s -- %s",
        reference_safe.name,
        secondary_safe.name,
    )

    # Ensure work directory exists before any sub-directory creation
    work_dir.mkdir(parents=True, exist_ok=True)

    # Download precise orbit files (critical for burst positioning)
    if orbit_dir is None:
        orbit_dir = work_dir / "orbits"
        orbit_dir.mkdir(parents=True, exist_ok=True)

    from peatguard.ingest.orbit import download_orbits_for_pair

    downloaded_orbits = download_orbits_for_pair(
        reference_safe=reference_safe,
        secondary_safe=secondary_safe,
        orbit_dir=orbit_dir,
    )
    logger.info("Downloaded %d orbit files to %s", len(downloaded_orbits), orbit_dir)

    generate_topsapp_config(
        reference_safe=reference_safe,
        secondary_safe=secondary_safe,
        work_dir=work_dir,
        config=config,
        orbit_dir=orbit_dir,
        dem_path=dem_path,
    )

    # Run through unwrapping (SNAPHU) when enabled, otherwise stop at filter.
    # Geocoding is left to MintPy which handles it internally.
    end_step = "unwrap" if do_unwrap else "filter"
    run_topsapp(work_dir, end_step=end_step)

    return work_dir
