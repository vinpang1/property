# 香港物業成交追蹤系統

追蹤香港物業成交數據，涵蓋屯門區明細成交同全港一手／二手趨勢。

## 系統架構

| 區域 | 路徑 | 說明 |
|------|------|------|
| 1. 數據採集 | `data/`, `logs/` | 暫存 CSV、下載、系統 log |
| 2. Python 區 | `src/` | 採集、ETL、驗證、入庫、分析 |
| 3. 版本藍圖 | `blueprints/` | 唔同情況嘅規則版本 |
| 4. Database | `database/` | 屯門明細 DB + 全港趨勢 DB |
| 5. 配置管理 | `config/` | 全局設定、數據源、區域對照 |
| 6. 排程 | `schedules/` | 定時自動化任務 |
| 7. 測試 | `tests/` | 單元 & 整合測試 |
| 8. 輸出 | `output/` | 報表、圖表、導出 |

詳細藍圖請睇 [docs/BLUEPRINT.md](docs/BLUEPRINT.md)。

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 複製環境變數
cp .env.example .env

# 初始化數據庫
sqlite3 database/tuen_mun.db < database/schemas/tuen_mun.sql
sqlite3 database/trends.db < database/schemas/trends.sql
```

## 文檔

- [整體藍圖](docs/BLUEPRINT.md)
- [數據字典](docs/DATA_DICTIONARY.md)
- [數據源說明](docs/SOURCES.md)

## 實施進度

- [x] 目錄結構 & 藍圖規劃
- [ ] Phase 1：基礎建設（配置、Log、DB schema）
- [ ] Phase 2：屯門區 MVP
- [ ] Phase 3：全港趨勢
- [ ] Phase 4：自動化 & 品質監控
- [ ] Phase 5：擴展至其他區
