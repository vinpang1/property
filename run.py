#!/usr/bin/env python3
"""Main pipeline CLI for the HK property tracking system."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.database.connection import init_database
from src.ingestion.download_tuen_mun import download_tuen_mun
from src.ingestion.download_primary import download_primary
from src.ingestion.download_secondary import download_secondary
from src.ingestion.download_monthly import download_monthly_data
from src.ingestion.export_listings_csv import export_tuen_mun_listings_csv
from src.ingestion.fetch_recent_pasp import export_recent_pasp_csv
from src.ingestion.infer_recent_deals import export_recent_deals_with_inference
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


def cmd_export_listings(args: argparse.Namespace) -> None:
    output_path, aggregates, stats = export_tuen_mun_listings_csv(
        keyword=args.keyword,
        fetch_agents=not args.no_agent_fetch,
    )

    print("=" * 60)
    print(f"屯門放盤索引匯出 — {args.keyword}")
    print("=" * 60)
    print(
        f"放盤紀錄 {stats['raw_listings']} 個 → 樓盤 {stats['properties']} 個 "
        f"(多公司跟盤 {stats['multi_company']} / 多代理跟盤 {stats['multi_agent']})"
    )
    print(f"CSV: {output_path}\n")

    for index, item in enumerate(aggregates[:20], 1):
        row = item.to_csv_row()
        print(
            f"{index:2}. {row['樓盤地址']} | ${row['叫價']:,} "
            f"| 公司{row['跟盤公司數']} 代理{row['跟盤代理數']}"
        )
        print(f"    中介: {row['中介公司']}")
        print(f"    代理: {row['代理及聯絡'][:120]}{'...' if len(str(row['代理及聯絡'])) > 120 else ''}")

    if len(aggregates) > 20:
        print(f"... 另有 {len(aggregates) - 20} 個樓盤，詳見 CSV")
    print("=" * 60)


def cmd_recent_deals(args: argparse.Namespace) -> None:
    output_path, transactions, stats = export_recent_deals_with_inference(
        days_back=args.days,
        enrich_direct_agents=not args.no_direct_enrich,
    )

    print("=" * 70)
    print(f"屯門區最近 {args.days} 日成交 + 代理推斷（放盤 & 新聞交叉比對）")
    print("=" * 70)
    print(
        f"成交 {stats['total']} 宗 | 有代理 {stats['with_agent']} 宗 "
        f"(直接 {stats['direct_agent']} / 推斷 {stats['inferred_agent']})"
    )
    print(
        f"放盤索引 {stats['listing_count']} 個 | 新聞線索 {stats['news_clues']} 則"
    )
    print(f"CSV: {output_path}\n")

    for index, tx in enumerate(transactions[:30], 1):
        stage = tx.transaction_stage or tx.to_csv_row()["成交階段"]
        agent = tx.agent_name or "—"
        branch = tx.branch_name or "—"
        phone = tx.agent_phone or "—"
        source_tag = tx.inference_source or ("直接" if tx.agent_name else "—")
        confidence = f" [{tx.inference_confidence}]" if tx.inference_confidence else ""
        print(
            f"{index:2}. {tx.transaction_date} | {stage} | {tx.estate_name} {tx.block} {tx.unit} "
            f"| ${tx.price:,}"
        )
        print(f"    分行: {branch} | 代理: {agent} | 電話: {phone} | 來源: {source_tag}{confidence}")

    if len(transactions) > 30:
        print(f"... 另有 {len(transactions) - 30} 宗，詳見 CSV")
    print("=" * 70)


def cmd_recent_pasp(args: argparse.Namespace) -> None:
    output_path, transactions = export_recent_pasp_csv(
        days_back=args.days,
        enrich_agents=not args.no_agent_enrich,
    )

    print("=" * 60)
    print(f"屯門區最近 {args.days} 日臨約成交（代理確認）")
    print("=" * 60)
    print(f"共 {len(transactions)} 宗")
    print(f"CSV: {output_path}\n")

    if not transactions:
        print("暫時未找到臨約紀錄。臨約只會喺代理行自行刊登（中原 AC、美聯 MIDLAND）時出現。")
        return

    with_agent = sum(1 for tx in transactions if tx.agent_name)
    print(f"含代理聯絡資料: {with_agent}/{len(transactions)} 宗\n")

    for index, tx in enumerate(transactions, 1):
        contact = tx.agent_phone or "—"
        branch = tx.branch_name or "—"
        agent = tx.agent_name or "—"
        print(
            f"{index:2}. {tx.transaction_date} | {tx.estate_name} {tx.block} {tx.floor} {tx.unit} "
            f"| ${tx.price:,} | {tx.source}"
        )
        print(f"    分行: {branch} | 代理: {agent} | 電話: {contact}")
        if tx.agent_licence:
            print(f"    牌照: {tx.agent_licence}")
    print("=" * 60)


def cmd_download(args: argparse.Namespace) -> None:
    months_back = args.months_back
    result = download_monthly_data(months_back=months_back)

    print("=" * 50)
    print(f"數據下載完成 — 最近 {months_back} 個月")
    print("=" * 50)

    if result["hk_wide_files"]:
        print("\n【全港成交數目】（土地註冊處官方）")
        for path in result["hk_wide_files"]:
            print(f"  ✓ {path}")
    else:
        print("\n【全港成交數目】")
        print("  ⚠ 官方月度數據暫未發布")

    if result["tuen_mun_files"]:
        print(f"\n【屯門單位成交】合併共 {result['tuen_mun_count']} 宗")
        for source, path in result["tuen_mun_files"].items():
            print(f"  ✓ [{source}] {path}")
    else:
        print("\n【屯門單位成交】")
        print("  ⚠ 未找到數據")

    if result["notes"]:
        print("\n備註：")
        for note in result["notes"]:
            print(f"  - {note}")

    print(f"\n摘要：{result['summary_file']}")
    print("=" * 50)


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
    subparsers.add_parser("report", help="輸出月度報告")

    download_parser = subparsers.add_parser("download", help="下載最近數月數據（全港 + 屯門多來源）")
    download_parser.add_argument(
        "--months-back",
        type=int,
        default=6,
        help="回溯月份數（預設：6）",
    )

    recent_parser = subparsers.add_parser("recent-pasp", help="顯示屯門最近臨約成交（含代理聯絡）")
    recent_parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="回溯日數（預設：14）",
    )
    recent_parser.add_argument(
        "--no-agent-enrich",
        action="store_true",
        help="略過代理／分行聯絡資料查詢",
    )

    deals_parser = subparsers.add_parser(
        "recent-deals",
        help="最近成交 + 放盤／新聞推斷負責代理",
    )
    deals_parser.add_argument("--days", type=int, default=14, help="回溯日數（預設：14）")
    deals_parser.add_argument(
        "--no-direct-enrich",
        action="store_true",
        help="略過臨約紀錄的直接代理查詢，只做放盤／新聞推斷",
    )

    listings_parser = subparsers.add_parser(
        "export-listings",
        help="匯出屯門現售放盤索引（按樓盤合併 agent/公司）",
    )
    listings_parser.add_argument("--keyword", default="屯門", help="搜尋關鍵字（預設：屯門）")
    listings_parser.add_argument(
        "--no-agent-fetch",
        action="store_true",
        help="略過中原放盤代理詳情查詢（較快但代理欄位可能空白）",
    )

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "ingest": cmd_ingest,
        "etl": cmd_etl,
        "validate": cmd_validate,
        "load": cmd_load,
        "analyze": cmd_analyze,
        "report": cmd_report,
        "download": cmd_download,
        "recent-pasp": cmd_recent_pasp,
        "recent-deals": cmd_recent_deals,
        "export-listings": cmd_export_listings,
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
