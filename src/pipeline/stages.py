from __future__ import annotations

import argparse

from src.analysis.calc_price_trend import calc_tuen_mun_trends, load_staging_trends
from src.database.connection import init_database
from src.database.load_tuen_mun import load_tuen_mun, query_transactions
from src.etl.clean_tuen_mun import clean_tuen_mun
from src.ingestion.download_primary import download_primary
from src.ingestion.download_secondary import download_secondary
from src.ingestion.download_tuen_mun import download_tuen_mun
from src.reporting.export_monthly_report import export_monthly_report
from src.reporting.workspace import archive_report as _archive_report
from src.reporting.workspace import list_reports as _list_reports
from src.utils.config import get_path
from src.validation.validate_schema import validate_tuen_mun


def init(_args: argparse.Namespace | None = None) -> None:
    tuen_mun_db = init_database("tuen_mun", "tuen_mun.sql")
    trends_db = init_database("trends", "trends.sql")
    print("✓ 數據庫已初始化")
    print(f"  - 屯門成交: {tuen_mun_db}")
    print(f"  - 全港趨勢: {trends_db}")


def ingest(args: argparse.Namespace) -> None:
    if args.source in ("tuen_mun", "all"):
        path = download_tuen_mun(provider=args.provider, use_seed=not args.generate)
        print(f"✓ 屯門成交數據: {path}")

    if args.source in ("primary", "all"):
        path = download_primary()
        print(f"✓ 全港一手數據: {path}")

    if args.source in ("secondary", "all"):
        path = download_secondary()
        print(f"✓ 全港二手數據: {path}")


def etl(_args: argparse.Namespace | None = None) -> None:
    path = clean_tuen_mun()
    print(f"✓ ETL 完成: {path}")


def validate(_args: argparse.Namespace | None = None) -> None:
    result = validate_tuen_mun()
    print(f"✓ 驗證通過: {result['valid_rows']}/{result['total_rows']} 行")


def load(_args: argparse.Namespace | None = None) -> None:
    processed_dir = get_path("processed")
    candidates = sorted(processed_dir.glob("cleaned_*.csv"), reverse=True)
    if not candidates:
        raise SystemExit("找不到已處理嘅 CSV，請先執行 etl")
    result = load_tuen_mun(candidates[0])
    print(f"✓ 入庫完成: {result['rows_imported']} 行寫入, {result['rows_skipped']} 行跳過")


def analyze(_args: argparse.Namespace | None = None) -> None:
    staging_count = load_staging_trends()
    tuen_mun_results = calc_tuen_mun_trends()
    print("✓ 趨勢分析完成")
    print(f"  - 全港趨勢: {staging_count} 筆")
    print(f"  - 屯門趨勢: {len(tuen_mun_results)} 個月份")


def report(_args: argparse.Namespace | None = None) -> None:
    path = export_monthly_report()
    print(f"✓ 報告已輸出: {path}")
    print("  工作區: workspace/reports/in_progress/")


def list_reports(_args: argparse.Namespace | None = None) -> None:
    reports = _list_reports()
    print("報告工作區")
    print("=" * 40)
    print(f"\n進行中 ({len(reports['in_progress'])} 份):")
    for p in reports["in_progress"]:
        print(f"  - {p.name}")
    if not reports["in_progress"]:
        print("  （空）")
    print(f"\n保留 ({len(reports['archived'])} 份):")
    for p in reports["archived"]:
        print(f"  - {p.name}")
    if not reports["archived"]:
        print("  （空）")


def archive_report(args: argparse.Namespace) -> None:
    dest = _archive_report(args.filename)
    print(f"✓ 已歸檔: {dest.name}")
    print("  位置: workspace/reports/archived/")


def print_recent_transactions(limit: int = 5) -> None:
    print(f"最近 {limit} 筆屯門成交:")
    for tx in query_transactions(limit):
        print(
            f"  {tx['transaction_date']} | {tx['estate_name']} {tx['block']} "
            f"{tx['floor']} | ${tx['price']:,} (@${tx['price_per_sqft']}/sqft)"
        )
