"""Threaded messages between operator and villager, scoped per task."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from peatguard.api.db import connect, row_to_dict
from peatguard.api.deps import current_user
from peatguard.api.schemas import MessageCreate, MessageOut, UserOut

router = APIRouter()


@router.get("/threads/{task_id}", response_model=list[MessageOut])
def list_messages(task_id: str) -> list[MessageOut]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE task_id = ? ORDER BY id", (task_id,)
        ).fetchall()
        return [MessageOut(**row_to_dict(r)) for r in rows]


@router.post("/threads/{task_id}", response_model=MessageOut)
def post_message(
    task_id: str, body: MessageCreate, user: UserOut = Depends(current_user)
) -> MessageOut:
    if not body.body and not body.attach:
        raise HTTPException(status_code=422, detail="empty message")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (task_id, sender, body, kind, attach) VALUES (?,?,?,?,?)",
            (task_id, user.name or user.email, body.body, body.kind, body.attach),
        )
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return MessageOut(**row_to_dict(row))
