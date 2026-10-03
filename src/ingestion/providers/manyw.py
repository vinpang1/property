"""Manyw (祥益) transaction provider."""

from __future__ import annotations

from src.ingestion.manyw_client import fetch_tuen_mun_transactions
from src.ingestion.models import UnitTransaction
from src.ingestion.providers.base import filter_sales, in_pasp_date_range


class ManywProvider:
    id = "manyw"
    label = "祥益地產"

    def fetch_recent(
        self,
        *,
        days_back: int,
        enrich_agents: bool,
        keyword: str = "屯門",
    ) -> list[UnitTransaction]:
        del enrich_agents, keyword
        months_back = max(1, (days_back + 29) // 30)
        transactions = fetch_tuen_mun_transactions(months_back=months_back)
        return [
            tx
            for tx in filter_sales(transactions)
            if in_pasp_date_range(tx.pasp_date, days_back=days_back)
        ]

    def fetch_monthly(self, *, months_back: int, enrich_agents: bool = True) -> list[UnitTransaction]:
        del enrich_agents
        return filter_sales(fetch_tuen_mun_transactions(months_back=months_back))
