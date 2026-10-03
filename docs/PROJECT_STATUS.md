# 項目狀態整理 — 網上資料對比遺留清單

> 整理日期：2026-08-11  
> 對比基準：各 agent 分支實作、`docs/BLUEPRINT.md` 規劃、官方／代理公開數據源

---

## 1. 分支與 PR 現況（尚未合併 main）

| PR | 分支 | 重點內容 | 狀態 |
|----|------|----------|------|
| #1 | `cursor/project-blueprint-c76a` | 目錄結構、藍圖、樣本 pipeline | Draft |
| #2 | `cursor/download-jul-aug-data-da66` | 中原／美聯 API、`download_monthly`、`fetch_recent_pasp`、放盤索引 | Draft |
| #3 | `cursor/mortgage-section-ef01` | HKMC 高成數按揭 PDF 下載 | Draft |
| #4 | `cursor/operation-area-reports-adeb` | 報告工作區、13 欄報告格式、代理推斷、利嘉閣／祥益 client | Draft |

**main 分支** 仍只有初始 README，所有功能分散喺四條分支，**未整合**。

---

## 2. 數據源對比表（網上可得 vs 項目實作）

### 2.1 屯門區成交明細

| 來源 | 網上取得方式 | 文檔記載 | 程式實作 | 接入主流程 | 遺留 |
|------|-------------|----------|----------|------------|------|
| **中原地產** | `centanet.com` 成交 API | ✅ | `centaline_client.py` | ✅ `infer_recent_deals`、報告採集 | — |
| **美聯物業** | `data.midland.com.hk` 成交 API | ✅（文檔未列） | `midland_client.py` | ✅ 同上 | 需補 `SOURCES.md` |
| **土地註冊處** | ① data.gov.hk 月度 JSON ② 代理轉載 LANDREG 紀錄 | ✅ | `landreg_client.py` | ⚠️ 經美聯 API 的 LANDREG 來源；月度 JSON 喺 #2 分支 | 月度統計未合併；IRIS 逐宗查冊 API 僅限銀行 |
| **利嘉閣** | `ricacorp.com` 屋苑成交 HTML | ✅ | `ricacorp_client.py` | ❌ `sources.yaml` `enabled: false`；未接入 `infer_recent_deals` | **需接入最近成交採集** |
| **祥益地產** | `manyw.com` 屋苑成交 HTML | ❌（文檔無） | `manyw_client.py` | ❌ 只用於新聞／輔助推斷 | **需補文檔 + 接入成交採集** |
| **香港置業** | 官網成交頁 | ❌ | ❌ | ❌ | **完全未覆蓋** |

### 2.2 全港趨勢（一手／二手）

| 來源 | 網上取得方式 | 文檔記載 | 程式實作 | 遺留 |
|------|-------------|----------|----------|------|
| **運輸及物流局** | 一手住宅成交統計 CSV/PDF | ✅ | `download_primary.py` 用**硬編碼樣本** | **需接真實下載／解析** |
| **差餉物業估價署** | 樓價指數、成交統計 | ✅ | `download_secondary.py` 用**硬編碼樣本** | **需接真實下載** |
| **地產代理監管局** | 每季成交統計 | ✅ | ❌ | **未實作** |
| **土地註冊處** | 月度註冊統計 JSON | ✅ | `landreg_client.py`（#2 分支 `download_monthly`） | **未合併到主線** |

### 2.3 高成數按揭（按揭保險）

| 來源 | 網上取得方式 | 文檔記載 | 程式實作 | 遺留 |
|------|-------------|----------|----------|------|
| **香港按證（HKMC）** | 合資格準則 + 保費 PDF（7 份） | ✅（#3 分支 `SOURCES.md`） | `download_mortgage.py` + 藍圖 | **整個模組喺 #3 分支，未合併**；無 ETL／入庫／報告 |

### 2.4 網上存在但項目未規劃

| 來源 | 說明 | 建議 |
|------|------|------|
| IRIS 土地查冊 API | 2025-04-28 起僅《銀行業條例》認可機構可用 | 一般開發者用 data.gov.hk 月度 JSON 代替 |
| 28Hse、Squarefoot 等 | 放盤／成交聚合 | 視需要再評估 |
| RVD Open Data API | 樓價指數 | 可補強二手趨勢 |

