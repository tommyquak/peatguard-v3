"""PeatGuard command-line interface.

Provides commands for each pipeline stage and a full end-to-end run.
Each command is designed to work standalone in ephemeral Cloud Run Jobs,
discovering data from GCS rather than relying on shared local state.

Usage:
    peatguard download --start 2024-01-01 --end 2024-12-31
    peatguard process --mode insar
    peatguard process --mode backscatter
    peatguard timeseries
    peatguard analyze
    peatguard run  # full pipeline
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger("peatguard")


def _setup_logging(verbose: bool) -> None:
    """Configure logging for CLI output."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    logging.root.handlers = [handler]
    logging.root.setLevel(level)


GCS_FUSE_MOUNT = Path("/mnt/gcs")


def _discover_slc_paths(config) -> list[Path]:
    """Discover SLC files from GCS FUSE mount, GCS sync, or local storage.

    Priority order:
    1. GCS FUSE mount at /mnt/gcs/raw/slc/ (Cloud Run with volume mount)
    2. GCS sync to local scratch (fallback if FUSE not available)
    3. Local directory scan
    """
    # Priority 1: GCS FUSE mount (zero-copy, no RAM usage)
    fuse_slc_dir = GCS_FUSE_MOUNT / "raw" / "slc"
    if fuse_slc_dir.exists():
        fuse_paths = sorted(fuse_slc_dir.glob("S1*.zip"))
        if fuse_paths:
            logger.info("Found %d SLC files via GCS FUSE mount: %s", len(fuse_paths), fuse_slc_dir)
            return fuse_paths

    # Priority 2: GCS listing (create placeholder paths, download per-pair later)
    local_slc_dir = config.storage.scratch_dir / "raw" / "slc"
    local_slc_dir.mkdir(parents=True, exist_ok=True)

    if config.storage.gcs_bucket:
        from peatguard.export.gcs import list_blobs

        logger.info("Listing SLC files in GCS bucket: %s", config.storage.gcs_bucket)
        blob_names = list_blobs(
            bucket_name=config.storage.gcs_bucket,
            prefix="raw/slc/",
            suffix=".zip",
        )
        if blob_names:
            # Create placeholder paths (files may not exist locally yet)
            # The orchestrator will download per-pair on demand
            paths = []
            for blob_name in blob_names:
                filename = blob_name.split("/")[-1]
                if filename:
                    paths.append(local_slc_dir / filename)
            logger.info("Found %d SLC files in GCS (will download per-pair)", len(paths))
            return sorted(paths)

    # Priority 3: Local directory scan
    local_paths = sorted(local_slc_dir.glob("S1*.zip"))
    if local_paths:
        logger.info("Found %d SLC files in local storage: %s", len(local_paths), local_slc_dir)
        return local_paths

    alt_dir = config.storage.output_dir / "raw" / "slc"
    alt_paths = sorted(alt_dir.glob("S1*.zip")) if alt_dir.exists() else []
    if alt_paths:
        logger.info("Found %d SLC files in output dir: %s", len(alt_paths), alt_dir)
        return alt_paths

    logger.warning("No SLC files found in GCS FUSE, GCS sync, or local storage")
    return []


