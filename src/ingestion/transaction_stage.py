"""Classify transaction records by deal type and registration stage."""

from __future__ import annotations

PASP_SOURCES = {"AC", "MIDLAND", "SRPE", "A"}
LANDREG_SOURCES = {"LANDREG", "Land", "LAND"}
SALE_CODES = {"S", "SALE", "SALEABLE"}
RENT_CODES = {"R", "RENT", "LEASE", "L"}


def classify_transaction_stage(record_source: str) -> str:
    normalized = (record_source or "").strip().upper()
    if normalized in PASP_SOURCES or normalized == "AC":
        return "臨約"
    if normalized in LANDREG_SOURCES or normalized == "LAND":
        return "土地註冊"
    return "未知"


def classify_deal_type(*, post_type: str = "", tx_type: str = "") -> str:
    """Return 'sale' or 'rent' based on API type codes."""
    for raw in (post_type, tx_type):
        code = (raw or "").strip().upper()
        if code in RENT_CODES:
            return "rent"
        if code in SALE_CODES:
            return "sale"
    return "sale"


def display_deal_type(deal_type: str) -> str:
    return {"sale": "買賣", "rent": "租"}.get(deal_type, deal_type)
