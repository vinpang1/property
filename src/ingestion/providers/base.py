"""Shared helpers for transaction providers."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from src.ingestion.models import UnitTransaction
from src.ingestion.report_date import enrich_pasp_dates


def in_pasp_date_range(pasp_date_raw: str | None, *, days_back: int) -> bool:
    if not pasp_date_raw:
        return False
    cutoff = date.today() - timedelta(days=days_back)
    pasp_date = datetime.strptime(pasp_date_raw, "%Y-%m-%d").date()
    return cutoff <= pasp_date <= date.today()


def filter_sales(transactions: list[UnitTransaction]) -> list[UnitTransaction]:
    return [tx for tx in transactions if tx.deal_type == "sale"]


def merge_recent_transactions(
    batches: list[list[UnitTransaction]],
    *,
    days_back: int,
) -> list[UnitTransaction]:
    collected: list[UnitTransaction] = []
    for batch in batches:
        collected.extend(batch)

    collected = enrich_pasp_dates(collected)

    seen: set[tuple] = set()
    merged: list[UnitTransaction] = []
    for tx in sorted(collected, key=lambda item: item.pasp_date or "", reverse=True):
        if not tx.pasp_date or not in_pasp_date_range(tx.pasp_date, days_back=days_back):
            continue
        key = (tx.estate_name, tx.block, tx.floor, tx.unit, tx.pasp_date, tx.price, tx.source)
        if key in seen:
            continue
        seen.add(key)
        merged.append(tx)
    return merged
