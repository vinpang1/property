from src.reporting.report_columns import format_address


def test_format_address_full():
    tx = {
        "estate_name": "青山灣",
        "block": "1座",
        "floor": "8/F",
        "unit": "A",
    }
    assert format_address(tx) == "屯門區 青山灣 1座 8/F A"


def test_format_address_partial():
    tx = {"estate_name": "山景邨", "block": "2座"}
    assert format_address(tx) == "屯門區 山景邨 2座"
