"""Velocity map extraction and export from MintPy outputs.

Reads MintPy's velocity.h5 HDF5 output, converts Line-of-Sight (LOS)
velocity to vertical velocity using the incidence angle, and exports
as Cloud-Optimized GeoTIFF for ArcGIS Pro consumption. Also extracts
velocity uncertainty for quality assessment.
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

    # 1. MintPy geocoded attributes (present when mintpy.geocode = yes)
    if "X_FIRST" in attrs and "X_STEP" in attrs:
        x_first = float(attrs["X_FIRST"])
        x_step = float(attrs["X_STEP"])
        y_first = float(attrs["Y_FIRST"])
        y_step = float(attrs["Y_STEP"])
        transform = from_origin(x_first, y_first, abs(x_step), abs(y_step))
        crs = int(attrs.get("EPSG", 4326))
        logger.info(
            "Geotransform from MintPy geocoded attrs: origin=(%.6f, %.6f), "
            "step=(%.6f, %.6f), EPSG:%d",
            x_first, y_first, x_step, y_step, crs,
        )
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
                            logger.warning(
                                "Geotransform from geometry lat/lon bounds (affine "
                                "approximation -- may have 1-3 km error in radar "
                                "geometry). Consider enabling mintpy.geocode = yes. "
                                "Bounds: [%.4f, %.4f, %.4f, %.4f]",
                                west, south, east, north,
                            )
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


def _load_incidence_angle(
    mintpy_dir: Path,
    height: int,
    width: int,
    config: Optional["PeatGuardConfig"] = None,
) -> Optional[np.ndarray]:
    """Load incidence angle array from MintPy geometry HDF5.

    Checks geometryGeo.h5 first (geocoded), then geometryRadar.h5
    (radar coordinates). The dataset name is "incidenceAngle" and
    values are in degrees.

    Args:
        mintpy_dir: MintPy working directory.
        height: Expected array height (rows).
        width: Expected array width (columns).
        config: Pipeline configuration (unused, reserved).

    Returns:
        2-D float32 array of incidence angles in degrees, or None if
        no geometry file is found.
    """
    import h5py

    inputs_dir = mintpy_dir / "inputs"
    # Prefer geocoded geometry (produced when mintpy.geocode = yes)
    candidates = [
        inputs_dir / "geometryGeo.h5",
        inputs_dir / "geometryRadar.h5",
    ]

    for geom_path in candidates:
        if not geom_path.exists():
            continue
        try:
            with h5py.File(str(geom_path), "r") as gf:
                if "incidenceAngle" not in gf:
                    logger.debug("No incidenceAngle dataset in %s", geom_path.name)
                    continue
                inc = gf["incidenceAngle"][:].astype(np.float32)
            # Validate shape matches velocity grid
            if inc.shape == (height, width):
                logger.info(
                    "Loaded incidence angle from %s (%dx%d)",
                    geom_path.name, height, width,
                )
                return inc
            else:
                logger.warning(
                    "Incidence angle shape %s does not match velocity shape (%d, %d) "
                    "in %s; skipping",
                    inc.shape, height, width, geom_path.name,
                )
                del inc
        except Exception as exc:
            logger.warning("Failed to read incidence angle from %s: %s", geom_path.name, exc)

    return None


def export_velocity(
    mintpy_dir: Path,
    output_dir: Path,
    config: Optional[PeatGuardConfig] = None,
    coherence_mask_threshold: float = 0.5,  # 0.5 for tropical peat; masks noisy low-coherence pixels
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

    # Convert LOS velocity to vertical velocity using a constant incidence angle.
    # MintPy outputs Line-of-Sight displacement; for subsidence monitoring we
    # need the vertical component: vertical = LOS / cos(incidence_angle).
    # Using a constant factor (from config) rather than per-pixel incidence to
    # avoid amplification artifacts from geocoded geometry edge pixels where
    # incidence angle values can be zero or near-90 degrees.
    fallback_deg = config.processing.incidence_deg if config else 37.0
    factor = 1.0 / np.cos(np.radians(fallback_deg))
    logger.info(
        "Converting LOS to vertical velocity (constant incidence: %.1f deg, factor: %.2f)",
        fallback_deg, factor,
    )
    velocity_m_yr *= factor

    # Convert m/yr to mm/yr. Do NOT clamp here -- noisy pixels are handled
    # by the coherence mask below (threshold 0.5). Clamping extreme values
    # before masking biases the mean when many pixels are at the clamp bound.
    velocity_mm_yr = velocity_m_yr * 1000.0
    valid_mask = np.isfinite(velocity_mm_yr)

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
        band_names=["vertical_velocity_mm_yr"],
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
            band_names=["vertical_velocity_std_mm_yr"],
            export_config=export_config,
            dtype="float32",
        )
        outputs["velocity_uncertainty"] = std_path

    # Reproject to standard output CRS (UTM) if different from native CRS.
    # Velocity is natively in EPSG:4326 from MintPy geometry; backscatter
    # products are in UTM. Standardizing avoids fragile on-the-fly reprojection
    # in the analysis stage.
    output_crs = config.aoi.epsg if config else None
    if output_crs is not None and output_crs != crs:
        import rasterio
        from rasterio.crs import CRS as RioCRS
        from rasterio.warp import calculate_default_transform, reproject
        from rasterio.enums import Resampling

        dst_crs = RioCRS.from_epsg(output_crs)
        logger.info("Reprojecting velocity products from EPSG:%s to EPSG:%s", crs, output_crs)

        utm_outputs = {}
        for product_name, src_path in outputs.items():
            utm_path = src_path.parent / src_path.name.replace(".tif", "_utm.tif")
            with rasterio.open(src_path) as src:
                dst_transform, dst_width, dst_height = calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds,
                )
                dst_profile = src.profile.copy()
                dst_profile.update(
                    crs=dst_crs,
                    transform=dst_transform,
                    width=dst_width,
                    height=dst_height,
                )
                resamp = Resampling.nearest if src.dtypes[0] == "uint8" else Resampling.bilinear
                with rasterio.open(utm_path, "w", **dst_profile) as dst:
                    for band_idx in range(1, src.count + 1):
                        reproject(
                            source=rasterio.band(src, band_idx),
                            destination=rasterio.band(dst, band_idx),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=dst_transform,
                            dst_crs=dst_crs,
                            resampling=resamp,
                        )
            utm_outputs[product_name + "_utm"] = utm_path
            logger.info("Reprojected %s -> %s", product_name, utm_path.name)
        outputs.update(utm_outputs)

    logger.info("Exported %d velocity products to %s", len(outputs), output_dir)
    return outputs
