#!/usr/bin/env python3
"""製造屯門區最近 N 日成交報告。"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.export_tuen_mun_recent_report import export_tuen_mun_recent_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="屯門區最近成交報告")
    parser.add_argument("--days", type=int, default=14, help="回溯日數（預設 14 日）")
    args = parser.parse_args()

    report_path = export_tuen_mun_recent_report(days=args.days)
    md_path = report_path.with_suffix(".md")
    print(f"✓ 報告已生成:")
    print(f"  CSV: {report_path}")
    print(f"  MD:  {md_path}")
    print(f"  歸檔: python run.py workspace archive {report_path.name}")


if __name__ == "__main__":
    main()
