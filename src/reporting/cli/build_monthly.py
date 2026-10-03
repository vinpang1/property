"""製造月度報告 — 從數據庫生成報告並寫入工作區進行中目錄。"""

from src.reporting.export_monthly_report import export_monthly_report


def main() -> None:
    report_path = export_monthly_report()
    print(f"✓ 報告已生成: {report_path}")
    print("  位置: workspace/reports/in_progress/")
    print(f"  歸檔: python run.py workspace archive {report_path.name}")


if __name__ == "__main__":
    main()
