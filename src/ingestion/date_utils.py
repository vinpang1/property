"""Date helpers for ingestion modules."""

from __future__ import annotations

from datetime import date


def month_cutoff(months_back: int) -> date:
    today = date.today().replace(day=1)
    year, month = today.year, today.month
    month -= months_back - 1
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)
