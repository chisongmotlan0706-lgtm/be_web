from fastapi import APIRouter, HTTPException, Query

from app.db import get_supabase_client

router = APIRouter(prefix="/getorder", tags=["getorder"])


@router.get("")
def get_orders(
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Read records from public.convert_results ordered by newest first.
    """
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("convert_results")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {
            "count": len(result.data) if result.data else 0,
            "items": result.data or [],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc
