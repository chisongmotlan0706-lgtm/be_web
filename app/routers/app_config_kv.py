from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_supabase_client

router = APIRouter(prefix="/app-config-kv", tags=["app-config-kv"])

_SELECT_FIELDS = (
    "id,config_key,value_1,value_2,value_3,value_4,value_5,"
    "label_1,label_2,label_3,label_4,label_5,"
    "description,category,is_active,created_at,updated_at"
)


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


class AppConfigKvCreate(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=500)
    value_1: str | None = None
    value_2: str | None = None
    value_3: str | None = None
    value_4: str | None = None
    value_5: str | None = None
    label_1: str | None = Field(default=None, max_length=500)
    label_2: str | None = Field(default=None, max_length=500)
    label_3: str | None = Field(default=None, max_length=500)
    label_4: str | None = Field(default=None, max_length=500)
    label_5: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=200)
    is_active: bool = True


class AppConfigKvUpdate(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=500)
    value_1: str | None = None
    value_2: str | None = None
    value_3: str | None = None
    value_4: str | None = None
    value_5: str | None = None
    label_1: str | None = Field(default=None, max_length=500)
    label_2: str | None = Field(default=None, max_length=500)
    label_3: str | None = Field(default=None, max_length=500)
    label_4: str | None = Field(default=None, max_length=500)
    label_5: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=200)
    is_active: bool = True


def _row_from_create(payload: AppConfigKvCreate) -> dict:
    key = str(payload.config_key or "").strip()
    if not key:
        raise HTTPException(status_code=422, detail="config_key khong duoc rong")
    return {
        "config_key": key,
        "value_1": _blank_to_none(payload.value_1),
        "value_2": _blank_to_none(payload.value_2),
        "value_3": _blank_to_none(payload.value_3),
        "value_4": _blank_to_none(payload.value_4),
        "value_5": _blank_to_none(payload.value_5),
        "label_1": _blank_to_none(payload.label_1),
        "label_2": _blank_to_none(payload.label_2),
        "label_3": _blank_to_none(payload.label_3),
        "label_4": _blank_to_none(payload.label_4),
        "label_5": _blank_to_none(payload.label_5),
        "description": _blank_to_none(payload.description),
        "category": _blank_to_none(payload.category),
        "is_active": bool(payload.is_active),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _row_from_update(payload: AppConfigKvUpdate) -> dict:
    key = str(payload.config_key or "").strip()
    if not key:
        raise HTTPException(status_code=422, detail="config_key khong duoc rong")
    return {
        "config_key": key,
        "value_1": _blank_to_none(payload.value_1),
        "value_2": _blank_to_none(payload.value_2),
        "value_3": _blank_to_none(payload.value_3),
        "value_4": _blank_to_none(payload.value_4),
        "value_5": _blank_to_none(payload.value_5),
        "label_1": _blank_to_none(payload.label_1),
        "label_2": _blank_to_none(payload.label_2),
        "label_3": _blank_to_none(payload.label_3),
        "label_4": _blank_to_none(payload.label_4),
        "label_5": _blank_to_none(payload.label_5),
        "description": _blank_to_none(payload.description),
        "category": _blank_to_none(payload.category),
        "is_active": bool(payload.is_active),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
def list_app_config_kv(
    limit: int = Query(default=200, ge=1, le=1000),
    category: str | None = Query(default=None, description="Loc theo category (trim, dung =)"),
    search: str | None = Query(default=None, description="Tim config_key chua chuoi (ilike)"),
):
    try:
        supabase = get_supabase_client()
        query = supabase.table("app_config_kv").select(_SELECT_FIELDS)
        if category is not None and str(category).strip():
            query = query.eq("category", str(category).strip())
        if search is not None and str(search).strip():
            query = query.ilike("config_key", f"%{str(search).strip()}%")
        result = query.order("id", desc=True).limit(limit).execute()
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query app_config_kv failed: {exc}") from exc


@router.post("")
def create_app_config_kv(payload: AppConfigKvCreate):
    row = _row_from_create(payload)
    try:
        supabase = get_supabase_client()
        result = supabase.table("app_config_kv").insert(row).execute()
        created = (result.data or [None])[0]
        if created is None:
            raise HTTPException(status_code=500, detail="Insert app_config_kv tra ve rong")
        return {"item": created}
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(
                status_code=409,
                detail="config_key da ton tai",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Create app_config_kv failed: {exc}") from exc


@router.put("/{row_id}")
def update_app_config_kv(
    row_id: int,
    payload: AppConfigKvUpdate,
):
    row = _row_from_update(payload)
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("app_config_kv")
            .update(row)
            .eq("id", row_id)
            .execute()
        )
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"app_config_kv id={row_id} not found")
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(status_code=409, detail="config_key da ton tai") from exc
        raise HTTPException(status_code=500, detail=f"Update app_config_kv failed: {exc}") from exc


@router.delete("/{row_id}")
def delete_app_config_kv(row_id: int):
    try:
        supabase = get_supabase_client()
        result = supabase.table("app_config_kv").delete().eq("id", row_id).execute()
        deleted = result.data or []
        if not deleted:
            raise HTTPException(status_code=404, detail=f"app_config_kv id={row_id} not found")
        return {"ok": True, "id": row_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delete app_config_kv failed: {exc}") from exc
