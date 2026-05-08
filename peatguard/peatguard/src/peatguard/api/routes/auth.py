"""Stub auth: any credentials yield a deterministic dev token.

Real SSO is out of scope for v1 -- swap for OIDC/JWT before production. The
token format ``dev-<email>`` lets ``deps.current_user`` recover the caller.
"""

from __future__ import annotations

from fastapi import APIRouter

from peatguard.api.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    name_part = req.email.split("@")[0] if "@" in req.email else req.email
    user = UserOut(email=req.email, name=name_part.title() or "Operator", role="operator")
    return LoginResponse(token=f"dev-{req.email}", user=user)


@router.post("/auth/villager-login", response_model=LoginResponse)
def villager_login(req: LoginRequest) -> LoginResponse:
    """Villager onboarding shortcut -- accepts a phone or worker id as ``email``."""
    user = UserOut(email=req.email, name=req.email, role="villager")
    return LoginResponse(token=f"dev-{req.email}", user=user)
