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

# 一鍵執行完整 pipeline（初始化 → 採集 → 清洗 → 驗證 → 入庫 → 分析 → 報告）
python run.py run-all
```

### 分步執行

```bash
python run.py init          # 初始化數據庫
python run.py ingest          # 採集數據（屯門 + 全港一手/二手）
python run.py etl             # 清洗屯門成交數據
python run.py validate        # 驗證數據品質
python run.py load            # 入庫
python run.py analyze         # 計算趨勢
python run.py report          # 輸出月度報告
```

### 測試

```bash
pytest tests/ -v
```

## 文檔

- [整體藍圖](docs/BLUEPRINT.md)
- [數據字典](docs/DATA_DICTIONARY.md)
- [數據源說明](docs/SOURCES.md)

## 實施進度

- [x] 目錄結構 & 藍圖規劃
- [x] Phase 1：基礎建設（配置、Log、DB schema）
- [x] Phase 2：屯門區 MVP（採集 → 入庫 pipeline）
- [x] Phase 3：全港趨勢（一手/二手樣本數據 + 趨勢入庫）
- [ ] Phase 4：自動化 & 品質監控
- [ ] Phase 5：擴展至其他區
