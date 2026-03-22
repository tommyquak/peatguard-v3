"""SAR scene discovery via ASF DAAC.

Uses asf_search as the primary interface to the Alaska Satellite Facility,
which provides the most reliable access to Sentinel-1 SLC/GRD and NISAR
L-band SLC products. Falls back to earthaccess (NASA CMR) if ASF is
unavailable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import asf_search as asf

from peatguard.config import PeatGuardConfig

logger = logging.getLogger(__name__)


def _search_sentinel1(
    config: PeatGuardConfig,
    start_date: str,
    end_date: str,
    processing_level: str,
    max_results: Optional[int],
) -> list[asf.ASFProduct]:
    """Search ASF DAAC for Sentinel-1 scenes."""
    west, south, east, north = config.aoi.bbox
    return list(asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=processing_level,
        beamMode=asf.BEAMMODE.IW,
        intersectsWith=f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))",
        start=start_date,
        end=end_date,
        maxResults=max_results,
    ))


def _search_nisar(
    config: PeatGuardConfig,
    start_date: str,
    end_date: str,
    processing_level: str,
    max_results: Optional[int],
) -> list[asf.ASFProduct]:
    """Search ASF DAAC for NISAR L-band scenes.

    NISAR L-SAR SLC products are available from ASF since February 2026.
    The platform keyword is 'NISAR' in asf_search.
    """
    west, south, east, north = config.aoi.bbox
    return list(asf.search(
        platform="NISAR",
        processingLevel=processing_level,
        intersectsWith=f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))",
        start=start_date,
        end=end_date,
        maxResults=max_results,
    ))


def search_scenes(
    config: PeatGuardConfig,
    start_date: str,
    end_date: str,
    processing_level: str = "SLC",
    max_results: Optional[int] = None,
) -> list[asf.ASFProduct]:
    """Search for SAR scenes over the configured AOI.

    Routes to Sentinel-1 or NISAR search based on the active sensor
    in the pipeline configuration.

    Args:
        config: Pipeline configuration.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        processing_level: One of 'SLC' or 'GRD_HD'.
        max_results: Maximum number of results to return.

    Returns:
        List of ASF product results sorted by acquisition date.
    """
    west, south, east, north = config.aoi.bbox
    sensor_name = config.sensor

    logger.info(
        "Searching ASF DAAC for %s %s scenes: bbox=[%.3f, %.3f, %.3f, %.3f], "
        "dates=%s to %s",
        sensor_name,
        processing_level,
        west,
        south,
        east,
        north,
        start_date,
        end_date,
    )

    if config.is_nisar:
        results = _search_nisar(config, start_date, end_date, processing_level, max_results)
    else:
        results = _search_sentinel1(config, start_date, end_date, processing_level, max_results)

    # Filter out scenes with missing startTime (some NISAR products lack metadata)
    valid = [r for r in results if r.properties.get("startTime") is not None]
    if len(valid) < len(results):
        logger.warning("Filtered %d scenes with missing startTime", len(results) - len(valid))
    logger.info("Found %d valid %s scenes", len(valid), sensor_name)
    return sorted(valid, key=lambda r: r.properties["startTime"])


def select_best_orbit(results: list[asf.ASFProduct]) -> int:
    """Select the relative orbit with the most acquisitions.

    This mirrors the orbit selection heuristic from the original
    slcdownloader.py -- grouping by relative orbit and picking
    the orbit track with the densest temporal coverage.

    Args:
        results: List of ASF search results.

    Returns:
        The relative orbit number with the most scenes.
    """
    orbits: dict[int, list[asf.ASFProduct]] = {}
    for product in results:
        path = product.properties.get("pathNumber")
        if path is not None:
            orbits.setdefault(path, []).append(product)

    if not orbits:
        raise ValueError("No scenes with valid orbit information found")

    best_orbit = max(orbits, key=lambda k: len(orbits[k]))
    logger.info(
        "Selected orbit %d with %d scenes (of %d orbits total)",
        best_orbit,
        len(orbits[best_orbit]),
        len(orbits),
    )
    return best_orbit


def filter_temporal_stack(
    results: list[asf.ASFProduct],
    orbit: int,
    min_gap_days: int = 14,
    max_scenes: Optional[int] = None,
) -> list[asf.ASFProduct]:
    """Filter scenes for a single orbit track with minimum temporal gaps.

    Ensures at least min_gap_days between consecutive acquisitions to
    provide measurable deformation signal for InSAR. Preserves the
    14-day minimum gap enforcement from the original pipeline.

    Args:
        results: All search results (will be filtered to the specified orbit).
        orbit: Relative orbit number to filter to.
        min_gap_days: Minimum days between consecutive scenes.
        max_scenes: Maximum number of scenes to select.

    Returns:
        Temporally filtered list of scenes for the specified orbit.
    """
    orbit_scenes = [
        r
        for r in results
        if r.properties.get("pathNumber") == orbit
    ]
    orbit_scenes.sort(key=lambda r: r.properties["startTime"])

    selected = []
    last_date: Optional[datetime] = None

    for scene in orbit_scenes:
        acq_time = scene.properties["startTime"]
        if isinstance(acq_time, str):
            current_date = datetime.fromisoformat(acq_time.replace("Z", "+00:00"))
        else:
            current_date = acq_time

        if last_date is None or (current_date - last_date).days >= min_gap_days:
            selected.append(scene)
            last_date = current_date

        if max_scenes is not None and len(selected) >= max_scenes:
            break

    logger.info(
        "Selected %d scenes from orbit %d with >= %d day gaps",
        len(selected),
        orbit,
        min_gap_days,
    )
    return selected


def build_acquisition_stack(
    config: PeatGuardConfig,
    start_date: str,
    end_date: str,
    processing_level: str = "SLC",
    max_scenes: Optional[int] = None,
) -> list[asf.ASFProduct]:
    """High-level function to build a temporal stack of Sentinel-1 scenes.

    Searches ASF DAAC, selects the best orbit, and filters for minimum
    temporal gaps. This is the primary entry point for data discovery.

    Args:
        config: Pipeline configuration.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        processing_level: One of 'SLC' or 'GRD_HD'.
        max_scenes: Maximum number of scenes to select.

    Returns:
        Ordered list of scenes ready for download.
    """
    results = search_scenes(config, start_date, end_date, processing_level)

    if not results:
        logger.warning("No scenes found for the specified parameters")
        return []

    best_orbit = select_best_orbit(results)

    sensor_cfg = config.active_sensor_config
    return filter_temporal_stack(
        results,
        orbit=best_orbit,
        min_gap_days=sensor_cfg.min_temporal_gap_days,
        max_scenes=max_scenes,
    )
