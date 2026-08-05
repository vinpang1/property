"""Ricacorp estate transaction HTML parser."""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from src.ingestion.date_utils import month_cutoff
from src.ingestion.models import UnitTransaction
from src.utils.paths import PROJECT_ROOT

ESTATE_CONFIG = PROJECT_ROOT / "config" / "tuen_mun_estates.yaml"
BASE_URL = "https://www.ricacorp.com/zh-hk/property/transaction/estate/{slug}"


def _load_estates() -> list[dict]:
    with open(ESTATE_CONFIG, encoding="utf-8") as handle:
        return yaml.safe_load(handle)["estates"]


def _parse_price_million(value: str) -> int:
    cleaned = value.replace("$", "").replace("萬", "").replace(",", "").strip()
    return int(float(cleaned) * 10000)


def _parse_estate_page(html: str, estate_name: str, slug: str, cutoff: date) -> list[UnitTransaction]:
    transactions: list[UnitTransaction] = []
    pattern = re.compile(
        r"(?P<block>\d+座)\s*(?P<floor>\d+樓)\s*(?P<unit>[A-Z]室).*?"
        r"(?P<date>\d{4}/\d{2}/\d{2}).*?"
        r"\$\s*(?P<price>[\d.]+\s*萬).*?"
        r"(?P<area>\d+)呎",
        re.S,
    )

    for match in pattern.finditer(html):
        tx_date = datetime.strptime(match.group("date"), "%Y/%m/%d").date()
        if tx_date < cutoff:
            continue
        area = int(match.group("area"))
        price = _parse_price_million(match.group("price"))
        transactions.append(
            UnitTransaction(
                estate_name=estate_name,
                block=match.group("block"),
                floor=match.group("floor"),
                unit=match.group("unit"),
                area_sqft=area,
                price=price,
                price_per_sqft=round(price / area, 2) if area else None,
                transaction_date=tx_date.isoformat(),
                district="屯門區",
                sub_district="",
                market_type="secondary",
                source="ricacorp",
                source_id=f"{slug}:{match.group('date')}:{match.group('block')}:{match.group('unit')}",
                address=estate_name,
            )
        )

    if transactions:
        return transactions

    for match in re.finditer(
        r"(?P<date>\d{4}/\d{2}/\d{2})\s*</mat-cell>.*?\$\s*(?P<price>[\d.]+\s*萬)",
        html,
        re.S,
    ):
        tx_date = datetime.strptime(match.group("date"), "%Y/%m/%d").date()
        if tx_date < cutoff:
            continue
        price = _parse_price_million(match.group("price"))
        transactions.append(
            UnitTransaction(
                estate_name=estate_name,
                block="",
                floor="",
                unit="",
                area_sqft=None,
                price=price,
                price_per_sqft=None,
                transaction_date=tx_date.isoformat(),
                district="屯門區",
                sub_district="",
                market_type="secondary",
                source="ricacorp",
                source_id=f"{slug}:{match.group('date')}:{price}",
                address=estate_name,
            )
        )
    return transactions


def fetch_tuen_mun_transactions(
    *,
    months_back: int = 6,
    request_interval_seconds: float = 1.0,
) -> list[UnitTransaction]:
    cutoff = month_cutoff(months_back)

    collected: list[UnitTransaction] = []
    for estate in _load_estates():
        slug = estate.get("ricacorp_slug")
        if not slug:
            continue
        url = BASE_URL.format(slug=urllib.parse.quote(slug))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
            collected.extend(_parse_estate_page(html, estate["name"], slug, cutoff))
        except Exception:
            continue
        time.sleep(request_interval_seconds)
    return collected
