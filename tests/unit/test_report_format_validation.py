import csv
from pathlib import Path

import pytest

from src.reporting.export_tuen_mun_recent_report import export_tuen_mun_recent_report
from src.reporting.report_columns import (
    TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT,
    TUEN_MUN_RECENT_DETAIL_HEADER_NAMES,
    ReportFormatError,
    detail_headers,
    detail_row,
    validate_detail_headers,
    validate_detail_row,
    validate_exported_csv_detail,
    validate_exported_markdown_detail,
)


def test_column_definition_matches_authoritative_headers():
    assert len(detail_headers()) == TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT
    assert detail_headers() == list(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES)


def test_validate_detail_headers_rejects_wrong_order():
    bad = list(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES)
    bad[0], bad[1] = bad[1], bad[0]
    with pytest.raises(ReportFormatError):
        validate_detail_headers(bad)


def test_validate_detail_row_rejects_wrong_length():
    with pytest.raises(ReportFormatError):
        validate_detail_row(["only", "two"])


def test_validate_exported_files_from_existing_report():
    csv_path = Path("workspace/reports/in_progress/tuen_mun_recent_14d_2026-08-05.csv")
    md_path = csv_path.with_suffix(".md")
    if not csv_path.exists():
        pytest.skip("report fixture not generated")
    validate_exported_csv_detail(csv_path)
    validate_exported_markdown_detail(md_path)


def test_export_validates_thirteen_column_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.reporting.export_tuen_mun_recent_report.in_progress_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "src.reporting.export_tuen_mun_recent_report.query_transactions_by_date_range",
        lambda *_args, **_kwargs: [
            {
                "pasp_date": "2026-08-03",
                "transaction_date": "2026-08-03",
                "estate_name": "青山灣",
                "block": "1座",
                "floor": "8/F",
                "unit": "A",
                "deal_type": "sale",
                "transaction_stage": "臨約",
                "market_type": "secondary",
                "branch_name": "屯門分行",
                "agent_name": "陳大文",
                "agent_phone": "91234567",
                "source": "中原",
                "price": 5000000,
                "price_per_sqft": 10000,
            }
        ],
    )

    csv_path = export_tuen_mun_recent_report(days=14)
    md_path = csv_path.with_suffix(".md")

    validate_exported_csv_detail(csv_path)
    validate_exported_markdown_detail(md_path)

    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    detail_header = next(row for row in rows if row and row[0] == "簽臨約日期")
    assert detail_header == list(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES)
    detail_rows = [row for row in rows if row and row[0] == "2026-08-03"]
    assert len(detail_rows) == 1
    assert len(detail_rows[0]) == TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT
