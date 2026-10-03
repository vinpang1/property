import csv
import statistics
from pathlib import Path

from src.database.load_trends import upsert_monthly_trend
from src.database.connection import get_connection
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("calc_price_trend", "etl")


def calc_tuen_mun_trends() -> list[dict]:
    with get_connection("tuen_mun") as conn:
        cursor = conn.execute(
            """
            SELECT
                strftime('%Y-%m', transaction_date) AS period,
                market_type,
                COUNT(*) AS transaction_count,
                AVG(price) AS avg_price,
                SUM(price) AS total_volume,
                AVG(price_per_sqft) AS avg_price_per_sqft
            FROM tuen_mun_transactions
            GROUP BY period, market_type
            ORDER BY period
            """
        )
        groups = cursor.fetchall()

    results = []
    prev_avg: dict[str, float] = {}

    with get_connection("tuen_mun") as conn:
        for group in groups:
            period = group["period"]
            market_type = group["market_type"] or "secondary"

            prices_cursor = conn.execute(
                """
                SELECT price FROM tuen_mun_transactions
                WHERE strftime('%Y-%m', transaction_date) = ?
                  AND COALESCE(market_type, 'secondary') = ?
                ORDER BY price
                """,
                (period, market_type),
            )
            prices = [row["price"] for row in prices_cursor.fetchall()]
            median_price = statistics.median(prices) if prices else 0

            avg_price = group["avg_price"] or 0
            key = market_type
            price_change_pct = None
            if key in prev_avg and prev_avg[key]:
                price_change_pct = round((avg_price - prev_avg[key]) / prev_avg[key] * 100, 2)
            prev_avg[key] = avg_price

            upsert_monthly_trend(
                period=period,
                market_type=market_type,
                district="屯門區",
                transaction_count=group["transaction_count"],
                avg_price=round(avg_price, 2),
                median_price=round(median_price, 2),
                total_volume=int(group["total_volume"] or 0),
                avg_price_per_sqft=round(group["avg_price_per_sqft"] or 0, 2),
                price_change_pct=price_change_pct,
                source="tuen_mun_analysis",
            )
            results.append(
                {
                    "period": period,
                    "market_type": market_type,
                    "district": "屯門區",
                    "transaction_count": group["transaction_count"],
                    "avg_price": round(avg_price, 2),
                }
            )

    log_event(logger, "info", "Tuen Mun trends calculated", periods=len(results))
    return results


def load_staging_trends() -> int:
    count = 0
    for subdir in ("primary", "secondary"):
        staging_dir = get_path("staging") / subdir
        for csv_path in staging_dir.glob("*.csv"):
            count += _load_trend_csv(csv_path)
    return count


def _load_trend_csv(csv_path: Path) -> int:
    loaded = 0
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            upsert_monthly_trend(
                period=row["period"],
                market_type=row["market_type"],
                district=row.get("district") or "ALL",
                transaction_count=int(row["transaction_count"]),
                avg_price=float(row["avg_price"]),
                median_price=float(row["median_price"]),
                total_volume=int(float(row["total_volume"])),
                avg_price_per_sqft=float(row["avg_price_per_sqft"]),
                source=csv_path.stem,
            )
            loaded += 1
    log_event(logger, "info", "Trend CSV loaded", file=csv_path.name, rows=loaded)
    return loaded
