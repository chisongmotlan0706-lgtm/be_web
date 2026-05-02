import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.commission_report import parse_and_aggregate_report
from app.db import get_supabase_client

router = APIRouter(prefix="/commission-report", tags=["commission-report"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
UPSERT_CHUNK = 500
LOOKUP_CHUNK = 500
PLACED_WITHIN_DAYS_ALLOWED = frozenset({1, 3, 7, 14})
ORDER_STATUS_PAID_SYNCED = "Đã cộng tiền"


def _chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _fetch_existing_order_status_by_order_id(
    supabase, order_ids: list[str]
) -> dict[str, str | None]:
    """order_id -> order_status trong DB truoc lan import nay."""
    out: dict[str, str | None] = {}
    unique_ids = sorted({oid.strip() for oid in order_ids if str(oid).strip()})
    for chunk in _chunked(unique_ids, LOOKUP_CHUNK):
        result = (
            supabase.table("affiliate_commission_orders")
            .select("order_id,order_status")
            .in_("order_id", chunk)
            .execute()
        )
        for item in result.data or []:
            oid = str(item.get("order_id") or "").strip()
            if not oid:
                continue
            out[oid] = str(item.get("order_status") or "").strip() or None
    return out


def _apply_order_status_transition(rows: list[dict], existing_status: dict[str, str | None]) -> None:
    """
    order_status luon lay tu file (da co trong row).
    order_status_transition: chi khi doi trang thai (cũ -> mới); khong doi thi null.
    """
    for row in rows:
        oid = str(row.get("order_id") or "").strip()
        new_st = str(row.get("order_status") or "").strip()
        old_st = existing_status.get(oid)
        if old_st is None:
            row["order_status_transition"] = None
            continue
        if old_st != new_st:
            row["order_status_transition"] = f"{old_st} -> {new_st}"
        else:
            row["order_status_transition"] = None


def _build_convert_info_map(supabase, sub_id_values: list[str]) -> dict[str, dict[str, str | None]]:
    """
    Map sub_id1 -> convert_results info (zl, group).
    Rule: id_zl in convert_results is unique.
    """
    mapping: dict[str, dict[str, str | None]] = {}
    for chunk in _chunked(sub_id_values, LOOKUP_CHUNK):
        result = (
            supabase.table("convert_results")
            .select("id_zl,zl,group")
            .in_("id_zl", chunk)
            .execute()
        )
        for item in result.data or []:
            id_zl = str(item.get("id_zl") or "").strip()
            zl = str(item.get("zl") or "").strip()
            group_id = str(item.get("group") or "").strip() or None
            if id_zl and zl:
                mapping[id_zl] = {"zl": zl, "group_id": group_id}
    return mapping


def _build_contact_map(supabase, id_from_values: list[str]) -> dict[str, dict[str, str | None]]:
    """
    Map zalo_contacts.id_from -> {id_from, name}
    """
    mapping: dict[str, dict[str, str | None]] = {}
    for chunk in _chunked(id_from_values, LOOKUP_CHUNK):
        result = (
            supabase.table("zalo_contacts")
            .select("id_from,d_name")
            .in_("id_from", chunk)
            .execute()
        )
        for item in result.data or []:
            id_from = str(item.get("id_from") or "").strip()
            if not id_from:
                continue
            name_raw = item.get("d_name")
            mapping[id_from] = {
                "id_from": id_from,
                "name": str(name_raw).strip() if name_raw is not None else None,
            }
    return mapping


def _build_commission_config_rows(supabase) -> list[dict]:
    result = (
        supabase.table("commission_config")
        .select("scope,group_id,id_from,payout_pct,is_active")
        .eq("is_active", True)
        .execute()
    )
    return result.data or []


def _pick_payout_pct(
    configs: list[dict], group_id: str | None, id_from: str | None
) -> float | None:
    for config in configs:
        if config.get("scope") == "group_id_from":
            if (
                group_id
                and id_from
                and str(config.get("group_id") or "").strip() == group_id
                and str(config.get("id_from") or "").strip() == id_from
            ):
                return float(config.get("payout_pct") or 0)

    for config in configs:
        if config.get("scope") == "group":
            if group_id and str(config.get("group_id") or "").strip() == group_id:
                return float(config.get("payout_pct") or 0)

    for config in configs:
        if config.get("scope") == "id_from":
            if id_from and str(config.get("id_from") or "").strip() == id_from:
                return float(config.get("payout_pct") or 0)

    for config in configs:
        if config.get("scope") == "global":
            return float(config.get("payout_pct") or 0)

    return None


@router.get("/orders")
def list_commission_orders(
    limit: int = Query(default=200, ge=1, le=1000),
    placed_within_days: int | None = Query(
        default=None,
        description="Loc theo order_placed_at: chi lay don dat trong N ngay gan day (1, 3, 7, 14). Bo qua = tat ca.",
    ),
):
    """Doc ban ghi da import trong affiliate_commission_orders (moi nhat truoc)."""
    if placed_within_days is not None and placed_within_days not in PLACED_WITHIN_DAYS_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail="placed_within_days chi chap nhan 1, 3, 7 hoac 14",
        )
    try:
        supabase = get_supabase_client()
        query = supabase.table("affiliate_commission_orders").select("*")
        if placed_within_days is not None:
            start = datetime.now(timezone.utc) - timedelta(days=placed_within_days)
            query = query.gte("order_placed_at", start.isoformat())
        result = query.order("order_placed_at", desc=True).limit(limit).execute()
        items = result.data or []
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Query Supabase loi: {exc}",
        ) from exc


