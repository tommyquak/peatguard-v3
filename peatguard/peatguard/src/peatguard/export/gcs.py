"""Google Cloud Storage upload and download utilities.

Handles transfer of pipeline inputs and outputs between local storage
and GCS buckets. Supports both individual files and directory uploads.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from peatguard.config import StorageConfig

logger = logging.getLogger(__name__)


def _get_client():
    """Lazy import and create GCS client."""
    from google.cloud import storage

    return storage.Client()


def upload_file(
    local_path: Path,
    bucket_name: str,
    blob_name: str,
    content_type: Optional[str] = None,
) -> str:
    """Upload a single file to GCS.

    Args:
        local_path: Path to the local file.
        bucket_name: GCS bucket name.
        blob_name: Destination blob path within the bucket.
        content_type: MIME type. Inferred if None.

    Returns:
        GCS URI (gs://bucket/blob) of the uploaded file.
    """
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if content_type:
        blob.content_type = content_type

    blob.upload_from_filename(str(local_path))
    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    logger.info("Uploaded %s to %s", local_path.name, gcs_uri)
    return gcs_uri


def download_file(
    bucket_name: str,
    blob_name: str,
    local_path: Path,
) -> Path:
    """Download a single file from GCS.

    Args:
        bucket_name: GCS bucket name.
        blob_name: Source blob path within the bucket.
        local_path: Local destination path.

    Returns:
        Path to the downloaded file.
    """
    local_path.parent.mkdir(parents=True, exist_ok=True)

    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(str(local_path))

    logger.info("Downloaded gs://%s/%s to %s", bucket_name, blob_name, local_path)
    return local_path


def upload_directory(
    local_dir: Path,
    bucket_name: str,
    prefix: str,
    pattern: str = "*",
) -> list[str]:
    """Upload all files in a directory to GCS.

    Args:
        local_dir: Local directory to upload.
        bucket_name: GCS bucket name.
        prefix: Destination prefix within the bucket.
        pattern: Glob pattern for files to upload.

    Returns:
        List of GCS URIs for uploaded files.
    """
    uploaded = []
    for filepath in sorted(local_dir.glob(pattern)):
        if filepath.is_file():
            blob_name = f"{prefix}/{filepath.name}"
            uri = upload_file(filepath, bucket_name, blob_name)
            uploaded.append(uri)

    logger.info("Uploaded %d files from %s to gs://%s/%s", len(uploaded), local_dir, bucket_name, prefix)
    return uploaded


def list_blobs(
    bucket_name: str,
    prefix: str,
    suffix: str = "",
) -> list[str]:
    """List blob names in a GCS bucket matching a prefix and optional suffix.

    Args:
        bucket_name: GCS bucket name.
        prefix: Prefix to filter blobs.
        suffix: Optional suffix filter (e.g., '.zip').

    Returns:
        List of blob names matching the criteria.
    """
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    names = [b.name for b in blobs if b.name.endswith(suffix) or not suffix]
    logger.info("Found %d blobs in gs://%s/%s (suffix=%s)", len(names), bucket_name, prefix, suffix)
    return names


def sync_from_gcs(
    bucket_name: str,
    prefix: str,
    local_dir: Path,
    suffix: str = "",
) -> list[Path]:
    """Download all files matching prefix from GCS to a local directory.

    Skips files that already exist locally with matching size.

    Args:
        bucket_name: GCS bucket name.
        prefix: GCS prefix to sync from.
        local_dir: Local destination directory.
        suffix: Optional suffix filter.

    Returns:
        List of local file paths.
    """
    local_dir.mkdir(parents=True, exist_ok=True)
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))

    local_paths = []
    for blob in blobs:
        if suffix and not blob.name.endswith(suffix):
            continue
        filename = blob.name.split("/")[-1]
        if not filename:
            continue
        local_path = local_dir / filename

        # Skip if already exists with same size
        if local_path.exists() and local_path.stat().st_size == blob.size:
            logger.info("Skipping %s (already exists)", filename)
            local_paths.append(local_path)
            continue

        logger.info("Downloading %s (%d MB)", filename, blob.size // (1024 * 1024))
        blob.download_to_filename(str(local_path))
        local_paths.append(local_path)

    logger.info("Synced %d files from gs://%s/%s to %s", len(local_paths), bucket_name, prefix, local_dir)
    return local_paths


def upload_products(
    output_dir: Path,
    storage_config: StorageConfig,
    run_date: str,
) -> list[str]:
    """Upload final pipeline products to GCS.

    Organizes outputs under the configured prefix with date-based
    partitioning for easy discovery and versioning.

    Args:
        output_dir: Local directory containing output products.
        storage_config: Storage configuration with bucket details.
        run_date: Processing run date for partitioning.

    Returns:
        List of GCS URIs for uploaded products.
    """
    if not storage_config.gcs_bucket:
        logger.info("No GCS bucket configured, skipping upload")
        return []

    prefix = f"{storage_config.gcs_prefix}/products/{run_date}"
    return upload_directory(
        output_dir,
        storage_config.gcs_bucket,
        prefix,
        pattern="*.tif",
    )