---

## 3. 功能模組對比（藍圖 vs 實作）

| 藍圖區域 | 規劃 | 現況 | 遺留 |
|----------|------|------|------|
| 數據採集 `src/ingestion/` | 多源下載 | 中原／美聯真實 API ✅；屯門預設仍用 seed 樣本 | 利嘉閣／祥益接入；`run.py ingest` 預設改為真實源 |
| ETL `src/etl/` | 清洗藍圖驅動 | 屯門 MVP ✅ | 按揭 PDF 解析；多源合併規則 |
| 驗證 `src/validation/` | 品質檢查 | 基本 schema ✅ | 異常偵測、outlier 檢查未做 |
| 入庫 `src/database/` | DB-A + DB-B | SQLite schema ✅ | 按揭無 schema |
| 報告 `workspace/` | 13 欄屯門最近成交 | v8 格式 + 驗證 ✅ | 只採中原+美聯；按揭章節未做 |
| 藍圖 `blueprints/` | ingestion/etl/validation/analysis | ingestion + etl + validation ✅ | `analysis/` 目錄未建 |
| 排程 `schedules/` | Cron 定義 | ❌ | Phase 4 未開始 |
| 歸檔 `data/archive/` | 按月封存 | ❌ | 未實作 |
| 測試 `tests/` | unit + integration | 25 passed ✅ | 缺利嘉閣／祥益／按揭整合測試 |

---

## 4. `run.py` CLI 指令對比（分支差異）

| 指令 | #2 download 分支 | #3 mortgage 分支 | #4 operation 分支（現最完整） |
|------|------------------|------------------|-------------------------------|
| `ingest --source mortgage` | ❌ | ✅ | ❌ |
| `download`（月度土地註冊 JSON） | ✅ | ❌ | ❌ |
| `recent-deals` / `recent-pasp` | ✅ | ❌ | ❌ |
| `export-listings` | ✅ | ❌ | ❌ |
| `workspace list/archive` | ❌ | ❌ | ✅ |
| 屯門最近報告製造腳本 | 部分 | ❌ | ✅ `fetch_recent_and_report.py` |

**遺留：需合併分支，統一 CLI。**

---

## 5. 報告格式 v8 vs 採集覆蓋

| 項目 | 狀態 |
|------|------|
| 13 欄明細（簽臨約日、地址、代理等） | ✅ 已鎖定 `report_columns.py` |
| 只計買賣、以臨約日為準 | ✅ |
| 明細不含成交價／呎價（用戶要求 v5） | ✅ 報告層；DB 仍有價格欄 |
| 採集來源 | ⚠️ 僅中原 + 美聯（2026-08-05 實測：8+89 宗） |
| 利嘉閣／祥益成交 | ❌ 有 client 但未進主採集 |
| 新聞代理推斷 | ✅ `agent_inference` + `news_review` |
| 按揭／高成數章節 | ❌ |

---

## 6. 建議優先處理順序

### P0 — 整合分支
1. 合併 #2 + #3 + #4 到單一主線（或依次 merge PR）
2. 統一 `run.py` 子命令
3. 更新 `main` README 實施進度

### P1 — 補齊文檔與採集一致
1. `SOURCES.md` 加入美聯、祥益
2. `config/sources.yaml` 啟用利嘉閣，接入 `infer_recent_deals`
3. 祥益成交接入主採集（`manyw_client.fetch_estate_transactions`）
4. `download_primary` / `download_secondary` 接真實官方源（或標明「樣本模式」）

### P2 — 藍圖 Phase 4
1. `schedules/cron` 排程
2. `data/archive/` 歸檔
3. EAA 每季統計
4. 按揭 PDF 結構化入庫（若報告需要）

### P3 — 擴展
1. 香港置業
2. 其他 17 區（複製屯門模式）
3. 可視化儀表板

---

## 7. 一句話總結

**網上資料已研究並部分實作，但分散喺 4 條未合併分支；屯門最近成交報告只覆蓋中原+美聯，利嘉閣／祥益有程式未接入；全港趨勢仍用樣本數；高成數按揭整模組未入主線；藍圖 Phase 4（排程、歸檔、EAA）尚未開始。**
