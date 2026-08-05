"""Midland Realty transaction search client."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from src.ingestion.date_utils import month_cutoff
from src.ingestion.models import UnitTransaction

API_BASE = "https://data.midland.com.hk/search/v2/transactions"
TOKEN_PAGE = "https://www.midland.com.hk/zh-hk/list/transaction"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HKPropertyTracker/0.1)",
    "Accept": "application/json",
    "Origin": "https://www.midland.com.hk",
    "Referer": "https://www.midland.com.hk/",
}


def _fetch_build_token() -> str:
    req = urllib.request.Request(TOKEN_PAGE, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    match = re.search(r'BUILD_TOKEN":"([^"]+)"', html)
    if not match:
        raise RuntimeError("Unable to locate Midland BUILD_TOKEN")
    return match.group(1)


def _parse_tx_date(raw: str) -> str:
    if not raw:
        return ""
    return raw[:10]


def _to_transaction(item: dict) -> UnitTransaction:
    estate = (item.get("estate") or {}).get("name") or ""
    phase = (item.get("phase") or {}).get("name")
    if phase:
        estate = f"{estate} {phase}".strip()

    return UnitTransaction(
        estate_name=estate,
        block=(item.get("building") or {}).get("name") or "",
        floor=str(item.get("floor") or ""),
        unit=str(item.get("flat") or ""),
        area_sqft=item.get("net_area") or item.get("area"),
        price=int(item.get("price") or 0),
        price_per_sqft=item.get("unit_price_net"),
        transaction_date=_parse_tx_date(item.get("tx_date") or ""),
        district=(item.get("district") or {}).get("name") or "屯門區",
        sub_district=(item.get("int_sm_district") or {}).get("name")
        or (item.get("subregion") or {}).get("name")
        or "",
        market_type="secondary" if item.get("mkt_type") == 2 else "primary",
        source="midland",
        source_id=item.get("id") or "",
        address=estate,
    )


def fetch_tuen_mun_transactions(
    *,
    months_back: int = 6,
    page_size: int = 100,
    request_interval_seconds: float = 0.4,
) -> list[UnitTransaction]:
    token = _fetch_build_token()
    cutoff = month_cutoff(months_back)
    collected: list[UnitTransaction] = []
    page = 1

    while True:
        params = {
            "text": "屯門",
            "tx_type": "S",
            "page": str(page),
            "limit": str(page_size),
            "lang": "zh-hk",
        }
        url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={**DEFAULT_HEADERS, "Authorization": f"Bearer {token}"},
        )
        body = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        rows = body.get("result") or []
        if not rows:
            break

        stop = False
        for item in rows:
            tx = _to_transaction(item)
            if not tx.transaction_date:
                continue
            tx_date = datetime.strptime(tx.transaction_date, "%Y-%m-%d").date()
            if tx_date < cutoff:
                stop = True
                continue
            collected.append(tx)

        if stop or page * page_size >= int(body.get("count") or 0):
            break
        page += 1
        time.sleep(request_interval_seconds)

    return collected
