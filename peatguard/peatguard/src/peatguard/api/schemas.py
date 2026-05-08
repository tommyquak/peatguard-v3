"""Pydantic v2 wire models for the operator + villager API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- Auth ------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: "UserOut"


class UserOut(BaseModel):
    email: str
    name: str
    role: str = "operator"


# ---- AOI -------------------------------------------------------------------


class AoiOut(BaseModel):
    code: str
    name: str
    risk: float
    pct_critical: float
    refresh_date: str
    progress_pct: int
    restored_ha: int
    area_ha: int
    center_lat: float
    center_lng: float


# ---- Worker ----------------------------------------------------------------


class WorkerOut(BaseModel):
    id: str
    name: str
    village: Optional[str] = None
    nik_verified: bool = False
    rating: float = 0
    role: Optional[str] = None
    total_paid: int = 0
    completion_rate: int = 0
    tasks_done: int = 0
    flag: Optional[str] = None


# ---- Task ------------------------------------------------------------------


TaskStatus = Literal["available", "accepted", "submitted", "approved", "rejected", "paid"]
TaskType = Literal["canal_block", "revegetation", "patrol", "fire_watch"]


class GpsFix(BaseModel):
    lat: float
    lng: float
    acc: float


class PhotoOut(BaseModel):
    id: int
    phase: Literal["before", "during", "after"]
    ts: int
    lat: float
    lng: float
    accuracy_m: float
    sha256: str
    prev_sha256: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    aoi_code: str
    village_id: Optional[str]
    type: str
    title: str
    sub: Optional[str] = None
    payout_idr: int
    deadline: str
    status: TaskStatus
    worker_id: Optional[str] = None
    deliverables: list[str] = Field(default_factory=list)
    rail: Optional[str] = None
    arrived: Optional[GpsFix] = None
    arrived_at: Optional[str] = None
    submitted_at: Optional[str] = None
    decided_at: Optional[str] = None
    decision_note: Optional[str] = None
    created_at: str
    photos: list[PhotoOut] = Field(default_factory=list)
    polygon: Optional[dict] = None  # geojson


class TaskCreateRequest(BaseModel):
    aoi_code: str
    type: TaskType
    title: str
    sub: Optional[str] = None
    payout_idr: int
    deadline: str
    village_id: Optional[str] = None
    polygon: Optional[dict] = None
    deliverables: list[str] = Field(default_factory=list)


class ArriveRequest(BaseModel):
    lat: float
    lng: float
    accuracy_m: float = 8.0


class ValidationDecision(BaseModel):
    action: Literal["approve", "revise", "reject"]
    note: Optional[str] = None


# ---- Payments --------------------------------------------------------------


PaymentStatus = Literal["pending", "released", "disputed"]


class PaymentOut(BaseModel):
    id: str
    task_id: str
    worker_id: str
    worker_name: Optional[str] = None
    task_title: Optional[str] = None
    amount: int
    rail: str
    status: PaymentStatus
    flag: Optional[str] = None
    created_at: str
    released_at: Optional[str] = None


class BatchReleaseRequest(BaseModel):
    ids: list[str]


# ---- Messages --------------------------------------------------------------


class MessageOut(BaseModel):
    id: int
    task_id: str
    sender: str
    body: str
    kind: Literal["user", "operator", "system"] = "user"
    attach: Optional[str] = None
    created_at: str


class MessageCreate(BaseModel):
    body: str
    kind: Literal["user", "operator", "system"] = "user"
    attach: Optional[str] = None


# Resolve forward refs for nested models.
LoginResponse.model_rebuild()
