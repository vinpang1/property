"""Classify transaction records by provisional agreement vs land registration."""

from __future__ import annotations

PASP_SOURCES = {"AC", "MIDLAND", "SRPE", "A"}
LANDREG_SOURCES = {"LANDREG", "Land", "LAND"}


def classify_transaction_stage(record_source: str) -> str:
    normalized = (record_source or "").strip().upper()
    if normalized in PASP_SOURCES or normalized == "AC":
        return "臨約"
    if normalized in LANDREG_SOURCES or normalized == "LAND":
        return "土地註冊"
    return "未知"
