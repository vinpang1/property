"""Provider registry driven by config/sources.yaml."""

from __future__ import annotations

from typing import Protocol

from src.ingestion.models import UnitTransaction
from src.ingestion.providers.base import merge_recent_transactions
from src.ingestion.providers.centaline import CentalineProvider
from src.ingestion.providers.manyw import ManywProvider
from src.ingestion.providers.midland import MidlandProvider
from src.ingestion.providers.ricacorp import RicacorpProvider
from src.utils.config import get_sources

PROVIDER_REGISTRY: dict[str, object] = {
    "centaline": CentalineProvider(),
    "midland": MidlandProvider(),
    "ricacorp": RicacorpProvider(),
    "manyw": ManywProvider(),
}


class TransactionProvider(Protocol):
    id: str
    label: str

    def fetch_recent(
        self,
        *,
        days_back: int,
        enrich_agents: bool,
        keyword: str = "屯門",
    ) -> list[UnitTransaction]: ...

    def fetch_monthly(self, *, months_back: int, enrich_agents: bool = True) -> list[UnitTransaction]: ...


def get_enabled_providers(source_key: str = "tuen_mun") -> list[TransactionProvider]:
    providers_cfg = get_sources()["sources"][source_key]["providers"]
    enabled: list[TransactionProvider] = []
    for item in providers_cfg:
        if not item.get("enabled", False):
            continue
        provider = PROVIDER_REGISTRY.get(item["id"])
        if provider is not None:
            enabled.append(provider)  # type: ignore[arg-type]
    return enabled


def fetch_recent_transactions(
    *,
    days_back: int,
    enrich_agents: bool,
    keyword: str = "屯門",
    source_key: str = "tuen_mun",
) -> list[UnitTransaction]:
    batches: list[list[UnitTransaction]] = []
    for provider in get_enabled_providers(source_key):
        batches.append(
            provider.fetch_recent(
                days_back=days_back,
                enrich_agents=enrich_agents,
                keyword=keyword,
            )
        )
    return merge_recent_transactions(batches, days_back=days_back)


def monthly_fetchers(source_key: str = "tuen_mun") -> dict[str, tuple[str, TransactionProvider]]:
    fetchers: dict[str, tuple[str, TransactionProvider]] = {}
    for provider in get_enabled_providers(source_key):
        fetchers[provider.id] = (provider.label, provider)
    return fetchers
