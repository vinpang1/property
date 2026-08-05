import json
from unittest.mock import patch

from src.ingestion.agent_enrichment import AgentEnricher, AgentInfo
from src.ingestion.models import UnitTransaction


def test_unit_transaction_csv_includes_branch_and_agent():
    tx = UnitTransaction(
        estate_name="新屯門中心",
        block="1座",
        floor="44",
        unit="D",
        area_sqft=517,
        price=4600000,
        price_per_sqft=8897,
        transaction_date="2026-08-03",
        district="屯門區",
        sub_district="屯門碼頭",
        market_type="secondary",
        source="midland",
        source_id="NO2026080426080401750466",
        address="新屯門中心",
        branch_name="屯門 - 瓏門分行",
        agent_name="林巧慧",
        record_source="MIDLAND",
        detail_url="https://example.com/tx",
    )

    row = tx.to_csv_row()

    assert row["分行"] == "屯門 - 瓏門分行"
    assert row["負責代理"] == "林巧慧"
    assert row["成交來源"] == "MIDLAND"
    assert row["詳情連結"] == "https://example.com/tx"


def test_resolve_centaline_agent_from_post_detail():
    enricher = AgentEnricher(request_interval_seconds=0)
    item = {
        "dataSource": "AC",
        "transactionPrice": 3450000,
        "buildingName": "Elverum 1座",
        "nArea": 236,
        "bigEstateName": "Novo Land",
        "estateName": "1A期",
    }

    post_search = {
        "data": [
            {
                "refNo": "CZG846",
                "buildingName": "Elverum 1座",
                "priceInfo": {"price": 3450000},
                "areaInfo": {"nSize": 236},
            }
        ]
    }
    post_detail = {
        "postAgents": [
            {
                "agentNameC": "曾麗珍",
                "branchName": "屯門碼頭分行",
            }
        ]
    }

    with patch.object(enricher, "_fetch_json", side_effect=[post_search, post_detail]):
        info = enricher.resolve_centaline_agent(item)

    assert info == AgentInfo(agent_name="曾麗珍", branch_name="屯門碼頭分行")


def test_resolve_midland_branch_from_branch_page():
    enricher = AgentEnricher(request_interval_seconds=0)
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"result":{"branchData":{"alt_name":"屯門 - 瓏門分行"}}}}}
    </script>
    """

    with patch.object(enricher, "_fetch_html", return_value=html):
        branch = enricher.resolve_midland_branch("02350")

    assert branch == "屯門 - 瓏門分行"
