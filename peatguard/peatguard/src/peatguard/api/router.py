"""Aggregator router that ``dashboard.app`` mounts under ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from peatguard.api.routes import (
    aois,
    auth,
    messages,
    payments,
    products,
    tasks,
    validation,
    workers,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(products.router, tags=["products"])
api_router.include_router(aois.router, tags=["aois"])
api_router.include_router(workers.router, tags=["workers"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(validation.router, tags=["validation"])
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(messages.router, tags=["messages"])
