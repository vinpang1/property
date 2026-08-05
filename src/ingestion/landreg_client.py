"""Land Registry monthly statistics client (data.gov.hk / landreg.gov.hk)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any

BASE_URL = "https://www.landreg.gov.hk/datagovhk/{yyyymm}_data.json"

RESIDENTIAL_TOTAL = "Number of ASP for Residential Building Units"
PRIMARY_TOTAL = "Number of Primary Sales for ASP Residential Building Units"
SECONDARY_TOTAL = "Number of Secondary Sales for ASP Residential Building Units"
TUEN_MUN_TOTAL = "Number of Tuen Mun transactions for ASP building units"


@dataclass
class MonthlySummary:
    year: int
    month: int
    residential_count: int
    primary_count: int
    secondary_count: int
    tuen_mun_count: int
    residential_volume_million: int | None
    source_url: str

    @property
    def period(self) -> str:
        return f"{self.year}-{self.month:02d}"


def fetch_monthly_json(year: int, month: int, retry: int = 3, delay: float = 2.0) -> list[dict[str, Any]]:
    yyyymm = f"{year}{month:02d}"
    url = BASE_URL.format(yyyymm=yyyymm)
    last_error: Exception | None = None

    for attempt in range(retry):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8-sig"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 404:
                raise FileNotFoundError(f"Land Registry data not published: {url}") from exc
        except Exception as exc:
            last_error = exc
        if attempt < retry - 1:
            time.sleep(delay)

    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def _parse_units(value: str | int | None) -> int:
    if value is None or value == "-":
        return 0
    return int(str(value).replace(",", ""))


def _parse_volume(value: str | int | None) -> int | None:
    if value is None or value == "-":
        return None
    return int(str(value).replace(",", ""))


def _find_row(rows: list[dict[str, Any]], description: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("Description") == description:
            return row
    return None


def parse_monthly_summary(rows: list[dict[str, Any]], source_url: str) -> MonthlySummary:
    if not rows:
        raise ValueError("Empty Land Registry dataset")

    year = int(rows[0]["Year"])
    month = int(rows[0]["Month"])
    residential = _find_row(rows, RESIDENTIAL_TOTAL)
    primary = _find_row(rows, PRIMARY_TOTAL)
    secondary = _find_row(rows, SECONDARY_TOTAL)
    tuen_mun = _find_row(rows, TUEN_MUN_TOTAL)

    if not residential:
        raise ValueError("Residential transaction row not found in Land Registry data")

    return MonthlySummary(
        year=year,
        month=month,
        residential_count=_parse_units(residential.get("Units")),
        primary_count=_parse_units(primary.get("Units") if primary else 0),
        secondary_count=_parse_units(secondary.get("Units") if secondary else 0),
        tuen_mun_count=_parse_units(tuen_mun.get("Units") if tuen_mun else 0),
        residential_volume_million=_parse_volume(residential.get("Consideration (nearest $ million)")),
        source_url=source_url,
    )


def fetch_monthly_summary(year: int, month: int) -> MonthlySummary:
    yyyymm = f"{year}{month:02d}"
    url = BASE_URL.format(yyyymm=yyyymm)
    rows = fetch_monthly_json(year, month)
    return parse_monthly_summary(rows, url)


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1


def fetch_latest_months(count: int = 6) -> list[MonthlySummary]:
    today = date.today()
    year, month = today.year, today.month
    summaries: list[MonthlySummary] = []
    offset = 0

    while len(summaries) < count and offset < count + 6:
        target_year, target_month = _shift_month(year, month, -offset)
        try:
            summaries.append(fetch_monthly_summary(target_year, target_month))
        except FileNotFoundError:
            pass
        offset += 1

    summaries.sort(key=lambda item: item.period)
    return summaries
