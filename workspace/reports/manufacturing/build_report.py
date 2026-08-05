#!/usr/bin/env python3
"""製造報告入口 — 從數據庫生成報告並寫入工作區進行中目錄。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.export_monthly_report import export_monthly_report  # noqa: E402


def main() -> None:
    report_path = export_monthly_report()
    print(f"✓ 報告已生成: {report_path}")
    print(f"  位置: workspace/reports/in_progress/")
    print(f"  歸檔: python run.py workspace archive {report_path.name}")


if __name__ == "__main__":
    main()
