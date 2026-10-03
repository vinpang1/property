import csv
from datetime import datetime
from pathlib import Path

from src.database.connection import get_connection
from src.database.load_trends import query_trends
from src.reporting.workspace import ensure_workspace_dirs, in_progress_dir
from src.utils.logger import get_logger, log_event

logger = get_logger("export_monthly_report", "system")


def export_monthly_report() -> Path:
    ensure_workspace_dirs()
    report_dir = in_progress_dir()

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = report_dir / f"monthly_report_{today}.csv"

    trends = query_trends(limit=24)
    tuen_mun_summary = _tuen_mun_summary()

    with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["# 香港物業成交追蹤系統 — 月度報告"])
        writer.writerow([f"# 生成日期: {today}"])
        writer.writerow([])

        writer.writerow(["## 屯門區成交摘要"])
        writer.writerow(
            ["總成交宗數", "平均成交價", "平均呎價", "最早成交", "最近成交"]
        )
        writer.writerow(
            [
                tuen_mun_summary["total_count"],
                tuen_mun_summary["avg_price"],
                tuen_mun_summary["avg_price_per_sqft"],
                tuen_mun_summary["earliest_date"],
                tuen_mun_summary["latest_date"],
            ]
        )
        writer.writerow([])

        writer.writerow(["## 全港趨勢（月度）"])
        writer.writerow(
            [
                "月份",
                "市場類型",
                "區域",
                "成交宗數",
                "平均價",
                "中位數",
                "平均呎價",
                "環比變化(%)",
            ]
        )
        for t in trends:
            writer.writerow(
                [
                    t["period"],
                    t["market_type"],
                    t["district"],
                    t["transaction_count"],
                    t["avg_price"],
                    t["median_price"],
                    t["avg_price_per_sqft"],
                    t.get("price_change_pct", ""),
                ]
            )

    log_event(logger, "info", "Report exported", path=str(report_path))
    return report_path


def _tuen_mun_summary() -> dict:
    with get_connection("tuen_mun") as conn:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                ROUND(AVG(price), 2) AS avg_price,
                ROUND(AVG(price_per_sqft), 2) AS avg_price_per_sqft,
                MIN(transaction_date) AS earliest_date,
                MAX(transaction_date) AS latest_date
            FROM tuen_mun_transactions
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else {}