def _unwrap_rpc_jsonb(result) -> dict:
    """Chuan hoa response RPC tra ve jsonb (dict / list mot phan tu / key ten ham)."""
    data = result.data
    if data is None:
        return {}
    if isinstance(data, dict):
        if "orders_updated" in data:
            return data
        if len(data) == 1:
            inner = next(iter(data.values()))
            if isinstance(inner, dict):
                return inner
        return data
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        row = data[0]
        if "orders_updated" in row:
            return row
        if len(row) == 1:
            inner = next(iter(row.values()))
            if isinstance(inner, dict):
                return inner
    return {}


@router.post("/sync-hh-to-zalo")
def sync_hh_to_zalo():
    """
    Goi RPC sync_commission_hh_to_zalo: cong HH user don Hoan thanh vao zalo_contacts.available_amount,
    doi trang thai don sang Da cong tien (mot transaction tren Supabase).
    """
    try:
        supabase = get_supabase_client()
        result = supabase.rpc("sync_commission_hh_to_zalo", {}).execute()
    except Exception as exc:
        logger.exception("[commission-sync] RPC failed")
        raise HTTPException(status_code=500, detail=f"RPC loi: {exc}") from exc

    payload = _unwrap_rpc_jsonb(result)
    if not payload:
        raise HTTPException(status_code=500, detail="RPC tra ve rong")
    logger.info(
        "[commission-sync] orders_updated=%s skipped=%s contacts=%s total=%s",
        payload.get("orders_updated"),
        payload.get("orders_skipped_no_contact"),
        len(payload.get("contacts") or []) if isinstance(payload.get("contacts"), list) else 0,
        payload.get("total_amount_added"),
    )
    return payload


