from src.ingestion.agent_inference import infer_agent_for_transaction
from src.ingestion.listing_index import ListingRecord
from src.ingestion.models import UnitTransaction
from src.ingestion.news_transactions import parse_news_article


def test_parse_news_article_extracts_estate_price_and_agent():
    clue = parse_news_article(
        {
            "title": "屯門市廣場2房單位以$300萬成交，代理：鄭俊彥",
            "source": "centaline",
            "published_date": "2026-08-04",
            "url": "https://example.com",
        }
    )

    assert clue is not None
    assert "屯門市廣場" in clue.estate_name
    assert clue.price == 3000000
    assert clue.agent_name == "鄭俊彥"


def test_infer_agent_from_matching_listing():
    tx = UnitTransaction(
        estate_name="屯門市廣場 1期",
        block="4座",
        floor="",
        unit="",
        area_sqft=326,
        price=3000000,
        price_per_sqft=None,
        pasp_date="2026-08-03",
        transaction_date="2026-08-03",
        district="屯門區",
        sub_district="屯門市中心",
        market_type="secondary",
        source="midland",
        source_id="TX1",
        address="屯門市廣場",
        record_source="LANDREG",
        transaction_stage="土地註冊",
    )
    listing = ListingRecord(
        source="centaline",
        listing_ref="CFO646",
        estate_name="屯門市廣場",
        block="4座",
        floor="",
        unit="",
        price=3000000,
        area_sqft=326,
        agent_name="鄭俊彥",
        branch_name="屯門時代廣場第三分行",
        agent_phone="60834270",
        agent_licence="E-438077",
    )

    result = infer_agent_for_transaction(tx, listings=[listing])

    assert result is not None
    assert result.agent_name == "鄭俊彥"
    assert result.branch_name == "屯門時代廣場第三分行"
    assert result.inference_confidence in {"高", "中", "低"}
    assert "放盤配對" in result.inference_source
