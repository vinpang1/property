"""Fetch recent Tuen Mun deals and infer agents from listings and news."""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.agent_inference import infer_agents_for_transactions
from src.ingestion.centaline_client import _parse_date, _to_transaction as centaline_to_tx
from src.ingestion.centaline_client import iter_transaction_items
from src.ingestion.listing_index import build_listing_index
from src.ingestion.midland_client import (
    API_BASE,
    DEFAULT_HEADERS,
    _fetch_build_token,
    _parse_report_date,
    _to_transaction as midland_to_tx,
)
from src.ingestion.models import UnitTransaction
from src.ingestion.news_review import collect_tuen_mun_news_review
from src.ingestion.news_transactions import collect_news_transaction_clues
from src.ingestion.report_date import enrich_pasp_dates, parse_midland_registration_date
from src.utils.config import get_path

import json
import time
import urllib.parse
import urllib.request


def _in_date_range(pasp_date_raw: str, *, days_back: int) -> bool:
    if not pasp_date_raw:
        return False
    cutoff = date.today() - timedelta(days=days_back)
    pasp_date = datetime.strptime(pasp_date_raw, "%Y-%m-%d").date()
    return cutoff <= pasp_date <= date.today()


def _fetch_recent_transactions(*, days_back: int, enrich_agents: bool) -> list[UnitTransaction]:
    enricher = AgentEnricher(request_interval_seconds=0.2) if enrich_agents else None
    collected: list[UnitTransaction] = []
    day_window = "Day30" if days_back <= 30 else "Day60"

    for item in iter_transaction_items(keyword="屯門", day=day_window, request_interval_seconds=0.2):
        pasp_date_raw = _parse_date(item)
        if not pasp_date_raw:
            continue
        if not _in_date_range(pasp_date_raw, days_back=days_back):
            continue
        agent_info = enricher.resolve_centaline_agent(item) if enricher else None
        tx = centaline_to_tx(item, agent_info=agent_info)
        if tx.deal_type != "sale":
            continue
        collected.append(tx)

    token = _fetch_build_token()
    page = 1
    cutoff = date.today() - timedelta(days=days_back)
    while page <= 15:
        params = {
            "text": "屯門",
            "tx_type": "S",
            "page": str(page),
            "limit": "100",
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
            pasp_date_raw = _parse_report_date(item)
            reg_date_raw = parse_midland_registration_date(item)
            date_for_window = pasp_date_raw or reg_date_raw
            if not date_for_window:
                continue
            if datetime.strptime(date_for_window, "%Y-%m-%d").date() < cutoff:
                if not pasp_date_raw:
                    stop = True
                continue
            if pasp_date_raw and not _in_date_range(pasp_date_raw, days_back=days_back):
                continue
            if not pasp_date_raw and reg_date_raw and not _in_date_range(reg_date_raw, days_back=days_back):
                continue

            agent_info = None
            record_source = item.get("source") or item.get("original_source") or ""
            if enricher and record_source != "LANDREG":
                estate_id = (item.get("estate") or {}).get("id") or ""
                agent_info = enricher.resolve_midland_agent(
                    token=token,
                    estate_id=estate_id,
                    flat=str(item.get("flat") or ""),
                    price=int(item.get("price") or 0),
                    record_source=record_source,
                )
            tx = midland_to_tx(item, agent_info=agent_info)
            if tx.deal_type != "sale":
                continue
            collected.append(tx)

        if stop or page * 100 >= int(body.get("count") or 0):
            break
        page += 1
        time.sleep(0.2)

    collected = enrich_pasp_dates(collected)

    seen: set[tuple] = set()
    merged: list[UnitTransaction] = []
    for tx in sorted(collected, key=lambda item: item.pasp_date or "", reverse=True):
        if not tx.pasp_date or not _in_date_range(tx.pasp_date, days_back=days_back):
            continue
        key = (tx.estate_name, tx.block, tx.floor, tx.unit, tx.pasp_date, tx.price, tx.source)
        if key in seen:
            continue
        seen.add(key)
        merged.append(tx)
    return merged


def fetch_recent_transactions(*, days_back: int, enrich_agents: bool) -> list[UnitTransaction]:
    """Collect recent Tuen Mun transactions from enabled ingestion providers."""
    return _fetch_recent_transactions(days_back=days_back, enrich_agents=enrich_agents)


def export_recent_deals_with_inference(
    *,
    days_back: int = 14,
    enrich_direct_agents: bool = True,
) -> tuple[Path, list[UnitTransaction], dict]:
    transactions = _fetch_recent_transactions(days_back=days_back, enrich_agents=enrich_direct_agents)
    listings = build_listing_index(keyword="屯門", max_centaline_pages=3, max_midland_pages=5)
    news_articles = collect_tuen_mun_news_review(limit_per_source=15)
    news_clues = collect_news_transaction_clues(news_articles)
    transactions = infer_agents_for_transactions(
        transactions,
        listings=listings,
        news_clues=news_clues,
    )

    export_dir = get_path("output") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    output_path = export_dir / f"tuen_mun_deals_inferred_{days_back}d_{today}.csv"

    if transactions:
        rows = [tx.to_csv_row() for tx in transactions]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    stats = {
        "total": len(transactions),
        "with_agent": sum(1 for tx in transactions if tx.agent_name),
        "direct_agent": sum(1 for tx in transactions if tx.agent_name and not tx.inference_source),
        "inferred_agent": sum(1 for tx in transactions if tx.inference_source),
        "listing_count": len(listings),
        "news_clues": len(news_clues),
    }
    return output_path, transactions, stats
