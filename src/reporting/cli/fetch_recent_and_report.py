"""採集屯門最近成交（中原 + 美聯）並入庫，再生成報告。"""

import argparse
import sys

from src.database.connection import connect, _migrate_tuen_mun_schema
from src.database.load_tuen_mun import load_unit_transactions
from src.ingestion.infer_recent_deals import fetch_recent_transactions
from src.reporting.export_tuen_mun_recent_report import export_tuen_mun_recent_report


def run(*, days: int = 14, enrich_agents: bool = True) -> None:
    conn = connect("tuen_mun")
    _migrate_tuen_mun_schema(conn)
    conn.execute("DELETE FROM tuen_mun_transactions")
    conn.commit()
    conn.close()
    print("✓ 已清空舊成交數據（移除樣本同舊格式記錄）")

    print(f"採集中原 + 美聯 屯門最近 {days} 日成交（只計買賣，唔計租）...")
    transactions = fetch_recent_transactions(
        days_back=days,
        enrich_agents=enrich_agents,
    )
    print(f"✓ 採集到 {len(transactions)} 宗")

    if not transactions:
        print("✗ 未採集到成交，報告維持現有數據")
        sys.exit(1)

    load_result = load_unit_transactions(transactions)
    print(f"✓ 入庫: {load_result['rows_imported']} 宗新增, {load_result['rows_skipped']} 宗跳過（重複）")

    report_path = export_tuen_mun_recent_report(days=days)
    md_path = report_path.with_suffix(".md")
    print("✓ 報告已生成:")
    print(f"  CSV: {report_path}")
    print(f"  MD:  {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="採集屯門最近成交並生成報告")
    parser.add_argument("--days", type=int, default=14, help="回溯日數（預設 14）")
    parser.add_argument("--no-enrich", action="store_true", help="略過代理資料查詢（較快）")
    args = parser.parse_args()
    run(days=args.days, enrich_agents=not args.no_enrich)


if __name__ == "__main__":
    main()
