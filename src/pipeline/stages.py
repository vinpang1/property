from __future__ import annotations

import argparse

from src.analysis.calc_price_trend import calc_tuen_mun_trends, load_staging_trends
from src.database.connection import init_database
from src.database.load_tuen_mun import load_tuen_mun, query_transactions
from src.etl.clean_tuen_mun import clean_tuen_mun
from src.ingestion.download_monthly import download_monthly_data
from src.ingestion.download_mortgage import download_mortgage
from src.ingestion.download_primary import download_primary
from src.ingestion.download_secondary import download_secondary
from src.ingestion.download_tuen_mun import download_tuen_mun
from src.ingestion.export_listings_csv import export_tuen_mun_listings_csv
from src.ingestion.fetch_recent_pasp import export_recent_pasp_csv
from src.ingestion.infer_recent_deals import export_recent_deals_with_inference
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

    if args.source in ("mortgage", "all"):
        path = download_mortgage()
        print(f"✓ 高成數按揭資料: {path}")


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


def download(args: argparse.Namespace) -> None:
    result = download_monthly_data(months_back=args.months_back)

    print("=" * 50)
    print(f"數據下載完成 — 最近 {args.months_back} 個月")
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
            print(f"  ✓ {source}: {path}")
    else:
        print("\n【屯門單位成交】")
        print("  ⚠ 未採集到成交")

    print("\n【摘要】")
    for note in result["notes"]:
        print(f"  • {note}")
    print(f"\n摘要檔: {result['summary_file']}")
    print("=" * 50)


def recent_pasp(args: argparse.Namespace) -> None:
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


def recent_deals(args: argparse.Namespace) -> None:
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


def export_listings(args: argparse.Namespace) -> None:
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
