"""Radiometric calibration for Sentinel-1 GRD products.

Converts raw DN (digital number) values to calibrated sigma0
backscatter coefficients by applying the calibration lookup table
stored in the GRD product annotation XML. This replaces SNAP's
Calibration operator entirely.

The Sentinel-1 GRD product stores calibration vectors in:
  <SAFE>/annotation/calibration/calibration-{swath}-{pol}.xml

Each vector contains sigma0, beta0, gamma, and dn LUT values
that vary across range (columns). The calibration formula is:
  sigma0 = |DN|^2 / sigma0_lut^2
"""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import numpy as np
import rasterio

logger = logging.getLogger(__name__)


def _parse_calibration_lut(cal_xml_path: str, cal_type: str = "sigmaNought") -> dict:
    """Parse calibration LUT vectors from a Sentinel-1 calibration XML.

    Args:
        cal_xml_path: Path to the calibration annotation XML (may be inside a zip).
        cal_type: Calibration type. One of 'sigmaNought', 'betaNought', 'gamma', 'dn'.

    Returns:
        Dict with 'lines', 'pixels', and 'values' arrays for interpolation.
    """
    tree = ET.parse(cal_xml_path)
    root = tree.getroot()

    cal_vectors = root.findall(".//calibrationVector")
    if not cal_vectors:
        raise ValueError(f"No calibration vectors found in {cal_xml_path}")

    lines = []
    pixels_list = []
    values_list = []

    for vector in cal_vectors:
        line = int(vector.find("line").text)
        pixel_str = vector.find("pixel").text
        cal_str = vector.find(cal_type).text

        pixels = np.array([int(p) for p in pixel_str.split()])
        values = np.array([float(v) for v in cal_str.split()])

        lines.append(line)
        pixels_list.append(pixels)
        values_list.append(values)

    return {
        "lines": np.array(lines),
        "pixels": pixels_list,
        "values": values_list,
    }


def _interpolate_lut(lut: dict, height: int, width: int) -> np.ndarray:
    """Interpolate calibration LUT to match image dimensions.

    The LUT is provided at sparse line/pixel positions and must be
    interpolated to cover the full image grid.

    Args:
        lut: Parsed LUT dict from _parse_calibration_lut.
        height: Image height in pixels.
        width: Image width in pixels.

    Returns:
        2D array of calibration values matching (height, width).
    """
    from scipy.interpolate import RegularGridInterpolator

    lines = lut["lines"]
    # Use the pixel grid from the first vector (same for all vectors)
    pixels = lut["pixels"][0]

    # Build 2D LUT grid
    lut_grid = np.zeros((len(lines), len(pixels)), dtype=np.float64)
    for i, values in enumerate(lut["values"]):
        if len(values) == len(pixels):
            lut_grid[i] = values
        else:
            # Handle mismatched lengths by interpolating
            lut_grid[i] = np.interp(
                pixels, np.linspace(0, width - 1, len(values)), values
            )

    # Interpolate to full image dimensions row-by-row to save memory.
    # The meshgrid approach allocates ~10GB for a full IW GRD; this uses ~100KB.
    result = np.zeros((height, width), dtype=np.float32)
    col_coords = np.arange(width, dtype=np.float64)

    for row in range(height):
        # Find the two bounding LUT lines for this row
        row_f = float(row)
        idx = np.searchsorted(lines, row_f, side="right") - 1
        idx = np.clip(idx, 0, len(lines) - 2)

        line0, line1 = float(lines[idx]), float(lines[idx + 1])
        frac = (row_f - line0) / max(line1 - line0, 1e-6)
        frac = np.clip(frac, 0.0, 1.0)

        # Interpolate the LUT values at sparse pixel positions
        vals0 = lut_grid[idx]
        vals1 = lut_grid[idx + 1]
        interp_vals = vals0 * (1 - frac) + vals1 * frac

        # Interpolate across columns to full width
        result[row] = np.interp(col_coords, pixels.astype(np.float64), interp_vals).astype(np.float32)

    return result


