from src.ingestion.landreg_client import parse_monthly_summary


def test_parse_monthly_summary_extracts_residential_count():
    rows = [
        {
            "Year": 2025,
            "Month": 7,
            "Description": "Number of ASP for Residential Building Units",
            "Units": "5,766",
            "Consideration (nearest $ million)": "46,354",
        },
        {
            "Year": 2025,
            "Month": 7,
            "Description": "Number of Tuen Mun transactions for ASP building units",
            "Units": "608",
            "Consideration (nearest $ million)": "2,824",
        },
    ]

    summary = parse_monthly_summary(rows, "https://example.test/202507_data.json")

    assert summary.period == "2025-07"
    assert summary.residential_count == 5766
    assert summary.tuen_mun_count == 608
    assert summary.residential_volume_million == 46354
