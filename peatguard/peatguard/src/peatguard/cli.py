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
        fuse_paths = sorted(fuse_slc_dir.glob("*.zip"))
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
    local_paths = sorted(local_slc_dir.glob("*.zip"))
    if local_paths:
        logger.info("Found %d SLC files in local storage: %s", len(local_paths), local_slc_dir)
        return local_paths

    alt_dir = config.storage.output_dir / "raw" / "slc"
    alt_paths = sorted(alt_dir.glob("*.zip")) if alt_dir.exists() else []
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
        fuse_paths = sorted(fuse_grd_dir.glob("*.zip"))
        if fuse_paths:
            logger.info("Found %d GRD files via GCS FUSE mount: %s", len(fuse_paths), fuse_grd_dir)
            return fuse_paths

    # Priority 2: GCS sync
    local_grd_dir = config.storage.scratch_dir / "raw" / "grd"
    local_grd_dir.mkdir(parents=True, exist_ok=True)

    if config.storage.gcs_bucket:
        from peatguard.export.gcs import list_blobs

        # Create placeholder paths for GRD files in GCS (downloaded on-demand
        # by the backscatter stage to avoid OOM from bulk download).
        for prefix in ["raw/grd/", "raw/slc/"]:
            blob_names = list_blobs(config.storage.gcs_bucket, prefix, suffix=".zip")
            grd_blobs = [b for b in blob_names if "GRDH" in b or "GRD" in b]
            if grd_blobs:
                paths = []
                for blob in grd_blobs:
                    filename = blob.split("/")[-1]
                    paths.append(local_grd_dir / filename)
                logger.info("Found %d GRD files in gs://%s/%s (will download per-scene)",
                            len(paths), config.storage.gcs_bucket, prefix)
                return sorted(paths)

    # Priority 3: Local scan
    local_paths = sorted(local_grd_dir.glob("*.zip"))
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
    # Try downloading from GCS if not available locally
    if not vv_path.exists() and config.storage.gcs_bucket:
        try:
            download_file(config.storage.gcs_bucket, "products/vv_median.tif", vv_path)
            click.echo("Downloaded VV composite from GCS")
        except Exception:
            pass
    vv = vv_path if vv_path.exists() else None
    if not vv:
        click.echo("VV composite not found -- skipping canal detection and risk scoring")

    products = run_analysis_stage(config, velocity_path, vv)
    click.echo(f"Analysis complete: {len(products)} products generated")


@main.command()
@click.option(
    "--c-vel",
    "c_vel_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to C-band velocity GeoTIFF. Auto-discovered from output_dir or GCS if omitted.",
)
@click.option(
    "--c-coh",
    "c_coh_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to C-band coherence GeoTIFF.",
)
@click.option(
    "--l-vel",
    "l_vel_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to L-band (NISAR) velocity GeoTIFF.",
)
@click.option(
    "--l-coh",
    "l_coh_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to L-band (NISAR) coherence GeoTIFF.",
)
@click.pass_context
def fuse(
    ctx: click.Context,
    c_vel_path: Optional[Path],
    c_coh_path: Optional[Path],
    l_vel_path: Optional[Path],
    l_coh_path: Optional[Path],
) -> None:
    """Fuse C-band and L-band InSAR velocity maps into a unified subsidence product.

    Combines Sentinel-1 (C-band) and NISAR (L-band) velocity and coherence
    products using coherence-weighted averaging. C-band works well over cleared
    land while L-band penetrates forest canopy, so the fused product has better
    spatial coverage than either sensor alone.

    If paths are not provided explicitly, the command looks for products in
    the configured output directory and GCS bucket.
    """
    from peatguard.analysis.fusion import generate_fusion_products
    from peatguard.config import load_config

    config = load_config(ctx.obj["config_path"], ctx.obj["override_path"])
    output_dir = config.storage.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Auto-discover paths from output_dir if not provided
    if c_vel_path is None:
        c_vel_path = output_dir / "subsidence_velocity.tif"
    if c_coh_path is None:
        c_coh_path = output_dir / "coherence_median.tif"
    if l_vel_path is None:
        l_vel_path = output_dir / "nisar_subsidence_velocity.tif"
    if l_coh_path is None:
        l_coh_path = output_dir / "nisar_coherence_median.tif"

    # Try downloading from GCS if files are missing
    missing_paths = {
        c_vel_path: "products/subsidence_velocity.tif",
        c_coh_path: "products/coherence_median.tif",
        l_vel_path: "products/nisar_subsidence_velocity.tif",
        l_coh_path: "products/nisar_coherence_median.tif",
    }
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import download_file

        for local_path, blob_name in missing_paths.items():
            if not local_path.exists():
                try:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    download_file(config.storage.gcs_bucket, blob_name, local_path)
                    click.echo(f"Downloaded {blob_name} from GCS")
                except Exception:
                    pass

    # Validate all inputs exist
    for label, path in [
        ("C-band velocity", c_vel_path),
        ("C-band coherence", c_coh_path),
        ("L-band velocity", l_vel_path),
        ("L-band coherence", l_coh_path),
    ]:
        if not path.exists():
            click.echo(
                f"{label} not found: {path}\n"
                "Run the pipeline for both sentinel1 and nisar sensors first, "
                "or provide explicit paths with --c-vel, --c-coh, --l-vel, --l-coh.",
                err=True,
            )
            sys.exit(1)

    fusion_cfg = config.fusion
    products = generate_fusion_products(
        c_vel_path=c_vel_path,
        c_coh_path=c_coh_path,
        l_vel_path=l_vel_path,
        l_coh_path=l_coh_path,
        output_dir=output_dir,
        nodata=config.export.nodata,
        min_coherence=fusion_cfg.min_coherence,
        c_band_weight_boost=fusion_cfg.c_band_weight_boost,
    )

    # Re-run subsidence classification on fused velocity
    fused_vel = products.get("fused_velocity")
    if fused_vel:
        from peatguard.analysis.subsidence_class import classify_subsidence_file

        fused_class_path = output_dir / "fused_subsidence_class.tif"
        water_mask_path = output_dir / "water_mask.tif"
        classify_subsidence_file(
            fused_vel,
            fused_class_path,
            config.classification,
            water_mask_path=water_mask_path if water_mask_path.exists() else None,
        )
        products["fused_subsidence_class"] = fused_class_path

        # Re-run risk scoring if canal distance exists
        canal_dist = output_dir / "canal_distance.tif"
        if canal_dist.exists():
            from peatguard.analysis.risk_score import generate_risk_map

            fused_risk_path = output_dir / "fused_canal_risk.tif"
            risk_cfg = config.risk_score
            generate_risk_map(
                fused_vel,
                canal_dist,
                fused_risk_path,
                proximity_weight=risk_cfg.proximity_weight,
                subsidence_weight=risk_cfg.subsidence_weight,
                max_influence_m=risk_cfg.max_influence_m,
                severe_velocity_mm_yr=risk_cfg.severe_velocity_mm_yr,
                water_mask_path=water_mask_path if water_mask_path.exists() else None,
            )
            products["fused_canal_risk"] = fused_risk_path

    # Upload to GCS
    if config.storage.gcs_bucket:
        from peatguard.export.gcs import upload_file

        for name, path in products.items():
            blob_name = f"products/{path.name}"
            try:
                upload_file(path, config.storage.gcs_bucket, blob_name)
                click.echo(f"Uploaded {name} to gs://{config.storage.gcs_bucket}/{blob_name}")
            except Exception as exc:
                click.echo(f"Failed to upload {name}: {exc}", err=True)

    click.echo(f"Fusion complete: {len(products)} products generated")
    for name, path in products.items():
        click.echo(f"  {name}: {path}")


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind address.")
@click.option("--port", default=8080, type=int, help="Port number.")
@click.pass_context
def dashboard(ctx: click.Context, host: str, port: int) -> None:
    """Launch the web dashboard for visualizing COG products."""
    try:
        import uvicorn
    except ImportError:
        click.echo(
            "Dashboard dependencies not installed. "
            "Run: pip install peatguard[dashboard]",
            err=True,
        )
        sys.exit(1)

    logger.info("Starting PeatGuard dashboard on %s:%d", host, port)
    uvicorn.run("peatguard.dashboard.app:app", host=host, port=port, log_level="info")


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


