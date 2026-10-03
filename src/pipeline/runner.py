"""Run the full pipeline — stage order unchanged."""

from __future__ import annotations

import argparse

from src.pipeline import stages


def run_all(_args: argparse.Namespace | None = None) -> None:
    print("=" * 50)
    print("香港物業成交追蹤系統 — 完整 Pipeline")
    print("=" * 50)

    stages.init()
    print()

    args_ingest = argparse.Namespace(source="all", provider="sample", generate=False)
    stages.ingest(args_ingest)
    print()

    stages.etl()
    print()

    stages.validate()
    print()

    stages.load()
    print()

    stages.analyze()
    print()

    stages.report()
    print()

    print("=" * 50)
    stages.print_recent_transactions(5)
    print("=" * 50)
    print("✓ Pipeline 執行完成")
