"""Centaline transaction provider."""

from __future__ import annotations

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.centaline_client import _parse_date, _to_transaction
from src.ingestion.centaline_client import fetch_tuen_mun_transactions as fetch_monthly_centaline
from src.ingestion.centaline_client import iter_transaction_items
from src.ingestion.models import UnitTransaction
from src.ingestion.providers.base import filter_sales, in_pasp_date_range


class CentalineProvider:
    id = "centaline"
    label = "中原地產"

    def fetch_recent(
        self,
        *,
        days_back: int,
        enrich_agents: bool,
        keyword: str = "屯門",
    ) -> list[UnitTransaction]:
        enricher = AgentEnricher(request_interval_seconds=0.2) if enrich_agents else None
        collected: list[UnitTransaction] = []
        day_window = "Day30" if days_back <= 30 else "Day60"

        for item in iter_transaction_items(
            keyword=keyword,
            day=day_window,
            request_interval_seconds=0.2,
        ):
            pasp_date_raw = _parse_date(item)
            if not pasp_date_raw or not in_pasp_date_range(pasp_date_raw, days_back=days_back):
                continue
            agent_info = enricher.resolve_centaline_agent(item) if enricher else None
            tx = _to_transaction(item, agent_info=agent_info)
            if tx.deal_type != "sale":
                continue
            collected.append(tx)
        return collected

    def fetch_monthly(self, *, months_back: int, enrich_agents: bool = True) -> list[UnitTransaction]:
        return filter_sales(
            fetch_monthly_centaline(months_back=months_back, enrich_agents=enrich_agents)
        )
