# 數據字典

> 定義系統中所有核心欄位。單位預設為港元（HKD）、平方呎（sqft），日期格式為 `YYYY-MM-DD`。

---

## DB-A：屯門成交（`tuen_mun_transactions`）

| 欄位 | 類型 | 必填 | 說明 | 示例 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | 主鍵，自動遞增 | 1 |
| `estate_name` | TEXT | ✓ | 屋苑名稱 | 青山灣 |
| `block` | TEXT | | 座數 | 1座 |
| `floor` | TEXT | | 樓層 | 12/F |
| `unit` | TEXT | | 單位 | A |
| `area_sqft` | REAL | | 實用面積（平方呎） | 520.0 |
| `price` | INTEGER | ✓ | 成交價（港元） | 4500000 |
| `price_per_sqft` | REAL | | 呎價（自動計算或來源提供） | 8653.85 |
| `transaction_date` | DATE | ✓ | 成交日期 | 2026-07-15 |
| `market_type` | TEXT | | 市場類型：`primary` / `secondary` | secondary |
| `source` | TEXT | ✓ | 數據來源 | centaline |
| `blueprint_version` | TEXT | | 入庫時使用嘅 ETL 藍圖版本 | etl_tuen_mun_v1.0 |
| `created_at` | DATETIME | ✓ | 入庫時間 | 2026-08-04 13:00:00 |

---

## DB-B：全港趨勢（`trend_monthly`）

| 欄位 | 類型 | 必填 | 說明 | 示例 |
|------|------|------|------|------|
| `id` | INTEGER | ✓ | 主鍵 | 1 |
| `period` | TEXT | ✓ | 統計月份 `YYYY-MM` | 2026-07 |
| `market_type` | TEXT | ✓ | `primary`（一手）/ `secondary`（二手） | secondary |
| `district` | TEXT | | 區域（18 區之一，全港則為 `ALL`） | 屯門區 |
| `transaction_count` | INTEGER | ✓ | 成交宗數 | 342 |
| `avg_price` | REAL | | 平均成交價 | 5200000.0 |
| `median_price` | REAL | | 中位數成交價 | 4800000.0 |
| `total_volume` | BIGINT | | 總成交額 | 1778400000 |
| `avg_price_per_sqft` | REAL | | 平均呎價 | 9200.0 |
| `price_change_pct` | REAL | | 環比變化（%） | 2.3 |
| `source` | TEXT | | 數據來源 | rvd |
| `created_at` | DATETIME | ✓ | 計算時間 | 2026-08-04 13:00:00 |

---

## 香港 18 區對照

| 代碼 | 區名 |
|------|------|
| CW | 中西區 |
| WC | 灣仔區 |
| E | 東區 |
| S | 南區 |
| YTM | 油尖旺區 |
| SSP | 深水埗區 |
| KC | 九龍城區 |
| WTS | 黃大仙區 |
| KT | 觀塘區 |
| TW | 荃灣區 |
| TM | 屯門區 |
| YL | 元朗區 |
| N | 北區 |
| TP | 大埔區 |
| ST | 沙田區 |
| SK | 西貢區 |
| KI | 葵青區 |
| IS | 離島區 |

---

## 市場類型定義

| 值 | 中文 | 說明 |
|----|------|------|
| `primary` | 一手 | 發展商首次出售 |
| `secondary` | 二手 | 市場上轉手交易 |
