-- DB-B: 全港成交趨勢（一手 & 二手）

CREATE TABLE IF NOT EXISTS trend_monthly (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period              TEXT NOT NULL,          -- YYYY-MM
    market_type         TEXT NOT NULL CHECK(market_type IN ('primary', 'secondary')),
    district            TEXT DEFAULT 'ALL',       -- 18 區之一或 ALL
    transaction_count   INTEGER NOT NULL,
    avg_price           REAL,
    median_price        REAL,
    total_volume        BIGINT,
    avg_price_per_sqft  REAL,
    price_change_pct    REAL,
    source              TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period, market_type, district)
);

CREATE TABLE IF NOT EXISTS trend_quarterly (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period              TEXT NOT NULL,          -- YYYY-Q1 ~ YYYY-Q4
    market_type         TEXT NOT NULL CHECK(market_type IN ('primary', 'secondary')),
    district            TEXT DEFAULT 'ALL',
    transaction_count   INTEGER NOT NULL,
    avg_price           REAL,
    median_price        REAL,
    total_volume        BIGINT,
    avg_price_per_sqft  REAL,
    price_change_pct    REAL,
    source              TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period, market_type, district)
);

CREATE TABLE IF NOT EXISTS trend_district_rank (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period              TEXT NOT NULL,
    market_type         TEXT NOT NULL,
    district            TEXT NOT NULL,
    rank_by_volume      INTEGER,
    rank_by_price_change INTEGER,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period, market_type, district)
);

CREATE INDEX IF NOT EXISTS idx_trend_monthly_period ON trend_monthly(period, market_type);
CREATE INDEX IF NOT EXISTS idx_trend_quarterly_period ON trend_quarterly(period, market_type);
