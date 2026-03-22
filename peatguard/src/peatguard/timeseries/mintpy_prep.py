"""MintPy data preparation from ISCE2 outputs.

Converts ISCE2 topsApp/stripmapApp output directory structure into
MintPy's expected HDF5 input format. MintPy requires an ifgramStack.h5
(interferogram stack) and geometryGeo.h5 (geometry in geo coordinates).

Supports both Sentinel-1 (C-band, topsApp) and NISAR (L-band,
stripmapApp) with sensor-appropriate SAR parameters in the HDF5
metadata (wavelength, orbit height, pixel sizes).
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


def _get_sar_params(config: PeatGuardConfig) -> dict:
    """Return sensor-specific SAR parameters for HDF5 metadata.

    These parameters are required by MintPy for phase-to-displacement
    conversion (wavelength), slant range computation (starting range,
    range pixel size), and other corrections.

    Args:
        config: Pipeline configuration with active sensor selection.

    Returns:
        Dict of SAR parameter strings suitable for HDF5 attributes.
    """
    if config.is_nisar:
        nisar = config.nisar
        # NISAR L-band stripmap: different multilook factors
        az_looks = 5
        rg_looks = 11
        return {
            "WAVELENGTH": str(nisar.wavelength_m),
            "HEIGHT": str(nisar.orbit_height_m),
            "STARTING_RANGE": "900000.0",  # approximate slant range, meters
            "RANGE_PIXEL_SIZE": str(nisar.range_pixel_size_m * rg_looks),
            "AZIMUTH_PIXEL_SIZE": str(nisar.azimuth_pixel_size_m * az_looks),
            "EARTH_RADIUS": "6371000.0",
            "CENTER_LINE_UTC": "21600.0",  # ~06:00 UTC (typical NISAR ascending)
            "PLATFORM": "NISAR",
            "ORBIT_DIRECTION": "ASCENDING",
            "ANTENNA_SIDE": "-1",
            "ALOOKS": str(az_looks),
            "RLOOKS": str(rg_looks),
            "HEADING": "-13.0",  # typical ascending, equatorial
            "PRF": "1740.0",  # approximate NISAR L-SAR PRF
        }
    else:
        # Sentinel-1 C-band TOPS (existing hardcoded values)
        return {
            "WAVELENGTH": "0.05546576",
            "HEIGHT": "693000.0",
            "STARTING_RANGE": "800000.0",
            "RANGE_PIXEL_SIZE": str(2.329562 * 9),
            "AZIMUTH_PIXEL_SIZE": str(13.97 * 3),
            "EARTH_RADIUS": "6371000.0",
            "CENTER_LINE_UTC": "79200.0",
            "PLATFORM": "Sentinel-1A",
            "ORBIT_DIRECTION": "DESCENDING",
            "ANTENNA_SIDE": "-1",
            "ALOOKS": "3",
            "RLOOKS": "9",
            "HEADING": "-166.0",
            "PRF": "486.486",
        }

_MINTPY_TEMPLATE = textwrap.dedent("""\
    ##----------------- PeatGuard MintPy Configuration -----------------##

    ########## computing resource configuration
    mintpy.compute.cluster     = no

    ########## loading data
    mintpy.load.processor      = isce
    mintpy.load.updateMode     = auto
    mintpy.load.compression    = lzf

    # ISCE2 topsApp output directory structure
    mintpy.load.unwFile        = {isce_dir}/merged/interferograms/*/filt_topophase.unw
    mintpy.load.corFile        = {isce_dir}/merged/interferograms/*/phsig.cor
    mintpy.load.connCompFile   = {isce_dir}/merged/interferograms/*/filt_topophase.unw.conncomp
    mintpy.load.intFile        = {isce_dir}/merged/interferograms/*/filt_topophase.flat
    mintpy.load.ionoFile       = auto
    mintpy.load.demFile        = {isce_dir}/merged/geom_reference/hgt.rdr
    mintpy.load.lookupYFile    = {isce_dir}/merged/geom_reference/lat.rdr
    mintpy.load.lookupXFile    = {isce_dir}/merged/geom_reference/lon.rdr
    mintpy.load.incAngleFile   = {isce_dir}/merged/geom_reference/los.rdr
    mintpy.load.azAngleFile    = {isce_dir}/merged/geom_reference/los.rdr
    mintpy.load.shadowMaskFile = {isce_dir}/merged/geom_reference/shadowMask.rdr
    mintpy.load.waterMaskFile  = auto
    mintpy.load.bperpFile      = auto

    ########## subset (disabled -- data already covers AOI)
    ## mintpy.subset.lalo         = {south}:{north},{west}:{east}

    ########## reference point
{reference_point_block}

    ########## network modification
    mintpy.network.coherenceBased  = {coh_based}
    mintpy.network.minCoherence    = {min_coh}

    ########## unwrapping error correction (skip -- MCF unwrapper handles this)
    mintpy.unwrapError.method      = no

    ########## tropospheric delay correction
    mintpy.troposphericDelay.method          = {tropo_method}
    mintpy.troposphericDelay.weatherModel    = ERA5
    mintpy.troposphericDelay.weatherDir      = {weather_dir}

    ########## topographic residual (DEM error) -- skip for flat peatlands
    mintpy.topographicResidual         = no

    ########## residual phase (orbital ramp removal)
    mintpy.deramp                      = linear
    mintpy.deramp.maskFile             = auto

    ########## velocity estimation
    mintpy.velocity.startDate          = auto
    mintpy.velocity.endDate            = auto

    ########## geocoding (skip -- export handles this separately)
    mintpy.geocode                     = no
""")


def _is_cds_api_available() -> bool:
    """Check whether CDS API credentials are available.

    Credentials can come from:
    1. Environment variables CDS_API_URL and CDS_API_KEY
    2. A ~/.cdsapirc file

    Returns:
        True if CDS API credentials are configured.
    """
    if os.environ.get("CDS_API_KEY"):
        return True
    cdsapirc = Path.home() / ".cdsapirc"
    if cdsapirc.exists() and cdsapirc.stat().st_size > 0:
        return True
    return False


def _ensure_cdsapirc() -> None:
    """Create ~/.cdsapirc from environment variables if it does not exist.

    PyAPS reads CDS API credentials from ~/.cdsapirc. When running in
    Cloud Run, the credentials are injected as environment variables
    (CDS_API_URL and CDS_API_KEY) rather than baked into the image.
    This function bridges the two by writing the rc file at runtime.
    """
    cdsapirc = Path.home() / ".cdsapirc"
    if cdsapirc.exists():
        logger.debug("CDS API config already exists: %s", cdsapirc)
        return

    api_url = os.environ.get("CDS_API_URL", "https://cds.climate.copernicus.eu/api")
    api_key = os.environ.get("CDS_API_KEY", "")

    if not api_key:
        logger.warning(
            "CDS_API_KEY environment variable not set and ~/.cdsapirc not found. "
            "ERA5 tropospheric correction will be skipped."
        )
        return

    cdsapirc.write_text(f"url: {api_url}\nkey: {api_key}\n")
    cdsapirc.chmod(0o600)
    logger.info("Created %s from environment variables", cdsapirc)


def generate_mintpy_config(
    isce_dir: Path,
    mintpy_dir: Path,
    config: PeatGuardConfig,
    weather_dir: Optional[Path] = None,
) -> Path:
    """Generate a MintPy configuration template file.

    Args:
        isce_dir: Root directory of ISCE2 topsApp outputs.
        mintpy_dir: MintPy working directory.
        config: Pipeline configuration.
        weather_dir: Directory for ERA5 weather model data.

    Returns:
        Path to the generated MintPy config file.
    """
    mintpy_dir.mkdir(parents=True, exist_ok=True)

    if weather_dir is None:
        weather_dir = mintpy_dir / "weather"
        weather_dir.mkdir(exist_ok=True)

    west, south, east, north = config.aoi.bbox

    coh_based = "yes" if config.mintpy.network_modification.coherence_based else "no"
    min_coh = config.mintpy.network_modification.min_coherence

    # Build reference point configuration from config.
    # A fixed lat/lon ensures deterministic velocity baselines across runs.
    ref_lalo = config.mintpy.reference_lalo
    if ref_lalo and len(ref_lalo) == 2:
        reference_point_block = (
            "    ## Fixed reference point on stable ground (configured in YAML)\n"
            f"    mintpy.reference.lalo       = {ref_lalo[0]}, {ref_lalo[1]}\n"
            f"    mintpy.reference.minCoherence = {config.mintpy.reference_min_coherence}"
        )
        logger.info(
            "Using fixed reference point: lat=%.6f, lon=%.6f",
            ref_lalo[0], ref_lalo[1],
        )
    else:
        reference_point_block = (
            "    ## Auto-select from highest coherence unmasked pixel\n"
            "    mintpy.reference.yx        = auto\n"
            f"    mintpy.reference.minCoherence = {config.mintpy.reference_min_coherence}"
        )
        logger.info(
            "No fixed reference point configured; using MintPy auto-selection "
            "(minCoherence=%.2f)",
            config.mintpy.reference_min_coherence,
        )

    # Determine tropospheric correction method.
    # Use PyAPS (ERA5) when the config requests it AND CDS API credentials are available.
    # Fall back to no correction otherwise to avoid a hard failure.
    tropo_method = "no"
    tropo_setting = config.mintpy.tropospheric_correction.lower()
    if tropo_setting in ("pyaps", "era5"):
        _ensure_cdsapirc()
        if _is_cds_api_available():
            tropo_method = "pyaps"
            logger.info(
                "ERA5 tropospheric correction enabled (weather dir: %s)", weather_dir
            )
        else:
            logger.warning(
                "Tropospheric correction requested (%s) but CDS API credentials "
                "are not available. Falling back to no correction. Set CDS_API_KEY "
                "env var or create ~/.cdsapirc to enable ERA5 correction.",
                tropo_setting,
            )
    else:
        logger.info("Tropospheric correction disabled by config (method=%s)", tropo_setting)

    template_content = _MINTPY_TEMPLATE.format(
        isce_dir=str(isce_dir),
        south=south,
        north=north,
        west=west,
        east=east,
        coh_based=coh_based,
        min_coh=min_coh,
        reference_point_block=reference_point_block,
        tropo_method=tropo_method,
        weather_dir=str(weather_dir),
    )

    config_path = mintpy_dir / "peatguard.cfg"
    config_path.write_text(template_content)
    logger.info("Generated MintPy config: %s", config_path)
    return config_path


def _read_isce_xml_dims(xml_path: Path) -> tuple[int, int, int]:
    """Read width, length, number_bands from an ISCE2 XML sidecar."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(str(xml_path))
    width = length = 0
    n_bands = 1
    for prop in tree.iter("property"):
        name = prop.get("name", "")
        val_elem = prop.find("value")
        if val_elem is None:
            continue
        if name == "width":
            width = int(val_elem.text)
        elif name == "length":
            length = int(val_elem.text)
        elif name == "number_bands":
            n_bands = int(val_elem.text)
    return width, length, n_bands


def prep_data_for_mintpy(
    isce_dir: Path,
    mintpy_dir: Path,
    config: "PeatGuardConfig",
) -> tuple[Path, Path]:
    """Prepare ISCE2 outputs for MintPy by creating HDF5 stack files.

    Directly reads ISCE2 binary files and creates MintPy's expected
    ifgramStack.h5 and geometryRadar.h5 without relying on prep_isce.py.
    This avoids metadata dependency issues when data is reconstructed
    from GCS rather than produced in a single topsApp run.

    Args:
        isce_dir: Root directory with merged/ structure.
        mintpy_dir: MintPy working directory.
        config: Pipeline configuration.

    Returns:
        Tuple of (ifgramStack.h5 path, geometry.h5 path).
    """
    import h5py
    import numpy as np
    from datetime import datetime

    mintpy_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = mintpy_dir / "inputs"
    inputs_dir.mkdir(exist_ok=True)

    ifg_root = isce_dir / "merged" / "interferograms"
    geom_root = isce_dir / "merged" / "geom_reference"

    # Discover pairs (YYYYMMDD_YYYYMMDD directories)
    pair_dirs = sorted([d for d in ifg_root.iterdir() if d.is_dir()])
    if not pair_dirs:
        raise RuntimeError(f"No interferogram directories in {ifg_root}")

    # Read dimensions from first pair's unwrapped phase
    first_unw = pair_dirs[0] / "filt_topophase.unw"
    first_xml = pair_dirs[0] / "filt_topophase.unw.xml"
    if not first_unw.exists():
        raise RuntimeError(f"Missing unwrapped phase: {first_unw}")

    width, length, n_bands = _read_isce_xml_dims(first_xml)
    logger.info("Interferogram dimensions: %d x %d (%d bands)", length, width, n_bands)

    # Parse pair dates
    pairs = []
    dates = set()
    for d in pair_dirs:
        name = d.name  # YYYYMMDD_YYYYMMDD
        parts = name.split("_")
        if len(parts) == 2 and len(parts[0]) == 8:
            pairs.append((parts[0], parts[1]))
            dates.add(parts[0])
            dates.add(parts[1])
    dates = sorted(dates)
    logger.info("Found %d pairs spanning %d dates: %s to %s",
                len(pairs), len(dates), dates[0], dates[-1])

    # Create date list in decimal years for metadata
    date_list = [datetime.strptime(d, "%Y%m%d") for d in dates]

    # Build ifgramStack.h5
    ifgram_file = inputs_dir / "ifgramStack.h5"
    logger.info("Creating %s", ifgram_file)

    with h5py.File(str(ifgram_file), "w") as f:
        n_pairs = len(pairs)

        # Unwrapped phase (main dataset)
        unw_dset = f.create_dataset(
            "unwrapPhase", shape=(n_pairs, length, width),
            dtype=np.float32, chunks=(1, length, width),
            compression="lzf",
        )
        # Coherence
        cor_dset = f.create_dataset(
            "coherence", shape=(n_pairs, length, width),
            dtype=np.float32, chunks=(1, length, width),
            compression="lzf",
        )
        # Connected components
        conn_dset = f.create_dataset(
            "connectComponent", shape=(n_pairs, length, width),
            dtype=np.int16, chunks=(1, length, width),
            compression="lzf",
        )
        # Date pairs
        date12 = f.create_dataset("date", shape=(n_pairs, 2), dtype="S8")

        for i, (ref_date, sec_date) in enumerate(pairs):
            pair_dir = ifg_root / f"{ref_date}_{sec_date}"

            # Read unwrapped phase (2-band BIL: amp + phase)
            unw_path = pair_dir / "filt_topophase.unw"
            if unw_path.exists():
                data = np.fromfile(str(unw_path), dtype=np.float32)
                expected = length * width * 2
                data = data[:expected]  # trim trailing bytes if any
                data = data.reshape(length, width * 2)
                unw_dset[i] = data[:, width:]  # Band 2 is phase
            else:
                logger.warning("Missing unw for %s_%s", ref_date, sec_date)

            # Read coherence (single band float32)
            cor_path = pair_dir / "phsig.cor"
            if cor_path.exists():
                data = np.fromfile(str(cor_path), dtype=np.float32)
                expected = length * width
                data = data[:expected]
                cor_dset[i] = data.reshape(length, width)

            # Read connected components (byte format, trim to expected size)
            conn_path = pair_dir / "filt_topophase.unw.conncomp"
            if conn_path.exists():
                data = np.fromfile(str(conn_path), dtype=np.uint8)
                expected = length * width
                data = data[:expected]
                conn_dset[i] = data.reshape(length, width).astype(np.int16)

            date12[i] = [ref_date.encode(), sec_date.encode()]
            logger.info("  Loaded pair %d/%d: %s_%s", i + 1, n_pairs, ref_date, sec_date)

        # Bperp placeholder (MintPy can work without accurate baselines)
        f.create_dataset("bperp", data=np.zeros(n_pairs, dtype=np.float32))

        # Drop lists for network modification
        drop_date = f.create_dataset("dropIfgram", data=np.ones(n_pairs, dtype=np.bool_))

        # SAR parameters (required by MintPy for phase-to-displacement conversion)
        sar_params = _get_sar_params(config)
        f.attrs["PROCESSOR"] = "isce"
        f.attrs["FILE_TYPE"] = "ifgramStack"
        f.attrs["UNIT"] = "radian"
        f.attrs["LENGTH"] = str(length)
        f.attrs["WIDTH"] = str(width)
        for key, value in sar_params.items():
            f.attrs[key] = value

    logger.info("ifgramStack.h5 created: %d pairs, %dx%d", n_pairs, length, width)

    # Build geometry HDF5
    geom_file = inputs_dir / "geometryRadar.h5"
    logger.info("Creating %s", geom_file)

    def _read_geom(path: Path, target_h: int, target_w: int,
                   n_bands: int = 1) -> np.ndarray:
        """Read a geometry binary file and match to target dimensions."""
        xml_path = path.with_suffix(".rdr.xml")
        gw, gl, gn = (target_w, target_h, n_bands)
        if xml_path.exists():
            gw, gl, gn = _read_isce_xml_dims(xml_path)
        data = np.fromfile(str(path), dtype=np.float32)
        data = data.reshape(gl, gw * gn)
        # Trim or pad to match interferogram dimensions
        if data.shape[0] > target_h:
            data = data[:target_h, :]
        if data.shape[1] > target_w * gn:
            data = data[:, :target_w * gn]
        return data, gn

    with h5py.File(str(geom_file), "w") as f:
        # Height (DEM in radar coordinates)
        hgt_path = geom_root / "hgt.rdr"
        if hgt_path.exists():
            data, _ = _read_geom(hgt_path, length, width)
            f.create_dataset("height", data=data[:, :width], compression="lzf")
        else:
            logger.warning("No hgt.rdr found, creating zeros placeholder")
            f.create_dataset("height", data=np.zeros((length, width), dtype=np.float32))

        # LOS (incidence angle + azimuth angle, 2-band BIL)
        los_path = geom_root / "los.rdr"
        if los_path.exists():
            data, n = _read_geom(los_path, length, width, n_bands=2)
            lw = data.shape[1] // max(n, 2)
            inc_angle = data[:, :lw]
            az_angle = data[:, lw:2*lw] if n >= 2 else np.zeros_like(inc_angle)
            f.create_dataset("incidenceAngle", data=inc_angle[:length, :width], compression="lzf")
            f.create_dataset("azimuthAngle", data=az_angle[:length, :width], compression="lzf")

        # Latitude (multilooked float32 from burst merge)
        lat_path = geom_root / "lat.rdr"
        if lat_path.exists():
            data, _ = _read_geom(lat_path, length, width)
            f.create_dataset("latitude", data=data[:length, :width].astype(np.float64), compression="lzf")

        # Longitude
        lon_path = geom_root / "lon.rdr"
        if lon_path.exists():
            data, _ = _read_geom(lon_path, length, width)
            f.create_dataset("longitude", data=data[:length, :width].astype(np.float64), compression="lzf")

        # Shadow mask
        shadow_path = geom_root / "shadowMask.rdr"
        if shadow_path.exists():
            data, _ = _read_geom(shadow_path, length, width)
            f.create_dataset("shadowMask", data=data[:length, :width], compression="lzf")

        # Slant range distance (needed by dem_error.py for DEM correction)
        # Computed from starting range + pixel index * range pixel size
        sar_params = _get_sar_params(config)
        starting_range = float(sar_params["STARTING_RANGE"])
        range_pixel_size = float(sar_params["RANGE_PIXEL_SIZE"])
        slant_range = np.zeros((length, width), dtype=np.float32)
        for col in range(width):
            slant_range[:, col] = starting_range + col * range_pixel_size
        f.create_dataset("slantRangeDistance", data=slant_range, compression="lzf")

        f.attrs["PROCESSOR"] = "isce"
        f.attrs["FILE_TYPE"] = "geometry"
        f.attrs["LENGTH"] = str(length)
        f.attrs["WIDTH"] = str(width)
        for key, value in sar_params.items():
            f.attrs[key] = value

    logger.info("geometryRadar.h5 created")
    return ifgram_file, geom_file


def prep_isce_for_mintpy(
    isce_dir: Path,
    mintpy_dir: Path,
) -> None:
    """Run MintPy's prep_isce.py to convert ISCE2 outputs to HDF5.

    This creates the ifgramStack.h5 and geometryGeo.h5 files that
    MintPy needs for time-series analysis.

    Args:
        isce_dir: Root ISCE2 output directory.
        mintpy_dir: MintPy working directory.
    """
    logger.info("Running prep_isce.py for %s", isce_dir)

    cmd = [
        "prep_isce.py",
        "-i", str(isce_dir / "merged" / "interferograms"),
        "-g", str(isce_dir / "merged" / "geom_reference"),
        "-d", str(mintpy_dir),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(mintpy_dir))

    if result.returncode != 0:
        logger.error("prep_isce.py failed:\n%s", result.stderr[-2000:])
        raise RuntimeError(f"prep_isce.py failed with return code {result.returncode}")

    logger.info("MintPy data preparation complete")
