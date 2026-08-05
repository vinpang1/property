"""Download Hong Kong-wide and Tuen Mun property transaction data."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.ingestion.centaline_client import fetch_tuen_mun_transactions as fetch_centaline
from src.ingestion.landreg_client import MonthlySummary, fetch_latest_months
from src.ingestion.midland_client import fetch_tuen_mun_transactions as fetch_midland
from src.ingestion.manyw_client import fetch_tuen_mun_transactions as fetch_manyw
from src.ingestion.models import UnitTransaction
from src.ingestion.news_review import collect_tuen_mun_news_review, write_news_review
from src.ingestion.ricacorp_client import fetch_tuen_mun_transactions as fetch_ricacorp
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("download_monthly", "ingestion")

TUEN_MUN_SOURCES = {
    "centaline": ("中原地產", fetch_centaline),
    "midland": ("美聯物業", fetch_midland),
    "ricacorp": ("利嘉閣", fetch_ricacorp),
    "manyw": ("祥益地產", fetch_manyw),
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


def download_hk_wide_latest(months: int = 6) -> tuple[list[Path], list[str]]:
    staging_dir = get_path("staging") / "primary"
    staging_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    saved: list[Path] = []
    notes: list[str] = []

    summaries = fetch_latest_months(months)
    if not summaries:
        notes.append(f"土地註冊處最近 {months} 個月官方數據暫未發布。")
        return saved, notes

    periods = [summary.period for summary in summaries]
    month_tag = f"{periods[0].split('-')[1]}-{periods[-1].split('-')[1]}"
    year_tag = f"{periods[0].split('-')[0]}-{periods[-1].split('-')[0]}"
    output_path = staging_dir / f"{today}_landreg_hk_wide_latest_{months}m_{year_tag}_{month_tag}.csv"
    rows = [_summary_to_row(summary) for summary in summaries]
    _write_csv(output_path, rows, list(rows[0].keys()))
    saved.append(output_path)

    raw_dir = get_path("downloads") / "landreg"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for summary in summaries:
        raw_path = raw_dir / f"{summary.period}_summary.json"
        raw_path.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
        saved.append(raw_path)

    notes.append(
        "全港住宅成交（土地註冊處）："
        + "；".join(f"{summary.period} {summary.residential_count:,} 宗" for summary in summaries)
    )
    log_event(logger, "info", "HK-wide latest months downloaded", months=months, rows=len(summaries))
    return saved, notes


def _merge_transactions(transactions: list[UnitTransaction]) -> list[UnitTransaction]:
    seen: set[tuple] = set()
    merged: list[UnitTransaction] = []
    for tx in transactions:
        key = (
            tx.estate_name,
            tx.block,
            tx.floor,
            tx.unit,
            tx.transaction_date,
            tx.price,
            tx.source,
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(tx)
    merged.sort(key=lambda item: item.transaction_date, reverse=True)
    return merged


def download_tuen_mun_multi_source(months_back: int = 6) -> tuple[dict[str, Path], list[str], int]:
    staging_dir = get_path("staging") / "tuen_mun"
    export_dir = get_path("output") / "exports"
    staging_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    notes: list[str] = []
    source_files: dict[str, Path] = {}
    all_transactions: list[UnitTransaction] = []

    for source_id, (label, fetcher) in TUEN_MUN_SOURCES.items():
        try:
            transactions = fetcher(months_back=months_back)
            if not transactions:
                notes.append(f"{label}：最近 {months_back} 個月未找到屯門成交紀錄。")
                continue

            output_path = staging_dir / f"{today}_{source_id}_tuen_mun_latest_{months_back}m.csv"
            rows = [tx.to_csv_row() for tx in transactions]
            _write_csv(output_path, rows, list(rows[0].keys()))
            source_files[source_id] = output_path
            all_transactions.extend(transactions)

            with_agent = sum(1 for tx in transactions if tx.agent_name)
            by_month = Counter(tx.transaction_date[:7] for tx in transactions)
            notes.append(
                f"{label}：{len(transactions)} 宗（"
                + "；".join(f"{period} {count} 宗" for period, count in sorted(by_month.items()))
                + f"），含代理資料 {with_agent} 宗"
            )
            log_event(
                logger,
                "info",
                "Tuen Mun source downloaded",
                source=source_id,
                rows=len(transactions),
            )
        except Exception as exc:
            notes.append(f"{label} 下載失敗：{exc}")

    merged = _merge_transactions(all_transactions)
    merged_path = export_dir / f"tuen_mun_transactions_latest_{months_back}m.csv"
    if merged:
        rows = [tx.to_csv_row() for tx in merged]
        _write_csv(merged_path, rows, list(rows[0].keys()))
        source_files["merged"] = merged_path

    news_path = export_dir / f"tuen_mun_news_review_{today}.json"
    articles = collect_tuen_mun_news_review()
    write_news_review(str(news_path), articles)
    source_files["news_review"] = news_path
    notes.append(f"新聞 Review：已整理 {len(articles)} 則屯門相關報導／快訊。")

    return source_files, notes, len(merged)


def download_monthly_data(months_back: int = 6) -> dict:
    hk_files, hk_notes = download_hk_wide_latest(months_back)
    tuen_mun_files, tuen_mun_notes, tuen_mun_count = download_tuen_mun_multi_source(months_back)

    result = {
        "months_back": months_back,
        "hk_wide_files": [str(path) for path in hk_files],
        "tuen_mun_files": {key: str(path) for key, path in tuen_mun_files.items()},
        "tuen_mun_count": tuen_mun_count,
        "notes": hk_notes + tuen_mun_notes,
    }

    summary_path = get_path("output") / "exports" / f"download_summary_latest_{months_back}m.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["summary_file"] = str(summary_path)
    return result
