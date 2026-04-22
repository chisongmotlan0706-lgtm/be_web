from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.db import get_supabase_client

router = APIRouter(prefix="/getorder", tags=["getorder"])
DatePreset = Literal["today", "yesterday", "custom"]


@router.get("")
def get_orders(
    limit: int = Query(default=100, ge=1, le=1000),
    group: str | None = Query(default=None),
    date_preset: DatePreset | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
):
    """
    Read records from public.convert_results ordered by newest first.
    """
    try:
        supabase = get_supabase_client()
        query = supabase.table("convert_results").select("*")

        if group:
            query = query.eq("group", group)

        if date_preset:
            utc_today = datetime.now(timezone.utc).date()

            if date_preset == "today":
                start_dt = datetime.combine(utc_today, time.min, tzinfo=timezone.utc)
                end_dt = start_dt + timedelta(days=1)
            elif date_preset == "yesterday":
                start_dt = datetime.combine(
                    utc_today - timedelta(days=1), time.min, tzinfo=timezone.utc
                )
                end_dt = start_dt + timedelta(days=1)
            else:
                if not from_date or not to_date:
                    raise HTTPException(
                        status_code=422,
                        detail="from_date and to_date are required when date_preset=custom",
                    )
                if from_date > to_date:
                    raise HTTPException(
                        status_code=422,
                        detail="from_date must be less than or equal to to_date",
                    )

                start_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
                # include full to_date by using less-than next day
                end_dt = datetime.combine(
                    to_date + timedelta(days=1), time.min, tzinfo=timezone.utc
                )

            query = query.gte("created_at", start_dt.isoformat()).lt(
                "created_at", end_dt.isoformat()
            )

        result = query.order("created_at", desc=True).limit(limit).execute()
        return {
            "count": len(result.data) if result.data else 0,
            "items": result.data or [],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc
