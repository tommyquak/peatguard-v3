"""SAR scene download manager.

Handles authenticated downloads from ASF DAAC with streaming support,
progress tracking, and catalog integration. Supports both Sentinel-1
and NISAR products. Uses NASA Earthdata credentials stored in ~/.netrc.

Downloads are streamed in chunks to avoid buffering entire SLC files
(4-6 GB each) in memory, which is critical for Cloud Run's memory limits.
Files are streamed directly to GCS when a bucket is configured.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import asf_search as asf

from peatguard.catalog import Catalog, ProcessingStatus
from peatguard.config import PeatGuardConfig

logger = logging.getLogger(__name__)

STREAM_CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB chunks


def _compute_md5(filepath: Path, chunk_size: int = 8192) -> str:
    """Compute MD5 checksum of a file."""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def _get_scene_date(product: asf.ASFProduct) -> str:
    """Extract acquisition date string from an ASF product."""
    start_time = product.properties["startTime"]
    if isinstance(start_time, str):
        return start_time[:10]
    return start_time.strftime("%Y-%m-%d")


def _get_scene_id(product: asf.ASFProduct) -> str:
    """Extract a unique scene identifier from an ASF product."""
    return product.properties.get("sceneName", product.properties.get("fileID", ""))


def _stream_download(url: str, filepath: Path, session: asf.ASFSession) -> int:
    """Stream download a file in chunks to avoid buffering in memory.

    Args:
        url: Download URL.
        filepath: Local file path to write to.
        session: Authenticated ASF session.

    Returns:
        Total bytes written.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = filepath.with_suffix(filepath.suffix + ".part")

    total_bytes = 0
    response = session.get(url, stream=True)
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length:
        logger.info("File size: %.1f GB", int(content_length) / (1024 ** 3))

    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                total_bytes += len(chunk)

                if total_bytes % (256 * 1024 * 1024) < STREAM_CHUNK_SIZE:
                    logger.info(
                        "  Progress: %.1f GB downloaded", total_bytes / (1024 ** 3)
                    )

    tmp_path.rename(filepath)
    return total_bytes


def _stream_download_to_gcs(
    url: str, gcs_uri: str, session: asf.ASFSession
) -> int:
    """Stream download directly to GCS without touching local disk.

    Args:
        url: Download URL.
        gcs_uri: GCS destination path (gs://bucket/path).
        session: Authenticated ASF session.

    Returns:
        Total bytes written.
    """
    from google.cloud import storage as gcs

    bucket_name = gcs_uri.split("/")[2]
    blob_path = "/".join(gcs_uri.split("/")[3:])

    client = gcs.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    response = session.get(url, stream=True)
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length:
        logger.info("File size: %.1f GB", int(content_length) / (1024 ** 3))

    total_bytes = 0

    with blob.open("wb", chunk_size=STREAM_CHUNK_SIZE) as gcs_file:
        for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
            if chunk:
                gcs_file.write(chunk)
                total_bytes += len(chunk)

                if total_bytes % (256 * 1024 * 1024) < STREAM_CHUNK_SIZE:
                    logger.info(
                        "  Progress: %.1f GB streamed to GCS",
                        total_bytes / (1024 ** 3),
                    )

    return total_bytes


def authenticate_earthdata(
    username: Optional[str] = None, password: Optional[str] = None
) -> asf.ASFSession:
    """Create an authenticated ASF session.

    Uses credentials from ~/.netrc if username/password are not provided.

    Args:
        username: NASA Earthdata username. Read from ~/.netrc if None.
        password: NASA Earthdata password. Read from ~/.netrc if None.

    Returns:
        Authenticated ASF session for downloading.
    """
    session = asf.ASFSession()
    if username and password:
        session.auth_with_creds(username, password)
    else:
        import netrc as netrc_module

        netrc_path = Path.home() / ".netrc"
        if netrc_path.exists():
            try:
                creds = netrc_module.netrc(str(netrc_path))
                auth = creds.authenticators("urs.earthdata.nasa.gov")
                if auth:
                    session.auth_with_creds(auth[0], auth[2])
                else:
                    logger.warning("No urs.earthdata.nasa.gov entry in .netrc")
            except netrc_module.NetrcParseError:
                logger.warning("Failed to parse .netrc file")
        else:
            logger.warning("No .netrc file found at %s", netrc_path)
    logger.info("Authenticated with NASA Earthdata")
    return session


