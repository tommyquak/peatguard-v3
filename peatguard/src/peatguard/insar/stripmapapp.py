"""ISCE2 stripmapApp wrapper for NISAR L-band InSAR processing.

Wraps ISCE2's stripmapApp.py to handle stripmap-mode InSAR processing
for NISAR L-band data. Unlike Sentinel-1 TOPS mode (topsApp), NISAR
L-band uses a conventional stripmap acquisition without burst structure,
so stripmapApp is the correct ISCE2 workflow.

NISAR L-band (24cm wavelength) penetrates tropical forest canopy,
enabling peatland subsidence measurement under intact forest where
C-band Sentinel-1 loses coherence.
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


# Template for ISCE2 stripmapApp XML configuration.
_STRIPMAP_XML_TEMPLATE = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <stripmapApp>
        <component name="insar">
            <property name="Sensor name">NISAR_L</property>
            <component name="reference">
                <property name="hdf5">{reference_slc}</property>
                <property name="output directory">{work_dir}/reference</property>
            </component>
            <component name="secondary">
                <property name="hdf5">{secondary_slc}</property>
                <property name="output directory">{work_dir}/secondary</property>
            </component>
            {dem_property}
            <property name="do unwrap">{do_unwrap_str}</property>
            <property name="unwrapper name">snaphu_mcf</property>
            <property name="azimuth looks">{az_looks}</property>
            <property name="range looks">{rg_looks}</property>
            <property name="filter strength">{filter_strength}</property>
            <property name="geocode list">['merged/filt_topophase.unw',
                'merged/filt_topophase.unw.conncomp',
                'merged/phsig.cor',
                'merged/filt_topophase.flat',
                'merged/los.rdr',
                'merged/topophase.cor']</property>
            <property name="geocode bounding box">[{south}, {north}, {west}, {east}]</property>
        </component>
    </stripmapApp>
""")


def generate_stripmapapp_config(
    reference_slc: Path,
    secondary_slc: Path,
    work_dir: Path,
    config: PeatGuardConfig,
    dem_path: Optional[Path] = None,
    az_looks: int = 5,
    rg_looks: int = 11,
) -> Path:
    """Generate an ISCE2 stripmapApp XML configuration file for NISAR.

    Args:
        reference_slc: Path to the reference NISAR L-band SLC (HDF5).
        secondary_slc: Path to the secondary NISAR L-band SLC (HDF5).
        work_dir: Working directory for ISCE2 outputs.
        config: Pipeline configuration.
        dem_path: Path to the DEM file. Auto-downloaded if None.
        az_looks: Azimuth multilooking factor (default 5 for NISAR L-band).
        rg_looks: Range multilooking factor (default 11 for NISAR L-band).

    Returns:
        Path to the generated stripmapApp.xml file.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    dem_property = ""
    if dem_path is not None and Path(str(dem_path) + ".xml").exists():
        dem_property = f'<property name="demFilename">{dem_path}</property>'
        logger.info("Using pre-downloaded DEM: %s", dem_path)
    else:
        logger.info("No DEM provided -- ISCE2 will auto-download SRTM tiles")

    west, south, east, north = config.aoi.bbox

    xml_content = _STRIPMAP_XML_TEMPLATE.format(
        reference_slc=str(reference_slc),
        secondary_slc=str(secondary_slc),
        work_dir=str(work_dir),
        dem_property=dem_property,
        do_unwrap_str="True",
        south=south,
        north=north,
        west=west,
        east=east,
        az_looks=az_looks,
        rg_looks=rg_looks,
        filter_strength=config.processing.goldstein_alpha,
    )

    config_path = work_dir / "stripmapApp.xml"
    config_path.write_text(xml_content)
    logger.info("Generated stripmapApp config: %s", config_path)
    return config_path


def run_stripmapapp(
    work_dir: Path,
    end_step: Optional[str] = None,
    start_step: Optional[str] = None,
) -> None:
    """Execute ISCE2 stripmapApp.py processing.

    Runs the configured stripmapApp workflow. Steps are executed in
    ISCE2's defined order: startup, preprocess, formSLC, misreg,
    fineoffsets, fineresamp, interferogram, filter, unwrap, geocode.

    Args:
        work_dir: Working directory containing stripmapApp.xml.
        end_step: Stop after this step.
        start_step: Start from this step.
    """
    import shutil

    stripmap_bin = shutil.which("stripmapApp.py") or shutil.which("stripmapApp")
    if stripmap_bin:
        cmd = [stripmap_bin]
    else:
        cmd = ["python", "-m", "isce.applications.stripmapApp"]

    if start_step:
        cmd.append(f"--start={start_step}")
    if end_step:
        cmd.append(f"--end={end_step}")

    logger.info("Running stripmapApp in %s (cmd: %s)", work_dir, cmd[0])
    if start_step or end_step:
        logger.info("  Steps: %s -> %s", start_step or "startup", end_step or "geocode")

    env = os.environ.copy()
    isce_home = os.environ.get("ISCE_HOME", "")
    if isce_home:
        env["PATH"] = f"{isce_home}/bin:{env.get('PATH', '')}"
    if "PROJ_LIB" not in env:
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

    if result.stdout:
        logger.info("stripmapApp STDOUT:\n%s", result.stdout[-3000:])
    if result.stderr:
        logger.info("stripmapApp STDERR:\n%s", result.stderr[-3000:])

    if result.returncode != 0:
        xml_path = work_dir / "stripmapApp.xml"
        if xml_path.exists():
            logger.error("stripmapApp.xml contents:\n%s", xml_path.read_text())
        raise RuntimeError(
            f"stripmapApp.py failed with return code {result.returncode}"
        )

    logger.info("stripmapApp completed successfully")


def process_pair(
    reference_slc: Path,
    secondary_slc: Path,
    work_dir: Path,
    config: PeatGuardConfig,
    dem_path: Optional[Path] = None,
    do_unwrap: bool = True,
) -> Path:
    """Process a single NISAR L-band interferometric pair with ISCE2 stripmapApp.

    This is the main entry point for single-pair NISAR InSAR processing.
    Unlike Sentinel-1, NISAR L-band data is in HDF5 format and does not
    require orbit file downloads or burst handling.

    Args:
        reference_slc: Path to reference NISAR SLC (HDF5).
        secondary_slc: Path to secondary NISAR SLC (HDF5).
        work_dir: Working directory for this pair.
        config: Pipeline configuration.
        dem_path: DEM file path.
        do_unwrap: Whether to run ISCE2's built-in unwrapping.

    Returns:
        Path to the work directory containing ISCE2 outputs.
    """
    logger.info(
        "Processing NISAR pair: %s -- %s",
        reference_slc.name,
        secondary_slc.name,
    )

    work_dir.mkdir(parents=True, exist_ok=True)

    generate_stripmapapp_config(
        reference_slc=reference_slc,
        secondary_slc=secondary_slc,
        work_dir=work_dir,
        config=config,
        dem_path=dem_path,
    )

    end_step = "unwrap" if do_unwrap else "filter"
    run_stripmapapp(work_dir, end_step=end_step)

    return work_dir
