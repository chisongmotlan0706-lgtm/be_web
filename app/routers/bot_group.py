from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_supabase_client

router = APIRouter(prefix="/bot-group", tags=["bot-group"])

_SELECT_FIELDS = "id,created_at,id_bot,name_bot,type_bot,priority,max_rep,current_rep"

BotType = Literal["REP", "GHI"]


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _generate_id_bot_16_digits() -> str:
    """Dãy số ngẫu nhiên đúng 16 ký tự (0-9), dùng khi tạo mới."""
    n = secrets.randbelow(10**16)
    return f"{n:016d}"


class BotGroupCreate(BaseModel):
    name_bot: str | None = Field(default=None, max_length=2000)
    type_bot: BotType = "REP"
    priority: int = Field(default=1, ge=1, le=100)
    max_rep: int | None = Field(
        default=None,
        description="Gioi han REP (bigint); null = chua dat. current_rep do server/job cap nhat.",
    )


class BotGroupUpdate(BaseModel):
    name_bot: str | None = Field(default=None, max_length=2000)
    type_bot: BotType = "REP"
    priority: int = Field(default=1, ge=1, le=100)
    max_rep: int | None = Field(
        default=None,
        description="Chi cap nhat max_rep; current_rep khong nhan tu client.",
    )


def _optional_bigint(v: int | None) -> int | None:
    if v is None:
        return None
    return int(v)


def _row_from_create(payload: BotGroupCreate) -> dict:
    return {
        "id_bot": _generate_id_bot_16_digits(),
        "name_bot": _blank_to_none(payload.name_bot),
        "type_bot": str(payload.type_bot),
        "priority": int(payload.priority),
        "max_rep": _optional_bigint(payload.max_rep),
        "current_rep": None,
    }


def _row_from_update(payload: BotGroupUpdate) -> dict:
    """Không gửi id_bot, current_rep — giữ nguyên sau khi tạo / cap nhat tu job."""
    return {
        "name_bot": _blank_to_none(payload.name_bot),
        "type_bot": str(payload.type_bot),
        "priority": int(payload.priority),
        "max_rep": _optional_bigint(payload.max_rep),
    }


@router.get("")
def list_bot_group(limit: int = Query(default=200, ge=1, le=1000)):
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("bot_group")
            .select(_SELECT_FIELDS)
            .order("priority", desc=False)
            .order("id", desc=False)
            .limit(limit)
            .execute()
        )
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query bot_group failed: {exc}") from exc


@router.post("")
def create_bot_group(payload: BotGroupCreate):
    row = _row_from_create(payload)
    try:
        supabase = get_supabase_client()
        result = supabase.table("bot_group").insert(row).execute()
        created = (result.data or [None])[0]
        if created is None:
            raise HTTPException(status_code=500, detail="Insert bot_group tra ve rong")
        return {"item": created}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Create bot_group failed: {exc}") from exc


@router.put("/{row_id}")
def update_bot_group(row_id: int, payload: BotGroupUpdate):
    row = _row_from_update(payload)
    try:
        supabase = get_supabase_client()
        result = supabase.table("bot_group").update(row).eq("id", row_id).execute()
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"bot_group id={row_id} not found")
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update bot_group failed: {exc}") from exc


@router.delete("/{row_id}")
def delete_bot_group(row_id: int):
    try:
        supabase = get_supabase_client()
        result = supabase.table("bot_group").delete().eq("id", row_id).execute()
        deleted = result.data or []
        if not deleted:
            raise HTTPException(status_code=404, detail=f"bot_group id={row_id} not found")
        return {"ok": True, "id": row_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delete bot_group failed: {exc}") from exc
