from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_supabase_client

router = APIRouter(prefix="/bot-registry", tags=["bot-registry"])

_SELECT_FIELDS = "id_bot,display_name,max_consecutive_replies,sort_order,is_enabled,created_at"
_ROUTER_SCOPE = "global"


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _fetch_router_state(supabase) -> tuple[str | None, int]:
    result = (
        supabase.table("reply_router_state")
        .select("current_bot_id,consecutive_used")
        .eq("scope_key", _ROUTER_SCOPE)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None, 0
    row = rows[0]
    current_bot_id = row.get("current_bot_id")
    try:
        consecutive_used = int(row.get("consecutive_used") or 0)
    except (TypeError, ValueError):
        consecutive_used = 0
    return (str(current_bot_id) if current_bot_id is not None else None), consecutive_used


def _enrich_linked_groups(supabase, items: list[dict]) -> None:
    if not items:
        return

    bot_ids = list({str(r.get("id_bot") or "").strip() for r in items if str(r.get("id_bot") or "").strip()})
    if not bot_ids:
        for row in items:
            row["linked_groups"] = []
        return

    maps_result = (
        supabase.table("bot_datagroup")
        .select("id_bot,id_localgroup,id_globalgroup")
        .in_("id_bot", bot_ids)
        .execute()
    )
    maps = maps_result.data or []

    global_ids = list(
        {
            str(m.get("id_globalgroup") or "").strip()
            for m in maps
            if str(m.get("id_globalgroup") or "").strip()
        }
    )

    name_by_global: dict[str, str] = {}
    globalzalo_by_global: dict[str, str | None] = {}
    if global_ids:
        groups_result = (
            supabase.table("zalo_groups")
            .select("id_global,group_name,id_globalzalo")
            .in_("id_global", global_ids)
            .is_("deleted_at", "null")
            .execute()
        )
        for g in groups_result.data or []:
            gid = str(g.get("id_global") or "").strip()
            if gid:
                name = str(g.get("group_name") or "").strip()
                name_by_global[gid] = name or gid
                gz = str(g.get("id_globalzalo") or "").strip()
                globalzalo_by_global[gid] = gz or None

    globalzalo_ids = list(
        {gz for gz in globalzalo_by_global.values() if gz}
    )
    contact_name_by_global: dict[str, str] = {}
    if globalzalo_ids:
        contacts_result = (
            supabase.table("zalo_contacts")
            .select("id_global,d_name")
            .in_("id_global", globalzalo_ids)
            .execute()
        )
        for c in contacts_result.data or []:
            cid = str(c.get("id_global") or "").strip()
            if cid:
                dname = str(c.get("d_name") or "").strip()
                contact_name_by_global[cid] = dname or cid

    by_bot: dict[str, list[dict]] = {bid: [] for bid in bot_ids}
    seen: set[tuple[str, str]] = set()
    for m in maps:
        bid = str(m.get("id_bot") or "").strip()
        ggid = str(m.get("id_globalgroup") or "").strip()
        if not bid or not ggid:
            continue
        key = (bid, ggid)
        if key in seen:
            continue
        seen.add(key)
        local = m.get("id_localgroup")
        id_globalzalo = globalzalo_by_global.get(ggid)
        by_bot.setdefault(bid, []).append(
            {
                "id_localgroup": str(local).strip() if local is not None and str(local).strip() else None,
                "id_global": ggid,
                "id_globalgroup": ggid,
                "group_name": name_by_global.get(ggid),
                "id_globalzalo": id_globalzalo,
                "contact_name": contact_name_by_global.get(id_globalzalo) if id_globalzalo else None,
            }
        )

    for row in items:
        bid = str(row.get("id_bot") or "").strip()
        linked = by_bot.get(bid, [])
        row["linked_groups"] = sorted(
            linked,
            key=lambda x: (x.get("group_name") or x.get("id_globalgroup") or "").lower(),
        )


def _enrich_items(items: list[dict]) -> list[dict]:
    if not items:
        return []
    supabase = get_supabase_client()
    current_bot_id, consecutive_used = _fetch_router_state(supabase)
    enriched: list[dict] = []
    for raw in items:
        row = dict(raw)
        bot_id = str(row.get("id_bot") or "")
        row["consecutive_used"] = consecutive_used if bot_id == current_bot_id else 0
        enriched.append(row)
    _enrich_linked_groups(supabase, enriched)
    return enriched


class BotRegistryUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=2000)
    max_consecutive_replies: int = Field(..., ge=1)
    sort_order: int = Field(..., ge=0)
    is_enabled: bool


