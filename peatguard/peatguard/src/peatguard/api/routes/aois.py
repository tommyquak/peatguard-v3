"""AOI listing and per-AOI detail."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from peatguard.api.db import connect, row_to_dict
from peatguard.api.schemas import AoiOut

router = APIRouter()


@router.get("/aois", response_model=list[AoiOut])
def list_aois() -> list[AoiOut]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM aois ORDER BY risk DESC").fetchall()
    return [AoiOut(**row_to_dict(r)) for r in rows]


@router.get("/aois/{code}", response_model=AoiOut)
def get_aoi(code: str) -> AoiOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM aois WHERE code = ?", (code,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="aoi not found")
    return AoiOut(**row_to_dict(row))


@router.get("/villages")
def list_villages() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM villages ORDER BY name").fetchall()
    return [row_to_dict(r) for r in rows]
