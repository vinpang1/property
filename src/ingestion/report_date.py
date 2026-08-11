"""Report date parsing — use provisional agreement (PASP) date, not registration date."""

from __future__ import annotations

from typing import Any

from src.ingestion.transaction_stage import PASP_SOURCES


def _normalize_date(raw: str | None) -> str:
    if not raw:
        return ""
    return raw[:10]


def parse_centaline_pasp_date(item: dict[str, Any]) -> str:
    """Centaline insDate = 簽臨時買賣合約日期。"""
    return _normalize_date(item.get("insDate"))


def parse_centaline_registration_date(item: dict[str, Any]) -> str:
    """Centaline regDate = 土地註冊日期（唔用作報告日期）。"""
    return _normalize_date(item.get("regDate"))


def parse_midland_pasp_date(item: dict[str, Any]) -> str:
    """Midland tx_date for provisional sources = 簽臨約日期。"""
    source = (item.get("source") or "").strip().upper()
    if source in PASP_SOURCES:
        return _normalize_date(item.get("tx_date"))
    return ""


def parse_midland_registration_date(item: dict[str, Any]) -> str:
    """Midland tx_date for LANDREG = 土地註冊日期（唔用作報告日期）。"""
    source = (item.get("source") or "").strip().upper()
    if source == "LANDREG":
        return _normalize_date(item.get("tx_date"))
    return ""


def report_date_from_centaline(item: dict[str, Any]) -> str:
    return parse_centaline_pasp_date(item)


def report_date_from_midland(item: dict[str, Any]) -> str:
    return parse_midland_pasp_date(item)


def match_key(tx) -> tuple:
    """Build a loose match key for cross-source PASP date enrichment."""
    return (
        _normalize_text(tx.estate_name),
        _normalize_text(tx.block),
        _normalize_text(tx.floor),
        _normalize_text(tx.unit),
        int(tx.price or 0),
    )


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return "".join(str(value).upper().split())


def enrich_pasp_dates(transactions: list) -> list:
    """Fill missing PASP dates on Midland LANDREG records from Centaline matches."""
    from src.ingestion.models import UnitTransaction

    index: dict[tuple, str] = {}
    for tx in transactions:
        if not isinstance(tx, UnitTransaction):
            continue
        if tx.source != "centaline" or not tx.pasp_date:
            continue
        index[match_key(tx)] = tx.pasp_date

    enriched: list[UnitTransaction] = []
    for tx in transactions:
        if not isinstance(tx, UnitTransaction):
            enriched.append(tx)
            continue
        if tx.pasp_date:
            enriched.append(tx)
            continue
        matched = index.get(match_key(tx))
        if matched:
            tx.pasp_date = matched
        enriched.append(tx)
    return enriched
