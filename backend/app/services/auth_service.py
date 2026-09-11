"""Authentication (Team A).

Demo mode (default): any non-empty email/password signs in (or the DEMO_USER_* pair
when configured) and receives an HMAC-signed bearer token. Supabase access tokens are
accepted as-is when SUPABASE_JWT_SECRET is set (HS256 verification, no extra deps).
Authentication is *optional* on every route so the demo never dead-locks; the user, if
present, is recorded as the actor in audit events.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.models._base import utcnow

settings = get_settings()
_TOKEN_TTL = 12 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(msg: bytes, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), msg, hashlib.sha256).digest())


def issue_token(user: dict[str, Any]) -> str:
    body = _b64(json.dumps({"sub": user["email"], "name": user.get("name"), "role": user.get("role", "underwriter"),
                            "exp": int(time.time()) + _TOKEN_TTL}).encode())
    return f"{body}.{_sign(body.encode(), settings.SECRET_KEY)}"


def _verify_demo(token: str) -> dict[str, Any] | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(body.encode(), settings.SECRET_KEY)):
        return None
    claims = json.loads(_unb64(body))
    if claims.get("exp", 0) < time.time():
        return None
    return {"email": claims["sub"], "name": claims.get("name"), "role": claims.get("role", "underwriter")}


def _verify_supabase(token: str) -> dict[str, Any] | None:
    if not settings.SUPABASE_JWT_SECRET:
        return None
    try:
        header, payload, sig = token.split(".")
        expected = _b64(hmac.new(settings.SUPABASE_JWT_SECRET.encode(), f"{header}.{payload}".encode(),
                                 hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            return None
        claims = json.loads(_unb64(payload))
        if claims.get("exp", 0) < time.time():
            return None
        return {"email": claims.get("email"), "name": (claims.get("user_metadata") or {}).get("name"),
                "role": (claims.get("app_metadata") or {}).get("role", "underwriter"), "supabase_uid": claims.get("sub")}
    except Exception:
        return None


def login(db: Session, email: str, password: str) -> dict[str, Any]:
    if not settings.DEMO_AUTH:
        raise HTTPException(status_code=501, detail="password login disabled; use Supabase Auth")
    if not email or not password:
        raise HTTPException(status_code=401, detail="email and password required")
    if settings.DEMO_USER_EMAIL and (email != settings.DEMO_USER_EMAIL or password != settings.DEMO_USER_PASSWORD):
        raise HTTPException(status_code=401, detail="invalid credentials")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        role = "admin" if email.startswith("admin") else ("reviewer" if "review" in email else "underwriter")
        user = User(email=email, name=email.split("@")[0].replace(".", " ").title(), role=role)
        db.add(user)
    user.last_login_at = utcnow()
    db.commit()
    info = {"email": user.email, "name": user.name, "role": user.role}
    return {"access_token": issue_token(info), "token_type": "bearer", "user": info}


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    """Optional-auth dependency: returns the user or None (never blocks)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return _verify_demo(token) or _verify_supabase(token)


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user
