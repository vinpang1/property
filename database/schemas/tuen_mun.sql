-- DB-A: 屯門區成交明細

CREATE TABLE IF NOT EXISTS tuen_mun_estates (
    estate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    estate_name     TEXT NOT NULL UNIQUE,
    district        TEXT DEFAULT '屯門區',
    developer       TEXT,
    completion_year INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tuen_mun_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estate_name         TEXT NOT NULL,
    block               TEXT,
    floor               TEXT,
    unit                TEXT,
    area_sqft           REAL,
    price               INTEGER NOT NULL,
    price_per_sqft      REAL,
    transaction_date    DATE NOT NULL,
    market_type         TEXT CHECK(market_type IN ('primary', 'secondary')),
    source              TEXT NOT NULL,
    branch_name         TEXT,
    agent_name          TEXT,
    agent_phone         TEXT,
    blueprint_version   TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(estate_name, block, floor, unit, transaction_date, price)
);

CREATE TABLE IF NOT EXISTS tuen_mun_import_log (
    import_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name           TEXT NOT NULL,
    rows_imported       INTEGER,
    rows_skipped        INTEGER DEFAULT 0,
    blueprint_version   TEXT,
    imported_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tm_tx_date ON tuen_mun_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_tm_tx_estate ON tuen_mun_transactions(estate_name, transaction_date);
CREATE INDEX IF NOT EXISTS idx_tm_tx_price_sqft ON tuen_mun_transactions(price_per_sqft);
