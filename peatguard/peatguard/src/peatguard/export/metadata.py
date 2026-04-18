"""STAC-compatible metadata generation for output products.

Produces JSON sidecar files that describe each product with enough
information for cataloging, provenance tracking, and integration
with spatial data infrastructure.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import rasterio

from peatguard import __version__

logger = logging.getLogger(__name__)


def generate_product_metadata(
    product_path: Path,
    product_type: str,
    source_scenes: Optional[list[str]] = None,
    processing_params: Optional[dict[str, Any]] = None,
) -> Path:
    """Generate a STAC-compatible JSON metadata sidecar for a product.

    Args:
        product_path: Path to the GeoTIFF product.
        product_type: Product type identifier (e.g., 'subsidence_velocity').
        source_scenes: List of source scene IDs used to produce this product.
        processing_params: Key processing parameters for provenance.

    Returns:
        Path to the generated JSON metadata file.
    """
    metadata_path = product_path.with_suffix(".json")

    with rasterio.open(product_path) as src:
        bounds = src.bounds
        crs = str(src.crs)
        shape = (src.height, src.width)
        dtype = str(src.dtypes[0])
        band_count = src.count
        nodata = src.nodata

    metadata = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": product_path.stem,
        "properties": {
            "datetime": datetime.utcnow().isoformat() + "Z",
            "peatguard:product_type": product_type,
            "peatguard:pipeline_version": __version__,
            "proj:epsg": _extract_epsg(crs),
            "proj:shape": list(shape),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [bounds.left, bounds.bottom],
                    [bounds.right, bounds.bottom],
                    [bounds.right, bounds.top],
                    [bounds.left, bounds.top],
                    [bounds.left, bounds.bottom],
                ]
            ],
        },
        "bbox": [bounds.left, bounds.bottom, bounds.right, bounds.top],
        "assets": {
            "data": {
                "href": product_path.name,
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data"],
                "raster:bands": [
                    {
                        "data_type": dtype,
                        "nodata": nodata,
                    }
                ]
                * band_count,
            }
        },
    }

    if source_scenes:
        metadata["properties"]["peatguard:source_scenes"] = source_scenes

    if processing_params:
        metadata["properties"]["peatguard:processing"] = processing_params

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Metadata written: %s", metadata_path.name)
    return metadata_path


def _extract_epsg(crs_string: str) -> Optional[int]:
    """Extract EPSG code from a CRS string."""
    try:
        from pyproj import CRS

        crs = CRS.from_user_input(crs_string)
        return crs.to_epsg()
    except Exception:
        return None
