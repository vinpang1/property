#!/usr/bin/env python3
"""Main pipeline CLI for the HK property tracking system."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import init_database
from src.ingestion.download_tuen_mun import download_tuen_mun
from src.ingestion.download_primary import download_primary
from src.ingestion.download_secondary import download_secondary
from src.ingestion.download_mortgage import download_mortgage
from src.etl.clean_tuen_mun import clean_tuen_mun
from src.validation.validate_schema import validate_tuen_mun
from src.database.load_tuen_mun import load_tuen_mun, query_transactions
from src.analysis.calc_price_trend import calc_tuen_mun_trends, load_staging_trends
from src.reporting.export_monthly_report import export_monthly_report
from src.utils.logger import get_logger

logger = get_logger("pipeline", "system")


def cmd_init(_args: argparse.Namespace) -> None:
    tuen_mun_db = init_database("tuen_mun", "tuen_mun.sql")
    trends_db = init_database("trends", "trends.sql")
    print(f"✓ 數據庫已初始化")
    print(f"  - 屯門成交: {tuen_mun_db}")
    print(f"  - 全港趨勢: {trends_db}")


def cmd_ingest(args: argparse.Namespace) -> None:
    if args.source in ("tuen_mun", "all"):
        path = download_tuen_mun(provider=args.provider, use_seed=not args.generate)
        print(f"✓ 屯門成交數據: {path}")

    if args.source in ("primary", "all"):
        path = download_primary()
        print(f"✓ 全港一手數據: {path}")

    if args.source in ("secondary", "all"):
        path = download_secondary()
        print(f"✓ 全港二手數據: {path}")

    if args.source in ("mortgage", "all"):
        path = download_mortgage()
        print(f"✓ 高成數按揭資料: {path}")


def cmd_etl(_args: argparse.Namespace) -> None:
    path = clean_tuen_mun()
    print(f"✓ ETL 完成: {path}")


def cmd_validate(_args: argparse.Namespace) -> None:
    result = validate_tuen_mun()
    print(f"✓ 驗證通過: {result['valid_rows']}/{result['total_rows']} 行")


def cmd_load(_args: argparse.Namespace) -> None:
    from src.utils.config import get_path

    processed_dir = get_path("processed")
    candidates = sorted(processed_dir.glob("cleaned_*.csv"), reverse=True)
    if not candidates:
        raise SystemExit("找不到已處理嘅 CSV，請先執行 etl")
    result = load_tuen_mun(candidates[0])
    print(f"✓ 入庫完成: {result['rows_imported']} 行寫入, {result['rows_skipped']} 行跳過")


def cmd_analyze(_args: argparse.Namespace) -> None:
    staging_count = load_staging_trends()
    tuen_mun_results = calc_tuen_mun_trends()
    print(f"✓ 趨勢分析完成")
    print(f"  - 全港趨勢: {staging_count} 筆")
    print(f"  - 屯門趨勢: {len(tuen_mun_results)} 個月份")


def cmd_report(_args: argparse.Namespace) -> None:
    path = export_monthly_report()
    print(f"✓ 報告已輸出: {path}")


def cmd_run_all(_args: argparse.Namespace) -> None:
    print("=" * 50)
    print("香港物業成交追蹤系統 — 完整 Pipeline")
    print("=" * 50)

    cmd_init(_args)
    print()

    args_ingest = argparse.Namespace(source="all", provider="sample", generate=False)
    cmd_ingest(args_ingest)
    print()

    cmd_etl(_args)
    print()

    cmd_validate(_args)
    print()

    cmd_load(_args)
    print()

    cmd_analyze(_args)
    print()

    cmd_report(_args)
    print()

    print("=" * 50)
    print("最近 5 筆屯門成交:")
    for tx in query_transactions(5):
        print(
            f"  {tx['transaction_date']} | {tx['estate_name']} {tx['block']} "
            f"{tx['floor']} | ${tx['price']:,} (@${tx['price_per_sqft']}/sqft)"
        )
    print("=" * 50)
    print("✓ Pipeline 執行完成")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="香港物業成交追蹤系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py init          # 初始化數據庫
  python run.py run-all       # 執行完整 pipeline
  python run.py ingest        # 採集數據
  python run.py etl           # 清洗數據
  python run.py validate      # 驗證數據
  python run.py load          # 入庫
  python run.py analyze       # 趨勢分析
  python run.py report        # 輸出報告
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="初始化數據庫")
    subparsers.add_parser("run-all", help="執行完整 pipeline")

    ingest_parser = subparsers.add_parser("ingest", help="採集數據")
    ingest_parser.add_argument(
        "--source",
        choices=["tuen_mun", "primary", "secondary", "mortgage", "all"],
        default="all",
    )
    ingest_parser.add_argument("--provider", default="sample")
    ingest_parser.add_argument(
        "--generate",
        action="store_true",
        help="生成隨機樣本數據而唔用 seed",
    )

    subparsers.add_parser("etl", help="清洗屯門成交數據")
    subparsers.add_parser("validate", help="驗證已處理數據")
    subparsers.add_parser("load", help="入庫屯門成交數據")
    subparsers.add_parser("analyze", help="計算趨勢")
    subparsers.add_parser("report", help="輸出月度報告")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "ingest": cmd_ingest,
        "etl": cmd_etl,
        "validate": cmd_validate,
        "load": cmd_load,
        "analyze": cmd_analyze,
        "report": cmd_report,
        "run-all": cmd_run_all,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        logger.exception("Pipeline failed")
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
