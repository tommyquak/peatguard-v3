"""SQLite-based acquisition and processing catalog.

Tracks downloaded scenes, generated interferogram pairs, and processing status
to support idempotent pipeline runs and restart from failure.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Generator, Optional


class ProcessingStatus(str, Enum):
    """Processing state for a catalog entry."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scenes (
    scene_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    acquisition_date TEXT NOT NULL,
    processing_level TEXT NOT NULL,
    relative_orbit INTEGER,
    polarization TEXT,
    local_path TEXT,
    gcs_path TEXT,
    download_status TEXT NOT NULL DEFAULT 'pending',
    download_started_at TEXT,
    download_completed_at TEXT,
    file_size_bytes INTEGER,
    checksum TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS interferograms (
    pair_id TEXT PRIMARY KEY,
    reference_scene_id TEXT NOT NULL,
    secondary_scene_id TEXT NOT NULL,
    temporal_baseline_days INTEGER NOT NULL,
    perpendicular_baseline_m REAL,
    processing_status TEXT NOT NULL DEFAULT 'pending',
    processing_started_at TEXT,
    processing_completed_at TEXT,
    output_dir TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (reference_scene_id) REFERENCES scenes(scene_id),
    FOREIGN KEY (secondary_scene_id) REFERENCES scenes(scene_id)
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL,
    run_date TEXT NOT NULL,
    local_path TEXT,
    gcs_path TEXT,
    crs TEXT,
    bounds TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scenes_date ON scenes(acquisition_date);
CREATE INDEX IF NOT EXISTS idx_scenes_status ON scenes(download_status);
CREATE INDEX IF NOT EXISTS idx_ifg_status ON interferograms(processing_status);
"""


class Catalog:
    """Manages the processing state database."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # -- Scene management --

    def add_scene(
        self,
        scene_id: str,
        platform: str,
        acquisition_date: str,
        processing_level: str,
        relative_orbit: Optional[int] = None,
        polarization: Optional[str] = None,
    ) -> None:
        """Register a discovered scene in the catalog."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO scenes
                (scene_id, platform, acquisition_date, processing_level,
                 relative_orbit, polarization, download_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    scene_id,
                    platform,
                    acquisition_date,
                    processing_level,
                    relative_orbit,
                    polarization,
                    ProcessingStatus.PENDING.value,
                ),
            )

    def update_scene_status(
        self,
        scene_id: str,
        status: ProcessingStatus,
        local_path: Optional[str] = None,
        gcs_path: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        checksum: Optional[str] = None,
    ) -> None:
        """Update the download status for a scene."""
        updates = ["download_status = ?"]
        params: list = [status.value]

        if status == ProcessingStatus.DOWNLOADING:
            updates.append("download_started_at = ?")
            params.append(datetime.utcnow().isoformat())
        elif status in (ProcessingStatus.DOWNLOADED, ProcessingStatus.COMPLETED):
            updates.append("download_completed_at = ?")
            params.append(datetime.utcnow().isoformat())

        if local_path is not None:
            updates.append("local_path = ?")
            params.append(local_path)
        if gcs_path is not None:
            updates.append("gcs_path = ?")
            params.append(gcs_path)
        if file_size_bytes is not None:
            updates.append("file_size_bytes = ?")
            params.append(file_size_bytes)
        if checksum is not None:
            updates.append("checksum = ?")
            params.append(checksum)

        params.append(scene_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE scenes SET {', '.join(updates)} WHERE scene_id = ?",
                params,
            )

    def get_scenes(
        self,
        processing_level: Optional[str] = None,
        status: Optional[ProcessingStatus] = None,
    ) -> list[dict]:
        """Retrieve scenes filtered by level and/or status."""
        query = "SELECT * FROM scenes WHERE 1=1"
        params: list = []
        if processing_level is not None:
            query += " AND processing_level = ?"
            params.append(processing_level)
        if status is not None:
            query += " AND download_status = ?"
            params.append(status.value)
        query += " ORDER BY acquisition_date"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def scene_exists(self, scene_id: str) -> bool:
        """Check if a scene is already registered."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM scenes WHERE scene_id = ?", (scene_id,)
            ).fetchone()
            return row is not None

    # -- Interferogram management --

    def add_interferogram(
        self,
        reference_scene_id: str,
        secondary_scene_id: str,
        temporal_baseline_days: int,
        perpendicular_baseline_m: Optional[float] = None,
    ) -> str:
        """Register an interferogram pair. Returns the pair_id."""
        pair_id = f"{reference_scene_id}__{secondary_scene_id}"
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO interferograms
                (pair_id, reference_scene_id, secondary_scene_id,
                 temporal_baseline_days, perpendicular_baseline_m, processing_status)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    pair_id,
                    reference_scene_id,
                    secondary_scene_id,
                    temporal_baseline_days,
                    perpendicular_baseline_m,
                    ProcessingStatus.PENDING.value,
                ),
            )
        return pair_id

    def update_interferogram_status(
        self,
        pair_id: str,
        status: ProcessingStatus,
        output_dir: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update processing status for an interferogram pair."""
        updates = ["processing_status = ?"]
        params: list = [status.value]

        if status == ProcessingStatus.PROCESSING:
            updates.append("processing_started_at = ?")
            params.append(datetime.utcnow().isoformat())
        elif status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            updates.append("processing_completed_at = ?")
            params.append(datetime.utcnow().isoformat())

        if output_dir is not None:
            updates.append("output_dir = ?")
            params.append(output_dir)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        params.append(pair_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE interferograms SET {', '.join(updates)} WHERE pair_id = ?",
                params,
            )

    def get_interferograms(
        self, status: Optional[ProcessingStatus] = None
    ) -> list[dict]:
        """Retrieve interferogram pairs optionally filtered by status."""
        query = "SELECT * FROM interferograms WHERE 1=1"
        params: list = []
        if status is not None:
            query += " AND processing_status = ?"
            params.append(status.value)
        query += " ORDER BY reference_scene_id"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # -- Product management --

    def add_product(
        self,
        product_type: str,
        run_date: str,
        local_path: str,
        gcs_path: Optional[str] = None,
        crs: Optional[str] = None,
        bounds: Optional[str] = None,
    ) -> str:
        """Register a final output product."""
        product_id = f"{product_type}_{run_date}"
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO products
                (product_id, product_type, run_date, local_path, gcs_path, crs, bounds)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (product_id, product_type, run_date, local_path, gcs_path, crs, bounds),
            )
        return product_id

    def get_latest_product(self, product_type: str) -> Optional[dict]:
        """Get the most recent product of a given type."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE product_type = ? ORDER BY run_date DESC LIMIT 1",
                (product_type,),
            ).fetchone()
            return dict(row) if row else None
