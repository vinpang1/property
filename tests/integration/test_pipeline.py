import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import init_database, get_connection
from src.ingestion.download_tuen_mun import download_tuen_mun
from src.etl.clean_tuen_mun import clean_tuen_mun
from src.validation.validate_schema import validate_tuen_mun
from src.database.load_tuen_mun import load_tuen_mun


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "database"
    db_dir.mkdir()

    def _get_db_path(name: str):
        return db_dir / f"{name}.db"

    monkeypatch.setattr("src.utils.config.get_db_path", _get_db_path)
    monkeypatch.setattr("src.database.connection.get_db_path", _get_db_path)
    init_database("tuen_mun", "tuen_mun.sql")
    init_database("trends", "trends.sql")
    yield


def test_full_pipeline():
    staging = download_tuen_mun(provider="test", use_seed=True)
    assert staging.exists()

    processed = clean_tuen_mun(staging)
    assert processed.exists()

    result = validate_tuen_mun(processed)
    assert result["passed"]
    assert result["valid_rows"] > 0

    load_result = load_tuen_mun(processed)
    assert load_result["rows_imported"] > 0

    with get_connection("tuen_mun") as conn:
        count = conn.execute("SELECT COUNT(*) FROM tuen_mun_transactions").fetchone()[0]
        assert count == load_result["rows_imported"]
