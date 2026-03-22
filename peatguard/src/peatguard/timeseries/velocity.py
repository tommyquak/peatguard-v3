"""Velocity map extraction and export from MintPy outputs.

Reads MintPy's velocity.h5 HDF5 output and converts it to
Cloud-Optimized GeoTIFF for ArcGIS Pro consumption. Also
extracts velocity uncertainty for quality assessment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from peatguard.config import PeatGuardConfig
from peatguard.export.cog import write_cog

logger = logging.getLogger(__name__)


def _read_mintpy_h5(h5_path: Path, dataset: str = "velocity") -> tuple[np.ndarray, dict]:
    """Read a dataset from a MintPy HDF5 file.

    Args:
        h5_path: Path to the MintPy HDF5 file.
        dataset: Dataset name within the file.

    Returns:
        Tuple of (data_array, attributes_dict).
    """
    import h5py

    with h5py.File(h5_path, "r") as f:
        data = f[dataset][:]
        attrs = dict(f.attrs)
        if dataset in f:
            attrs.update(dict(f[dataset].attrs))
    return data, attrs


def _get_transform(
    attrs: dict,
    mintpy_dir: Optional[Path] = None,
    config: Optional["PeatGuardConfig"] = None,
    height: int = 0,
    width: int = 0,
) -> tuple:
    """Derive a rasterio-compatible geotransform.

    Priority:
    1. MintPy geocoded attributes (X_FIRST/Y_FIRST/X_STEP/Y_STEP)
    2. Lat/lon arrays from geometryRadar.h5
    3. AOI bbox from pipeline config

    Returns:
        Tuple of (transform, crs_epsg).
    """
    from rasterio.transform import from_bounds, from_origin

    # 1. MintPy geocoded attributes
    x_first = float(attrs.get("X_FIRST", 0))
    x_step = float(attrs.get("X_STEP", 1))
    if x_first != 0 and x_step != 1:
        y_first = float(attrs.get("Y_FIRST", 0))
        y_step = float(attrs.get("Y_STEP", -1))
        transform = from_origin(x_first, y_first, abs(x_step), abs(y_step))
        crs = int(attrs.get("EPSG", 4326))
        logger.info("Geotransform from MintPy geocoded attrs")
        return transform, crs

    # 2. Lat/lon from geometry HDF5
    if mintpy_dir is not None:
        geom_file = mintpy_dir / "inputs" / "geometryRadar.h5"
        if geom_file.exists():
            import h5py
            with h5py.File(str(geom_file), "r") as gf:
                if "latitude" in gf and "longitude" in gf:
                    lat = gf["latitude"][:]
                    lon = gf["longitude"][:]
                    valid = (lat != 0) & (lon != 0) & np.isfinite(lat) & np.isfinite(lon)
                    if valid.any():
                        h, w = lat.shape
                        south = float(np.nanmin(lat[valid]))
                        north = float(np.nanmax(lat[valid]))
                        west = float(np.nanmin(lon[valid]))
                        east = float(np.nanmax(lon[valid]))
                        # Sanity check: bbox should be within reasonable bounds
                        if (-90 < south < north < 90) and (-180 < west < east < 180):
                            transform = from_bounds(west, south, east, north, w, h)
                            logger.info("Geotransform from geometry lat/lon: "
                                        "[%.4f, %.4f, %.4f, %.4f]", west, south, east, north)
                            return transform, 4326

    # 3. AOI bbox from config
    if config is not None:
        west, south, east, north = config.aoi.bbox
        if height > 0 and width > 0:
            transform = from_bounds(west, south, east, north, width, height)
            logger.info("Geotransform from config AOI bbox: "
                        "[%.4f, %.4f, %.4f, %.4f]", west, south, east, north)
            return transform, 4326

    logger.warning("No georeferencing available")
    return from_origin(0, 0, 1, 1), 4326


def export_velocity(
    mintpy_dir: Path,
    output_dir: Path,
    config: Optional[PeatGuardConfig] = None,
    coherence_mask_threshold: float = 0.3,
) -> dict[str, Path]:
    """Export MintPy velocity and uncertainty as COG GeoTIFFs.

    Reads MintPy's velocity.h5, applies a coherence mask to exclude
    unreliable pixels, and writes Cloud-Optimized GeoTIFFs.

    Args:
        mintpy_dir: MintPy working directory containing velocity.h5.
        output_dir: Directory for output COGs.
        config: Pipeline configuration for export settings.
        coherence_mask_threshold: Minimum coherence for valid pixels.

    Returns:
        Dict mapping product names to output file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}

    # Read velocity
    velocity_path = mintpy_dir / "velocity.h5"
    if not velocity_path.exists():
        raise FileNotFoundError(f"MintPy velocity file not found: {velocity_path}")

    velocity_m_yr, attrs = _read_mintpy_h5(velocity_path, "velocity")
    h, w = velocity_m_yr.shape
    transform, crs = _get_transform(attrs, mintpy_dir=mintpy_dir, config=config, height=h, width=w)

    # Convert m/yr to mm/yr and clamp extreme outliers
    velocity_mm_yr = velocity_m_yr * 1000.0
    valid_mask = np.isfinite(velocity_mm_yr)
    velocity_mm_yr[valid_mask] = np.clip(velocity_mm_yr[valid_mask], -200.0, 200.0)

    # Read velocity uncertainty if available
    velocity_std = None
    try:
        velocity_std_m_yr, _ = _read_mintpy_h5(velocity_path, "velocityStd")
        velocity_std = velocity_std_m_yr * 1000.0
    except (KeyError, Exception):
        logger.info("Velocity uncertainty not available")

    # Read coherence for masking
    temporal_coh_path = mintpy_dir / "temporalCoherence.h5"
    nodata = -9999.0
    coherence = None

    if temporal_coh_path.exists():
        coherence, _ = _read_mintpy_h5(temporal_coh_path, "temporalCoherence")

    # Clip all arrays to AOI bbox (avoids huge full-swath outputs)
    row_start = row_end = col_start = col_end = 0
    if config is not None:
        from rasterio.transform import from_bounds
        west, south, east, north = config.aoi.bbox
        # Add buffer (0.1 deg ~11km) to match backscatter's 10km buffer
        buf = 0.1
        west_b, south_b, east_b, north_b = west - buf, south - buf, east + buf, north + buf

        # Find pixel window corresponding to AOI bbox
        col_start = max(0, int((west_b - transform.c) / transform.a))
        col_end = min(w, int((east_b - transform.c) / transform.a) + 1)
        row_start = max(0, int((north_b - transform.f) / transform.e))
        row_end = min(h, int((south_b - transform.f) / transform.e) + 1)

        if col_end > col_start and row_end > row_start:
            logger.info("Clipping to AOI: rows [%d:%d], cols [%d:%d] (from %dx%d)",
                        row_start, row_end, col_start, col_end, h, w)
            velocity_mm_yr = velocity_mm_yr[row_start:row_end, col_start:col_end]
            h, w = velocity_mm_yr.shape
            transform = from_bounds(west_b, south_b, east_b, north_b, w, h)
            if velocity_std is not None:
                velocity_std = velocity_std[row_start:row_end, col_start:col_end]
            if coherence is not None:
                coherence = coherence[row_start:row_end, col_start:col_end]

    # Apply coherence mask
    if coherence is not None:
        mask = coherence < coherence_mask_threshold
        velocity_mm_yr[mask] = nodata
        if velocity_std is not None:
            velocity_std[mask] = nodata
        logger.info(
            "Applied coherence mask (threshold=%.2f): %d/%d pixels masked",
            coherence_mask_threshold,
            mask.sum(),
            mask.size,
        )

    # Export coherence
    if coherence is not None:
        export_config = config.export if config else None
        coh_path = write_cog(
            data=coherence.astype(np.float32),
            output_path=output_dir / "coherence_median.tif",
            crs=crs,
            transform=transform,
            nodata=nodata,
            band_names=["temporal_coherence"],
            export_config=export_config,
            dtype="float32",
        )
        outputs["coherence_median"] = coh_path

    # Export velocity
    export_config = config.export if config else None
    vel_path = write_cog(
        data=velocity_mm_yr.astype(np.float32),
        output_path=output_dir / "subsidence_velocity.tif",
        crs=crs,
        transform=transform,
        nodata=nodata,
        band_names=["velocity_mm_yr"],
        export_config=export_config,
        dtype="float32",
    )
    outputs["subsidence_velocity"] = vel_path

    # Export uncertainty
    if velocity_std is not None:
        std_path = write_cog(
            data=velocity_std.astype(np.float32),
            output_path=output_dir / "velocity_uncertainty.tif",
            crs=crs,
            transform=transform,
            nodata=nodata,
            band_names=["velocity_std_mm_yr"],
            export_config=export_config,
            dtype="float32",
        )
        outputs["velocity_uncertainty"] = std_path

    logger.info("Exported %d velocity products to %s", len(outputs), output_dir)
    return outputs
