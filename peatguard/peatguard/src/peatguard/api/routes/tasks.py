"""Task creation, listing, and the four mobile state-machine mutations.

Mirrors the contract documented in
``design_handoff_peatguard/README.md`` § State Management & Backend Contract:

    POST /tasks                       create (operator, W4)
    GET  /tasks?status=...            list (W5 + M2)
    GET  /tasks/:id                   detail (M3 + W5)
    POST /tasks/:id/accept            mobile accept (M3 -> M4)
    POST /tasks/:id/arrive            mobile gps fix (M4 banner)
    POST /tasks/:id/photos            multipart photo (M4) -- sealed sha256 chain
    POST /tasks/:id/submit            mobile submit (M5)

Validation/approval is in ``validation.py``; payments in ``payments.py``.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from peatguard.api.db import connect, default_blob_dir, row_to_dict
from peatguard.api.deps import current_user
from peatguard.api.schemas import (
    ArriveRequest,
    GpsFix,
    PhotoOut,
    TaskCreateRequest,
    TaskOut,
    UserOut,
)

router = APIRouter()


# ---- helpers --------------------------------------------------------------


def _hydrate_task(conn, row) -> TaskOut:
    d = row_to_dict(row)
    photos = conn.execute(
        "SELECT id, phase, ts, lat, lng, accuracy_m, sha256, prev_sha256 FROM photos WHERE task_id = ? ORDER BY id",
        (d["id"],),
    ).fetchall()
    arrived = None
    if d.get("arrived_lat") is not None:
        arrived = GpsFix(lat=d["arrived_lat"], lng=d["arrived_lng"], acc=d["arrived_acc_m"])
    return TaskOut(
        id=d["id"],
        aoi_code=d["aoi_code"],
        village_id=d.get("village_id"),
        type=d["type"],
        title=d["title"],
        sub=d.get("sub"),
        payout_idr=d["payout_idr"],
        deadline=d["deadline"],
        status=d["status"],
        worker_id=d.get("worker_id"),
        deliverables=json.loads(d.get("deliverables_json") or "[]"),
        rail=d.get("rail"),
        arrived=arrived,
        arrived_at=d.get("arrived_at"),
        submitted_at=d.get("submitted_at"),
        decided_at=d.get("decided_at"),
        decision_note=d.get("decision_note"),
        created_at=d["created_at"],
        polygon=json.loads(d["polygon_geojson"]) if d.get("polygon_geojson") else None,
        photos=[PhotoOut(**row_to_dict(p)) for p in photos],
    )


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


# ---- endpoints ------------------------------------------------------------


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    status: Optional[str] = Query(default=None),
    worker_id: Optional[str] = Query(default=None),
    village_id: Optional[str] = Query(default=None),
    aoi_code: Optional[str] = Query(default=None),
) -> list[TaskOut]:
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if worker_id:
        sql += " AND worker_id = ?"
        params.append(worker_id)
    if village_id:
        sql += " AND village_id = ?"
        params.append(village_id)
    if aoi_code:
        sql += " AND aoi_code = ?"
        params.append(aoi_code)
    sql += " ORDER BY created_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_hydrate_task(conn, r) for r in rows]


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str) -> TaskOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        return _hydrate_task(conn, row)


@router.post("/tasks", response_model=TaskOut)
def create_task(req: TaskCreateRequest, _user: UserOut = Depends(current_user)) -> TaskOut:
    new_id = req.aoi_code + "-" + secrets.token_hex(2).upper()
    with connect() as conn:
        conn.execute(
            """INSERT INTO tasks (id, aoi_code, village_id, type, title, sub, polygon_geojson,
                                  payout_idr, deadline, status, deliverables_json, rail)
               VALUES (?,?,?,?,?,?,?,?,?,'available',?,?)""",
            (
                new_id,
                req.aoi_code,
                req.village_id,
                req.type,
                req.title,
                req.sub,
                json.dumps(req.polygon) if req.polygon else None,
                req.payout_idr,
                req.deadline,
                json.dumps(req.deliverables),
                "DANA",
            ),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
        return _hydrate_task(conn, row)


@router.post("/tasks/{task_id}/accept", response_model=TaskOut)
def accept_task(task_id: str, user: UserOut = Depends(current_user)) -> TaskOut:
    worker_id = user.email if user.role == "villager" else "w-sumardi"
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        if row["status"] not in ("available", "accepted"):
            raise HTTPException(
                status_code=409,
                detail=f"cannot accept task in status {row['status']}",
            )
        conn.execute(
            "UPDATE tasks SET status='accepted', worker_id=? WHERE id = ?",
            (worker_id, task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _hydrate_task(conn, row)


@router.post("/tasks/{task_id}/arrive", response_model=TaskOut)
def arrive_at_site(task_id: str, req: ArriveRequest, _user: UserOut = Depends(current_user)) -> TaskOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        conn.execute(
            "UPDATE tasks SET arrived_lat=?, arrived_lng=?, arrived_acc_m=?, arrived_at=? WHERE id=?",
            (req.lat, req.lng, req.accuracy_m, _now_iso(), task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _hydrate_task(conn, row)


@router.post("/tasks/{task_id}/photos", response_model=TaskOut)
async def upload_photo(
    task_id: str,
    phase: str = Form(...),
    ts: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    accuracy_m: float = Form(8.0),
    prev_sha256: Optional[str] = Form(default=None),
    blob: UploadFile = File(...),
    _user: UserOut = Depends(current_user),
) -> TaskOut:
    if phase not in ("before", "during", "after"):
        raise HTTPException(status_code=422, detail="phase must be before/during/after")
    contents = await blob.read()
    sha = hashlib.sha256(contents + (prev_sha256 or "").encode("utf-8")).hexdigest()
    blob_dir = default_blob_dir()
    blob_dir.mkdir(parents=True, exist_ok=True)
    blob_path = blob_dir / f"{sha}.jpg"
    blob_path.write_bytes(contents)
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        # Validate the chain: prev_sha256 must equal the latest photo's sha256.
        last = conn.execute(
            "SELECT sha256 FROM photos WHERE task_id = ? ORDER BY id DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        if last and prev_sha256 and last["sha256"] != prev_sha256:
            raise HTTPException(status_code=409, detail="sha256 chain broken")
        conn.execute(
            "INSERT INTO photos (task_id, phase, ts, lat, lng, accuracy_m, sha256, prev_sha256, blob_path) VALUES (?,?,?,?,?,?,?,?,?)",
            (task_id, phase, ts, lat, lng, accuracy_m, sha, prev_sha256, str(blob_path)),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _hydrate_task(conn, row)


@router.post("/tasks/{task_id}/submit", response_model=TaskOut)
def submit_task(task_id: str, _user: UserOut = Depends(current_user)) -> TaskOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        photo_count = conn.execute(
            "SELECT COUNT(*) AS c FROM photos WHERE task_id = ?", (task_id,)
        ).fetchone()["c"]
        if photo_count < 1:
            raise HTTPException(status_code=409, detail="cannot submit without photos")
        conn.execute(
            "UPDATE tasks SET status='submitted', submitted_at=? WHERE id=?",
            (_now_iso(), task_id),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _hydrate_task(conn, row)
