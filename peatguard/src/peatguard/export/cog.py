"""Cloud-Optimized GeoTIFF (COG) writer.

Produces tiled, compressed GeoTIFFs with internal overviews that
ArcGIS Pro can open and render efficiently. All output products
pass through this module to ensure consistent formatting.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds

from peatguard.config import ExportConfig

logger = logging.getLogger(__name__)


def write_cog(
    data: np.ndarray,
    output_path: Path,
    crs: Union[str, int],
    transform: rasterio.transform.Affine,
    nodata: Optional[float] = None,
    band_names: Optional[list[str]] = None,
    export_config: Optional[ExportConfig] = None,
    dtype: Optional[str] = None,
) -> Path:
    """Write a numpy array as a Cloud-Optimized GeoTIFF.

    Produces a tiled, compressed GeoTIFF with internal overviews
    suitable for direct consumption in ArcGIS Pro.

    Args:
        data: Array to write. Shape (bands, height, width) or (height, width).
        output_path: Destination file path.
        crs: Coordinate reference system (EPSG code or WKT string).
        transform: Affine transform mapping pixel coordinates to CRS.
        nodata: NoData value. Uses config default if None.
        band_names: Optional list of band description strings.
        export_config: Export settings. Uses defaults if None.
        dtype: Output data type. Inferred from data if None.

    Returns:
        Path to the written COG file.
    """
    if export_config is None:
        export_config = ExportConfig()

    if nodata is None:
        nodata = export_config.nodata

    if dtype is None:
        dtype = str(data.dtype)

    # Ensure 3D array (bands, height, width)
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    num_bands, height, width = data.shape
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "dtype": dtype,
        "width": width,
        "height": height,
        "count": num_bands,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "tiled": True,
        "blockxsize": export_config.cog_blocksize,
        "blockysize": export_config.cog_blocksize,
        "compress": export_config.cog_compression,
    }

    logger.info(
        "Writing COG: %s (%dx%d, %d bands, %s)",
        output_path.name,
        width,
        height,
        num_bands,
        dtype,
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        for band_idx in range(num_bands):
            dst.write(data[band_idx], band_idx + 1)
            if band_names and band_idx < len(band_names):
                dst.set_band_description(band_idx + 1, band_names[band_idx])

        # Build internal overviews for fast rendering at multiple zoom levels
        dst.build_overviews(export_config.overview_levels, Resampling.average)
        dst.update_tags(ns="rio_overview", resampling="average")

    logger.info("COG written: %s (%.1f MB)", output_path.name, output_path.stat().st_size / 1e6)
    return output_path


def write_cog_from_bounds(
    data: np.ndarray,
    output_path: Path,
    crs: Union[str, int],
    bounds: tuple[float, float, float, float],
    nodata: Optional[float] = None,
    band_names: Optional[list[str]] = None,
    export_config: Optional[ExportConfig] = None,
    dtype: Optional[str] = None,
) -> Path:
    """Write a COG using geographic bounds instead of an explicit transform.

    Convenience wrapper that computes the affine transform from bounds.

    Args:
        data: Array to write. Shape (bands, height, width) or (height, width).
        output_path: Destination file path.
        crs: Coordinate reference system.
        bounds: (west, south, east, north) in CRS units.
        nodata: NoData value.
        band_names: Optional band descriptions.
        export_config: Export settings.
        dtype: Output data type.

    Returns:
        Path to the written COG file.
    """
    if data.ndim == 2:
        height, width = data.shape
    else:
        _, height, width = data.shape

    west, south, east, north = bounds
    transform = from_bounds(west, south, east, north, width, height)

    return write_cog(
        data=data,
        output_path=output_path,
        crs=crs,
        transform=transform,
        nodata=nodata,
        band_names=band_names,
        export_config=export_config,
        dtype=dtype,
    )


def read_raster(path: Path) -> tuple[np.ndarray, dict]:
    """Read a raster file and return the data array and metadata.

    Args:
        path: Path to the raster file.

    Returns:
        Tuple of (data_array, metadata_dict) where metadata contains
        crs, transform, nodata, bounds, and shape.
    """
    with rasterio.open(path) as src:
        data = src.read()
        metadata = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "bounds": src.bounds,
            "shape": data.shape,
            "dtype": str(src.dtypes[0]),
            "width": src.width,
            "height": src.height,
            "count": src.count,
        }
    return data, metadata
