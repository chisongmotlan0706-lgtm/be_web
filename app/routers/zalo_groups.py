from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, user_owner_global_zalo
from app.db import get_supabase_client

router = APIRouter(prefix="/zalo-groups", tags=["zalo-groups"])

ZaloGroupStatus = Literal["ACTIVE", "INACTIVE", "PENDING"]


class ZaloGroupUpdate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=500)
    status: ZaloGroupStatus


@router.get("")
def list_zalo_groups(
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: dict = Depends(get_current_user),
):
    """Doc zalo_groups theo id_global_main cua user dang nhap (id_globalzalo / fallback id_zl), moi cap nhat truoc."""
    owner_global = user_owner_global_zalo(current_user)
    if not owner_global:
        return {"count": 0, "items": []}

    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("zalo_groups")
            .select("*")
            .is_("deleted_at", "null")
            .eq("id_global_main", owner_global)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query zalo_groups loi: {exc}") from exc


@router.patch("/{group_row_id}")
def update_zalo_group(group_row_id: int, payload: ZaloGroupUpdate):
    """Cap nhat group_name va status theo id (primary key)."""
    name = payload.group_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="group_name khong duoc rong")
    row = {
        "group_name": name,
        "status": payload.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("zalo_groups")
            .update(row)
            .eq("id", group_row_id)
            .is_("deleted_at", "null")
            .execute()
        )
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail=f"zalo_groups id={group_row_id} khong tim thay hoac da xoa",
            )
        return {"item": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cap nhat zalo_groups loi: {exc}") from exc


@router.delete("/{group_row_id}")
def hard_delete_zalo_group(group_row_id: int):
    """Xoa cung ban ghi khoi zalo_groups."""
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("zalo_groups")
            .delete()
            .eq("id", group_row_id)
            .execute()
        )
        deleted = result.data or []
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"zalo_groups id={group_row_id} khong tim thay",
            )
        return {"ok": True, "id": group_row_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Xoa zalo_groups loi: {exc}") from exc