def _row_from_update(payload: BotRegistryUpdate) -> dict:
    return {
        "display_name": _blank_to_none(payload.display_name),
        "max_consecutive_replies": int(payload.max_consecutive_replies),
        "sort_order": int(payload.sort_order),
        "is_enabled": bool(payload.is_enabled),
    }


def _assert_sort_order_unique(supabase, sort_order: int, id_bot: str) -> None:
    result = (
        supabase.table("bot_registry")
        .select("id_bot")
        .eq("sort_order", int(sort_order))
        .neq("id_bot", id_bot)
        .limit(1)
        .execute()
    )
    if result.data:
        raise HTTPException(
            status_code=409,
            detail=f"sort_order={sort_order} da duoc su dung boi bot khac",
        )


def _next_sort_order_start(supabase) -> int:
    result = (
        supabase.table("bot_registry")
        .select("sort_order")
        .order("sort_order", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return 0
    try:
        return int(rows[0].get("sort_order") or 0) + 1
    except (TypeError, ValueError):
        return 0


class BotRegistryBulkCreate(BaseModel):
    id_bots: list[str] = Field(..., min_length=1, max_length=200)


@router.post("")
def bulk_create_bot_registry(payload: BotRegistryBulkCreate):
    seen: set[str] = set()
    id_bots: list[str] = []
    for raw in payload.id_bots:
        key = str(raw or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        id_bots.append(key)
    if not id_bots:
        raise HTTPException(status_code=422, detail="Can it nhat mot id_bot hop le")

    try:
        supabase = get_supabase_client()
        existing_result = (
            supabase.table("bot_registry")
            .select("id_bot")
            .in_("id_bot", id_bots)
            .execute()
        )
        existing_ids = {str(r.get("id_bot") or "").strip() for r in (existing_result.data or [])}
        to_create = [bid for bid in id_bots if bid not in existing_ids]
        skipped = [bid for bid in id_bots if bid in existing_ids]

        if not to_create:
            raise HTTPException(
                status_code=409,
                detail="Tat ca id_bot da ton tai trong bot_registry",
            )

        sort_start = _next_sort_order_start(supabase)
        rows = [
            {
                "id_bot": bid,
                "display_name": None,
                "max_consecutive_replies": 5,
                "sort_order": sort_start + i,
                "is_enabled": True,
            }
            for i, bid in enumerate(to_create)
        ]
        insert_result = supabase.table("bot_registry").insert(rows).execute()
        created_raw = insert_result.data or []
        created = _enrich_items(created_raw)
        return {
            "created_count": len(created),
            "skipped_count": len(skipped),
            "skipped_id_bots": skipped,
            "items": created,
        }
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(status_code=409, detail="id_bot hoac sort_order da ton tai") from exc
        raise HTTPException(status_code=500, detail=f"Create bot_registry failed: {exc}") from exc


@router.get("")
def list_bot_registry(limit: int = Query(default=200, ge=1, le=1000)):
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("bot_registry")
            .select(_SELECT_FIELDS)
            .order("sort_order", desc=False)
            .order("id_bot", desc=False)
            .limit(limit)
            .execute()
        )
        items = _enrich_items(result.data or [])
        return {"count": len(items), "items": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query bot_registry failed: {exc}") from exc


@router.put("/{id_bot}")
def update_bot_registry(id_bot: str, payload: BotRegistryUpdate):
    key = str(id_bot or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="id_bot khong hop le")
    row = _row_from_update(payload)
    try:
        supabase = get_supabase_client()
        _assert_sort_order_unique(supabase, row["sort_order"], key)
        result = supabase.table("bot_registry").update(row).eq("id_bot", key).execute()
        updated = (result.data or [None])[0]
        if updated is None:
            raise HTTPException(status_code=404, detail=f"bot_registry id_bot={key} not found")
        enriched = _enrich_items([updated])[0]
        return {"item": enriched}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update bot_registry failed: {exc}") from exc
