import pytest

from src.ingestion.models import UnitTransaction
from src.ingestion.providers.base import in_pasp_date_range, merge_recent_transactions
from src.ingestion.providers.registry import get_enabled_providers, monthly_fetchers


def test_enabled_providers_include_four_sources():
    providers = get_enabled_providers()
    ids = {provider.id for provider in providers}
    assert ids == {"centaline", "midland", "ricacorp", "manyw"}


def test_monthly_fetchers_match_enabled_providers():
    fetchers = monthly_fetchers()
    assert set(fetchers) == {"centaline", "midland", "ricacorp", "manyw"}
    assert fetchers["ricacorp"][0] == "利嘉閣"


def test_in_pasp_date_range_rejects_empty():
    assert in_pasp_date_range("", days_back=14) is False


def test_merge_recent_transactions_deduplicates_by_source():
    tx_a = UnitTransaction(
        estate_name="青山灣",
        block="1座",
        floor="8/F",
        unit="A",
        area_sqft=500,
        price=5000000,
        price_per_sqft=10000,
        pasp_date="2026-08-03",
        district="屯門區",
        sub_district="",
        market_type="secondary",
        source="centaline",
        source_id="a",
        address="青山灣",
    )
    tx_b = UnitTransaction(
        estate_name="青山灣",
        block="1座",
        floor="8/F",
        unit="A",
        area_sqft=500,
        price=5000000,
        price_per_sqft=10000,
        pasp_date="2026-08-03",
        district="屯門區",
        sub_district="",
        market_type="secondary",
        source="midland",
        source_id="b",
        address="青山灣",
    )
    merged = merge_recent_transactions([[tx_a, tx_b]], days_back=30)
    assert len(merged) == 2

    merged_dup = merge_recent_transactions([[tx_a, tx_a]], days_back=30)
    assert len(merged_dup) == 1


def test_merge_recent_transactions_filters_outside_window():
    tx_old = UnitTransaction(
        estate_name="青山灣",
        block="1座",
        floor="8/F",
        unit="A",
        area_sqft=500,
        price=5000000,
        price_per_sqft=10000,
        pasp_date="2020-01-01",
        district="屯門區",
        sub_district="",
        market_type="secondary",
        source="centaline",
        source_id="old",
        address="青山灣",
    )
    merged = merge_recent_transactions([[tx_old]], days_back=14)
    assert merged == []
