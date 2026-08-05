"""Midland Realty transaction search client."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.date_utils import month_cutoff
from src.ingestion.models import UnitTransaction
from src.ingestion.transaction_stage import classify_transaction_stage

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


def _to_transaction(item: dict, *, agent_info=None) -> UnitTransaction:
    from src.ingestion.agent_enrichment import AgentInfo

    estate = (item.get("estate") or {}).get("name") or ""
    phase = (item.get("phase") or {}).get("name")
    if phase:
        estate = f"{estate} {phase}".strip()

    info = agent_info or AgentInfo()
    record_source = item.get("source") or item.get("original_source") or ""

    return UnitTransaction(
        estate_name=estate,
        block=(item.get("building") or {}).get("name") or "",
        floor=str(item.get("floor") or item.get("floor_level", {}).get("name") or ""),
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
        branch_name=info.branch_name,
        agent_name=info.agent_name,
        agent_phone=info.agent_phone,
        agent_licence=info.agent_licence,
        agent_whatsapp=info.agent_whatsapp,
        agent_wechat=info.agent_wechat,
        listing_ref=info.listing_ref,
        record_source=record_source,
        transaction_stage=classify_transaction_stage(record_source),
        detail_url=item.get("url_desc") or "",
    )


def fetch_tuen_mun_transactions(
    *,
    months_back: int = 6,
    page_size: int = 100,
    request_interval_seconds: float = 0.4,
    enrich_agents: bool = True,
) -> list[UnitTransaction]:
    token = _fetch_build_token()
    cutoff = month_cutoff(months_back)
    collected: list[UnitTransaction] = []
    enricher = AgentEnricher(request_interval_seconds=request_interval_seconds) if enrich_agents else None
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
            tx_date_raw = _parse_tx_date(item.get("tx_date") or "")
            if not tx_date_raw:
                continue
            tx_date = datetime.strptime(tx_date_raw, "%Y-%m-%d").date()
            if tx_date < cutoff:
                stop = True
                continue

            branch_name = ""
            agent_name = ""
            record_source = item.get("source") or item.get("original_source") or ""
            agent_info = None
            if enricher and record_source != "LANDREG":
                estate_id = (item.get("estate") or {}).get("id") or ""
                agent_info = enricher.resolve_midland_agent(
                    token=token,
                    estate_id=estate_id,
                    flat=str(item.get("flat") or ""),
                    price=int(item.get("price") or 0),
                    record_source=record_source,
                )

            collected.append(_to_transaction(item, agent_info=agent_info))

        if stop or page * page_size >= int(body.get("count") or 0):
            break
        page += 1
        time.sleep(request_interval_seconds)

    return collected
