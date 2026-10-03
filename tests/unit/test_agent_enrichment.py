import json
from unittest.mock import patch

from src.ingestion.agent_enrichment import AgentEnricher, AgentInfo
from src.ingestion.models import UnitTransaction
from src.ingestion.transaction_stage import classify_transaction_stage


def test_unit_transaction_csv_includes_branch_agent_and_contact():
    tx = UnitTransaction(
        estate_name="新屯門中心",
        block="1座",
        floor="44",
        unit="D",
        area_sqft=517,
        price=4600000,
        price_per_sqft=8897,
        pasp_date="2026-08-03",
        transaction_date="2026-08-03",
        district="屯門區",
        sub_district="屯門碼頭",
        market_type="secondary",
        source="midland",
        source_id="NO2026080426080401750466",
        address="新屯門中心",
        branch_name="屯門 - 瓏門分行",
        agent_name="林巧慧",
        agent_phone="98215549",
        agent_licence="E-488353",
        agent_whatsapp="98215549",
        agent_wechat="wall07127",
        listing_ref="M350182538",
        record_source="MIDLAND",
        transaction_stage="臨約",
        detail_url="https://example.com/tx",
    )

    row = tx.to_csv_row()

    assert row["成交階段"] == "臨約"
    assert row["分行"] == "屯門 - 瓏門分行"
    assert row["負責代理"] == "林巧慧"
    assert row["代理電話"] == "98215549"
    assert row["代理牌照"] == "E-488353"
    assert row["放盤編號"] == "M350182538"


def test_classify_transaction_stage():
    assert classify_transaction_stage("AC") == "臨約"
    assert classify_transaction_stage("MIDLAND") == "臨約"
    assert classify_transaction_stage("LANDREG") == "土地註冊"
    assert classify_transaction_stage("Land") == "土地註冊"


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
                "agentLicense": "S-611564",
                "agentRealMobile": "61234567",
                "whatsAppInfo": {"enabled": True, "url": "https://wa.me/85261234567"},
                "weChatInfo": {"weChatId": "agent123"},
            }
        ]
    }

    with patch.object(enricher, "_fetch_json", side_effect=[post_search, post_detail]):
        info = enricher.resolve_centaline_agent(item)

    assert info.agent_name == "曾麗珍"
    assert info.branch_name == "屯門碼頭分行"
    assert info.agent_phone == "61234567"
    assert info.agent_licence == "S-611564"
    assert info.listing_ref == "CZG846"


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
