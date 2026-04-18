"""Temporal compositing for multi-temporal backscatter stacks.

Combines multiple calibrated and geocoded GRD scenes into a single
composite image. The temporal median is used to suppress transient
noise (e.g., ships, rain cells) while preserving stable features
like canals and land cover.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from peatguard.config import PeatGuardConfig
from peatguard.export.cog import write_cog

logger = logging.getLogger(__name__)


def _align_to_reference(
    src_path: Path,
    ref_profile: dict,
) -> np.ndarray:
    """Reproject/align a raster to match a reference grid.

    Args:
        src_path: Path to the source raster.
        ref_profile: Reference rasterio profile to align to.

    Returns:
        Aligned 2D array matching the reference dimensions.
    """
    dst_data = np.full(
        (ref_profile["height"], ref_profile["width"]),
        fill_value=np.nan,
        dtype=np.float32,
    )

    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_profile["transform"],
            dst_crs=ref_profile["crs"],
            resampling=Resampling.bilinear,
        )

    return dst_data


def create_temporal_composite(
    input_paths: list[Path],
    output_path: Path,
    method: str = "median",
    config: Optional[PeatGuardConfig] = None,
) -> Path:
    """Create a temporal composite from multiple geocoded backscatter scenes.

    Uses the first scene as the spatial reference grid. All subsequent
    scenes are aligned to this grid before stacking.

    Args:
        input_paths: List of paths to geocoded sigma0 GeoTIFFs.
        output_path: Path for the composite output.
        method: Compositing method ('median', 'mean', 'max', 'min').
        config: Pipeline configuration for export settings.

    Returns:
        Path to the composite GeoTIFF.
    """
    if not input_paths:
        raise ValueError("No input files provided for compositing")

    logger.info(
        "Creating %s composite from %d scenes",
        method,
        len(input_paths),
    )

    # Use first scene as spatial reference
    with rasterio.open(input_paths[0]) as ref_src:
        ref_profile = ref_src.profile.copy()
        ref_data = ref_src.read(1).astype(np.float32)

    height = ref_profile["height"]
    width = ref_profile["width"]

    # Stack all scenes
    stack = np.full((len(input_paths), height, width), fill_value=np.nan, dtype=np.float32)
    stack[0] = ref_data

    for i, path in enumerate(input_paths[1:], 1):
        logger.info("  Aligning scene %d/%d: %s", i + 1, len(input_paths), path.name)
        stack[i] = _align_to_reference(path, ref_profile)

    # Compute composite
    composite_funcs = {
        "median": lambda s: np.nanmedian(s, axis=0),
        "mean": lambda s: np.nanmean(s, axis=0),
        "max": lambda s: np.nanmax(s, axis=0),
        "min": lambda s: np.nanmin(s, axis=0),
    }

    if method not in composite_funcs:
        raise ValueError(f"Unknown compositing method: {method}. Use one of {list(composite_funcs)}")

    composite = composite_funcs[method](stack)

    # Count valid observations per pixel
    valid_count = np.sum(~np.isnan(stack), axis=0)
    logger.info(
        "Composite coverage: min=%d, max=%d, mean=%.1f observations per pixel",
        valid_count.min(),
        valid_count.max(),
        valid_count.mean(),
    )

    # Replace remaining NaN with nodata
    nodata = -9999.0
    composite = np.where(np.isnan(composite), nodata, composite)

    # Write as COG
    from peatguard.export.cog import write_cog

    export_config = config.export if config else None
    return write_cog(
        data=composite,
        output_path=output_path,
        crs=ref_profile["crs"],
        transform=ref_profile["transform"],
        nodata=nodata,
        band_names=[f"sigma0_VV_{method}"],
        export_config=export_config,
        dtype="float32",
    )
