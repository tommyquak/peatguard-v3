"""MintPy SBAS time-series inversion.

Orchestrates the MintPy processing chain for Small BAseline Subset
(SBAS) time-series analysis. This replaces the naive per-pair
displacement summation with a proper inversion that accounts for
atmospheric delays, unwrapping errors, and orbital ramps.

The MintPy chain:
    load_data -> modify_network -> reference_point ->
    correct_unwrap_error -> correct_troposphere -> deramp ->
    invert_network -> timeseries2velocity
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from peatguard.config import PeatGuardConfig

logger = logging.getLogger(__name__)

# MintPy processing steps in execution order
MINTPY_STEPS = [
    ("load_data.py", "Loading interferogram stack"),
    ("modify_network.py", "Modifying network (removing low-coherence pairs)"),
    ("reference_point.py", "Setting reference point"),
    ("quick_overview.py", "Generating quick overview"),
    ("correct_unwrap_error.py", "Correcting unwrapping errors"),
    ("correct_troposphere.py", "Correcting tropospheric delay (ERA5)"),
    ("deramp.py", "Removing orbital ramps"),
    ("correct_topography.py", "Correcting topographic residual"),
    ("residual_RMS.py", "Computing residual RMS"),
    ("reference_date.py", "Selecting reference date"),
    ("invert_network.py", "Running SBAS network inversion"),
    ("timeseries2velocity.py", "Estimating velocity"),
]


def _run_mintpy_step(
    script: str,
    config_path: Path,
    work_dir: Path,
    extra_args: Optional[list[str]] = None,
) -> None:
    """Run a single MintPy processing step.

    Args:
        script: MintPy script name (e.g., 'load_data.py').
        config_path: Path to the MintPy template file.
        work_dir: MintPy working directory.
        extra_args: Additional command-line arguments.
    """
    cmd = [script, str(config_path)]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )

    if result.returncode != 0:
        logger.error(
            "%s failed:\nSTDOUT: %s\nSTDERR: %s",
            script,
            result.stdout[-1000:],
            result.stderr[-1000:],
        )
        raise RuntimeError(f"MintPy step {script} failed with return code {result.returncode}")


def run_sbas_inversion(
    config_path: Path,
    work_dir: Path,
    skip_steps: Optional[list[str]] = None,
    start_step: Optional[str] = None,
) -> Path:
    """Run the complete MintPy SBAS processing chain.

    Args:
        config_path: Path to the MintPy template file.
        work_dir: MintPy working directory.
        skip_steps: List of step script names to skip.
        start_step: Script name to start from (skips earlier steps).

    Returns:
        Path to the velocity file produced by MintPy.
    """
    if skip_steps is None:
        skip_steps = []

    started = start_step is None

    for script, description in MINTPY_STEPS:
        if not started:
            if script == start_step:
                started = True
            else:
                continue

        if script in skip_steps:
            logger.info("Skipping: %s (%s)", script, description)
            continue

        logger.info("Running: %s -- %s", script, description)
        _run_mintpy_step(script, config_path, work_dir)

    velocity_file = work_dir / "velocity.h5"
    if velocity_file.exists():
        logger.info("SBAS inversion complete. Velocity file: %s", velocity_file)
    else:
        logger.warning("Velocity file not found at expected path: %s", velocity_file)

    return velocity_file


def run_smallbaselineApp(
    config_path: Path,
    work_dir: Path,
) -> Path:
    """Run MintPy's smallbaselineApp.py as a single command.

    This is the all-in-one MintPy entry point that runs the entire
    SBAS chain. Use this instead of run_sbas_inversion when you
    don't need per-step control.

    Args:
        config_path: Path to the MintPy template file.
        work_dir: MintPy working directory.

    Returns:
        Path to the velocity file.
    """
    logger.info("Running smallbaselineApp.py with config: %s", config_path)

    cmd = ["smallbaselineApp.py", str(config_path)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )

    if result.returncode != 0:
        logger.error(
            "smallbaselineApp.py failed:\nSTDOUT: %s\nSTDERR: %s",
            result.stdout[-2000:],
            result.stderr[-2000:],
        )
        raise RuntimeError(f"smallbaselineApp.py failed with return code {result.returncode}")

    velocity_file = work_dir / "velocity.h5"
    logger.info("smallbaselineApp complete. Velocity: %s", velocity_file)
    return velocity_file


def run_smallbaselineApp_from_step(
    config_path: Path,
    work_dir: Path,
    start_step: str = "modify_network",
) -> Path:
    """Run smallbaselineApp.py starting from a specific step.

    Use this to skip earlier steps (e.g. load_data) when the HDF5
    input files have already been created manually.

    Args:
        config_path: Path to the MintPy template file.
        work_dir: MintPy working directory.
        start_step: Step name to start from (without .py extension).

    Returns:
        Path to the velocity file.
    """
    logger.info("Running smallbaselineApp.py --start %s", start_step)

    cmd = ["smallbaselineApp.py", str(config_path), "--start", start_step]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(work_dir),
    )

    if result.returncode != 0:
        logger.error(
            "smallbaselineApp.py (from %s) failed:\nSTDOUT: %s\nSTDERR: %s",
            start_step,
            result.stdout[-3000:],
            result.stderr[-3000:],
        )
        raise RuntimeError(
            f"smallbaselineApp.py failed (start={start_step}) with rc {result.returncode}"
        )

    velocity_file = work_dir / "velocity.h5"
    logger.info("smallbaselineApp complete (from %s). Velocity: %s", start_step, velocity_file)
    return velocity_file
