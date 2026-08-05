"""Download Hong Kong-wide and Tuen Mun property transaction data for selected months."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.ingestion.centaline_client import UnitTransaction, fetch_transactions_for_months
from src.ingestion.landreg_client import MonthlySummary, fetch_monthly_summary
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("download_monthly", "ingestion")

MONTH_LABELS = {
    1: "一月",
    2: "二月",
    3: "三月",
    4: "四月",
    5: "五月",
    6: "六月",
    7: "七月",
    8: "八月",
    9: "九月",
    10: "十月",
    11: "十一月",
    12: "十二月",
}


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summary_to_row(summary: MonthlySummary) -> dict:
    return {
        "period": summary.period,
        "market_type": "all_residential",
        "district": "ALL",
        "transaction_count": summary.residential_count,
        "primary_count": summary.primary_count,
        "secondary_count": summary.secondary_count,
        "tuen_mun_count": summary.tuen_mun_count,
        "total_volume_million_hkd": summary.residential_volume_million,
        "source": "landreg",
        "source_url": summary.source_url,
    }


def download_hk_wide(months: list[int], year: int) -> tuple[list[Path], list[str]]:
    staging_dir = get_path("staging") / "primary"
    staging_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    saved: list[Path] = []
    notes: list[str] = []

    summaries: list[MonthlySummary] = []
    missing_months: list[int] = []

    for month in months:
        label = MONTH_LABELS.get(month, str(month))
        try:
            summary = fetch_monthly_summary(year, month)
            summaries.append(summary)
            log_event(
                logger,
                "info",
                "Land Registry monthly summary downloaded",
                period=summary.period,
                residential_count=summary.residential_count,
            )
        except FileNotFoundError:
            missing_months.append(month)
            notes.append(
                f"土地註冊處 {year} 年{label}官方數據尚未發布（通常於次月中旬更新）。"
            )
        except Exception as exc:
            notes.append(f"土地註冊處 {year} 年{label}下載失敗：{exc}")

    if missing_months and year == date.today().year:
        fallback_year = year - 1
        recovered: list[MonthlySummary] = []
        for month in missing_months:
            label = MONTH_LABELS.get(month, str(month))
            try:
                summary = fetch_monthly_summary(fallback_year, month)
                recovered.append(summary)
                notes.append(
                    f"已改為下載 {fallback_year} 年{label}官方數據：住宅成交 {summary.residential_count:,} 宗。"
                )
            except Exception:
                pass
        summaries.extend(recovered)

    if summaries:
        periods = sorted({summary.period for summary in summaries})
        month_tag = "-".join(period.split("-")[1] for period in periods)
        data_years = sorted({summary.year for summary in summaries})
        year_tag = data_years[0] if len(data_years) == 1 else f"{data_years[0]}-{data_years[-1]}"
        output_path = staging_dir / f"{today}_landreg_hk_wide_{year_tag}_{month_tag}.csv"
        rows = [_summary_to_row(summary) for summary in summaries]
        fieldnames = list(rows[0].keys())
        _write_csv(output_path, rows, fieldnames)
        saved.append(output_path)

        raw_dir = get_path("downloads") / "landreg"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for summary in summaries:
            raw_path = raw_dir / f"{summary.period}_summary.json"
            raw_path.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
            saved.append(raw_path)

    return saved, notes


def download_tuen_mun_units(months: list[int], year: int) -> tuple[Path | None, list[str], int]:
    staging_dir = get_path("staging") / "tuen_mun"
    staging_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    notes: list[str] = []

    day_window = "Day90" if year == date.today().year else "Day1095"
    transactions = fetch_transactions_for_months(
        year=year,
        months=months,
        keyword="屯門",
        day=day_window,
        request_interval_seconds=0.5,
    )

    if not transactions:
        notes.append(f"中原地產未找到 {year} 年指定月份的屯門成交紀錄。")
        return None, notes, 0

    month_tag = "-".join(f"{month:02d}" for month in months)
    output_path = staging_dir / f"{today}_centaline_tuen_mun_{year}_{month_tag}.csv"
    rows = [tx.to_csv_row() for tx in transactions]
    fieldnames = list(rows[0].keys())
    _write_csv(output_path, rows, fieldnames)

    export_dir = get_path("output") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"tuen_mun_transactions_{year}_{month_tag}.csv"
    _write_csv(export_path, rows, fieldnames)

    by_month: dict[str, int] = {}
    for tx in transactions:
        key = tx.transaction_date[:7]
        by_month[key] = by_month.get(key, 0) + 1

    log_event(
        logger,
        "info",
        "Tuen Mun unit transactions downloaded",
        file=str(output_path),
        rows=len(transactions),
        by_month=by_month,
    )
    notes.append(
        "屯門單位成交按月統計："
        + "；".join(f"{period} {count} 宗" for period, count in sorted(by_month.items()))
    )
    return output_path, notes, len(transactions)


def download_monthly_data(months: list[int], year: int | None = None) -> dict:
    year = year or date.today().year
    hk_files, hk_notes = download_hk_wide(months, year)
    tuen_mun_file, tuen_mun_notes, tuen_mun_count = download_tuen_mun_units(months, year)

    result = {
        "year": year,
        "months": months,
        "hk_wide_files": [str(path) for path in hk_files],
        "tuen_mun_file": str(tuen_mun_file) if tuen_mun_file else None,
        "tuen_mun_count": tuen_mun_count,
        "notes": hk_notes + tuen_mun_notes,
    }

    summary_path = get_path("output") / "exports" / f"download_summary_{year}_{'-'.join(f'{m:02d}' for m in months)}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["summary_file"] = str(summary_path)
    return result
