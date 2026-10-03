"""Midland transaction provider."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.midland_client import (
    API_BASE,
    DEFAULT_HEADERS,
    _fetch_build_token,
    _parse_report_date,
    _to_transaction,
    fetch_tuen_mun_transactions as fetch_monthly_midland,
)
from src.ingestion.models import UnitTransaction
from src.ingestion.providers.base import filter_sales, in_pasp_date_range
from src.ingestion.report_date import parse_midland_registration_date


class MidlandProvider:
    id = "midland"
    label = "美聯物業"

    def fetch_recent(
        self,
        *,
        days_back: int,
        enrich_agents: bool,
        keyword: str = "屯門",
    ) -> list[UnitTransaction]:
        enricher = AgentEnricher(request_interval_seconds=0.2) if enrich_agents else None
        collected: list[UnitTransaction] = []
        token = _fetch_build_token()
        page = 1
        cutoff = date.today() - timedelta(days=days_back)

        while page <= 15:
            params = {
                "text": keyword,
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
                if pasp_date_raw and not in_pasp_date_range(pasp_date_raw, days_back=days_back):
                    continue
                if not pasp_date_raw and reg_date_raw and not in_pasp_date_range(
                    reg_date_raw, days_back=days_back
                ):
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
                tx = _to_transaction(item, agent_info=agent_info)
                if tx.deal_type != "sale":
                    continue
                collected.append(tx)

            if stop or page * 100 >= int(body.get("count") or 0):
                break
            page += 1
            time.sleep(0.2)

        return collected

    def fetch_monthly(self, *, months_back: int, enrich_agents: bool = True) -> list[UnitTransaction]:
        return filter_sales(
            fetch_monthly_midland(months_back=months_back, enrich_agents=enrich_agents)
        )
