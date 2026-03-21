"""Precise orbit file management for Sentinel-1.

Downloads ESA precise orbit files (POEORB/RESORB) required for
accurate InSAR burst positioning and coregistration.
Uses the S1QC ASF mirror with retry logic and fallback to
ESA CDSE (Copernicus Data Space Ecosystem).
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Primary: ESA Copernicus GNSS orbit distribution (no auth needed)
CDSE_ORBIT_URL = "https://step.esa.int/auxdata/orbits/Sentinel-1"
# Fallback: ASF mirror
ASF_ORBIT_URL = "https://s1qc.asf.alaska.edu"


def _parse_platform_from_safe(safe_name: str) -> str:
    """Extract platform (S1A/S1B) from SAFE filename."""
    if safe_name.upper().startswith("S1A"):
        return "S1A"
    elif safe_name.upper().startswith("S1B"):
        return "S1B"
    return "S1A"


def _parse_date_from_safe(safe_name: str) -> datetime:
    """Extract acquisition datetime from SAFE filename."""
    match = re.search(r"(\d{8}T\d{6})", safe_name)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")
    raise ValueError(f"Cannot parse date from SAFE name: {safe_name}")


def _orbit_covers_date(orbit_name: str, acq_date: datetime) -> bool:
    """Check if an orbit file covers a given acquisition date."""
    try:
        match = re.search(r"V(\d{8}T\d{6})_(\d{8}T\d{6})", orbit_name)
        if not match:
            return False
        start = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")
        end = datetime.strptime(match.group(2), "%Y%m%dT%H%M%S")
        return start <= acq_date <= end
    except (IndexError, ValueError):
        return False


def _download_url(url: str, dest: Path, retries: int = 3) -> bool:
    """Download a URL to a local file with retry logic."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "peatguard/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            if dest.stat().st_size > 0:
                return True
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            logger.warning("Download attempt %d/%d failed for %s: %s", attempt + 1, retries, url, exc)
            if dest.exists():
                dest.unlink()
    return False


def _try_esa_step_download(
    platform: str,
    acq_date: datetime,
    orbit_type_code: str,
    orbit_dir: Path,
) -> Optional[Path]:
    """Download orbit from ESA STEP auxiliary data server.

    URL pattern: https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/2024/01/
    Files are distributed as .EOF.zip which must be unzipped after download.
    """
    import zipfile

    year = acq_date.strftime("%Y")
    month = acq_date.strftime("%m")
    index_url = f"{CDSE_ORBIT_URL}/{orbit_type_code}/{platform}/{year}/{month}/"

    logger.info("Searching ESA STEP for %s orbit: %s", orbit_type_code, index_url)

    try:
        req = urllib.request.Request(index_url, headers={"User-Agent": "peatguard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")

        # ESA STEP distributes orbit files as .EOF.zip
        eof_pattern = re.compile(r'href="([^"]+\.EOF(?:\.zip)?)"')
        matches = eof_pattern.findall(html)

        logger.info("Found %d orbit files on ESA STEP for %s/%s", len(matches), year, month)

        for orbit_name in matches:
            if _orbit_covers_date(orbit_name, acq_date):
                orbit_url = f"{index_url}{orbit_name}"
                download_path = orbit_dir / orbit_name
                logger.info("Downloading orbit from ESA STEP: %s", orbit_name)

                if _download_url(orbit_url, download_path):
                    # Unzip if it's a .EOF.zip file
                    if orbit_name.endswith(".EOF.zip"):
                        try:
                            with zipfile.ZipFile(str(download_path), "r") as zf:
                                eof_files = [n for n in zf.namelist() if n.endswith(".EOF")]
                                if eof_files:
                                    zf.extract(eof_files[0], str(orbit_dir))
                                    eof_path = orbit_dir / eof_files[0]
                                    download_path.unlink()  # Remove the zip
                                    logger.info("Extracted orbit: %s (%d bytes)", eof_files[0], eof_path.stat().st_size)
                                    return eof_path
                        except zipfile.BadZipFile:
                            logger.warning("Bad ZIP file: %s", orbit_name)
                            download_path.unlink(missing_ok=True)
                            continue
                    else:
                        logger.info("Downloaded orbit file: %s (%d bytes)", orbit_name, download_path.stat().st_size)
                        return download_path

    except Exception as exc:
        logger.warning("ESA STEP orbit search failed: %s", exc)

    return None


def _try_asf_download(
    platform: str,
    acq_date: datetime,
    orbit_type_code: str,
    orbit_dir: Path,
) -> Optional[Path]:
    """Download orbit from ASF S1QC mirror."""
    orbit_type_lower = "aux_poeorb" if orbit_type_code == "POEORB" else "aux_resorb"
    index_url = (
        f"{ASF_ORBIT_URL}/{orbit_type_lower}/"
        f"?sentinel1__mission={platform.lower()}"
        f"&validity_start={acq_date.strftime('%Y-%m-%d')}"
        f"&validity_start_accuracy=1day"
    )

    logger.info("Searching ASF for %s orbit: %s", orbit_type_code, index_url)

    try:
        req = urllib.request.Request(index_url, headers={"User-Agent": "peatguard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")

        eof_pattern = re.compile(
            rf'href="({platform.upper()}_OPER_AUX_{orbit_type_code}_[^"]+\.EOF)"'
        )
        matches = eof_pattern.findall(html)

        for orbit_name in matches:
            if _orbit_covers_date(orbit_name, acq_date):
                orbit_url = f"{ASF_ORBIT_URL}/{orbit_type_lower}/{orbit_name}"
                orbit_path = orbit_dir / orbit_name
                logger.info("Downloading orbit from ASF: %s", orbit_name)
                if _download_url(orbit_url, orbit_path):
                    logger.info("Downloaded orbit file: %s (%d bytes)", orbit_name, orbit_path.stat().st_size)
                    return orbit_path

    except Exception as exc:
        logger.warning("ASF orbit search failed: %s", exc)

    return None


def download_orbit_file(
    scene_date: str,
    platform: str = "S1A",
    orbit_dir: Path = Path("./orbits"),
    orbit_type: str = "precise",
) -> Optional[Path]:
    """Download the orbit file covering a given acquisition date.

    Tries multiple sources in order:
    1. ESA STEP auxiliary data server (no auth required)
    2. ASF S1QC mirror
    3. Falls back from precise to restituted if needed

    Args:
        scene_date: Acquisition date (various formats supported).
        platform: Satellite platform (S1A or S1B).
        orbit_dir: Directory to store orbit files.
        orbit_type: 'precise' (POEORB) or 'restituted' (RESORB).

    Returns:
        Path to the downloaded orbit file, or None if not found.
    """
    orbit_dir.mkdir(parents=True, exist_ok=True)

    # Parse date from various formats
    if "T" in scene_date:
        acq_date = datetime.strptime(scene_date[:15], "%Y%m%dT%H%M%S")
    elif len(scene_date) == 10:
        acq_date = datetime.strptime(scene_date, "%Y-%m-%d")
    else:
        acq_date = datetime.strptime(scene_date[:8], "%Y%m%d")

    # Check for existing orbit file
    if orbit_dir.exists():
        for orbit_file in orbit_dir.iterdir():
            if orbit_file.suffix.upper() == ".EOF" and _orbit_covers_date(orbit_file.name, acq_date):
                logger.info("Using cached orbit file: %s", orbit_file.name)
                return orbit_file

    orbit_type_code = "POEORB" if orbit_type == "precise" else "RESORB"

    # Try ESA STEP first (most reliable, no auth)
    result = _try_esa_step_download(platform, acq_date, orbit_type_code, orbit_dir)
    if result:
        return result

    # Try ASF mirror
    result = _try_asf_download(platform, acq_date, orbit_type_code, orbit_dir)
    if result:
        return result

    # Fall back to restituted if precise was requested but not found
    if orbit_type == "precise":
        logger.info("Precise orbit not available, trying restituted")
        return download_orbit_file(
            scene_date, platform, orbit_dir, orbit_type="restituted"
        )

    logger.warning("No orbit file found for %s on %s", platform, scene_date)
    return None


def download_orbits_for_pair(
    reference_safe: Path,
    secondary_safe: Path,
    orbit_dir: Path,
) -> list[Path]:
    """Download orbit files for both scenes in an InSAR pair.

    Args:
        reference_safe: Path to reference SAFE directory or zip.
        secondary_safe: Path to secondary SAFE directory or zip.
        orbit_dir: Directory to store orbit files.

    Returns:
        List of paths to downloaded orbit files.
    """
    orbit_dir.mkdir(parents=True, exist_ok=True)
    orbits = []

    for safe_path in [reference_safe, secondary_safe]:
        safe_name = safe_path.name
        platform = _parse_platform_from_safe(safe_name)
        try:
            acq_date = _parse_date_from_safe(safe_name)
            date_str = acq_date.strftime("%Y%m%dT%H%M%S")
        except ValueError:
            logger.warning("Cannot parse date from %s, skipping orbit download", safe_name)
            continue

        orbit_path = download_orbit_file(
            scene_date=date_str,
            platform=platform,
            orbit_dir=orbit_dir,
        )
        if orbit_path:
            orbits.append(orbit_path)
        else:
            logger.warning("No orbit file found for %s", safe_name)

    return orbits
