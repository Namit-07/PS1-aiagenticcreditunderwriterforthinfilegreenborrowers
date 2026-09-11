"""Authentication routes — Team A (demo login + Supabase token passthrough)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import auth_service
from app.services.auth_service import current_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Exchange credentials for a bearer token (demo auth) — see auth_service."""
    return auth_service.login(db, payload.email.strip().lower(), payload.password)


@router.get("/me")
async def me(user: dict | None = Depends(current_user)) -> dict[str, Any]:
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


@router.post("/refresh")
async def refresh(user: dict | None = Depends(current_user)) -> dict[str, Any]:
    """Re-issue a token for the current user."""
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return {"access_token": auth_service.issue_token(user), "token_type": "bearer", "user": user}


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Stateless tokens: the client discards the token."""
    return {"status": "ok"}
