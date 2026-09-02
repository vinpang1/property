from src.database.connection import get_connection
from src.utils.logger import get_logger, log_event

logger = get_logger("load_trends", "database")


def upsert_monthly_trend(
    period: str,
    market_type: str,
    district: str,
    transaction_count: int,
    avg_price: float,
    median_price: float,
    total_volume: int,
    avg_price_per_sqft: float,
    price_change_pct: float | None = None,
    source: str = "analysis",
) -> None:
    with get_connection("trends") as conn:
        conn.execute(
            """
            INSERT INTO trend_monthly (
                period, market_type, district, transaction_count,
                avg_price, median_price, total_volume,
                avg_price_per_sqft, price_change_pct, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(period, market_type, district) DO UPDATE SET
                transaction_count = excluded.transaction_count,
                avg_price = excluded.avg_price,
                median_price = excluded.median_price,
                total_volume = excluded.total_volume,
                avg_price_per_sqft = excluded.avg_price_per_sqft,
                price_change_pct = excluded.price_change_pct,
                source = excluded.source,
                created_at = CURRENT_TIMESTAMP
            """,
            (
                period,
                market_type,
                district,
                transaction_count,
                avg_price,
                median_price,
                total_volume,
                avg_price_per_sqft,
                price_change_pct,
                source,
            ),
        )

    log_event(
        logger,
        "info",
        "Trend upserted",
        period=period,
        market_type=market_type,
        district=district,
        count=transaction_count,
    )


def query_trends(market_type: str | None = None, limit: int = 12) -> list[dict]:
    with get_connection("trends") as conn:
        if market_type:
            cursor = conn.execute(
                """
                SELECT * FROM trend_monthly
                WHERE market_type = ?
                ORDER BY period DESC
                LIMIT ?
                """,
                (market_type, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM trend_monthly
                ORDER BY period DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]