def download_scenes(
    products: list[asf.ASFProduct],
    download_dir: Path,
    catalog: Optional[Catalog] = None,
    session: Optional[asf.ASFSession] = None,
    verify_checksum: bool = True,
    gcs_bucket: Optional[str] = None,
    gcs_prefix: str = "raw/slc",
) -> list[Path]:
    """Download a list of ASF products with streaming.

    Uses chunked streaming to avoid buffering entire files in memory.
    When gcs_bucket is set, streams directly to GCS to avoid local
    disk limitations on Cloud Run.

    Args:
        products: List of ASF products to download.
        download_dir: Local directory for downloaded files.
        catalog: Optional catalog for tracking download state.
        session: Authenticated ASF session. Creates one if None.
        verify_checksum: Whether to compute and store MD5 after download.
        gcs_bucket: If set, stream directly to this GCS bucket.
        gcs_prefix: GCS path prefix within the bucket.

    Returns:
        List of paths to downloaded files (local paths or GCS URIs as Path).
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    if session is None:
        session = authenticate_earthdata()

    # Auto-detect GCS bucket from environment
    if gcs_bucket is None:
        gcs_bucket = os.environ.get("PEATGUARD_STORAGE__GCS_BUCKET")

    downloaded_paths = []

    for i, product in enumerate(products, 1):
        scene_id = _get_scene_id(product)
        scene_date = _get_scene_date(product)
        filename = product.properties.get("fileName", f"{scene_id}.zip")
        filepath = download_dir / filename

        logger.info(
            "[%d/%d] Processing %s (%s)",
            i,
            len(products),
            scene_id,
            scene_date,
        )

        if catalog is not None:
            processing_level = product.properties.get("processingLevel", "SLC")
            path_number = product.properties.get("pathNumber")
            catalog.add_scene(
                scene_id=scene_id,
                platform="SENTINEL-1",
                acquisition_date=scene_date,
                processing_level=processing_level,
                relative_orbit=path_number,
                polarization="VV",
            )

        # Check for existing complete download (local)
        if filepath.exists():
            expected_size = product.properties.get("bytes")
            actual_size = filepath.stat().st_size
            if expected_size is None or actual_size == int(expected_size):
                logger.info("Already downloaded: %s (%d bytes)", filename, actual_size)
                if catalog is not None:
                    catalog.update_scene_status(
                        scene_id,
                        ProcessingStatus.DOWNLOADED,
                        local_path=str(filepath),
                        file_size_bytes=actual_size,
                    )
                downloaded_paths.append(filepath)
                continue
            else:
                logger.info(
                    "Incomplete download detected (%d/%s bytes), re-downloading",
                    actual_size,
                    expected_size,
                )

        # Check for existing download in GCS
        if gcs_bucket:
            try:
                from google.cloud import storage as gcs
                client = gcs.Client()
                bucket_obj = client.bucket(gcs_bucket)
                blob = bucket_obj.blob(f"{gcs_prefix}/{filename}")
                if blob.exists():
                    blob.reload()
                    logger.info(
                        "Already in GCS: %s (%d bytes)",
                        filename,
                        blob.size or 0,
                    )
                    if catalog is not None:
                        catalog.update_scene_status(
                            scene_id,
                            ProcessingStatus.DOWNLOADED,
                            local_path=f"gs://{gcs_bucket}/{gcs_prefix}/{filename}",
                            file_size_bytes=blob.size or 0,
                        )
                    downloaded_paths.append(filepath)
                    continue
            except Exception:
                pass

        if catalog is not None:
            catalog.update_scene_status(scene_id, ProcessingStatus.DOWNLOADING)

        try:
            download_url = product.properties.get("url")
            if not download_url:
                urls = product.properties.get("additionalUrls", [])
                download_url = urls[0] if urls else None
            if not download_url:
                download_url = f"https://datapool.asf.alaska.edu/SLC/SA/{filename}"

            if gcs_bucket:
                gcs_uri = f"gs://{gcs_bucket}/{gcs_prefix}/{filename}"
                logger.info("Streaming to GCS: %s", gcs_uri)
                file_size = _stream_download_to_gcs(download_url, gcs_uri, session)

                if catalog is not None:
                    catalog.update_scene_status(
                        scene_id,
                        ProcessingStatus.DOWNLOADED,
                        local_path=gcs_uri,
                        file_size_bytes=file_size,
                    )
                downloaded_paths.append(filepath)
            else:
                logger.info("Streaming to disk: %s", filepath)
                file_size = _stream_download(download_url, filepath, session)

                checksum = None
                if verify_checksum:
                    checksum = _compute_md5(filepath)

                if catalog is not None:
                    catalog.update_scene_status(
                        scene_id,
                        ProcessingStatus.DOWNLOADED,
                        local_path=str(filepath),
                        file_size_bytes=file_size,
                        checksum=checksum,
                    )
                downloaded_paths.append(filepath)

            logger.info("Downloaded: %s (%.1f GB)", filename, file_size / (1024 ** 3))

        except Exception as exc:
            logger.error("Failed to download %s: %s", scene_id, exc)
            if catalog is not None:
                catalog.update_scene_status(scene_id, ProcessingStatus.FAILED)
            raise

    logger.info(
        "Download complete: %d/%d scenes", len(downloaded_paths), len(products)
    )
    return downloaded_paths
