from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.commission_report import parse_and_aggregate_report
from app.db import get_supabase_client

router = APIRouter(prefix="/commission-report", tags=["commission-report"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
UPSERT_CHUNK = 500


@router.get("/orders")
def list_commission_orders(
    limit: int = Query(default=200, ge=1, le=1000),
):
    """Doc ban ghi da import trong affiliate_commission_orders (moi nhat truoc)."""
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("affiliate_commission_orders")
            .select("*")
            .order("order_placed_at", desc=True)
            .limit(limit)
            .execute()
        )
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Query Supabase loi: {exc}",
        ) from exc


@router.post("/import")
async def import_commission_report(file: UploadFile = File(...)):
    """
    Nhan file CSV/XLSX bao cao hoa hong Shopee, gop theo ID don hang, upsert vao Supabase.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Thieu ten file")

    suffix = file.filename.lower()
    if not (suffix.endswith(".csv") or suffix.endswith(".xlsx") or suffix.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="Chi ho tro file .csv, .xlsx hoac .xls",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File rong")

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File vuot qua 15MB")

    try:
        rows = parse_and_aggregate_report(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Doc file loi: {exc}") from exc

    if not rows:
        return {
            "upserted": 0,
            "unique_orders": 0,
            "message": "Khong co dong hop le sau khi doc file",
        }

    for row in rows:
        row["source_filename"] = file.filename

    supabase = get_supabase_client()
    upserted = 0
    for start in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[start : start + UPSERT_CHUNK]
        try:
            supabase.table("affiliate_commission_orders").upsert(
                chunk,
                on_conflict="order_id",
            ).execute()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Luu Supabase loi: {exc}",
            ) from exc
        upserted += len(chunk)

    return {
        "upserted": upserted,
        "unique_orders": len(rows),
        "source_filename": file.filename,
    }
