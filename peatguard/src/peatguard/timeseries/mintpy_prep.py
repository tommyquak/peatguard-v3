"""MintPy data preparation from ISCE2 outputs.

Converts ISCE2 topsApp output directory structure into MintPy's
expected HDF5 input format. MintPy requires an ifgramStack.h5
(interferogram stack) and geometryGeo.h5 (geometry in geo coordinates).

This module generates the MintPy configuration template and calls
MintPy's prep_isce.py utility for the format conversion.
"""

from __future__ import annotations

import logging
import subprocess
import textwrap
from pathlib import Path
from typing import Optional

from peatguard.config import PeatGuardConfig

logger = logging.getLogger(__name__)

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

    ########## reference point (auto-select from highest coherence area)
    mintpy.reference.yx        = auto

    ########## network modification
    mintpy.network.coherenceBased  = {coh_based}
    mintpy.network.minCoherence    = {min_coh}

    ########## unwrapping error correction
    mintpy.unwrapError.method      = bridging

    ########## tropospheric delay correction (skip for now -- ERA5 needs auth)
    mintpy.troposphericDelay.method     = no

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

    template_content = _MINTPY_TEMPLATE.format(
        isce_dir=str(isce_dir),
        south=south,
        north=north,
        west=west,
        east=east,
        coh_based=coh_based,
        min_coh=min_coh,
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
                data = data.reshape(length, width * 2)
                # Band 2 is phase (band 1 is amplitude)
                unw_dset[i] = data[:, width:]
            else:
                logger.warning("Missing unw for %s_%s", ref_date, sec_date)

            # Read coherence
            cor_path = pair_dir / "phsig.cor"
            if cor_path.exists():
                data = np.fromfile(str(cor_path), dtype=np.float32)
                cor_dset[i] = data.reshape(length, width)

            # Read connected components
            conn_path = pair_dir / "filt_topophase.unw.conncomp"
            if conn_path.exists():
                data = np.fromfile(str(conn_path), dtype=np.uint8)
                conn_dset[i] = data.reshape(length, width).astype(np.int16)

            date12[i] = [ref_date.encode(), sec_date.encode()]
            logger.info("  Loaded pair %d/%d: %s_%s", i + 1, n_pairs, ref_date, sec_date)

        # Bperp placeholder (MintPy can work without accurate baselines)
        f.create_dataset("bperp", data=np.zeros(n_pairs, dtype=np.float32))

        # Drop lists for network modification
        drop_date = f.create_dataset("dropIfgram", data=np.ones(n_pairs, dtype=np.bool_))

        # Sentinel-1 SAR parameters (required by MintPy)
        f.attrs["PROCESSOR"] = "isce"
        f.attrs["FILE_TYPE"] = "ifgramStack"
        f.attrs["UNIT"] = "radian"
        f.attrs["LENGTH"] = str(length)
        f.attrs["WIDTH"] = str(width)
        f.attrs["WAVELENGTH"] = "0.05546576"  # C-band, meters
        f.attrs["HEIGHT"] = "693000.0"  # Sentinel-1 orbit altitude, meters
        f.attrs["STARTING_RANGE"] = "800000.0"  # approximate, meters
        f.attrs["RANGE_PIXEL_SIZE"] = str(2.329562 * 9)  # multilooked by rg_looks=9
        f.attrs["AZIMUTH_PIXEL_SIZE"] = str(13.97 * 3)  # multilooked by az_looks=3
        f.attrs["EARTH_RADIUS"] = "6371000.0"
        f.attrs["CENTER_LINE_UTC"] = "79200.0"  # ~22:00 UTC (typical for this orbit)
        f.attrs["PLATFORM"] = "Sentinel-1A"
        f.attrs["ORBIT_DIRECTION"] = "DESCENDING"
        f.attrs["ANTENNA_SIDE"] = "-1"
        f.attrs["ALOOKS"] = "3"
        f.attrs["RLOOKS"] = "9"
        f.attrs["HEADING"] = "-166.0"  # typical for descending, equatorial
        f.attrs["PRF"] = "486.486"  # Sentinel-1 PRF

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
        starting_range = 800000.0  # approximate, meters
        range_pixel_size = 2.329562 * 9  # multilooked
        slant_range = np.zeros((length, width), dtype=np.float32)
        for col in range(width):
            slant_range[:, col] = starting_range + col * range_pixel_size
        f.create_dataset("slantRangeDistance", data=slant_range, compression="lzf")

        f.attrs["PROCESSOR"] = "isce"
        f.attrs["FILE_TYPE"] = "geometry"
        f.attrs["LENGTH"] = str(length)
        f.attrs["WIDTH"] = str(width)
        f.attrs["WAVELENGTH"] = "0.05546576"
        f.attrs["HEIGHT"] = "693000.0"
        f.attrs["STARTING_RANGE"] = "800000.0"
        f.attrs["RANGE_PIXEL_SIZE"] = str(2.329562 * 9)
        f.attrs["AZIMUTH_PIXEL_SIZE"] = str(13.97 * 3)
        f.attrs["EARTH_RADIUS"] = "6371000.0"
        f.attrs["PLATFORM"] = "Sentinel-1A"
        f.attrs["ORBIT_DIRECTION"] = "DESCENDING"
        f.attrs["ALOOKS"] = "3"
        f.attrs["RLOOKS"] = "9"

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
