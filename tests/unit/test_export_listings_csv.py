from src.ingestion.export_listings_csv import (
    PropertyListingAggregate,
    aggregate_listings_by_property,
)
from src.ingestion.listing_index import ListingRecord


def _listing(**kwargs) -> ListingRecord:
    return ListingRecord(source=kwargs.pop("source"), listing_ref=kwargs.pop("ref", "X1"), **kwargs)


def test_aggregate_groups_same_property_with_multiple_agents_and_companies():
    listings = [
        _listing(
            source="centaline",
            ref="C1",
            estate_name="屯門市廣場 1期",
            block="4座",
            floor="高層",
            unit="C室",
            price=3000000,
            area_sqft=326,
            agent_name="鄭俊彥",
            branch_name="屯門時代廣場第三分行",
            agent_phone="60834270",
            agent_licence="E-438077",
        ),
        _listing(
            source="midland",
            ref="M1",
            estate_name="屯門市廣場 1期",
            block="4座",
            floor="高層",
            unit="C室",
            price=3100000,
            area_sqft=326,
            agent_name="冼美華",
            branch_name="屯門市廣場分行",
            agent_phone="93334444",
            agent_licence="E-111111",
        ),
        _listing(
            source="midland",
            ref="M2",
            estate_name="屯門市廣場 1期",
            block="4座",
            floor="高層",
            unit="C室",
            price=3100000,
            area_sqft=326,
            agent_name="冼美華",
            branch_name="屯門市廣場分行",
            agent_phone="93334444",
            agent_licence="E-111111",
        ),
    ]

    aggregates = aggregate_listings_by_property(listings)
    assert len(aggregates) == 1

    row = aggregates[0].to_csv_row()
    assert row["樓盤地址"] == "屯門市廣場 1期 4座 高層 C室"
    assert row["中介公司"] == "中原 | 美聯"
    assert row["跟盤代理數"] == 2
    assert row["跟盤公司數"] == 2
    assert "中原-鄭俊彥" in row["代理及聯絡"]
    assert "美聯-冼美華" in row["代理及聯絡"]
