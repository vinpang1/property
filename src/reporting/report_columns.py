"""報告欄位定義 — CSV 同 Markdown 必須一致，只可加不可減。"""

from typing import Callable


def format_address(tx: dict, district: str = "屯門區") -> str:
    """組合完整地址：區域 + 屋苑 + 座數 + 樓層 + 單位。"""
    parts = [district, tx.get("estate_name")]
    for key in ("block", "floor", "unit"):
        value = tx.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


# 屯門區最近成交報告 — 成交明細欄位（權威定義）
TUEN_MUN_RECENT_DETAIL_COLUMNS: list[tuple[str, Callable[[dict], object]]] = [
    ("成交日期", lambda tx: tx["transaction_date"]),
    ("地址", lambda tx: format_address(tx)),
    ("屋苑", lambda tx: tx["estate_name"]),
    ("座數", lambda tx: tx.get("block") or ""),
    ("樓層", lambda tx: tx.get("floor") or ""),
    ("單位", lambda tx: tx.get("unit") or ""),
    ("實用面積(呎)", lambda tx: tx.get("area_sqft") or ""),
    ("成交價", lambda tx: tx["price"]),
    ("呎價", lambda tx: tx.get("price_per_sqft") or ""),
    ("市場類型", lambda tx: tx.get("market_type") or ""),
    ("分行", lambda tx: tx.get("branch_name") or ""),
    ("代理", lambda tx: tx.get("agent_name") or ""),
    ("代理電話", lambda tx: tx.get("agent_phone") or ""),
    ("來源", lambda tx: tx.get("source") or ""),
]


def detail_headers() -> list[str]:
    return [name for name, _ in TUEN_MUN_RECENT_DETAIL_COLUMNS]


def detail_row(tx: dict) -> list[object]:
    return [getter(tx) for _, getter in TUEN_MUN_RECENT_DETAIL_COLUMNS]
