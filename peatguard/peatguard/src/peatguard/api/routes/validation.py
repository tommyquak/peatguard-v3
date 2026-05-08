"""Operator validation: approve, request revision, or reject a submission.

Approval inserts a pending Payment row that the W6 batch-release endpoint can
move to ``released``. Reject sets ``status='rejected'`` and records the note;
the appeal lane (handoff §Pushback #3) is presentational only in v1.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException

from peatguard.api.db import connect, row_to_dict
from peatguard.api.deps import current_user
from peatguard.api.routes.tasks import _hydrate_task, _now_iso
from peatguard.api.schemas import TaskOut, UserOut, ValidationDecision

router = APIRouter()


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def decide_submission(
    task_id: str,
    decision: ValidationDecision,
    user: UserOut = Depends(current_user),
) -> TaskOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task not found")
        d = row_to_dict(row)
        if d["status"] not in ("submitted",):
            raise HTTPException(
                status_code=409,
                detail=f"can only decide on submitted tasks, got {d['status']}",
            )
        if decision.action == "approve":
            conn.execute(
                "UPDATE tasks SET status='approved', decided_at=?, decision_note=? WHERE id=?",
                (_now_iso(), decision.note, task_id),
            )
            # Open a pending payment.
            pid = "pay-" + secrets.token_hex(4)
            conn.execute(
                """INSERT INTO payments (id, task_id, worker_id, amount, rail, status)
                   VALUES (?,?,?,?,?,'pending')""",
                (pid, task_id, d["worker_id"], d["payout_idr"], d.get("rail") or "DANA"),
            )
            conn.execute(
                "INSERT INTO messages (task_id, sender, body, kind) VALUES (?,?,?, 'system')",
                (task_id, user.name or "Operator",
                 f"Submission approved. Payment Rp {d['payout_idr']:,} queued for release."),
            )
        elif decision.action == "revise":
            # Revision keeps status=submitted; we just add an operator message.
            conn.execute(
                "INSERT INTO messages (task_id, sender, body, kind) VALUES (?,?,?, 'operator')",
                (task_id, user.name or "Operator",
                 decision.note or "Please revise your submission."),
            )
        elif decision.action == "reject":
            conn.execute(
                "UPDATE tasks SET status='rejected', decided_at=?, decision_note=? WHERE id=?",
                (_now_iso(), decision.note or "rejected", task_id),
            )
            conn.execute(
                "INSERT INTO messages (task_id, sender, body, kind) VALUES (?,?,?, 'system')",
                (task_id, "System", f"Submission rejected: {decision.note or 'no reason given'}"),
            )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _hydrate_task(conn, row)
