import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.db import get_supabase_client

_bearer = HTTPBearer(auto_error=False)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(raw_password: str) -> str:
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, settings: Settings) -> str:
    now = _utc_now()
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.auth_access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token khong hop le") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Sai loai token")
    user_id = str(payload.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Token khong co sub")
    return payload


def store_refresh_token(
    *,
    user_id: str,
    refresh_token: str,
    settings: Settings,
    created_ip: str | None,
    user_agent: str | None,
) -> None:
    expires_at = _utc_now() + timedelta(days=settings.auth_refresh_token_days)
    row = {
        "user_id": user_id,
        "token_hash": _token_hash(refresh_token),
        "expires_at": expires_at.isoformat(),
        "created_ip": created_ip,
        "user_agent": user_agent,
    }
    get_supabase_client().table("auth_refresh_tokens").insert(row).execute()


def revoke_refresh_token(refresh_token: str) -> None:
    now = _utc_now().isoformat()
    get_supabase_client().table("auth_refresh_tokens").update({"revoked_at": now}).eq(
        "token_hash", _token_hash(refresh_token)
    ).is_("revoked_at", "null").execute()


def validate_refresh_token(refresh_token: str) -> dict:
    now_iso = _utc_now().isoformat()
    result = (
        get_supabase_client()
        .table("auth_refresh_tokens")
        .select("id,user_id,expires_at,revoked_at")
        .eq("token_hash", _token_hash(refresh_token))
        .is_("revoked_at", "null")
        .gte("expires_at", now_iso)
        .limit(1)
        .execute()
    )
    row = (result.data or [None])[0]
    if not row:
        raise HTTPException(status_code=401, detail="Refresh token khong hop le hoac da het han")
    return row


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Chua dang nhap")
    payload = decode_access_token(credentials.credentials, settings)
    user_id = str(payload.get("sub"))
    result = (
        get_supabase_client()
        .table("auth_users")
        .select("id,username,is_active,id_zl")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    user = (result.data or [None])[0]
    if not user or not bool(user.get("is_active")):
        raise HTTPException(status_code=401, detail="Tai khoan khong ton tai hoac da khoa")
    return user
