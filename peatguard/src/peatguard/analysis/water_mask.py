"""Water body detection from SAR backscatter.

Identifies open water surfaces to prevent false subsidence detections.
Water bodies show low InSAR coherence and can be misclassified as
"severe subsidence" because some pixels pass the coherence threshold.

Primary method: VV backscatter thresholding. Water produces specular
reflection, resulting in very low backscatter (typically < -20 dB).
This is more reliable than coherence alone for water discrimination.

Future extension: Sentinel-2 optical indices (MNDWI, NDWI, NDVI) for
improved water/vegetation discrimination. The module is designed to
accept either SAR or optical inputs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from peatguard.config import WaterMaskConfig
from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)


def compute_water_mask_vv(
    vv_db: np.ndarray,
    threshold_db: float = -20.0,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Detect water bodies from VV backscatter in dB.

    Water surfaces produce specular reflection, giving very low
    backscatter values. Pixels below the threshold are classified
    as water.

    Args:
        vv_db: 2D array of VV backscatter in dB scale.
        threshold_db: Backscatter threshold in dB. Pixels below this
            value are classified as water. Default -20 dB is
            conservative for tropical peatlands (avoids flagging
            wet soil or flooded vegetation).
        nodata: NoData sentinel value to exclude.

    Returns:
        Boolean 2D array where True = water pixel.
    """
    valid = (vv_db != nodata) & np.isfinite(vv_db)
    water = valid & (vv_db < threshold_db)

    n_valid = valid.sum()
    n_water = water.sum()
    pct = (n_water / n_valid * 100) if n_valid > 0 else 0.0
    logger.info(
        "VV water mask: threshold=%.1f dB, %d/%d pixels (%.1f%%) classified as water",
        threshold_db,
        n_water,
        n_valid,
        pct,
    )
    return water


