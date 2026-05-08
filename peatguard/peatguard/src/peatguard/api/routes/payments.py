"""Payment dashboard (W6) endpoints.

Real DANA/OVO/GoPay/BRI/PT-Pos rails are out of scope for v1: ``release`` is a
status flip with a system message in the task thread. The contract is shaped
so a real adapter can drop in later.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from peatguard.api.db import connect, row_to_dict
from peatguard.api.deps import current_user
from peatguard.api.routes.tasks import _now_iso
from peatguard.api.schemas import BatchReleaseRequest, PaymentOut, UserOut

router = APIRouter()


def _hydrate(row) -> PaymentOut:
    d = row_to_dict(row)
    return PaymentOut(**d)


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(status: str | None = Query(default=None)) -> list[PaymentOut]:
    sql = (
        "SELECT p.*, w.name AS worker_name, t.title AS task_title FROM payments p "
        "LEFT JOIN workers w ON w.id = p.worker_id "
        "LEFT JOIN tasks t ON t.id = p.task_id"
    )
    params: list = []
    if status:
        sql += " WHERE p.status = ?"
        params.append(status)
    sql += " ORDER BY p.created_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_hydrate(r) for r in rows]


@router.post("/payments/batch-release", response_model=list[PaymentOut])
def batch_release(
    req: BatchReleaseRequest, user: UserOut = Depends(current_user)
) -> list[PaymentOut]:
    if not req.ids:
        raise HTTPException(status_code=422, detail="no payment ids provided")
    with connect() as conn:
        placeholders = ",".join("?" * len(req.ids))
        rows = conn.execute(
            f"SELECT * FROM payments WHERE id IN ({placeholders}) AND status='pending'",
            req.ids,
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=409, detail="no pending payments matched")
        for r in rows:
            conn.execute(
                "UPDATE payments SET status='released', released_at=? WHERE id=?",
                (_now_iso(), r["id"]),
            )
            conn.execute(
                "UPDATE tasks SET status='paid' WHERE id=?", (r["task_id"],)
            )
            conn.execute(
                "INSERT INTO messages (task_id, sender, body, kind) VALUES (?,?,?, 'system')",
                (r["task_id"], "System", f"Payment Rp {r['amount']:,} released to {r['rail']}."),
            )
        # Re-fetch hydrated rows.
        rows = conn.execute(
            f"SELECT p.*, w.name AS worker_name, t.title AS task_title FROM payments p "
            f"LEFT JOIN workers w ON w.id = p.worker_id "
            f"LEFT JOIN tasks t ON t.id = p.task_id "
            f"WHERE p.id IN ({placeholders})",
            req.ids,
        ).fetchall()
        return [_hydrate(r) for r in rows]


@router.get("/payments/summary")
def payment_summary() -> dict:
    with connect() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS total FROM payments WHERE status='pending'"
        ).fetchone()
        released_mtd = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE status='released'"
        ).fetchone()
        return {
            "pending_count": pending["n"],
            "pending_total": pending["total"],
            "released_total_mtd": released_mtd["total"],
        }
