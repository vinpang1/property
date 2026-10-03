from src.ingestion.report_date import (
    enrich_pasp_dates,
    parse_centaline_pasp_date,
    parse_centaline_registration_date,
    parse_midland_pasp_date,
    parse_midland_registration_date,
)
from src.ingestion.models import UnitTransaction


def test_centaline_pasp_date_uses_ins_date_only():
    item = {"insDate": "2026-07-24T00:00:00", "regDate": "2026-08-03T00:00:00"}
    assert parse_centaline_pasp_date(item) == "2026-07-24"
    assert parse_centaline_registration_date(item) == "2026-08-03"


def test_midland_pasp_date_only_for_provisional_sources():
    provisional = {"source": "MIDLAND", "tx_date": "2026-07-26T16:00:00.000Z"}
    landreg = {"source": "LANDREG", "tx_date": "2026-08-03T16:00:00.000Z"}
    assert parse_midland_pasp_date(provisional) == "2026-07-26"
    assert parse_midland_pasp_date(landreg) == ""
    assert parse_midland_registration_date(landreg) == "2026-08-03"


def test_enrich_pasp_dates_from_centaline_match():
    centaline = UnitTransaction(
        estate_name="新圍苑",
        block="新順閣 (B座)",
        floor="七樓",
        unit="8室",
        area_sqft=None,
        price=4200000,
        price_per_sqft=None,
        pasp_date="2026-07-24",
        district="屯門區",
        sub_district="",
        market_type="secondary",
        source="centaline",
        source_id="1",
        address="新圍苑",
        registration_date="2026-08-03",
    )
    midland = UnitTransaction(
        estate_name="新圍苑",
        block="新順閣 (B座)",
        floor="七樓",
        unit="8室",
        area_sqft=None,
        price=4200000,
        price_per_sqft=None,
        pasp_date="",
        district="屯門區",
        sub_district="",
        market_type="secondary",
        source="midland",
        source_id="2",
        address="新圍苑",
        registration_date="2026-08-03",
    )
    enriched = enrich_pasp_dates([centaline, midland])
    assert enriched[1].pasp_date == "2026-07-24"
