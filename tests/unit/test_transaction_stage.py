from src.ingestion.transaction_stage import classify_deal_type, classify_transaction_stage, display_deal_type


def test_classify_deal_type_sale():
    assert classify_deal_type(post_type="S") == "sale"
    assert classify_deal_type(tx_type="S") == "sale"


def test_classify_deal_type_rent():
    assert classify_deal_type(post_type="R") == "rent"
    assert classify_deal_type(tx_type="R") == "rent"


def test_display_deal_type():
    assert display_deal_type("sale") == "買賣"
    assert display_deal_type("rent") == "租"


def test_classify_transaction_stage():
    assert classify_transaction_stage("LANDREG") == "土地註冊"
    assert classify_transaction_stage("AC") == "臨約"