@router.post("/import")
async def import_commission_report(file: UploadFile = File(...)):
    """
    Nhan file CSV/XLSX bao cao hoa hong Shopee, gop theo ID don hang, upsert vao Supabase.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Thieu ten file")
    logger.info("[commission-import] start filename=%s", file.filename)

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
        logger.info(
            "[commission-import] parsed rows=%s unique_orders=%s",
            len(rows),
            len(rows),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Doc file loi: {exc}") from exc

    if not rows:
        return {
            "upserted": 0,
            "unique_orders": 0,
            "skipped_already_paid": 0,
            "message": "Khong co dong hop le sau khi doc file",
        }

    supabase = get_supabase_client()
    for row in rows:
        row["source_filename"] = file.filename
        row["id_zl"] = None
        row["name"] = None
        row["hh_user"] = 0

    sub_id_values = sorted(
        {
            str(row.get("sub_id1") or "").strip()
            for row in rows
            if str(row.get("sub_id1") or "").strip()
        }
    )
    logger.info("[commission-import] unique sub_id1 count=%s", len(sub_id_values))
    if sub_id_values:
        logger.info(
            "[commission-import] sub_id1 sample=%s",
            sub_id_values[:10],
        )

    try:
        convert_info_map = _build_convert_info_map(supabase, sub_id_values)
        zl_values = sorted(
            {
                str(info.get("zl") or "").strip()
                for info in convert_info_map.values()
                if str(info.get("zl") or "").strip()
            }
        )
        contact_map = _build_contact_map(supabase, zl_values)
        config_rows = _build_commission_config_rows(supabase)
        missing_convert = [value for value in sub_id_values if value not in convert_info_map]
        missing_contacts = [value for value in zl_values if value not in contact_map]
        logger.info(
            "[commission-import] convert_results matched=%s missing=%s",
            len(convert_info_map),
            len(missing_convert),
        )
        if missing_convert:
            logger.warning(
                "[commission-import] missing convert_results.id_zl sample=%s",
                missing_convert[:20],
            )
        logger.info(
            "[commission-import] zalo_contacts(id_from) matched=%s missing=%s",
            len(contact_map),
            len(missing_contacts),
        )
        if missing_contacts:
            logger.warning(
                "[commission-import] missing zalo_contacts.id_from sample=%s",
                missing_contacts[:20],
            )
        if convert_info_map:
            sample_map = {key: convert_info_map[key] for key in list(convert_info_map)[:10]}
            logger.info(
                "[commission-import] sample sub_id1->convert_info mapping=%s",
                sample_map,
            )
        logger.info(
            "[commission-import] active commission_config rows=%s",
            len(config_rows),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Tra cuu convert_results/zalo_contacts loi: {exc}",
        ) from exc

    matched_convert = 0
    matched_contact = 0
    matched_config = 0
    missing_config = 0
    for row in rows:
        sub_id1 = str(row.get("sub_id1") or "").strip()
        if not sub_id1:
            continue

        convert_info = convert_info_map.get(sub_id1)
        if not convert_info:
            continue
        matched_convert += 1
        zl = str(convert_info.get("zl") or "").strip()
        group_id = str(convert_info.get("group_id") or "").strip() or None

        contact = contact_map.get(zl)
        if not contact:
            continue

        payout_pct = _pick_payout_pct(config_rows, group_id=group_id, id_from=zl)
        if payout_pct is None:
            missing_config += 1
            payout_pct = 0
        else:
            matched_config += 1

        net_commission = float(row.get("net_affiliate_commission") or 0)
        row["id_zl"] = zl
        row["name"] = contact.get("name")
        row["hh_user"] = round((net_commission * payout_pct) / 100, 4)
        matched_contact += 1

    logger.info(
        "[commission-import] enrich summary matched_convert=%s matched_contact=%s matched_config=%s missing_config=%s",
        matched_convert,
        matched_contact,
        matched_config,
        missing_config,
    )

    order_id_list = [str(r.get("order_id") or "") for r in rows]
    try:
        existing_order_status = _fetch_existing_order_status_by_order_id(supabase, order_id_list)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Doc order_status hien co loi: {exc}",
        ) from exc

    unique_orders_from_file = len(rows)
    rows_to_upsert: list[dict] = []
    for r in rows:
        oid = str(r.get("order_id") or "").strip()
        prev = existing_order_status.get(oid)
        if str(prev or "").strip() == ORDER_STATUS_PAID_SYNCED:
            continue
        rows_to_upsert.append(r)
    skipped_already_paid = unique_orders_from_file - len(rows_to_upsert)
    rows = rows_to_upsert
    logger.info(
        "[commission-import] skip_paid_synced=%s remaining_for_upsert=%s",
        skipped_already_paid,
        len(rows),
    )

    if not rows:
        return {
            "upserted": 0,
            "unique_orders": unique_orders_from_file,
            "skipped_already_paid": skipped_already_paid,
            "source_filename": file.filename,
            "lookup": {
                "sub_id1_count": len(sub_id_values),
                "matched_convert_results": matched_convert,
                "missing_convert_results": len(sub_id_values) - len(convert_info_map),
                "matched_zalo_contacts": matched_contact,
                "missing_zalo_contacts": max(matched_convert - matched_contact, 0),
                "matched_commission_config": matched_config,
                "missing_commission_config": missing_config,
            },
        }

    _apply_order_status_transition(rows, existing_order_status)

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
    logger.info("[commission-import] upsert done upserted=%s", upserted)

    return {
        "upserted": upserted,
        "unique_orders": unique_orders_from_file,
        "skipped_already_paid": skipped_already_paid,
        "source_filename": file.filename,
        "lookup": {
            "sub_id1_count": len(sub_id_values),
            "matched_convert_results": matched_convert,
            "missing_convert_results": len(sub_id_values) - len(convert_info_map),
            "matched_zalo_contacts": matched_contact,
            "missing_zalo_contacts": max(matched_convert - matched_contact, 0),
            "matched_commission_config": matched_config,
            "missing_commission_config": missing_config,
        },
    }
