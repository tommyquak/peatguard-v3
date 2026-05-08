"""SQLite ledger backing the operator + villager REST API.

Schema and connection management mirror the existing acquisition catalog at
``peatguard.catalog`` so both pieces share the same conventions: file in
``~/.peatguard/``, WAL journal, foreign keys on, ``Row`` row factory.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS aois (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    risk REAL NOT NULL,
    pct_critical REAL NOT NULL,
    refresh_date TEXT NOT NULL,
    progress_pct INTEGER NOT NULL,
    restored_ha INTEGER NOT NULL,
    area_ha INTEGER NOT NULL,
    center_lat REAL NOT NULL,
    center_lng REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS villages (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    aoi_code TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    FOREIGN KEY (aoi_code) REFERENCES aois(code)
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    village_id TEXT,
    nik_verified INTEGER NOT NULL DEFAULT 0,
    rating REAL NOT NULL DEFAULT 0,
    role TEXT,
    total_paid INTEGER NOT NULL DEFAULT 0,
    completion_rate INTEGER NOT NULL DEFAULT 0,
    tasks_done INTEGER NOT NULL DEFAULT 0,
    flag TEXT,
    suspended_until TEXT,
    suspend_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (village_id) REFERENCES villages(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    aoi_code TEXT NOT NULL,
    village_id TEXT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    sub TEXT,
    polygon_geojson TEXT,
    payout_idr INTEGER NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    worker_id TEXT,
    deliverables_json TEXT,
    rail TEXT,
    arrived_lat REAL,
    arrived_lng REAL,
    arrived_acc_m REAL,
    arrived_at TEXT,
    submitted_at TEXT,
    decided_at TEXT,
    decision_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (aoi_code) REFERENCES aois(code),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (village_id) REFERENCES villages(id)
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    ts INTEGER NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    accuracy_m REAL NOT NULL,
    sha256 TEXT NOT NULL,
    prev_sha256 TEXT,
    blob_path TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    worker_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    rail TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    flag TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    released_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    body TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'user',
    attach TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_village ON tasks(village_id);
CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_messages_task ON messages(task_id);
"""


def default_db_path() -> Path:
    override = os.environ.get("PEATGUARD_API__DB_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".peatguard" / "ledger.db"


def default_blob_dir() -> Path:
    override = os.environ.get("PEATGUARD_API__BLOB_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".peatguard" / "photo_blobs"


_DB_PATH: Path | None = None


def init_db(db_path: Path | None = None) -> Path:
    """Create tables if they don't exist; return the resolved DB path."""
    global _DB_PATH
    _DB_PATH = (db_path or default_db_path()).resolve()
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    default_blob_dir().mkdir(parents=True, exist_ok=True)
    with _connect(_DB_PATH) as conn:
        conn.executescript(_SCHEMA_SQL)
    return _DB_PATH


@contextmanager
def _connect(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(db_path))
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


@contextmanager
def connect() -> Generator[sqlite3.Connection, None, None]:
    """Open a connection against the initialised ledger DB."""
    if _DB_PATH is None:
        init_db()
    with _connect(_DB_PATH) as conn:  # type: ignore[arg-type]
        yield conn


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}
