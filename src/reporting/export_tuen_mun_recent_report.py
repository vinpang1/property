import csv
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from src.database.load_tuen_mun import query_transactions_by_date_range
from src.reporting.report_columns import (
    FORMAT_VERSION,
    TUEN_MUN_RECENT_DETAIL_COLUMNS,
    detail_headers,
    detail_row,
    validate_exported_csv_detail,
    validate_exported_markdown_detail,
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

    _write_csv(report_path, days, start_str, end_str, today, summary, transactions)

    md_path = report_path.with_suffix(".md")
    _write_markdown(md_path, days, start_str, end_str, today, summary, transactions)

    validate_exported_csv_detail(report_path)
    validate_exported_markdown_detail(md_path)

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
            "by_stage": {},
            "by_source": {},
            "by_market": {},
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
        "by_stage": dict(Counter(tx.get("transaction_stage") or "未知" for tx in transactions)),
        "by_source": dict(Counter(tx.get("source") or "未知" for tx in transactions)),
        "by_market": dict(
            Counter(
                {"primary": "一手", "secondary": "二手"}.get(tx.get("market_type") or "", "未知")
                for tx in transactions
            )
        ),
    }


def _write_csv(
    path: Path,
    days: int,
    start_str: str,
    end_str: str,
    today: str,
    summary: dict,
    transactions: list[dict],
) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["# 屯門區最近成交報告"])
        writer.writerow([f"# 格式版本: {FORMAT_VERSION}"])
        writer.writerow([f"# 報告期間: {start_str} 至 {end_str}（簽臨約日期）"])
        writer.writerow([f"# 生成日期: {today}"])
        writer.writerow([f"# 狀態: 進行中"])
        writer.writerow([])

        writer.writerow(["## 採集規則"])
        writer.writerow(["只計買賣", "租盤唔入庫"])
        writer.writerow(["報告日期", "以簽臨時買賣合約日期為準"])
        writer.writerow(["成交階段", "臨約（代理公布）或 土地註冊（已入冊）"])
        writer.writerow([])

        writer.writerow(["## 摘要"])
        writer.writerow(["成交宗數", summary["count"]])
        writer.writerow(["總成交額", summary["total_volume"]])
        writer.writerow(["平均成交價", summary["avg_price"]])
        writer.writerow(["平均呎價", summary["avg_price_per_sqft"]])
        writer.writerow(["最高成交價", summary["max_price"]])
        writer.writerow(["最低成交價", summary["min_price"]])
        for stage, count in sorted(summary["by_stage"].items()):
            writer.writerow([f"成交階段｜{stage}", count])
        for source, count in sorted(summary["by_source"].items()):
            writer.writerow([f"數據來源｜{source}", count])
        writer.writerow([])

        writer.writerow(["## 成交明細"])
        writer.writerow(detail_headers())
        for tx in transactions:
            writer.writerow(detail_row(tx))


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
        "# 屯門區最近成交報告",
        "",
        "## 報告基本資料",
        "",
        "| 項目 | 內容 |",
        "|------|------|",
        "| 報告名稱 | 屯門區最近成交報告 |",
        f"| 報告期間 | {start_str} 至 {end_str}（簽臨約日期） |",
        f"| 回溯日數 | 最近 {days} 日 |",
        f"| 生成日期 | {today} |",
        f"| 格式版本 | {FORMAT_VERSION} |",
        "| 狀態 | 進行中 |",
        "",
        "## 採集規則",
        "",
        "| 規則 | 說明 |",
        "|------|------|",
        "| 只計買賣 | 租盤唔入庫 |",
        "| 報告日期 | 以簽臨時買賣合約日期為準，唔用土地註冊日／成交日 |",
        "| 成交階段 | 臨約（代理公布）或 土地註冊（已入冊） |",
        "| 數據來源 | 中原／美聯等平台 |",
        "",
        "## 摘要",
        "",
        "### 成交統計",
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
        "### 分佈",
        "",
        "| 維度 | 分佈 |",
        "|------|------|",
        f"| 成交階段 | {_format_breakdown(summary['by_stage'])} |",
        f"| 數據來源 | {_format_breakdown(summary['by_source'])} |",
        f"| 市場類型 | {_format_breakdown(summary['by_market'])} |",
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


def _format_breakdown(counter: dict[str, int]) -> str:
    if not counter:
        return "-"
    return "、".join(f"{name} {count} 宗" for name, count in sorted(counter.items(), key=lambda item: -item[1]))


def _format_md_cell(column: str, value: object) -> str:
    if value in (None, ""):
        return "-"
    return str(value)