@main.command()
@click.option("--status", is_flag=True, help="Show current scheduling status (requires gcloud).")
def schedule(status: bool) -> None:
    """Show automated scheduling setup and status.

    The PeatGuard pipeline can be scheduled to run monthly using Google Cloud
    Scheduler triggering a Cloud Workflow. The workflow orchestrates all 5
    pipeline stages sequentially (with InSAR and backscatter in parallel).

    Setup:
        cd peatguard/peatguard
        bash cloud/scheduler-setup.sh

    Management:
        bash cloud/scheduler-setup.sh --status
        bash cloud/scheduler-setup.sh --pause
        bash cloud/scheduler-setup.sh --resume
        bash cloud/scheduler-setup.sh --run-now
        bash cloud/scheduler-setup.sh --delete
    """
    import subprocess

    click.echo("PeatGuard Automated Scheduling")
    click.echo("=" * 40)
    click.echo("")
    click.echo("Schedule:    1st of each month at 06:00 WIB (Asia/Jakarta)")
    click.echo("Workflow:    peatguard-monthly")
    click.echo("Scheduler:   peatguard-monthly-trigger")
    click.echo("Region:      asia-southeast1")
    click.echo("Project:     peatguard")
    click.echo("")
    click.echo("Pipeline execution order:")
    click.echo("  1. ingest      -- download new Sentinel-1 SLC + GRD")
    click.echo("  2. insar       -- ISCE2 topsApp per pair (parallel with backscatter)")
    click.echo("  3. backscatter -- GRD calibration + composite (parallel with insar)")
    click.echo("  4. timeseries  -- MintPy SBAS inversion")
    click.echo("  5. analyze     -- classification + canal detection + risk scoring")
    click.echo("")
    click.echo("Setup:   bash cloud/scheduler-setup.sh")
    click.echo("Pause:   bash cloud/scheduler-setup.sh --pause")
    click.echo("Resume:  bash cloud/scheduler-setup.sh --resume")
    click.echo("Run now: bash cloud/scheduler-setup.sh --run-now")

    if status:
        click.echo("")
        click.echo("Querying GCP for current status...")
        click.echo("-" * 40)
        try:
            result = subprocess.run(
                [
                    "gcloud", "scheduler", "jobs", "describe",
                    "peatguard-monthly-trigger",
                    "--location=asia-southeast1",
                    "--project=peatguard",
                    "--format=yaml(name,state,schedule,timeZone,lastAttemptTime,nextRunTime)",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                click.echo(result.stdout)
            else:
                click.echo("Scheduler job not found. Run 'bash cloud/scheduler-setup.sh' to deploy.")
        except FileNotFoundError:
            click.echo("gcloud CLI not found. Install the Google Cloud SDK to check status.")
        except subprocess.TimeoutExpired:
            click.echo("Timed out querying GCP. Check your network connection.")


if __name__ == "__main__":
    main()
