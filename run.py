#!/usr/bin/env python3
"""Main pipeline CLI for the HK property tracking system."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import stages  # noqa: E402
from src.pipeline.runner import run_all  # noqa: E402
from src.reporting.cli.build_recent import run as build_recent_report  # noqa: E402
from src.reporting.cli.fetch_recent_and_report import run as fetch_recent_report  # noqa: E402
from src.reporting.cli.validate_format import run as validate_report  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger("pipeline", "system")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="香港物業成交追蹤系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py init                    # 初始化數據庫
  python run.py run-all                 # 執行完整 pipeline
  python run.py ingest                  # 採集數據
  python run.py report                  # 月度報告（同 report monthly）
  python run.py report recent --days 14 # 屯門最近成交報告
  python run.py workspace list          # 列出工作區報告
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="初始化數據庫")
    subparsers.add_parser("run-all", help="執行完整 pipeline")

    ingest_parser = subparsers.add_parser("ingest", help="採集數據")
    ingest_parser.add_argument(
        "--source",
        choices=["tuen_mun", "primary", "secondary", "all"],
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

    report_parser = subparsers.add_parser("report", help="報告生成")
    report_sub = report_parser.add_subparsers(dest="report_command")
    report_sub.add_parser("monthly", help="月度報告（預設）")
    recent_parser = report_sub.add_parser("recent", help="屯門最近成交報告")
    recent_parser.add_argument("--days", type=int, default=14)
    fetch_parser = report_sub.add_parser("fetch-recent", help="採集最近成交並出報告")
    fetch_parser.add_argument("--days", type=int, default=14)
    fetch_parser.add_argument("--no-enrich", action="store_true")
    validate_parser = report_sub.add_parser("validate", help="驗證報告 13 欄格式")
    validate_parser.add_argument("path", type=Path)

    workspace_parser = subparsers.add_parser("workspace", help="報告工作區管理")
    workspace_sub = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_sub.add_parser("list", help="列出進行中同保留報告")
    archive_parser = workspace_sub.add_parser("archive", help="將進行中報告移至保留")
    archive_parser.add_argument("filename", help="報告檔名，例如 monthly_report_2026-08-05.csv")

    args = parser.parse_args()

    try:
        if args.command == "init":
            stages.init(args)
        elif args.command == "run-all":
            run_all(args)
        elif args.command == "ingest":
            stages.ingest(args)
        elif args.command == "etl":
            stages.etl(args)
        elif args.command == "validate":
            stages.validate(args)
        elif args.command == "load":
            stages.load(args)
        elif args.command == "analyze":
            stages.analyze(args)
        elif args.command == "report":
            if args.report_command in (None, "monthly"):
                stages.report(args)
            elif args.report_command == "recent":
                build_recent_report(days=args.days)
            elif args.report_command == "fetch-recent":
                fetch_recent_report(days=args.days, enrich_agents=not args.no_enrich)
            elif args.report_command == "validate":
                validate_report(args.path)
        elif args.command == "workspace":
            if args.workspace_command == "list":
                stages.list_reports(args)
            elif args.workspace_command == "archive":
                stages.archive_report(args)
    except Exception as e:
        logger.exception("Pipeline failed")
        print(f"✗ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