def _discover_grd_paths(config) -> list[Path]:
    """Discover GRD files from GCS FUSE mount, GCS sync, or local storage."""
    # Priority 1: GCS FUSE mount
    fuse_grd_dir = GCS_FUSE_MOUNT / "raw" / "grd"
    if fuse_grd_dir.exists():
        fuse_paths = sorted(fuse_grd_dir.glob("S1*.zip"))
        if fuse_paths:
            logger.info("Found %d GRD files via GCS FUSE mount: %s", len(fuse_paths), fuse_grd_dir)
            return fuse_paths

    # Priority 2: GCS sync
    local_grd_dir = config.storage.scratch_dir / "raw" / "grd"
    local_grd_dir.mkdir(parents=True, exist_ok=True)

    if config.storage.gcs_bucket:
        from peatguard.export.gcs import sync_from_gcs

        logger.info("Syncing GRD files from GCS bucket: %s", config.storage.gcs_bucket)
        paths = sync_from_gcs(
            bucket_name=config.storage.gcs_bucket,
            prefix="raw/grd/",
            local_dir=local_grd_dir,
            suffix=".zip",
        )
        if paths:
            return sorted(paths)

    # Priority 3: Local scan
    local_paths = sorted(local_grd_dir.glob("S1*.zip"))
    if local_paths:
        logger.info("Found %d GRD files in local storage: %s", len(local_paths), local_grd_dir)
        return local_paths

    logger.warning("No GRD files found in GCS FUSE, GCS sync, or local storage")
    return []


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.option("-c", "--config", "config_path", type=click.Path(exists=True, path_type=Path), help="Path to config YAML.")
@click.option("--override", type=click.Path(exists=True, path_type=Path), help="Path to config override YAML.")
@click.pass_context
def main(ctx: click.Context, verbose: bool, config_path: Optional[Path], override: Optional[Path]) -> None:
    """PeatGuard: Satellite-based peatland monitoring pipeline."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["override_path"] = override


@main.command()
@click.option("--start", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end", required=True, help="End date (YYYY-MM-DD).")
@click.option("--level", default="SLC", type=click.Choice(["SLC", "GRD_HD"]), help="Processing level.")
@click.option("--max-scenes", type=int, default=None, help="Maximum scenes to download.")
@click.pass_context
def download(ctx: click.Context, start: str, end: str, level: str, max_scenes: Optional[int]) -> None:
    """Download Sentinel-1 scenes from ASF DAAC."""
    from peatguard.catalog import Catalog
    from peatguard.config import load_config
    from peatguard.pipeline.orchestrator import run_download_stage

    config = load_config(ctx.obj["config_path"], ctx.obj["override_path"])
    catalog = Catalog(config.storage.catalog_db)

    paths = run_download_stage(config, catalog, start, end, level, max_scenes)
    click.echo(f"Downloaded {len(paths)} scenes")


@main.command()
@click.option("--mode", required=True, type=click.Choice(["insar", "backscatter", "all"]), help="Processing mode.")
@click.option("--workers", default=2, help="Parallel workers for InSAR.")
@click.pass_context
def process(ctx: click.Context, mode: str, workers: int) -> None:
    """Process downloaded scenes (InSAR and/or backscatter).

    Discovers input files from GCS or local storage automatically.
    Does not depend on a shared SQLite catalog between jobs.
    """
    from peatguard.catalog import Catalog
    from peatguard.config import load_config

    config = load_config(ctx.obj["config_path"], ctx.obj["override_path"])
    catalog = Catalog(config.storage.catalog_db)

    if mode in ("insar", "all"):
        from peatguard.pipeline.orchestrator import run_insar_stage

        slc_paths = _discover_slc_paths(config)
        if not slc_paths:
            click.echo("No SLC files found. Run download first.", err=True)
            sys.exit(1)

        click.echo(f"Found {len(slc_paths)} SLC files for InSAR processing")
        run_insar_stage(config, catalog, slc_paths, workers)

    if mode in ("backscatter", "all"):
        from peatguard.pipeline.orchestrator import run_backscatter_stage

        grd_paths = _discover_grd_paths(config)
        if not grd_paths:
            click.echo("No GRD files found. Run download first.", err=True)
            sys.exit(1)

        click.echo(f"Found {len(grd_paths)} GRD files for backscatter processing")
        run_backscatter_stage(config, grd_paths)

    click.echo("Processing complete")


@main.command()
@click.pass_context
def timeseries(ctx: click.Context) -> None:
    """Run MintPy SBAS time-series analysis."""
    from peatguard.config import load_config
    from peatguard.pipeline.orchestrator import run_timeseries_stage

    config = load_config(ctx.obj["config_path"], ctx.obj["override_path"])
    isce_dir = config.storage.scratch_dir / "insar"
    mintpy_dir = run_timeseries_stage(config, isce_dir)
    click.echo(f"Time-series complete: {mintpy_dir}")


@main.command()
@click.pass_context
def analyze(ctx: click.Context) -> None:
    """Run analysis (classification, and optionally canal detection + risk scoring)."""
    from peatguard.config import load_config
    from peatguard.pipeline.orchestrator import run_analysis_stage

    config = load_config(ctx.obj["config_path"], ctx.obj["override_path"])
    velocity_path = config.storage.output_dir / "subsidence_velocity.tif"
    vv_path = config.storage.output_dir / "vv_median.tif"

    # Download velocity from GCS if not available locally
    if not velocity_path.exists() and config.storage.gcs_bucket:
        from peatguard.export.gcs import download_file
        velocity_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            download_file(config.storage.gcs_bucket, "products/subsidence_velocity.tif", velocity_path)
            click.echo(f"Downloaded velocity from GCS")
        except Exception:
            click.echo(f"Velocity file not found locally or in GCS", err=True)
            sys.exit(1)

    if not velocity_path.exists():
        click.echo(f"Velocity file not found: {velocity_path}", err=True)
        sys.exit(1)

    # VV backscatter is optional (canal detection + risk scoring need it)
    vv = vv_path if vv_path.exists() else None
    if not vv:
        click.echo("VV composite not found -- skipping canal detection and risk scoring")

    products = run_analysis_stage(config, velocity_path, vv)
    click.echo(f"Analysis complete: {len(products)} products generated")


@main.command(name="run")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end", required=True, help="End date (YYYY-MM-DD).")
@click.option("--workers", default=2, help="Parallel workers.")
@click.pass_context
def run_all(ctx: click.Context, start: str, end: str, workers: int) -> None:
    """Run the complete pipeline end-to-end."""
    from peatguard.pipeline.orchestrator import run_full_pipeline

    run_full_pipeline(
        config_path=ctx.obj["config_path"],
        override_path=ctx.obj["override_path"],
        start_date=start,
        end_date=end,
        max_workers=workers,
    )
    click.echo("Full pipeline complete")


if __name__ == "__main__":
    main()