def _find_calibration_xml(safe_path: Path, polarization: str = "vv") -> str:
    """Locate the calibration XML within a SAFE directory or zip.

    Args:
        safe_path: Path to the .SAFE directory or .zip file.
        polarization: Polarization channel (e.g., 'vv').

    Returns:
        Path to the calibration XML file.
    """
    pol = polarization.lower()

    if safe_path.suffix == ".zip":
        with zipfile.ZipFile(safe_path) as zf:
            for name in zf.namelist():
                if "calibration" in name and pol in name.lower() and name.endswith(".xml"):
                    # Extract to temp location
                    extracted = zf.extract(name, safe_path.parent / "_cal_tmp")
                    return extracted
        raise FileNotFoundError(
            f"No calibration XML for {pol} found in {safe_path}"
        )

    # Search in unzipped SAFE directory
    cal_dir = safe_path / "annotation" / "calibration"
    if not cal_dir.exists():
        # Try alternative structure
        for candidate in safe_path.rglob("calibration-*.xml"):
            if pol in candidate.name.lower():
                return str(candidate)
        raise FileNotFoundError(f"No calibration directory in {safe_path}")

    for xml_file in cal_dir.glob("calibration-*.xml"):
        if pol in xml_file.name.lower():
            return str(xml_file)

    raise FileNotFoundError(f"No calibration XML for {pol} in {cal_dir}")


def _find_measurement_tiff(safe_path: Path, polarization: str = "vv") -> str:
    """Locate the measurement GeoTIFF within a SAFE directory or zip.

    Args:
        safe_path: Path to the .SAFE directory or .zip file.
        polarization: Polarization channel.

    Returns:
        Path to the measurement TIFF file.
    """
    pol = polarization.lower()

    if safe_path.suffix == ".zip":
        with zipfile.ZipFile(safe_path) as zf:
            for name in zf.namelist():
                if "measurement" in name and pol in name.lower() and name.endswith(".tiff"):
                    extracted = zf.extract(name, safe_path.parent / "_meas_tmp")
                    return extracted
        raise FileNotFoundError(f"No measurement TIFF for {pol} in {safe_path}")

    meas_dir = safe_path / "measurement"
    if not meas_dir.exists():
        for candidate in safe_path.rglob("*.tiff"):
            if pol in candidate.name.lower():
                return str(candidate)
        raise FileNotFoundError(f"No measurement directory in {safe_path}")

    for tiff_file in meas_dir.glob("*.tiff"):
        if pol in tiff_file.name.lower():
            return str(tiff_file)

    raise FileNotFoundError(f"No measurement TIFF for {pol} in {meas_dir}")


def calibrate_grd(
    safe_path: Path,
    output_path: Path,
    polarization: str = "vv",
    cal_type: str = "sigmaNought",
) -> Path:
    """Calibrate a Sentinel-1 GRD product to sigma0 backscatter.

    Reads the raw DN values from the measurement TIFF and applies
    the calibration LUT from the annotation XML. No SNAP required.

    Args:
        safe_path: Path to the .SAFE directory or .zip file.
        output_path: Path for the calibrated output GeoTIFF.
        polarization: Polarization to calibrate (default 'vv').
        cal_type: Calibration type (default 'sigmaNought').

    Returns:
        Path to the calibrated GeoTIFF.
    """
    logger.info("Calibrating %s (%s, %s)", safe_path.name, polarization, cal_type)

    # Find and parse calibration LUT
    cal_xml = _find_calibration_xml(safe_path, polarization)
    lut = _parse_calibration_lut(cal_xml, cal_type)

    # Read measurement data
    meas_tiff = _find_measurement_tiff(safe_path, polarization)

    with rasterio.open(meas_tiff) as src:
        dn = src.read(1).astype(np.float64)
        profile = src.profile.copy()

    height, width = dn.shape

    # Interpolate LUT to image dimensions
    cal_lut = _interpolate_lut(lut, height, width)

    # Apply calibration: sigma0 = |DN|^2 / LUT^2
    # Avoid division by zero
    cal_lut = np.where(cal_lut == 0, 1.0, cal_lut)
    sigma0 = (dn ** 2) / (cal_lut ** 2)

    # Write calibrated output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(
        dtype="float32",
        count=1,
        nodata=0.0,
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(sigma0.astype(np.float32), 1)
        dst.set_band_description(1, f"sigma0_{polarization}")

    # Preserve GCPs from the source TIFF for geocoding downstream
    with rasterio.open(meas_tiff) as src:
        gcps = src.gcps
        if gcps and len(gcps[0]) > 0:
            with rasterio.open(output_path, "r+") as dst:
                dst.gcps = gcps
            logger.info("Preserved %d GCPs for geocoding", len(gcps[0]))

    logger.info("Calibrated output: %s", output_path.name)
    return output_path