def compute_water_mask_linear(
    vv_linear: np.ndarray,
    threshold_db: float = -20.0,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Detect water bodies from VV backscatter in linear (power) scale.

    Converts the threshold from dB to linear scale and applies it.
    Use this when the backscatter composite is in linear scale (not dB).

    Args:
        vv_linear: 2D array of VV backscatter in linear (power) scale.
        threshold_db: Backscatter threshold in dB (converted internally).
        nodata: NoData sentinel value to exclude.

    Returns:
        Boolean 2D array where True = water pixel.
    """
    threshold_linear = 10.0 ** (threshold_db / 10.0)
    valid = (vv_linear != nodata) & np.isfinite(vv_linear) & (vv_linear > 0)
    water = valid & (vv_linear < threshold_linear)

    n_valid = valid.sum()
    n_water = water.sum()
    pct = (n_water / n_valid * 100) if n_valid > 0 else 0.0
    logger.info(
        "VV water mask (linear): threshold=%.1f dB (%.6f linear), "
        "%d/%d pixels (%.1f%%) classified as water",
        threshold_db,
        threshold_linear,
        n_water,
        n_valid,
        pct,
    )
    return water


def morphological_cleanup_water(
    water_mask: np.ndarray,
    min_size_pixels: int = 50,
    closing_radius: int = 3,
) -> np.ndarray:
    """Clean up water mask using morphological operations.

    Removes small noise detections and fills holes in water bodies.
    Uses a larger minimum size than canal detection because water
    bodies are area features, not linear ones.

    Args:
        water_mask: Binary water mask (True = water).
        min_size_pixels: Minimum connected component size to retain.
            Default 50 pixels at 10m resolution = 5000 sq meters,
            roughly a small pond.
        closing_radius: Radius for morphological closing (fills small
            gaps within water bodies).

    Returns:
        Cleaned binary water mask.
    """
    from skimage.morphology import binary_closing, disk, remove_small_objects

    # Close small gaps within water bodies
    if closing_radius > 0:
        closed = binary_closing(water_mask, disk(closing_radius))
    else:
        closed = water_mask.copy()

    # Remove small isolated detections (noise, puddles)
    cleaned = remove_small_objects(closed, min_size=min_size_pixels)

    logger.info(
        "Water mask cleanup: %d -> %d pixels (min_size=%d, closing_radius=%d)",
        water_mask.sum(),
        cleaned.sum(),
        min_size_pixels,
        closing_radius,
    )
    return cleaned


def exclude_canals_from_water(
    water_mask: np.ndarray,
    canal_mask: np.ndarray,
) -> np.ndarray:
    """Remove canal pixels from the water mask.

    Canals are narrow linear water features that should be preserved
    in the canal detection layer. This prevents double-counting and
    ensures canal_detect.py results are not affected.

    Args:
        water_mask: Binary water body mask.
        canal_mask: Binary canal mask from canal_detect.py.

    Returns:
        Water mask with canal pixels removed.
    """
    combined = water_mask & ~canal_mask
    n_removed = water_mask.sum() - combined.sum()
    if n_removed > 0:
        logger.info(
            "Excluded %d canal pixels from water mask (%d -> %d water pixels)",
            n_removed,
            water_mask.sum(),
            combined.sum(),
        )
    return combined


def compute_ndvi(
    nir: np.ndarray,
    red: np.ndarray,
    nodata: float = 0.0,
) -> np.ndarray:
    """Compute NDVI from NIR and Red bands.

    NDVI = (NIR - Red) / (NIR + Red)

    Intended for future Sentinel-2 integration. NDVI can serve as
    a validation layer: water has NDVI < 0, bare soil ~ 0,
    vegetation > 0.3, dense vegetation > 0.6.

    Args:
        nir: 2D array of NIR reflectance (Sentinel-2 B8, 10m).
        red: 2D array of Red reflectance (Sentinel-2 B4, 10m).
        nodata: NoData value in the input bands.

    Returns:
        2D float32 array of NDVI values (-1 to 1). NoData pixels
        are set to NaN.
    """
    valid = (
        (nir != nodata)
        & (red != nodata)
        & np.isfinite(nir)
        & np.isfinite(red)
    )
    denominator = nir.astype(np.float32) + red.astype(np.float32)
    numerator = nir.astype(np.float32) - red.astype(np.float32)

    ndvi = np.full_like(nir, np.nan, dtype=np.float32)
    nonzero = valid & (denominator != 0)
    ndvi[nonzero] = numerator[nonzero] / denominator[nonzero]

    logger.info(
        "NDVI: min=%.3f, max=%.3f, mean=%.3f (valid pixels: %d)",
        np.nanmin(ndvi),
        np.nanmax(ndvi),
        np.nanmean(ndvi),
        nonzero.sum(),
    )
    return ndvi


def compute_mndwi(
    green: np.ndarray,
    swir: np.ndarray,
    nodata: float = 0.0,
) -> np.ndarray:
    """Compute MNDWI from Green and SWIR bands.

    MNDWI = (Green - SWIR) / (Green + SWIR)

    Intended for future Sentinel-2 integration. MNDWI > 0 indicates
    water. More reliable than NDWI for urban/built-up areas, though
    both work well in peatland environments.

    Args:
        green: 2D array of Green reflectance (Sentinel-2 B3, 10m).
        swir: 2D array of SWIR reflectance (Sentinel-2 B11, 20m).
            Must be resampled to match Green resolution.
        nodata: NoData value in the input bands.

    Returns:
        2D float32 array of MNDWI values (-1 to 1). NoData pixels
        are set to NaN.
    """
    valid = (
        (green != nodata)
        & (swir != nodata)
        & np.isfinite(green)
        & np.isfinite(swir)
    )
    denominator = green.astype(np.float32) + swir.astype(np.float32)
    numerator = green.astype(np.float32) - swir.astype(np.float32)

    mndwi = np.full_like(green, np.nan, dtype=np.float32)
    nonzero = valid & (denominator != 0)
    mndwi[nonzero] = numerator[nonzero] / denominator[nonzero]

    logger.info(
        "MNDWI: min=%.3f, max=%.3f, mean=%.3f (valid pixels: %d)",
        np.nanmin(mndwi),
        np.nanmax(mndwi),
        np.nanmean(mndwi),
        nonzero.sum(),
    )
    return mndwi


def generate_water_mask(
    vv_path: Path,
    output_path: Path,
    canal_mask_path: Optional[Path] = None,
    water_config: Optional[WaterMaskConfig] = None,
    is_db: bool = False,
) -> Path:
    """Generate a water body mask from VV backscatter.

    Full pipeline: threshold -> morphological cleanup -> optional
    canal exclusion -> write COG output.

    Args:
        vv_path: Path to VV backscatter GeoTIFF (linear or dB scale).
        output_path: Path for the water mask output (uint8 COG).
        canal_mask_path: Optional path to canal mask GeoTIFF. If
            provided, canal pixels are excluded from the water mask
            to avoid interfering with canal_detect.py results.
        water_config: Water mask configuration. Uses defaults if None.
        is_db: If True, input is in dB scale. If False, linear scale.

    Returns:
        Path to the water mask GeoTIFF (uint8: 0=not water, 1=water).
    """
    if water_config is None:
        water_config = WaterMaskConfig()

    logger.info("Generating water mask from %s (dB=%s)", vv_path.name, is_db)

    data, metadata = read_raster(vv_path)
    vv = data[0]

    nodata = metadata["nodata"] if metadata["nodata"] is not None else -9999.0

    # Compute raw water mask
    if is_db:
        raw_mask = compute_water_mask_vv(
            vv, threshold_db=water_config.vv_threshold_db, nodata=nodata
        )
    else:
        raw_mask = compute_water_mask_linear(
            vv, threshold_db=water_config.vv_threshold_db, nodata=nodata
        )

    # Morphological cleanup
    clean_mask = morphological_cleanup_water(
        raw_mask,
        min_size_pixels=water_config.min_water_size_pixels,
        closing_radius=water_config.closing_radius,
    )

    # Exclude canal pixels if canal mask is available
    if canal_mask_path is not None and canal_mask_path.exists():
        canal_data, _ = read_raster(canal_mask_path)
        canal_mask = canal_data[0].astype(bool)
        clean_mask = exclude_canals_from_water(clean_mask, canal_mask)

    # Write output
    result_path = write_cog(
        data=clean_mask.astype(np.uint8),
        output_path=output_path,
        crs=metadata["crs"],
        transform=metadata["transform"],
        nodata=255,
        band_names=["water_mask"],
        dtype="uint8",
    )

    logger.info(
        "Water mask written: %d water pixels (%.1f%% of valid area)",
        clean_mask.sum(),
        clean_mask.sum() / max(1, (vv != nodata).sum()) * 100,
    )
    return result_path
