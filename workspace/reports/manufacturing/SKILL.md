---
name: property-report-manufacturing
description: 製造香港物業成交追蹤系統報告。用於生成月度報告、整理進行中報告、歸檔保留報告。當用戶要求製作報告、輸出月度數據、或管理 workspace/reports 時使用。
---

# 物業報告製造

本 skill 指導如何喺 `workspace/reports/` 工作區製造同管理報告。

## 工作區結構

| 目錄 | 路徑 | 用途 |
|------|------|------|
| 進行中 | `workspace/reports/in_progress/` | 草稿、待審核報告 |
| 保留 | `workspace/reports/archived/` | 已確認嘅最終版本 |
| 製造 | `workspace/reports/manufacturing/` | 本 skill 同生成腳本 |

## 何時使用

- 用戶要求「製作報告」、「出月度報告」、「生成物業分析」
- 需要將報告由進行中移至保留
- 需要自訂報告內容或格式

## 製造報告步驟

### 1. 確保數據就緒

報告依賴已入庫嘅數據。如未執行 pipeline，先跑：

```bash
python run.py run-all
# 或分步：init → ingest → etl → validate → load → analyze
```

### 2. 生成報告

```bash
# 方式 A：CLI
python run.py report

# 方式 B：直接執行製造腳本
python workspace/reports/manufacturing/build_report.py
```

生成嘅 CSV 會寫入 `workspace/reports/in_progress/monthly_report_YYYY-MM-DD.csv`。

### 3. 檢視進行中報告

```bash
python run.py workspace list
```

### 4. 歸檔保留

確認報告無誤後：

```bash
python run.py workspace archive monthly_report_2026-08-05.csv
```

## 報告內容

月度報告包含：

1. **屯門區成交摘要** — 總宗數、平均價、平均呎價、日期範圍
2. **全港趨勢（月度）** — 一手/二手、各區成交宗數、均價、環比變化

數據來源：
- 屯門明細：`database/tuen_mun.db`
- 全港趨勢：`database/trends.db`

## 自訂報告

如需新增報告類型：

1. 喺 `workspace/reports/manufacturing/` 新增腳本（參考 `build_report.py`）
2. 輸出到 `in_progress/`，檔名格式：`{類型}_report_{YYYY-MM-DD}.csv`
3. 更新本 skill 嘅「報告內容」一節

## 命名規範

| 類型 | 格式 | 示例 |
|------|------|------|
| 月度報告 | `monthly_report_YYYY-MM-DD.csv` | `monthly_report_2026-08-05.csv` |
| 週報 | `weekly_report_YYYY-MM-DD.csv` | `weekly_report_2026-08-05.csv` |
| 自訂 | `{scope}_report_YYYY-MM-DD.csv` | `tuen_mun_report_2026-08-05.csv` |

## 注意事項

- 進行中同保留目錄嘅 `.csv` 唔入 git（見 `.gitignore`）
- 歸檔時如目標檔名已存在，會自動加 `_v2`、`_v3` 後綴
- 舊版 `output/reports/` 仍可用，但新報告預設寫入工作區
- **格式變更必須記錄** — 見 [FORMAT_CHANGELOG.md](FORMAT_CHANGELOG.md)
- 欄位定義以 `src/reporting/report_columns.py` 為準，**只可加不可減**

## 嚴格執行成交明細 13 欄

生成或匯報「屯門區最近成交報告」時，**必須**遵守：

1. **唯一權威**：`src/reporting/report_columns.py` 內 `TUEN_MUN_RECENT_DETAIL_HEADER_NAMES`（13 欄、順序固定）
2. **禁止手寫表頭**：用 `detail_headers()` / `detail_row()` 輸出；唔好喺 export、模板或對話入面自訂欄位
3. **CSV = Markdown**：兩種格式明細欄位必須完全一致
4. **出報告後驗證**：
   ```bash
   python workspace/reports/manufacturing/validate_report_format.py workspace/reports/in_progress/tuen_mun_recent_14d_YYYY-MM-DD.csv
   ```
5. **向用戶展示**：唔可以為咗簡短而縮減明細欄位；要完整 13 欄或請用戶開檔案
6. **改欄唯一途徑**：用戶明確要求 → 改 `report_columns.py` → 跑測試 → 更新 `FORMAT_CHANGELOG.md` 同 `REPORT_FORMAT.md`

完整格式表見 [REPORT_FORMAT.md](REPORT_FORMAT.md)。
