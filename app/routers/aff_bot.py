from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_supabase_client

router = APIRouter(prefix="/aff-bot", tags=["aff-bot"])

_SELECT_FIELDS = "id,created_at,id_aff"


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


class AffBotCreate(BaseModel):
    id_aff: str | None = Field(default=None, max_length=2000)


class AffBotUpdate(BaseModel):
    id_aff: str | None = Field(default=None, max_length=2000)


def _row_from_create(payload: AffBotCreate) -> dict:
    return {"id_aff": _blank_to_none(payload.id_aff)}


def _row_from_update(payload: AffBotUpdate) -> dict:
    return {"id_aff": _blank_to_none(payload.id_aff)}


@router.get("")
def list_aff_bot(
    limit: int = Query(default=200, ge=1, le=1000),
    search: str | None = Query(default=None, description="Tim id_aff chua chuoi (ilike)"),
):
    try:
        supabase = get_supabase_client()
        query = supabase.table("aff_bot").select(_SELECT_FIELDS)
        if search is not None and str(search).strip():
            query = query.ilike("id_aff", f"%{str(search).strip()}%")
        result = query.order("id", desc=True).limit(limit).execute()
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query aff_bot failed: {exc}") from exc


@router.post("")
def create_aff_bot(payload: AffBotCreate):
    row = _row_from_create(payload)
    try:
        supabase = get_supabase_client()
        result = supabase.table("aff_bot").insert(row).execute()
        created = (result.data or [None])[0]
        if created is None:
            raise HTTPException(status_code=500, detail="Insert aff_bot tra ve rong")
        return {"item": created}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Create aff_bot failed: {exc}") from exc


@router.put("/{row_id}")
def update_aff_bot(row_id: int, payload: AffBotUpdate):
    row = _row_from_update(payload)
    try:
        supabase = get_supabase_client()
        result = supabase.table("aff_bot").update(row).eq("id", row_id).execute()
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"aff_bot id={row_id} not found")
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update aff_bot failed: {exc}") from exc


@router.delete("/{row_id}")
def delete_aff_bot(row_id: int):
    try:
        supabase = get_supabase_client()
        result = supabase.table("aff_bot").delete().eq("id", row_id).execute()
        deleted = result.data or []
        if not deleted:
            raise HTTPException(status_code=404, detail=f"aff_bot id={row_id} not found")
        return {"ok": True, "id": row_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delete aff_bot failed: {exc}") from exc
