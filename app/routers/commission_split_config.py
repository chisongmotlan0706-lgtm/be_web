from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_supabase_client

router = APIRouter(prefix="/commission-split-config", tags=["commission-split-config"])


class CommissionSplitConfigRow(BaseModel):
    agency_pct: float = Field(..., ge=0, le=100)
    owner_pct: float = Field(..., ge=0, le=100)


def _validate_sum(agency_pct: float, owner_pct: float) -> None:
    if agency_pct + owner_pct > 100:
        raise HTTPException(status_code=422, detail="Tong agency_pct + owner_pct phai <= 100")


def _ensure_row_exists(supabase) -> None:
    # Singleton row id=1, insert defaults if missing.
    try:
        supabase.table("commission_split_config").upsert(
            {"id": 1, "agency_pct": 15, "owner_pct": 25}, on_conflict="id"
        ).execute()
    except Exception:
        # If table doesn't exist yet, let the caller see a clearer error later.
        return


@router.get("")
def get_commission_split_config(current_user: dict = Depends(get_current_user)):
    # current_user dependency keeps this endpoint authenticated like others.
    try:
        supabase = get_supabase_client()
        _ensure_row_exists(supabase)
        result = (
            supabase.table("commission_split_config")
            .select("agency_pct,owner_pct,updated_at")
            .eq("id", 1)
            .single()
            .execute()
        )
        item = result.data or {}
        if not item:
            return {"item": {"agency_pct": 15, "owner_pct": 25}}
        return {"item": item}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query commission_split_config failed: {exc}") from exc


@router.put("")
def update_commission_split_config(
    payload: CommissionSplitConfigRow, current_user: dict = Depends(get_current_user)
):
    agency = float(payload.agency_pct)
    owner = float(payload.owner_pct)
    _validate_sum(agency, owner)
    row = {
        "id": 1,
        "agency_pct": agency,
        "owner_pct": owner,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("commission_split_config")
            .upsert(row, on_conflict="id")
            .select("agency_pct,owner_pct,updated_at")
            .single()
            .execute()
        )
        return {"item": result.data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update commission_split_config failed: {exc}") from exc
