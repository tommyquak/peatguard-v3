"""Phase-to-displacement conversion.

Converts unwrapped InSAR phase (radians) to ground displacement
in physical units (meters, then mm/yr). Handles the geometry
correction from line-of-sight (LOS) to vertical displacement
assuming primarily vertical deformation (appropriate for peatland
subsidence).

The conversion formula:
    LOS displacement = phase * wavelength / (4 * pi)
    Vertical displacement = LOS / cos(incidence_angle)

For Sentinel-1 C-band:
    wavelength = 0.056 m (5.6 cm)
    incidence_angle ~ 37 degrees (center of IW2 swath)
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

import numpy as np

from peatguard.config import ProcessingConfig

logger = logging.getLogger(__name__)


def phase_to_los_displacement(
    unwrapped_phase: np.ndarray,
    wavelength_m: float = 0.056,
) -> np.ndarray:
    """Convert unwrapped phase to line-of-sight displacement.

    Args:
        unwrapped_phase: 2D array of unwrapped phase in radians.
        wavelength_m: Radar wavelength in meters (0.056 for C-band).

    Returns:
        2D array of LOS displacement in meters.
        Negative values indicate motion toward the satellite (uplift
        or toward-sensor component of subsidence).
    """
    los_m = unwrapped_phase * wavelength_m / (4.0 * math.pi)
    logger.info(
        "Phase to LOS: range [%.4f, %.4f] m",
        np.nanmin(los_m),
        np.nanmax(los_m),
    )
    return los_m


def los_to_vertical(
    los_displacement_m: np.ndarray,
    incidence_deg: float = 37.0,
) -> np.ndarray:
    """Convert LOS displacement to vertical displacement.

    Assumes deformation is purely vertical (valid for peatland
    subsidence where horizontal motion is negligible).

    Args:
        los_displacement_m: 2D array of LOS displacement in meters.
        incidence_deg: Radar incidence angle in degrees.

    Returns:
        2D array of vertical displacement in meters.
        Negative values indicate subsidence (downward motion).
    """
    incidence_rad = math.radians(incidence_deg)
    cos_inc = math.cos(incidence_rad)

    if cos_inc == 0:
        raise ValueError(f"Invalid incidence angle: {incidence_deg} degrees")

    vertical_m = los_displacement_m / cos_inc
    logger.info(
        "LOS to vertical (inc=%.1f deg): range [%.4f, %.4f] m",
        incidence_deg,
        np.nanmin(vertical_m),
        np.nanmax(vertical_m),
    )
    return vertical_m


def displacement_to_velocity(
    displacement_m: np.ndarray,
    temporal_span_days: float,
) -> np.ndarray:
    """Convert cumulative displacement to annual velocity.

    Args:
        displacement_m: 2D array of cumulative displacement in meters.
        temporal_span_days: Time span of the displacement in days.

    Returns:
        2D array of displacement velocity in mm/yr.
    """
    if temporal_span_days <= 0:
        raise ValueError(f"temporal_span_days must be positive, got {temporal_span_days}")

    years = temporal_span_days / 365.25
    velocity_mm_yr = (displacement_m * 1000.0) / years

    logger.info(
        "Displacement to velocity (span=%.1f days): range [%.1f, %.1f] mm/yr",
        temporal_span_days,
        np.nanmin(velocity_mm_yr),
        np.nanmax(velocity_mm_yr),
    )
    return velocity_mm_yr


def compute_displacement(
    unwrapped_phase: np.ndarray,
    processing_config: Optional[ProcessingConfig] = None,
    wavelength_m: Optional[float] = None,
    incidence_deg: Optional[float] = None,
    temporal_span_days: Optional[float] = None,
) -> dict[str, np.ndarray]:
    """Complete phase-to-displacement conversion pipeline.

    Args:
        unwrapped_phase: 2D array of unwrapped phase in radians.
        processing_config: Processing configuration (used for defaults).
        wavelength_m: Override radar wavelength.
        incidence_deg: Override incidence angle.
        temporal_span_days: If provided, also compute velocity.

    Returns:
        Dict with keys:
            'los_m': LOS displacement in meters
            'vertical_m': Vertical displacement in meters
            'velocity_mm_yr': Velocity in mm/yr (only if temporal_span_days given)
    """
    if processing_config is not None:
        wavelength_m = wavelength_m or processing_config.wavelength_m
        incidence_deg = incidence_deg or processing_config.incidence_deg
    else:
        wavelength_m = wavelength_m or 0.056
        incidence_deg = incidence_deg or 37.0

    los_m = phase_to_los_displacement(unwrapped_phase, wavelength_m)
    vertical_m = los_to_vertical(los_m, incidence_deg)

    result = {
        "los_m": los_m,
        "vertical_m": vertical_m,
    }

    if temporal_span_days is not None:
        result["velocity_mm_yr"] = displacement_to_velocity(vertical_m, temporal_span_days)

    return result
