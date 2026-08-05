import csv
from pathlib import Path

from src.database.connection import get_connection
from src.utils.blueprint import blueprint_version
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("load_tuen_mun", "database")

STANDARD_COLUMNS = [
    "estate_name",
    "block",
    "floor",
    "unit",
    "area_sqft",
    "price",
    "price_per_sqft",
    "transaction_date",
    "market_type",
    "source",
]


def load_tuen_mun(csv_path: Path, blueprint_name: str = "tuen_mun_v1.0.yaml") -> dict:
    bp_ver = blueprint_version("etl", blueprint_name)
    rows_imported = 0
    rows_skipped = 0

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with get_connection("tuen_mun") as conn:
        for row in rows:
            try:
                conn.execute(
                    """
                    INSERT INTO tuen_mun_transactions (
                        estate_name, block, floor, unit, area_sqft,
                        price, price_per_sqft, transaction_date,
                        market_type, source, blueprint_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["estate_name"],
                        row.get("block") or None,
                        row.get("floor") or None,
                        row.get("unit") or None,
                        float(row["area_sqft"]) if row.get("area_sqft") else None,
                        int(float(row["price"])),
                        float(row["price_per_sqft"]) if row.get("price_per_sqft") else None,
                        row["transaction_date"],
                        row.get("market_type") or "secondary",
                        row.get("source") or "unknown",
                        bp_ver,
                    ),
                )
                rows_imported += 1

                conn.execute(
                    """
                    INSERT OR IGNORE INTO tuen_mun_estates (estate_name, district)
                    VALUES (?, '屯門區')
                    """,
                    (row["estate_name"],),
                )
            except Exception as e:
                rows_skipped += 1
                log_event(
                    logger,
                    "warning",
                    "Skipped row",
                    error=str(e),
                    estate=row.get("estate_name"),
                )

        conn.execute(
            """
            INSERT INTO tuen_mun_import_log
                (file_name, rows_imported, rows_skipped, blueprint_version)
            VALUES (?, ?, ?, ?)
            """,
            (csv_path.name, rows_imported, rows_skipped, bp_ver),
        )

    archive_path = _archive_file(csv_path)
    result = {
        "file": csv_path.name,
        "rows_imported": rows_imported,
        "rows_skipped": rows_skipped,
        "archived_to": str(archive_path),
    }
    log_event(logger, "info", "Load complete", **result)
    return result


def _archive_file(csv_path: Path) -> Path:
    from datetime import datetime

    archive_dir = get_path("archive") / datetime.now().strftime("%Y-%m")
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / csv_path.name
    if not dest.exists():
        dest.write_bytes(csv_path.read_bytes())
    return dest


def query_transactions(limit: int = 10) -> list[dict]:
    with get_connection("tuen_mun") as conn:
        cursor = conn.execute(
            """
            SELECT estate_name, block, floor, price, transaction_date, price_per_sqft
            FROM tuen_mun_transactions
            ORDER BY transaction_date DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def query_transactions_by_date_range(start_date: str, end_date: str) -> list[dict]:
    with get_connection("tuen_mun") as conn:
        cursor = conn.execute(
            """
            SELECT
                estate_name, block, floor, unit, area_sqft,
                price, price_per_sqft, transaction_date, market_type, source
            FROM tuen_mun_transactions
            WHERE transaction_date >= ? AND transaction_date <= ?
            ORDER BY transaction_date DESC, estate_name
            """,
            (start_date, end_date),
        )
        return [dict(row) for row in cursor.fetchall()]
