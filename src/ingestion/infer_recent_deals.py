"""Fetch recent Tuen Mun deals and infer agents from listings and news."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from src.ingestion.agent_inference import infer_agents_for_transactions
from src.ingestion.listing_index import build_listing_index
from src.ingestion.models import UnitTransaction
from src.ingestion.news_review import collect_tuen_mun_news_review
from src.ingestion.news_transactions import collect_news_transaction_clues
from src.ingestion.providers.registry import fetch_recent_transactions as fetch_from_providers
from src.utils.config import get_path


def fetch_recent_transactions(*, days_back: int, enrich_agents: bool) -> list[UnitTransaction]:
    """Collect recent Tuen Mun transactions from enabled ingestion providers."""
    return fetch_from_providers(days_back=days_back, enrich_agents=enrich_agents)


def export_recent_deals_with_inference(
    *,
    days_back: int = 14,
    enrich_direct_agents: bool = True,
) -> tuple[Path, list[UnitTransaction], dict]:
    transactions = fetch_recent_transactions(days_back=days_back, enrich_agents=enrich_direct_agents)
    listings = build_listing_index(keyword="屯門", max_centaline_pages=3, max_midland_pages=5)
    news_articles = collect_tuen_mun_news_review(limit_per_source=15)
    news_clues = collect_news_transaction_clues(news_articles)
    transactions = infer_agents_for_transactions(
        transactions,
        listings=listings,
        news_clues=news_clues,
    )

    export_dir = get_path("output") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    output_path = export_dir / f"tuen_mun_deals_inferred_{days_back}d_{today}.csv"

    if transactions:
        rows = [tx.to_csv_row() for tx in transactions]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    stats = {
        "total": len(transactions),
        "with_agent": sum(1 for tx in transactions if tx.agent_name),
        "direct_agent": sum(1 for tx in transactions if tx.agent_name and not tx.inference_source),
        "inferred_agent": sum(1 for tx in transactions if tx.inference_source),
        "listing_count": len(listings),
        "news_clues": len(news_clues),
    }
    return output_path, transactions, stats
