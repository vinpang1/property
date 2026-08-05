import csv
from datetime import date, timedelta
from pathlib import Path

from src.database.load_tuen_mun import query_transactions_by_date_range
from src.reporting.report_columns import (
    TUEN_MUN_RECENT_DETAIL_COLUMNS,
    detail_headers,
    detail_row,
)
from src.reporting.workspace import ensure_workspace_dirs, in_progress_dir
from src.utils.logger import get_logger, log_event

logger = get_logger("export_tuen_mun_recent_report", "system")


def export_tuen_mun_recent_report(days: int = 14) -> Path:
    ensure_workspace_dirs()
    report_dir = in_progress_dir()

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    transactions = query_transactions_by_date_range(start_str, end_str)
    summary = _summarize(transactions)

    today = end_date.isoformat()
    report_path = report_dir / f"tuen_mun_recent_{days}d_{today}.csv"

    with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["# 屯門區成交報告 — 最近 {} 日（以簽臨約日計）".format(days)])
        writer.writerow([f"# 報告期間: {start_str} 至 {end_str}"])
        writer.writerow([f"# 生成日期: {today}"])
        writer.writerow([])

        writer.writerow(["## 摘要"])
        writer.writerow(
            ["成交宗數", "總成交額", "平均成交價", "平均呎價", "最高成交價", "最低成交價"]
        )
        writer.writerow(
            [
                summary["count"],
                summary["total_volume"],
                summary["avg_price"],
                summary["avg_price_per_sqft"],
                summary["max_price"],
                summary["min_price"],
            ]
        )
        writer.writerow([])

        writer.writerow(["## 成交明細"])
        writer.writerow(detail_headers())
        for tx in transactions:
            writer.writerow(detail_row(tx))

    md_path = report_path.with_suffix(".md")
    _write_markdown(md_path, days, start_str, end_str, today, summary, transactions)

    log_event(
        logger,
        "info",
        "Tuen Mun recent report exported",
        path=str(report_path),
        transactions=summary["count"],
    )
    return report_path


def _summarize(transactions: list[dict]) -> dict:
    if not transactions:
        return {
            "count": 0,
            "total_volume": 0,
            "avg_price": 0,
            "avg_price_per_sqft": 0,
            "max_price": 0,
            "min_price": 0,
        }

    prices = [tx["price"] for tx in transactions]
    sqft_prices = [tx["price_per_sqft"] for tx in transactions if tx.get("price_per_sqft")]

    return {
        "count": len(transactions),
        "total_volume": sum(prices),
        "avg_price": round(sum(prices) / len(prices), 2),
        "avg_price_per_sqft": round(sum(sqft_prices) / len(sqft_prices), 2) if sqft_prices else 0,
        "max_price": max(prices),
        "min_price": min(prices),
    }


def _write_markdown(
    path: Path,
    days: int,
    start_str: str,
    end_str: str,
    today: str,
    summary: dict,
    transactions: list[dict],
) -> None:
    lines = [
        f"# 屯門區成交報告 — 最近 {days} 日（以簽臨約日計）",
        "",
        f"- **報告期間**: {start_str} 至 {end_str}（簽臨約日期）",
        f"- **生成日期**: {today}",
        f"- **狀態**: 進行中",
        "",
        "## 摘要",
        "",
        "| 指標 | 數值 |",
        "|------|------|",
        f"| 成交宗數 | {summary['count']} |",
        f"| 總成交額 | ${summary['total_volume']:,} |",
        f"| 平均成交價 | ${summary['avg_price']:,.0f} |",
        f"| 平均呎價 | ${summary['avg_price_per_sqft']:,.0f} |",
        f"| 最高成交價 | ${summary['max_price']:,} |",
        f"| 最低成交價 | ${summary['min_price']:,} |",
        "",
        "## 成交明細",
        "",
    ]

    if transactions:
        headers = detail_headers()
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["------"] * len(headers)) + " |")
        for tx in transactions:
            cells = [_format_md_cell(name, getter(tx)) for name, getter in TUEN_MUN_RECENT_DETAIL_COLUMNS]
            lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append("_報告期間內暫無成交記錄。_")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_md_cell(column: str, value: object) -> str:
    if value in (None, ""):
        return "-"
    return str(value)
