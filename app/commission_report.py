from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

import pandas as pd


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_header(value: str) -> str:
    text = str(value).strip().lower()
    text = _strip_accents(text)
    text = text.replace("₫", "")
    text = text.replace("(vnd)", "").replace("vnd", "")
    text = re.sub(r"\(\s*\)", "", text)
    return " ".join(text.split())


def _resolve_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized_map = {col: normalize_header(col) for col in columns}
    candidate_norms = [normalize_header(c) for c in candidates if str(c).strip()]
    for col, nh in normalized_map.items():
        if nh in candidate_norms:
            return col
    return None


COLUMN_GROUPS: dict[str, list[str]] = {
    "order_id": ["ID đơn hàng"],
    "order_status": ["Trạng thái đặt hàng"],
    "order_placed_at": ["Thời Gian Đặt Hàng", "Thời gian đặt hàng"],
    "net_commission": [
        "Hoa hồng ròng tiếp thị liên kết(₫)",
        "Hoa hồng ròng tiếp thị liên kết",
    ],
    "sub_id1": ["Sub_id1", "sub_id1"],
}


def resolve_commission_columns(columns: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for key, candidates in COLUMN_GROUPS.items():
        col = _resolve_column(columns, candidates)
        if col:
            resolved[key] = col

    missing = [key for key in COLUMN_GROUPS if key not in resolved]
    if missing:
        available = ", ".join(columns[:30])
        if len(columns) > 30:
            available += ", ..."
        raise ValueError(
            "Khong tim thay day du cot trong file. Thieu: "
            + ", ".join(missing)
            + f". Mot so cot tim thay: {available}"
        )

    return resolved


def _read_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    buffer = io.BytesIO(content)

    if lower.endswith(".csv"):
        return pd.read_csv(buffer, encoding="utf-8-sig", dtype=str)

    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(buffer, dtype=str)

    raise ValueError("Chi ho tro file .csv, .xlsx hoac .xls")


def _first_nonempty(values: pd.Series) -> str | None:
    for raw in values:
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


_VN_TZ = "Asia/Ho_Chi_Minh"


def _parse_order_placed_at_vn_to_utc(raw: pd.Series) -> pd.Series:
    """
    Thoi gian dat hang trong file Shopee: dinh dang M/D/YYYY (thang/ngay), gio 24h, wall clock VN (khong offset).
    Uu tien dayfirst=False (MM/DD/YYYY); dong con NaT thu dayfirst=True (DD/MM fallback). Localize VN -> UTC.
    """
    s = pd.to_datetime(raw, errors="coerce", dayfirst=False, utc=False)
    if s.isna().any():
        missing = s.isna()
        s = s.copy()
        s.loc[missing] = pd.to_datetime(
            raw.loc[missing], errors="coerce", dayfirst=True, utc=False
        )

    tz = getattr(s.dtype, "tz", None)
    if tz is None:
        s = s.dt.tz_localize(
            _VN_TZ,
            ambiguous="infer",
            nonexistent="shift_forward",
        )
    return s.dt.tz_convert("UTC")


def aggregate_commission_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    columns = resolve_commission_columns(list(df.columns))

    work = pd.DataFrame(
        {
            "order_id": df[columns["order_id"]].astype(str).str.strip(),
            "order_status": df[columns["order_status"]].astype(str).str.strip(),
            "order_placed_at_raw": df[columns["order_placed_at"]],
            "net_commission": pd.to_numeric(
                df[columns["net_commission"]].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ),
            "sub_id1": df[columns["sub_id1"]],
        }
    )

    work = work[work["order_id"] != ""]
    work = work[work["order_id"].str.lower() != "nan"]

    if work.empty:
        return []

    work["order_placed_at"] = _parse_order_placed_at_vn_to_utc(work["order_placed_at_raw"])

    if work["net_commission"].isna().any():
        bad = int(work["net_commission"].isna().sum())
        raise ValueError(f"Co {bad} dong khong doc duoc hoa hong rong. Kiem tra dinh dang so.")

    if work["order_placed_at"].isna().any():
        bad = int(work["order_placed_at"].isna().sum())
        raise ValueError(f"Co {bad} dong khong doc duoc thoi gian dat hang.")

    grouped = work.groupby("order_id", sort=False)

    aggregated: list[dict[str, Any]] = []
    for order_id, group in grouped:
        aggregated.append(
            {
                "order_id": str(order_id),
                "order_status": str(group["order_status"].iloc[0]),
                "order_placed_at": group["order_placed_at"].min().isoformat(),
                "net_affiliate_commission": float(group["net_commission"].sum()),
                "sub_id1": _first_nonempty(group["sub_id1"]),
            }
        )

    return aggregated


def parse_and_aggregate_report(content: bytes, filename: str) -> list[dict[str, Any]]:
    df = _read_dataframe(content, filename)
    if df.empty:
        return []
    return aggregate_commission_rows(df)
