#!/usr/bin/env python3
"""驗證屯門最近成交報告是否符合 13 欄格式。"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.report_columns import (  # noqa: E402
    TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT,
    TUEN_MUN_RECENT_DETAIL_HEADER_NAMES,
    ReportFormatError,
    validate_exported_csv_detail,
    validate_exported_markdown_detail,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="驗證報告成交明細 13 欄格式")
    parser.add_argument("path", type=Path, help="報告 CSV 或 Markdown 路徑")
    args = parser.parse_args()

    path = args.path
    if not path.exists():
        print(f"✗ 找不到檔案: {path}")
        sys.exit(1)

    try:
        if path.suffix.lower() == ".csv":
            validate_exported_csv_detail(path)
        elif path.suffix.lower() == ".md":
            validate_exported_markdown_detail(path)
        else:
            print("✗ 只支援 .csv 或 .md")
            sys.exit(1)
    except ReportFormatError as exc:
        print(f"✗ 格式驗證失敗: {exc}")
        sys.exit(1)

    print(f"✓ 成交明細符合 {TUEN_MUN_RECENT_DETAIL_COLUMN_COUNT} 欄格式")
    print("  " + " | ".join(TUEN_MUN_RECENT_DETAIL_HEADER_NAMES))


if __name__ == "__main__":
    main()
