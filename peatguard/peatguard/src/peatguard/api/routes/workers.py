"""Worker registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from peatguard.api.db import connect, row_to_dict
from peatguard.api.schemas import WorkerOut

router = APIRouter()


def _hydrate(row) -> WorkerOut:
    d = row_to_dict(row)
    d["village"] = d.pop("village_name", None)
    d["nik_verified"] = bool(d.get("nik_verified"))
    return WorkerOut(**d)


@router.get("/workers", response_model=list[WorkerOut])
def list_workers() -> list[WorkerOut]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT w.*, v.name AS village_name FROM workers w
               LEFT JOIN villages v ON v.id = w.village_id
               ORDER BY w.completion_rate DESC"""
        ).fetchall()
    return [_hydrate(r) for r in rows]


@router.get("/workers/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: str) -> WorkerOut:
    with connect() as conn:
        row = conn.execute(
            """SELECT w.*, v.name AS village_name FROM workers w
               LEFT JOIN villages v ON v.id = w.village_id
               WHERE w.id = ?""",
            (worker_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="worker not found")
    return _hydrate(row)
