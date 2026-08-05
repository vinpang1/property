"""Centaline / Centanet transaction search client."""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Iterator

from src.ingestion.agent_enrichment import AgentEnricher, AgentInfo
from src.ingestion.date_utils import month_cutoff
from src.ingestion.models import UnitTransaction
from src.ingestion.report_date import (
    parse_centaline_pasp_date,
    parse_centaline_registration_date,
    report_date_from_centaline,
)
from src.ingestion.transaction_stage import classify_deal_type, classify_transaction_stage

SEARCH_URL = "https://hk.centanet.com/findproperty/api/Transaction/Search"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Platform": "Web",
    "User-Agent": "Mozilla/5.0 (compatible; HKPropertyTracker/0.1)",
}


def _request_interval(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _post_search(payload: dict[str, Any], retry: int = 3, delay: float = 2.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(retry):
        try:
            req = urllib.request.Request(SEARCH_URL, data=data, headers=DEFAULT_HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            if body.get("title"):
                raise RuntimeError(body.get("title"))
            return body
        except Exception as exc:
            last_error = exc
            if attempt < retry - 1:
                time.sleep(delay)
    raise RuntimeError(f"Centaline search failed: {last_error}") from last_error


def _parse_date(item: dict[str, Any]) -> str:
    return report_date_from_centaline(item)


def _parse_pasp_date(item: dict[str, Any]) -> str:
    return parse_centaline_pasp_date(item)


def _parse_registration_date(item: dict[str, Any]) -> str:
    return parse_centaline_registration_date(item)


def _parse_market_type(item: dict[str, Any]) -> str:
    hand = (item.get("firstOrSecondHand") or "").lower()
    if hand == "firsthand":
        return "primary"
    if hand == "secondhand":
        return "secondary"
    return hand or "unknown"


def _to_transaction(item: dict[str, Any], *, agent_info: AgentInfo | None = None) -> UnitTransaction:
    scope = item.get("scope") or {}
    estate = item.get("estateName") or item.get("bigEstateName") or ""
    if item.get("bigEstateName") and item.get("estateName"):
        estate = f"{item['bigEstateName']} {item['estateName']}".strip()

    addr = (item.get("displayText") or {}).get("addr") or {}
    line1 = addr.get("line1") or ""
    info = agent_info or AgentInfo()
    record_source = item.get("dataSource") or ""
    post_type = item.get("postType") or "S"

    return UnitTransaction(
        estate_name=estate or line1,
        block=item.get("buildingName") or "",
        floor=item.get("yAxis") or "",
        unit=item.get("xAxis") or "",
        area_sqft=item.get("nArea") or item.get("gArea"),
        price=int(item.get("transactionPrice") or 0),
        price_per_sqft=item.get("nUnitPrice") or item.get("gUnitPrice"),
        pasp_date=_parse_pasp_date(item),
        registration_date=_parse_registration_date(item),
        transaction_date=_parse_date(item),
        district=scope.get("db") or item.get("districtName") or "",
        sub_district=scope.get("hma") or item.get("districtName") or "",
        market_type=_parse_market_type(item),
        source="centaline",
        source_id=item.get("id") or "",
        address=item.get("address") or line1,
        branch_name=info.branch_name,
        agent_name=info.agent_name,
        agent_phone=info.agent_phone,
        agent_licence=info.agent_licence,
        agent_whatsapp=info.agent_whatsapp,
        agent_wechat=info.agent_wechat,
        listing_ref=info.listing_ref,
        record_source=record_source,
        deal_type=classify_deal_type(post_type=post_type),
        transaction_stage=classify_transaction_stage(record_source),
        detail_url=item.get("detailUrl") or "",
    )


def iter_transaction_items(
    *,
    keyword: str | None = None,
    day: str = "Day1095",
    page_size: int = 100,
    request_interval_seconds: float = 0.5,
) -> Iterator[dict[str, Any]]:
    offset = 0
    while True:
        payload = {
            "postType": "Sale",
            "day": day,
            "sort": "InsOrRegDate",
            "order": "Descending",
            "size": page_size,
            "offset": offset,
        }
        if keyword:
            payload["keyword"] = keyword

        result = _post_search(payload)
        rows = result.get("data") or []
        if not rows:
            break

        yield from rows

        offset += page_size
        total = int(result.get("count") or 0)
        if offset >= total:
            break
        _request_interval(request_interval_seconds)


def iter_transactions(
    *,
    keyword: str | None = None,
    day: str = "Day1095",
    page_size: int = 100,
    request_interval_seconds: float = 0.5,
) -> Iterator[UnitTransaction]:
    for item in iter_transaction_items(
        keyword=keyword,
        day=day,
        page_size=page_size,
        request_interval_seconds=request_interval_seconds,
    ):
        yield _to_transaction(item)


def fetch_tuen_mun_transactions(
    *,
    months_back: int = 6,
    request_interval_seconds: float = 0.5,
    enrich_agents: bool = True,
) -> list[UnitTransaction]:
    cutoff = month_cutoff(months_back)
    day_window = "Day180" if months_back <= 6 else "Day365"
    collected: list[UnitTransaction] = []
    enricher = AgentEnricher(request_interval_seconds=request_interval_seconds) if enrich_agents else None

    for item in iter_transaction_items(
        keyword="屯門",
        day=day_window,
        request_interval_seconds=request_interval_seconds,
    ):
        tx_date_raw = _parse_date(item)
        if not tx_date_raw:
            continue
        tx_date = datetime.strptime(tx_date_raw, "%Y-%m-%d").date()
        if tx_date < cutoff:
            continue

        agent_info = enricher.resolve_centaline_agent(item) if enricher else None
        collected.append(_to_transaction(item, agent_info=agent_info))

    return collected
