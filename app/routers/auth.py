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


class UpdateProfilePayload(BaseModel):
    aff_id: str = Field(..., min_length=1, max_length=200)


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
        .select("id,username,password_hash,is_active,id_globalzalo,id_zl")
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
    access_token = create_access_token(
        user_id,
        settings,
        id_globalzalo=str(user.get("id_globalzalo") or "").strip() or None,
    )
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

    ures = (
        get_supabase_client()
        .table("auth_users")
        .select("id_globalzalo,id_zl")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    urow = (ures.data or [None])[0] or {}
    access_token = create_access_token(
        user_id,
        settings,
        id_globalzalo=str(urow.get("id_globalzalo") or "").strip() or None,
    )
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
            "id_globalzalo": user.get("id_globalzalo"),
            "aff_id": user.get("aff_id"),
        }
    }


@router.patch("/me")
def update_me(payload: UpdateProfilePayload, user: dict = Depends(get_current_user)):
    aff_id = payload.aff_id.strip()
    if not aff_id:
        raise HTTPException(status_code=422, detail="aff_id khong duoc rong")
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Token khong hop le")
    row = {
        "aff_id": aff_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase = get_supabase_client()
        supabase.table("auth_users").update(row).eq("id", user_id).execute()
        result = (
            supabase.table("auth_users")
            .select("id,username,id_zl,id_globalzalo,aff_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail="Khong tim thay user")
        return {"user": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cap nhat aff_id loi: {exc}") from exc
