"""報告欄位定義 — CSV 同 Markdown 必須一致，只可加不可減。"""

from typing import Callable

from pathlib import Path

FORMAT_VERSION = "v8"

# 屯門區最近成交報告 — 成交明細欄位數（硬性規定，改欄必須同步更新測試同 FORMAT_CHANGELOG）
TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT = 13

# 權威欄位名稱（順序固定）；改動必須更新 FORMAT_CHANGELOG.md 同 REPORT_FORMAT.md
TUEN_MUN_RECENT_DETAIL_HEADER_NAMES: tuple[str, ...] = (
    "簽臨約日期",
    "地址",
    "屋苑",
    "座數",
    "樓層",
    "單位",
    "成交類型",
    "成交階段",
    "市場類型",
    "分行",
    "代理",
    "代理電話",
    "數據來源",
)


class ReportFormatError(ValueError):
    """報告欄位唔符合 report_columns.py 權威定義。"""


def format_address(tx: dict, district: str = "屯門區") -> str:
    """組合完整地址：區域 + 屋苑 + 座數 + 樓層 + 單位。"""
    estate = tx.get("estate_name")
    parts = [district, estate]
    block = tx.get("block")
    if block and block != estate:
        parts.append(str(block))
    for key in ("floor", "unit"):
        value = tx.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


from src.ingestion.transaction_stage import display_deal_type


def _display_market_type(value: str) -> str:
    return {"primary": "一手", "secondary": "二手"}.get(value, value or "")


# 屯門區最近成交報告 — 成交明細欄位（權威定義）
TUEN_MUN_RECENT_DETAIL_COLUMNS: list[tuple[str, Callable[[dict], object]]] = [
    ("簽臨約日期", lambda tx: tx.get("pasp_date") or tx["transaction_date"]),
    ("地址", lambda tx: format_address(tx)),
    ("屋苑", lambda tx: tx["estate_name"]),
    ("座數", lambda tx: tx.get("block") or ""),
    ("樓層", lambda tx: tx.get("floor") or ""),
    ("單位", lambda tx: tx.get("unit") or ""),
    ("成交類型", lambda tx: display_deal_type(tx.get("deal_type") or "sale")),
    ("成交階段", lambda tx: tx.get("transaction_stage") or "未知"),
    ("市場類型", lambda tx: _display_market_type(tx.get("market_type") or "")),
    ("分行", lambda tx: tx.get("branch_name") or ""),
    ("代理", lambda tx: tx.get("agent_name") or ""),
    ("代理電話", lambda tx: tx.get("agent_phone") or ""),
    ("數據來源", lambda tx: tx.get("source") or ""),
]

if [name for name, _ in TUEN_MUN_RECENT_DETAIL_COLUMNS] != list(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES):
    raise ReportFormatError("TUEN_MUN_RECENT_DETAIL_COLUMNS 同 TUEN_MUN_RECENT_DETAIL_HEADER_NAMES 不一致")


def detail_headers() -> list[str]:
    headers = [name for name, _ in TUEN_MUN_RECENT_DETAIL_COLUMNS]
    validate_detail_headers(headers)
    return headers


def detail_row(tx: dict) -> list[object]:
    row = [getter(tx) for _, getter in TUEN_MUN_RECENT_DETAIL_COLUMNS]
    validate_detail_row(row)
    return row


def validate_detail_headers(headers: list[str] | tuple[str, ...]) -> None:
    """確保表頭同權威定義完全一致（13 欄、順序固定）。"""
    if list(headers) != list(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES):
        raise ReportFormatError(
            "成交明細表頭必須為 13 欄且順序固定："
            + "、".join(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES)
        )


def validate_detail_row(row: list[object] | tuple[object, ...]) -> None:
    """確保每行明細欄位數量正確。"""
    if len(row) != TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT:
        raise ReportFormatError(
            f"成交明細每行必須為 {TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT} 欄，"
            f"實際為 {len(row)} 欄"
        )


def validate_exported_csv_detail(path: Path) -> None:
    """驗證已輸出 CSV 嘅成交明細區符合 13 欄格式。"""
    import csv

    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if row and row[0] == TUEN_MUN_RECENT_DETAIL_HEADER_NAMES[0]:
                validate_detail_headers(row)
                return
    raise ReportFormatError(f"CSV 找不到成交明細表頭：{path}")


def validate_exported_markdown_detail(path: Path) -> None:
    """驗證已輸出 Markdown 嘅成交明細表符合 13 欄格式。"""
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(f"| {TUEN_MUN_RECENT_DETAIL_HEADER_NAMES[0]}"):
            headers = [cell.strip() for cell in line.split("|")[1:-1]]
            validate_detail_headers(headers)
            return
    raise ReportFormatError(f"Markdown 找不到成交明細表頭：{path}")
