from src.reporting.report_columns import detail_headers, detail_row


def test_detail_columns_count():
    assert len(detail_headers()) == 11


def test_detail_columns_include_required_fields():
    headers = detail_headers()
    required = [
        "成交日期", "地址", "屋苑", "座數", "樓層", "單位",
        "市場類型", "分行", "代理", "代理電話", "來源",
    ]
    assert headers == required


def test_detail_row_matches_headers():
    tx = {
        "transaction_date": "2026-08-03",
        "estate_name": "青山灣",
        "block": "1座",
        "floor": "8/F",
        "unit": "A",
        "market_type": "secondary",
        "branch_name": "屯門青山灣分行",
        "agent_name": "陳大文",
        "agent_phone": "9123-4567",
        "source": "中原",
    }
    row = detail_row(tx)
    assert len(row) == len(detail_headers())
    assert row[0] == "2026-08-03"
    assert row[1] == "屯門區 青山灣 1座 8/F A"
    assert row[6] == "secondary"
