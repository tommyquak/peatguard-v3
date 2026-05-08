"""Shared FastAPI dependencies for the operator + villager API."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from peatguard.api.schemas import UserOut


def current_user(
    authorization: str | None = Header(default=None),
) -> UserOut:
    """Stub auth: any ``Bearer dev-<email>`` token is accepted.

    Real SSO is out of scope for v1 (see plan §Out of scope). Production must
    swap this for OIDC or signed JWTs.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token.startswith("dev-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token format"
        )
    email = token[len("dev-") :]
    if not email or "@" not in email:
        # Allow village-side mobile tokens without @ (we use phone numbers).
        return UserOut(email=email or "anon", name=email or "Operator", role="villager")
    return UserOut(email=email, name=email.split("@")[0].title(), role="operator")
