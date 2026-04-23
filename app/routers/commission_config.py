from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_supabase_client

router = APIRouter(prefix="/commission-config", tags=["commission-config"])
ConfigScope = Literal["global", "group", "id_from", "group_id_from"]


class CommissionConfigCreate(BaseModel):
    scope: ConfigScope = "global"
    group_id: str | None = None
    id_from: str | None = None
    payout_pct: float = Field(..., ge=0)
    is_active: bool = True


class CommissionConfigUpdate(BaseModel):
    scope: ConfigScope
    group_id: str | None = None
    id_from: str | None = None
    payout_pct: float = Field(..., ge=0)
    is_active: bool


class CommissionConfigActiveUpdate(BaseModel):
    is_active: bool


def _validate_scope_fields(scope: ConfigScope, group_id: str | None, id_from: str | None) -> None:
    group_value = (group_id or "").strip()
    id_value = (id_from or "").strip()

    if scope == "global":
        return
    if scope == "group" and not group_value:
        raise HTTPException(status_code=422, detail="group_id is required when scope=group")
    if scope == "id_from" and not id_value:
        raise HTTPException(status_code=422, detail="id_from is required when scope=id_from")
    if scope == "group_id_from" and (not group_value or not id_value):
        raise HTTPException(
            status_code=422,
            detail="group_id and id_from are required when scope=group_id_from",
        )


def _normalize_payload(payload: CommissionConfigCreate | CommissionConfigUpdate) -> dict:
    group_value = (payload.group_id or "").strip() or None
    id_value = (payload.id_from or "").strip() or None
    _validate_scope_fields(payload.scope, group_value, id_value)

    if payload.scope == "global":
        group_value = None
        id_value = None
    elif payload.scope == "group":
        id_value = None
    elif payload.scope == "id_from":
        group_value = None

    return {
        "scope": payload.scope,
        "group_id": group_value,
        "id_from": id_value,
        "payout_pct": payload.payout_pct,
        "is_active": payload.is_active,
    }


@router.get("")
def list_commission_configs(
    limit: int = Query(default=200, ge=1, le=1000),
    scope: ConfigScope | None = Query(default=None),
    is_active: bool | None = Query(default=None),
):
    try:
        supabase = get_supabase_client()
        query = supabase.table("commission_config").select("*")
        if scope:
            query = query.eq("scope", scope)
        if is_active is not None:
            query = query.eq("is_active", is_active)

        result = query.order("id", desc=True).limit(limit).execute()
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query commission_config failed: {exc}") from exc


@router.post("")
def create_commission_config(payload: CommissionConfigCreate):
    row = _normalize_payload(payload)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        supabase = get_supabase_client()
        result = supabase.table("commission_config").insert(row).execute()
        created = (result.data or [None])[0]
        return {"item": created}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Create commission_config failed: {exc}") from exc


@router.put("/{config_id}")
def update_commission_config(config_id: int, payload: CommissionConfigUpdate):
    row = _normalize_payload(payload)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("commission_config")
            .update(row)
            .eq("id", config_id)
            .execute()
        )
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Config id={config_id} not found")
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update commission_config failed: {exc}") from exc


@router.patch("/{config_id}/active")
def update_commission_config_active(config_id: int, payload: CommissionConfigActiveUpdate):
    row = {
        "is_active": payload.is_active,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("commission_config")
            .update(row)
            .eq("id", config_id)
            .execute()
        )
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Config id={config_id} not found")
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Update commission_config active failed: {exc}"
        ) from exc
