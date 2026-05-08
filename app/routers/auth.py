from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    verify_password,
)
from app.config import Settings, get_settings
from app.db import get_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginPayload(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=300)


class RefreshPayload(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=2000)


@router.post("/login")
def login(
    payload: LoginPayload,
    request: Request,
    user_agent: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="username khong duoc rong")

    result = (
        get_supabase_client()
        .table("auth_users")
        .select("id,username,password_hash,is_active")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    user = (result.data or [None])[0]
    if not user or not bool(user.get("is_active")):
        raise HTTPException(status_code=401, detail="Sai tai khoan hoac mat khau")
    if not verify_password(payload.password, str(user.get("password_hash") or "")):
        raise HTTPException(status_code=401, detail="Sai tai khoan hoac mat khau")

    user_id = str(user["id"])
    access_token = create_access_token(user_id, settings)
    refresh_token = create_refresh_token()
    store_refresh_token(
        user_id=user_id,
        refresh_token=refresh_token,
        settings=settings,
        created_ip=request.client.host if request.client else None,
        user_agent=user_agent,
    )
    get_supabase_client().table("auth_users").update({"last_login_at": datetime.now(timezone.utc).isoformat()}).eq(
        "id", user_id
    ).execute()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.auth_access_token_minutes * 60,
        "user": {"id": user_id, "username": user.get("username")},
    }


@router.post("/refresh")
def refresh(payload: RefreshPayload, settings: Settings = Depends(get_settings)):
    token_row = validate_refresh_token(payload.refresh_token)
    revoke_refresh_token(payload.refresh_token)
    user_id = str(token_row["user_id"])

    access_token = create_access_token(user_id, settings)
    new_refresh_token = create_refresh_token()
    store_refresh_token(
        user_id=user_id,
        refresh_token=new_refresh_token,
        settings=settings,
        created_ip=None,
        user_agent=None,
    )
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.auth_access_token_minutes * 60,
    }


@router.post("/logout")
def logout(payload: RefreshPayload):
    revoke_refresh_token(payload.refresh_token)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "user": {
            "id": user.get("id"),
            "username": user.get("username"),
            "id_zl": user.get("id_zl"),
        }
    }
