# 屯門區最近成交報告 — 格式表格

> 權威格式定義（v8）。程式定義：`src/reporting/report_columns.py`  
> 變更記錄：`FORMAT_CHANGELOG.md`

---

## 報告基本資料

| 項目 | 內容 |
|------|------|
| 報告名稱 | 屯門區最近成交報告 |
| 檔名格式 | `tuen_mun_recent_{日數}d_{YYYY-MM-DD}.csv` / `.md` |
| 輸出位置 | `workspace/reports/in_progress/` |
| 製造指令 | `python workspace/reports/manufacturing/build_tuen_mun_recent_report.py --days 14` |
| 採集 + 報告 | `python workspace/reports/manufacturing/fetch_recent_and_report.py --days 14` |
| 格式版本 | **v8** |

---

## 採集規則

| 規則 | 說明 |
|------|------|
| **只計買賣** | API 只採集 `tx_type=S` / `postType=S`，租盤唔入庫 |
| **成交類型** | 報告顯示「買賣」，唔會出現「租」 |
| **成交階段** | 臨約（代理公布）或 土地註冊（已入冊） |
| **報告日期** | 以簽臨時買賣合約日期（臨約日）為準，唔用土地註冊日／成交日 |

---

## 報告結構

| 區塊 | 說明 |
|------|------|
| 報告基本資料 | 報告名稱、期間、生成日期、格式版本、狀態 |
| 採集規則 | 買賣篩選、臨約日定義、成交階段、數據來源 |
| 摘要 | 成交統計 + 分佈（成交階段、數據來源、市場類型） |
| 成交明細 | 13 欄明細表（CSV 同 Markdown 一致） |

---

## 成交明細區（13 欄）

| # | 欄位 | 說明 | 示例 |
|---|------|------|------|
| 1 | 簽臨約日期 | 簽臨時買賣合約日期（YYYY-MM-DD） | 2026-07-24 |
| 2 | 地址 | 屯門區 + 屋苑 + 座數 + 樓層 + 單位 | 屯門區 青山灣 1座 8/F A |
| 3 | 屋苑 | 屋苑名稱 | 青山灣 |
| 4 | 座數 | 座 | 1座 |
| 5 | 樓層 | 樓層 | 8/F |
| 6 | 單位 | 單位 | A |
| 7 | 成交類型 | 買賣（租盤唔計） | 買賣 |
| 8 | 成交階段 | 臨約 / 土地註冊 | 土地註冊 |
| 9 | 市場類型 | 一手 / 二手 | 二手 |
| 10 | 分行 | 分行名稱 | 屯門青山灣分行 |
| 11 | 代理 | 代理名稱 | 陳大文 |
| 12 | 代理電話 | 聯絡電話 | 9123-4567 |
| 13 | 數據來源 | 採集平台 | 中原 |

### 明細區唔包含

| 欄位 | 原因 |
|------|------|
| 租賃成交 | 只計買賣，租盤唔入庫（v7） |
| 實用面積(呎) | 用戶明確唔需要（v5 移除） |
| 成交價 | 用戶明確唔需要（v5 移除） |
| 呎價 | 用戶明確唔需要（v5 移除） |

---

## 摘要區

| 欄位 | 說明 |
|------|------|
| 成交宗數 | 報告期間內買賣成交總數（唔計租） |
| 總成交額 | 所有成交價加總 |
| 平均成交價 | 平均成交價 |
| 平均呎價 | 平均呎價 |
| 最高成交價 | 期內最高 |
| 最低成交價 | 期內最低 |

---

## 規則

1. CSV 同 Markdown 欄位必須一致
2. `地址` 係組合欄，唔取代屋苑／座數／樓層／單位
3. 變更格式必須更新本表格、`report_columns.py`、`FORMAT_CHANGELOG.md`

## 嚴格執行 13 欄（必讀）

| 層級 | 做法 |
|------|------|
| **權威定義** | 只改 `src/reporting/report_columns.py`；`TUEN_MUN_RECENT_DETAIL_HEADER_NAMES` 係唯一表頭來源 |
| **程式輸出** | `export_tuen_mun_recent_report.py` 必須用 `detail_headers()` / `detail_row()`；**禁止**手寫表頭或縮減欄位 |
| **輸出後驗證** | 每次出報告自動跑 `validate_exported_csv_detail` / `validate_exported_markdown_detail` |
| **手動驗證** | `python workspace/reports/manufacturing/validate_report_format.py <報告路徑>` |
| **對話／摘要** | 向用戶展示時**唔可以**縮減明細欄位；要麼貼完整 13 欄表，要麼指引打開 `.md` / `.csv` |
| **改欄流程** | 用戶明確要求 → 更新 `report_columns.py` → 測試 → `FORMAT_CHANGELOG.md` → `REPORT_FORMAT.md` |

**硬性規定：** 成交明細永遠 **13 欄、順序固定**；缺欄、調序、CSV 同 MD 不一致 → 程式拋 `ReportFormatError`。

---

*建立日期：2026-08-05 | 格式版本：v8*
