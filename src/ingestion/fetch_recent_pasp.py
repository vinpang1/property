"""Fetch recent provisional sale agreement (臨約) transactions for Tuen Mun."""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.centaline_client import _parse_date, _to_transaction as centaline_to_tx
from src.ingestion.centaline_client import iter_transaction_items
from src.ingestion.midland_client import (
    _fetch_build_token,
    _parse_tx_date,
    _to_transaction as midland_to_tx,
    API_BASE,
    DEFAULT_HEADERS,
)
from src.ingestion.models import UnitTransaction
from src.ingestion.transaction_stage import classify_transaction_stage
from src.utils.config import get_path


def _is_pasp(tx: UnitTransaction) -> bool:
    return (tx.transaction_stage or classify_transaction_stage(tx.record_source)) == "臨約"


def _in_date_range(tx: UnitTransaction, *, days_back: int) -> bool:
    if not tx.transaction_date:
        return False
    cutoff = date.today() - timedelta(days=days_back)
    tx_date = datetime.strptime(tx.transaction_date, "%Y-%m-%d").date()
    return cutoff <= tx_date <= date.today()


def _fetch_centaline_pasp(*, days_back: int, enricher: AgentEnricher | None) -> list[UnitTransaction]:
    day_window = "Day30" if days_back <= 30 else "Day60"
    collected: list[UnitTransaction] = []

    for item in iter_transaction_items(keyword="屯門", day=day_window, request_interval_seconds=0.2):
        tx_date_raw = _parse_date(item)
        if not tx_date_raw:
            continue
        tx_date = datetime.strptime(tx_date_raw, "%Y-%m-%d").date()
        if tx_date < date.today() - timedelta(days=days_back):
            break

        agent_info = enricher.resolve_centaline_agent(item) if enricher else None
        tx = centaline_to_tx(item, agent_info=agent_info)
        if _is_pasp(tx) and _in_date_range(tx, days_back=days_back):
            collected.append(tx)

    return collected


def _fetch_midland_pasp(*, days_back: int, enricher: AgentEnricher | None) -> list[UnitTransaction]:
    token = _fetch_build_token()
    collected: list[UnitTransaction] = []
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
            tx_date_raw = _parse_tx_date(item.get("tx_date") or "")
            if not tx_date_raw:
                continue
            tx_date = datetime.strptime(tx_date_raw, "%Y-%m-%d").date()
            if tx_date < cutoff:
                stop = True
                continue

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

            tx = midland_to_tx(item, agent_info=agent_info)
            if _is_pasp(tx) and _in_date_range(tx, days_back=days_back):
                collected.append(tx)

        if stop or page * 100 >= int(body.get("count") or 0):
            break
        page += 1
        time.sleep(0.2)

    return collected


def fetch_recent_pasp_transactions(
    *,
    days_back: int = 14,
    enrich_agents: bool = True,
) -> list[UnitTransaction]:
    enricher = AgentEnricher(request_interval_seconds=0.2) if enrich_agents else None
    transactions = _fetch_centaline_pasp(days_back=days_back, enricher=enricher)
    transactions.extend(_fetch_midland_pasp(days_back=days_back, enricher=enricher))

    seen: set[tuple] = set()
    merged: list[UnitTransaction] = []
    for tx in sorted(transactions, key=lambda item: item.transaction_date, reverse=True):
        key = (tx.estate_name, tx.block, tx.floor, tx.unit, tx.transaction_date, tx.price)
        if key in seen:
            continue
        seen.add(key)
        merged.append(tx)
    return merged


def export_recent_pasp_csv(
    *,
    days_back: int = 14,
    enrich_agents: bool = True,
) -> tuple[Path, list[UnitTransaction]]:
    transactions = fetch_recent_pasp_transactions(days_back=days_back, enrich_agents=enrich_agents)

    export_dir = get_path("output") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    output_path = export_dir / f"tuen_mun_pasp_latest_{days_back}d_{today}.csv"

    if transactions:
        rows = [tx.to_csv_row() for tx in transactions]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        output_path.write_text("", encoding="utf-8-sig")

    return output_path, transactions
