"""Hansen Global Forest Change data integration for temporal context.

Downloads and processes tiles from the Hansen et al. (2013) Global Forest
Change dataset (University of Maryland / Google). The "lossyear" band
indicates WHEN each pixel was deforested (2001-2023), which directly
relates to peat subsidence rate via the Hooijer et al. (2012) time-since-
drainage relationship.

Key insight: recently cleared peatland subsides faster (20-50 mm/yr in
first 5 years) than areas cleared decades ago (5-10 mm/yr). This temporal
dimension validates InSAR-measured subsidence rates and allows construction
of a time-adjusted risk product.

Data source:
    Hansen/UMD/Google/USGS/NASA "Global Forest Change 2000-2023 v1.11"
    https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/
    Resolution: 30m (1 arc-second)
    Tile size: 10x10 degrees
    Bands used: lossyear (uint8), treecover2000 (uint8)
    License: Free for all uses with attribution
"""

from __future__ import annotations

import json
import logging
import math
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask as rio_mask
from rasterio.warp import calculate_default_transform, reproject
from rasterio.windows import from_bounds as window_from_bounds
from shapely.geometry import box

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)

# Hansen GFC base URL and version
_HANSEN_BASE_URL = (
    "https://storage.googleapis.com/earthenginepartners-hansen"
)
_DEFAULT_VERSION = "GFC-2023-v1.11"

# Subsidence-time risk factors based on Hooijer et al. (2012)
# Years since clearing -> temporal risk multiplier
_RISK_RAPID = 1.2       # 0-5 years: rapid initial subsidence phase
_RISK_ONGOING = 1.0     # 5-15 years: ongoing but declining rate
_RISK_LONGTERM = 0.8    # 15+ years: long-term slow subsidence
_RISK_INTACT = 0.6      # Never cleared (intact forest): minimal C-band signal
_RISK_NONFOREST = 1.0   # Non-forest: neutral (subsidence rate from InSAR alone)

# Clearing year cohorts for validation statistics
_VALIDATION_COHORTS = {
    "2001-2005": (1, 5),
    "2006-2010": (6, 10),
    "2011-2015": (11, 15),
    "2016-2023": (16, 23),
}


def _determine_hansen_tile(bbox: list[float]) -> str:
    """Determine the Hansen 10x10 degree tile name covering a bounding box.

    Hansen tiles are named by their southwest corner, snapped to the nearest
    10-degree grid. For example, tile "10S_110E" covers latitudes 0 to -10
    and longitudes 110 to 120.

    Args:
        bbox: Bounding box as [west, south, east, north].

    Returns:
        Tile name string, e.g. "10S_110E".

    Raises:
        ValueError: If the AOI spans multiple tiles (not supported yet).
    """
    west, south, east, north = bbox

    # Snap to 10-degree grid (floor toward more negative)
    lat_tile_south = math.floor(south / 10) * 10
    lat_tile_north = math.floor(north / 10) * 10
    lon_tile_west = math.floor(west / 10) * 10
    lon_tile_east = math.floor(east / 10) * 10

    if lat_tile_south != lat_tile_north or lon_tile_west != lon_tile_east:
        logger.warning(
            "AOI spans multiple Hansen tiles. Using tile for center point. "
            "Multi-tile mosaicking is not yet implemented."
        )

    # Use the tile that covers the AOI center
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2
    lat_tile = math.floor(center_lat / 10) * 10
    lon_tile = math.floor(center_lon / 10) * 10

    # Format tile name: latitude uses absolute value + N/S, longitude + E/W
    # The tile name represents the edge AWAY from the equator
    if lat_tile >= 0:
        lat_str = f"{abs(lat_tile + 10)}N" if lat_tile + 10 > 0 else "00N"
    else:
        lat_str = f"{abs(lat_tile)}S" if lat_tile != 0 else "00N"

    if lon_tile >= 0:
        lon_str = f"{abs(lon_tile):03d}E"
    else:
        lon_str = f"{abs(lon_tile):03d}W"

    tile_name = f"{lat_str}_{lon_str}"
    logger.info("Hansen tile for AOI center (%.2f, %.2f): %s", center_lat, center_lon, tile_name)
    return tile_name


