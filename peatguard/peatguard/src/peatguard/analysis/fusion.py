"""Multi-sensor fusion of C-band and L-band InSAR velocity maps.

Combines Sentinel-1 (C-band, 5.6cm wavelength) and NISAR (L-band, 24cm
wavelength) velocity products into a unified subsidence map. The two
sensors have complementary coverage:

    - C-band: high coherence over cleared land, plantations, urban areas.
      Decorrelates rapidly over dense tropical forest canopy.
    - L-band: maintains coherence through forest canopy due to longer
      wavelength penetrating vegetation. Lower sensitivity to small
      deformations but works where C-band fails entirely.

Fusion strategy: coherence-weighted averaging. Each sensor's velocity
contribution is weighted by its temporal coherence at each pixel. This
is physically motivated because higher coherence implies a more reliable
phase measurement (lower phase noise), so the fused estimate naturally
favors the sensor with better signal quality at each location.

    fused_velocity = (coh_c * vel_c + coh_l * vel_l) / (coh_c + coh_l)

Where only one sensor has valid data (coherence above threshold), that
sensor's velocity is used directly. Where neither sensor has valid data,
the pixel is marked as nodata.

References:
    - Hanssen, R. (2001). Radar Interferometry. Kluwer Academic.
    - Zebker & Villasenor (1992). Decorrelation in interferometric radar
      echoes. IEEE TGRS, 30(5), 950-959.
    - Osmano et al. (2023). Multi-frequency InSAR fusion for tropical
      peatland monitoring. Remote Sensing of Environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.crs import CRS as RioCRS
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)

# Sensor coverage classification codes
COVERAGE_NONE = 0
COVERAGE_CBAND_ONLY = 1
COVERAGE_LBAND_ONLY = 2
COVERAGE_BOTH = 3

COVERAGE_LABELS = {
    COVERAGE_NONE: "No valid data",
    COVERAGE_CBAND_ONLY: "C-band (Sentinel-1) only",
    COVERAGE_LBAND_ONLY: "L-band (NISAR) only",
    COVERAGE_BOTH: "Both sensors",
}


def fuse_velocity_maps(
    c_vel: np.ndarray,
    c_coh: np.ndarray,
    l_vel: np.ndarray,
    l_coh: np.ndarray,
    nodata: float = -9999.0,
    min_coherence: float = 0.3,
    c_band_weight_boost: float = 1.0,
) -> np.ndarray:
    """Fuse C-band and L-band velocity maps using coherence weighting.

    The fusion uses temporal coherence as a per-pixel quality weight.
    Higher coherence indicates lower phase noise and therefore a more
    reliable velocity estimate. The coherence-weighted average naturally
    favors the sensor with better signal quality at each pixel.

    An optional C-band weight boost can be applied to increase the
    contribution of C-band measurements in areas where both sensors
    have valid data. This is useful because C-band has higher
    deformation sensitivity (shorter wavelength) in cleared areas
    where it maintains coherence.

    Args:
        c_vel: C-band velocity array (mm/yr). Nodata pixels have value
            equal to the nodata parameter.
        c_coh: C-band temporal coherence array (0-1).
        l_vel: L-band velocity array (mm/yr). Must be same shape as c_vel
            (caller is responsible for reprojection).
        l_coh: L-band temporal coherence array (0-1).
        nodata: Nodata value in velocity arrays.
        min_coherence: Minimum coherence for a sensor to contribute.
            Pixels below this threshold are treated as invalid for
            that sensor. Default 0.3 matches the pipeline's coherence
            masking threshold.
        c_band_weight_boost: Multiplicative boost applied to C-band
            coherence weight. 1.0 = no boost (pure coherence weighting).
            Values > 1.0 increase C-band influence in dual-coverage areas.

    Returns:
        Fused velocity array (mm/yr) with nodata where neither sensor
        has valid data.
    """
    # Identify valid pixels per sensor
    c_valid = (c_vel != nodata) & np.isfinite(c_vel) & (c_coh >= min_coherence)
    l_valid = (l_vel != nodata) & np.isfinite(l_vel) & (l_coh >= min_coherence)

    # Initialize output with nodata
    fused = np.full_like(c_vel, nodata, dtype=np.float32)

    # Case 1: only C-band valid
    c_only = c_valid & ~l_valid
    fused[c_only] = c_vel[c_only]

    # Case 2: only L-band valid
    l_only = l_valid & ~c_valid
    fused[l_only] = l_vel[l_only]

    # Case 3: both sensors valid -- coherence-weighted average
    both = c_valid & l_valid
    if both.any():
        w_c = c_coh[both] * c_band_weight_boost
        w_l = l_coh[both]
        w_total = w_c + w_l
        fused[both] = (w_c * c_vel[both] + w_l * l_vel[both]) / w_total

    # Log coverage statistics
    total = c_vel.size
    n_c_only = c_only.sum()
    n_l_only = l_only.sum()
    n_both = both.sum()
    n_none = total - n_c_only - n_l_only - n_both
    logger.info(
        "Fusion coverage: C-band only=%d (%.1f%%), L-band only=%d (%.1f%%), "
        "both=%d (%.1f%%), none=%d (%.1f%%)",
        n_c_only, 100.0 * n_c_only / total,
        n_l_only, 100.0 * n_l_only / total,
        n_both, 100.0 * n_both / total,
        n_none, 100.0 * n_none / total,
    )

    valid_fused = fused != nodata
    if valid_fused.any():
        logger.info(
            "Fused velocity: min=%.1f, max=%.1f, mean=%.1f mm/yr",
            np.nanmin(fused[valid_fused]),
            np.nanmax(fused[valid_fused]),
            np.nanmean(fused[valid_fused]),
        )

    return fused


def fuse_coherence_maps(
    c_coh: np.ndarray,
    l_coh: np.ndarray,
) -> np.ndarray:
    """Compute fused coherence as the maximum of both sensors.

    The fused coherence represents the best available measurement
    quality at each pixel. Taking the maximum (rather than the mean)
    ensures the quality metric reflects the most reliable sensor at
    each location, which matches how the velocity fusion works
    (dominated by the higher-coherence sensor).

    Args:
        c_coh: C-band temporal coherence (0-1).
        l_coh: L-band temporal coherence (0-1).

    Returns:
        Fused coherence array (0-1).
    """
    fused_coh = np.maximum(c_coh, l_coh).astype(np.float32)

    logger.info(
        "Fused coherence: min=%.3f, max=%.3f, mean=%.3f",
        np.nanmin(fused_coh),
        np.nanmax(fused_coh),
        np.nanmean(fused_coh),
    )

    return fused_coh


def compute_sensor_coverage(
    c_vel: np.ndarray,
    l_vel: np.ndarray,
    c_coh: np.ndarray,
    l_coh: np.ndarray,
    nodata: float = -9999.0,
    min_coherence: float = 0.3,
) -> np.ndarray:
    """Classify each pixel by which sensors provide valid data.

    This is a diagnostic product that shows the spatial complementarity
    of C-band and L-band coverage. In tropical peatlands, the typical
    pattern is:
        - C-band only over plantations, cleared areas, urban
        - L-band only over intact peat swamp forest
        - Both sensors over transitional/degraded forest
        - Neither over persistent water bodies

    Args:
        c_vel: C-band velocity array (mm/yr).
        l_vel: L-band velocity array (mm/yr).
        c_coh: C-band temporal coherence (0-1).
        l_coh: L-band temporal coherence (0-1).
        nodata: Nodata value in velocity arrays.
        min_coherence: Minimum coherence for valid classification.

    Returns:
        uint8 array: 0=none, 1=C-band only, 2=L-band only, 3=both.
    """
    c_valid = (c_vel != nodata) & np.isfinite(c_vel) & (c_coh >= min_coherence)
    l_valid = (l_vel != nodata) & np.isfinite(l_vel) & (l_coh >= min_coherence)

    coverage = np.full(c_vel.shape, COVERAGE_NONE, dtype=np.uint8)
    coverage[c_valid & ~l_valid] = COVERAGE_CBAND_ONLY
    coverage[l_valid & ~c_valid] = COVERAGE_LBAND_ONLY
    coverage[c_valid & l_valid] = COVERAGE_BOTH

    for code, label in COVERAGE_LABELS.items():
        count = (coverage == code).sum()
        pct = 100.0 * count / coverage.size if coverage.size > 0 else 0
        logger.info("  %s: %d pixels (%.1f%%)", label, count, pct)

    return coverage


def _reproject_to_reference(
    src_path: Path,
    ref_path: Path,
    resampling: Resampling = Resampling.bilinear,
) -> tuple[np.ndarray, dict]:
    """Reproject a raster to match the CRS, extent, and resolution of a reference.

    This handles the case where C-band and L-band products have different
    CRS (e.g., EPSG:4326 vs EPSG:32649) or different pixel grids. The
    L-band product is reprojected to match the C-band grid so that
    pixel-wise fusion is valid.

    Args:
        src_path: Path to the raster to reproject.
        ref_path: Path to the reference raster (target grid).
        resampling: Resampling method. Bilinear for continuous data
            (velocity, coherence), nearest for categorical.

    Returns:
        Tuple of (reprojected_data, reference_metadata).
    """
    ref_data, ref_meta = read_raster(ref_path)

    with rasterio.open(src_path) as src:
        if src.crs == ref_meta["crs"] and src.shape == (ref_meta["height"], ref_meta["width"]):
            # No reprojection needed -- grids already match
            data = src.read(1)
            logger.info(
                "No reprojection needed for %s (same CRS and shape)", src_path.name
            )
            return data, ref_meta

        logger.info(
            "Reprojecting %s from %s (%dx%d) to %s (%dx%d)",
            src_path.name,
            src.crs,
            src.width,
            src.height,
            ref_meta["crs"],
            ref_meta["width"],
            ref_meta["height"],
        )

        dst_array = np.full(
            (ref_meta["height"], ref_meta["width"]),
            src.nodata if src.nodata is not None else -9999.0,
            dtype=np.float32,
        )

        reproject(
            source=rasterio.band(src, 1),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_meta["transform"],
            dst_crs=ref_meta["crs"],
            resampling=resampling,
        )

    return dst_array, ref_meta


def generate_fusion_products(
    c_vel_path: Path,
    c_coh_path: Path,
    l_vel_path: Path,
    l_coh_path: Path,
    output_dir: Path,
    nodata: float = -9999.0,
    min_coherence: float = 0.3,
    c_band_weight_boost: float = 1.0,
) -> dict[str, Path]:
    """Generate all multi-sensor fusion products.

    Reads C-band and L-band velocity and coherence rasters, reprojects
    L-band to the C-band grid if necessary, performs coherence-weighted
    fusion, and writes output COG GeoTIFFs.

    The C-band grid is used as the reference because Sentinel-1 typically
    has finer resolution (10m) compared to NISAR L-band products, and
    C-band products are the primary baseline for the PeatGuard pipeline.

    Args:
        c_vel_path: Path to C-band velocity GeoTIFF (mm/yr).
        c_coh_path: Path to C-band temporal coherence GeoTIFF (0-1).
        l_vel_path: Path to L-band velocity GeoTIFF (mm/yr).
        l_coh_path: Path to L-band temporal coherence GeoTIFF (0-1).
        output_dir: Directory for output products.
        nodata: Nodata value for velocity products.
        min_coherence: Minimum coherence for a sensor to contribute.
        c_band_weight_boost: Weight boost for C-band (1.0 = no boost).

    Returns:
        Dict mapping product names to output file paths:
            - fused_velocity: coherence-weighted fused velocity (mm/yr)
            - fused_coherence: maximum coherence from both sensors (0-1)
            - sensor_coverage: coverage classification (uint8, 0-3)
    """
    logger.info("=== Multi-sensor fusion: C-band + L-band ===")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read C-band products (reference grid)
    logger.info("Reading C-band velocity: %s", c_vel_path.name)
    c_vel_data, c_meta = read_raster(c_vel_path)
    c_vel = c_vel_data[0].astype(np.float32)

    logger.info("Reading C-band coherence: %s", c_coh_path.name)
    c_coh_data, _ = read_raster(c_coh_path)
    c_coh = c_coh_data[0].astype(np.float32)

    # Read L-band products, reprojecting to C-band grid if needed
    logger.info("Reading L-band velocity: %s", l_vel_path.name)
    l_vel, _ = _reproject_to_reference(l_vel_path, c_vel_path, Resampling.bilinear)
    l_vel = l_vel.astype(np.float32)

    logger.info("Reading L-band coherence: %s", l_coh_path.name)
    l_coh, _ = _reproject_to_reference(l_coh_path, c_vel_path, Resampling.bilinear)
    l_coh = l_coh.astype(np.float32)

    # Verify shapes match after reprojection
    if c_vel.shape != l_vel.shape:
        raise ValueError(
            f"Shape mismatch after reprojection: C-band {c_vel.shape} vs L-band {l_vel.shape}. "
            "This indicates a bug in the reprojection logic."
        )

    # Perform fusion
    logger.info(
        "Fusing velocity maps (min_coherence=%.2f, c_band_weight_boost=%.2f)",
        min_coherence,
        c_band_weight_boost,
    )
    fused_vel = fuse_velocity_maps(
        c_vel, c_coh, l_vel, l_coh,
        nodata=nodata,
        min_coherence=min_coherence,
        c_band_weight_boost=c_band_weight_boost,
    )

    fused_coh = fuse_coherence_maps(c_coh, l_coh)

    coverage = compute_sensor_coverage(
        c_vel, l_vel, c_coh, l_coh,
        nodata=nodata,
        min_coherence=min_coherence,
    )

    # Extract georeferencing from C-band reference
    crs = c_meta["crs"]
    transform = c_meta["transform"]

    products = {}

    # Write fused velocity
    vel_path = write_cog(
        data=fused_vel,
        output_path=output_dir / "fused_velocity.tif",
        crs=crs,
        transform=transform,
        nodata=nodata,
        band_names=["fused_velocity_mm_yr"],
        dtype="float32",
    )
    products["fused_velocity"] = vel_path

    # Write fused coherence
    coh_path = write_cog(
        data=fused_coh,
        output_path=output_dir / "fused_coherence.tif",
        crs=crs,
        transform=transform,
        nodata=nodata,
        band_names=["fused_coherence"],
        dtype="float32",
    )
    products["fused_coherence"] = coh_path

    # Write sensor coverage classification
    cov_path = write_cog(
        data=coverage,
        output_path=output_dir / "sensor_coverage.tif",
        crs=crs,
        transform=transform,
        nodata=COVERAGE_NONE,
        band_names=["sensor_coverage"],
        dtype="uint8",
    )
    products["sensor_coverage"] = cov_path

    logger.info(
        "Fusion complete: %d products written to %s", len(products), output_dir
    )
    return products