def download_hansen_tile(
    bbox: list[float],
    output_dir: Path,
    version: str = _DEFAULT_VERSION,
) -> dict[str, Path]:
    """Download Hansen GFC lossyear and treecover2000 tiles for the AOI.

    Downloads the full 10x10 degree tile to a temporary directory. These
    are ~100MB each but only need to be downloaded once. The caller should
    clip to the AOI after downloading.

    Args:
        bbox: Bounding box as [west, south, east, north].
        output_dir: Directory to save downloaded tiles.
        version: Hansen GFC version string.

    Returns:
        Dict mapping band names to local file paths.
        Empty dict if download fails.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tile_name = _determine_hansen_tile(bbox)
    bands = ["lossyear", "treecover2000"]
    downloaded = {}

    for band in bands:
        filename = f"Hansen_{version}_{band}_{tile_name}.tif"
        local_path = output_dir / filename

        # Cache: skip if already downloaded
        if local_path.exists():
            logger.info("Hansen %s tile already cached: %s", band, local_path)
            downloaded[band] = local_path
            continue

        url = f"{_HANSEN_BASE_URL}/{version}/{filename}"
        logger.info("Downloading Hansen %s tile: %s", band, url)

        try:
            urllib.request.urlretrieve(url, str(local_path))
            file_size_mb = local_path.stat().st_size / 1e6
            logger.info(
                "Downloaded Hansen %s: %s (%.1f MB)",
                band, local_path.name, file_size_mb,
            )
            downloaded[band] = local_path
        except Exception as exc:
            logger.warning(
                "Failed to download Hansen %s tile from %s: %s. "
                "Forest change analysis will be skipped.",
                band, url, exc,
            )
            # Clean up partial download
            if local_path.exists():
                local_path.unlink()

    return downloaded


def clip_to_aoi(
    input_path: Path,
    bbox: list[float],
    output_path: Path,
    reference_raster_path: Optional[Path] = None,
) -> Path:
    """Clip a Hansen tile to the AOI bounding box.

    Reads only the window covering the AOI from the full tile (avoids
    loading the entire ~100MB file into memory). Optionally resamples
    to match a reference raster grid for pixel-aligned analysis.

    Args:
        input_path: Path to the full Hansen tile GeoTIFF.
        bbox: Bounding box as [west, south, east, north].
        output_path: Path for the clipped output.
        reference_raster_path: Optional path to a reference raster. If
            provided, the output will be reprojected and resampled to
            match the reference grid (CRS, extent, resolution).

    Returns:
        Path to the clipped GeoTIFF.
    """
    west, south, east, north = bbox
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(input_path) as src:
        # Read only the window covering the AOI
        window = window_from_bounds(west, south, east, north, src.transform)
        data = src.read(1, window=window)
        win_transform = src.window_transform(window)
        src_crs = src.crs
        src_dtype = src.dtypes[0]

    if reference_raster_path is not None and Path(reference_raster_path).exists():
        # Resample to match the reference raster grid
        with rasterio.open(reference_raster_path) as ref:
            dst_crs = ref.crs
            dst_transform = ref.transform
            dst_width = ref.width
            dst_height = ref.height

        resampled = np.zeros((dst_height, dst_width), dtype=np.uint8)
        reproject(
            source=data,
            destination=resampled,
            src_transform=win_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )

        profile = {
            "driver": "GTiff",
            "dtype": "uint8",
            "width": dst_width,
            "height": dst_height,
            "count": 1,
            "crs": dst_crs,
            "transform": dst_transform,
            "compress": "DEFLATE",
        }
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(resampled, 1)
    else:
        # Write clipped data in native CRS (EPSG:4326)
        profile = {
            "driver": "GTiff",
            "dtype": src_dtype,
            "width": data.shape[1],
            "height": data.shape[0],
            "count": 1,
            "crs": src_crs,
            "transform": win_transform,
            "compress": "DEFLATE",
        }
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data, 1)

    logger.info(
        "Clipped Hansen tile to AOI: %s (%dx%d pixels)",
        output_path.name, data.shape[1] if reference_raster_path is None else dst_width,
        data.shape[0] if reference_raster_path is None else dst_height,
    )
    return output_path


def compute_time_since_clearing(
    lossyear: np.ndarray,
    reference_year: int = 2024,
) -> np.ndarray:
    """Compute years elapsed since forest clearing at each pixel.

    Args:
        lossyear: 2D uint8 array from Hansen lossyear band.
            0 = no loss detected; 1-23 = year of loss (2001-2023).
        reference_year: Year to compute time since clearing relative to.

    Returns:
        Float32 array. Positive values = years since clearing.
        NaN where lossyear == 0 (no loss detected).
    """
    time_since = np.full(lossyear.shape, np.nan, dtype=np.float32)

    cleared = lossyear > 0
    # lossyear values 1-23 correspond to years 2001-2023
    time_since[cleared] = reference_year - (2000 + lossyear[cleared].astype(np.float32))

    n_cleared = cleared.sum()
    n_total = lossyear.size
    logger.info(
        "Time since clearing: %d/%d pixels cleared (%.1f%%)",
        n_cleared, n_total, n_cleared / max(1, n_total) * 100,
    )
    if n_cleared > 0:
        valid_times = time_since[cleared]
        logger.info(
            "  Range: %.0f - %.0f years, median: %.0f years",
            np.nanmin(valid_times), np.nanmax(valid_times), np.nanmedian(valid_times),
        )

    return time_since


def compute_clearing_risk_factor(
    time_since_clearing: np.ndarray,
    treecover2000: Optional[np.ndarray] = None,
    forest_threshold: int = 50,
) -> np.ndarray:
    """Compute temporal risk multiplier based on time since deforestation.

    Based on the Hooijer et al. (2012) subsidence-time relationship for
    tropical peatlands: subsidence rate is highest in the first 5 years
    after drainage/clearing, then gradually declines.

    Risk factors:
        - 0-5 years since clearing: 1.2 (rapid initial subsidence)
        - 5-15 years since clearing: 1.0 (ongoing but declining)
        - 15+ years since clearing: 0.8 (long-term slow subsidence)
        - Never cleared, was forest in 2000: 0.6 (intact forest, hard
          to detect with C-band due to canopy decorrelation)
        - Non-forest (no loss, low tree cover in 2000): 1.0 (neutral)

    Args:
        time_since_clearing: Float32 array from compute_time_since_clearing().
            NaN = no loss detected.
        treecover2000: Optional uint8 array of tree cover percentage in 2000.
            Used to distinguish intact forest from non-forest among pixels
            with no detected loss.
        forest_threshold: Tree cover percentage above which a pixel is
            considered forested in 2000.

    Returns:
        Float32 array of temporal risk multipliers.
    """
    risk = np.full(time_since_clearing.shape, _RISK_NONFOREST, dtype=np.float32)

    cleared = np.isfinite(time_since_clearing)

    # Apply time-dependent risk factors for cleared pixels
    rapid = cleared & (time_since_clearing <= 5)
    ongoing = cleared & (time_since_clearing > 5) & (time_since_clearing <= 15)
    longterm = cleared & (time_since_clearing > 15)

    risk[rapid] = _RISK_RAPID
    risk[ongoing] = _RISK_ONGOING
    risk[longterm] = _RISK_LONGTERM

    # For pixels with no loss: distinguish intact forest from non-forest
    no_loss = ~cleared
    if treecover2000 is not None:
        intact_forest = no_loss & (treecover2000 >= forest_threshold)
        risk[intact_forest] = _RISK_INTACT
        n_intact = intact_forest.sum()
        n_nonforest = (no_loss & (treecover2000 < forest_threshold)).sum()
    else:
        n_intact = 0
        n_nonforest = no_loss.sum()

    logger.info(
        "Clearing risk factor distribution: "
        "rapid(0-5yr)=%d, ongoing(5-15yr)=%d, longterm(15+yr)=%d, "
        "intact_forest=%d, non_forest=%d",
        rapid.sum(), ongoing.sum(), longterm.sum(), n_intact, n_nonforest,
    )

    return risk


def generate_forest_change_products(
    bbox: list[float],
    reference_raster_path: Path,
    output_dir: Path,
    reference_year: int = 2024,
    hansen_version: str = _DEFAULT_VERSION,
) -> dict[str, Path]:
    """Generate all forest change products for the AOI.

    Main entry point for forest change analysis. Downloads Hansen GFC
    tiles, clips to the AOI, and computes derived products including
    time since clearing and temporal risk multiplier.

    Args:
        bbox: Bounding box as [west, south, east, north].
        reference_raster_path: Path to a reference raster (velocity or
            backscatter) for grid alignment.
        output_dir: Directory for output products.
        reference_year: Year for time-since-clearing computation.
        hansen_version: Hansen GFC version string.

    Returns:
        Dict mapping product names to output file paths.
    """
    output_dir = Path(output_dir)
    products = {}

    # Download Hansen tiles to a temporary directory
    tmp_dir = Path(tempfile.gettempdir()) / "hansen_tiles"
    tile_paths = download_hansen_tile(bbox, tmp_dir, version=hansen_version)

    if "lossyear" not in tile_paths:
        logger.warning(
            "Hansen lossyear tile not available. "
            "Forest change products will be skipped."
        )
        return products

    # Clip lossyear to AOI
    lossyear_clipped_path = output_dir / "deforestation_year.tif"
    clip_to_aoi(
        tile_paths["lossyear"],
        bbox,
        lossyear_clipped_path,
        reference_raster_path=reference_raster_path,
    )
    products["deforestation_year"] = lossyear_clipped_path

    # Clip treecover2000 to AOI (if available)
    treecover_clipped_path = None
    if "treecover2000" in tile_paths:
        treecover_clipped_path = output_dir / "treecover2000.tif"
        clip_to_aoi(
            tile_paths["treecover2000"],
            bbox,
            treecover_clipped_path,
            reference_raster_path=reference_raster_path,
        )
        products["treecover2000"] = treecover_clipped_path

    # Read clipped arrays for derived products
    ly_data, ly_meta = read_raster(lossyear_clipped_path)
    lossyear = ly_data[0]

    treecover = None
    if treecover_clipped_path is not None:
        tc_data, _ = read_raster(treecover_clipped_path)
        treecover = tc_data[0]

    # Compute time since clearing
    time_since = compute_time_since_clearing(lossyear, reference_year=reference_year)
    time_since_path = output_dir / "time_since_clearing.tif"
    write_cog(
        data=time_since,
        output_path=time_since_path,
        crs=ly_meta["crs"],
        transform=ly_meta["transform"],
        nodata=np.nan,
        band_names=["time_since_clearing_years"],
        dtype="float32",
    )
    products["time_since_clearing"] = time_since_path

    # Compute temporal risk multiplier
    risk_factor = compute_clearing_risk_factor(time_since, treecover2000=treecover)
    risk_factor_path = output_dir / "clearing_risk_factor.tif"
    write_cog(
        data=risk_factor,
        output_path=risk_factor_path,
        crs=ly_meta["crs"],
        transform=ly_meta["transform"],
        nodata=-9999.0,
        band_names=["clearing_risk_factor"],
        dtype="float32",
    )
    products["clearing_risk_factor"] = risk_factor_path

    logger.info(
        "Forest change products generated: %s",
        ", ".join(products.keys()),
    )
    return products


def validate_subsidence_vs_clearing(
    velocity_path: Path,
    lossyear_path: Path,
    output_dir: Path,
) -> dict:
    """Validate InSAR subsidence rates against forest clearing year cohorts.

    For each clearing cohort (2001-2005, 2006-2010, 2011-2015, 2016-2023),
    computes the mean subsidence rate. If more recently cleared areas show
    higher subsidence rates, this provides independent validation that the
    InSAR signal captures real peat subsidence driven by drainage.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        lossyear_path: Path to clipped deforestation_year GeoTIFF.
        output_dir: Directory for output JSON report.

    Returns:
        Dict with per-cohort statistics and overall assessment.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vel_data, vel_meta = read_raster(velocity_path)
    ly_data, ly_meta = read_raster(lossyear_path)

    velocity = vel_data[0]
    lossyear = ly_data[0]

    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    # Handle shape mismatch by reprojecting lossyear to velocity grid
    if lossyear.shape != velocity.shape:
        logger.info(
            "Reprojecting lossyear to velocity grid (%s -> %s)",
            lossyear.shape, velocity.shape,
        )
        ly_reprojected = np.zeros(velocity.shape, dtype=np.uint8)
        reproject(
            source=lossyear,
            destination=ly_reprojected,
            src_transform=ly_meta["transform"],
            src_crs=ly_meta["crs"],
            dst_transform=vel_meta["transform"],
            dst_crs=vel_meta["crs"],
            resampling=Resampling.nearest,
        )
        lossyear = ly_reprojected

    valid_vel = (velocity != vel_nodata) & np.isfinite(velocity)

    cohort_stats = {}
    for cohort_name, (year_start, year_end) in _VALIDATION_COHORTS.items():
        cohort_mask = (lossyear >= year_start) & (lossyear <= year_end) & valid_vel
        n_pixels = int(cohort_mask.sum())

        if n_pixels == 0:
            cohort_stats[cohort_name] = {
                "n_pixels": 0,
                "mean_velocity_mm_yr": None,
                "std_velocity_mm_yr": None,
                "median_velocity_mm_yr": None,
            }
            continue

        cohort_vel = velocity[cohort_mask]
        cohort_stats[cohort_name] = {
            "n_pixels": n_pixels,
            "mean_velocity_mm_yr": float(np.mean(cohort_vel)),
            "std_velocity_mm_yr": float(np.std(cohort_vel)),
            "median_velocity_mm_yr": float(np.median(cohort_vel)),
        }
        logger.info(
            "Clearing cohort %s: n=%d, mean=%.1f mm/yr, median=%.1f mm/yr",
            cohort_name, n_pixels,
            cohort_stats[cohort_name]["mean_velocity_mm_yr"],
            cohort_stats[cohort_name]["median_velocity_mm_yr"],
        )

    # Also compute stats for no-loss pixels
    no_loss_mask = (lossyear == 0) & valid_vel
    n_no_loss = int(no_loss_mask.sum())
    if n_no_loss > 0:
        no_loss_vel = velocity[no_loss_mask]
        cohort_stats["no_loss"] = {
            "n_pixels": n_no_loss,
            "mean_velocity_mm_yr": float(np.mean(no_loss_vel)),
            "std_velocity_mm_yr": float(np.std(no_loss_vel)),
            "median_velocity_mm_yr": float(np.median(no_loss_vel)),
        }
    else:
        cohort_stats["no_loss"] = {"n_pixels": 0}

    # Assess whether the expected pattern holds: more recent clearing -> more subsidence
    recent_mean = cohort_stats.get("2016-2023", {}).get("mean_velocity_mm_yr")
    old_mean = cohort_stats.get("2001-2005", {}).get("mean_velocity_mm_yr")
    no_loss_mean = cohort_stats.get("no_loss", {}).get("mean_velocity_mm_yr")

    assessment = "insufficient_data"
    if recent_mean is not None and old_mean is not None:
        if recent_mean < old_mean:
            assessment = "consistent"
            logger.info(
                "Validation CONSISTENT: recent clearing (%.1f mm/yr) shows "
                "more subsidence than old clearing (%.1f mm/yr)",
                recent_mean, old_mean,
            )
        else:
            assessment = "inconsistent"
            logger.warning(
                "Validation INCONSISTENT: recent clearing (%.1f mm/yr) does NOT "
                "show more subsidence than old clearing (%.1f mm/yr). "
                "Possible causes: small sample size, spatial heterogeneity, "
                "or InSAR noise.",
                recent_mean, old_mean,
            )

    report = {
        "dataset": "Hansen GFC v1.11",
        "reference": "Hansen et al. (2013), Hooijer et al. (2012)",
        "cohort_statistics": cohort_stats,
        "assessment": assessment,
        "description": (
            "Compares mean InSAR subsidence velocity across forest clearing "
            "year cohorts. Hooijer et al. (2012) predicts higher subsidence "
            "rates for more recently cleared peatland."
        ),
    }

    report_path = output_dir / "validation_clearing.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Forest change validation report written: %s", report_path)

    return report
