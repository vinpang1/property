# 數據源說明

> 記錄各數據來源嘅 URL、更新頻率、限制同注意事項。  
> 啟用狀態以 `config/sources.yaml` 為準；採集程式經 `src/ingestion/providers/` 統一接入。

---

## 屯門區成交

| 來源 | URL | 類型 | 頻率 | Provider | 備註 |
|------|-----|------|------|----------|------|
| 中原地產 | centanet.com | API | 每週 | `centaline` | 最近成交、臨約、放盤 |
| 美聯物業 | data.midland.com.hk | API | 每週 | `midland` | 成交 API + LANDREG 來源 |
| 利嘉閣 | ricacorp.com | 爬蟲 | 每週 | `ricacorp` | 屋苑成交 HTML |
| 祥益地產 | manyw.com | 爬蟲 | 每週 | `manyw` | 屋苑成交 HTML + 新聞 |
| 土地註冊處 | data.gov.hk | 官方 JSON | 每月 | `landreg_client` | 全港月度統計（`run.py download`） |

**暫存路徑：** `data/staging/tuen_mun/`

**最近成交採集：** 经 `providers/registry.py`，只會呼叫 `sources.yaml` 中 `enabled: true` 嘅 provider。

---

## 全港一手成交

| 來源 | URL | 類型 | 頻率 | 備註 |
|------|-----|------|------|------|
| 運輸及物流局 | tlb.gov.hk | 官方 CSV/PDF | 每月 | 一手住宅成交統計 |

**暫存路徑：** `data/staging/primary/`

---

## 全港二手成交

| 來源 | URL | 類型 | 頻率 | 備註 |
|------|-----|------|------|------|
| 差餉物業估價署 | rvd.gov.hk | 官方 | 每月 | 樓價指數 |
| 地產代理監管局 | eaa.org.hk | 官方 | 每季 | 成交統計（規劃中） |

**暫存路徑：** `data/staging/secondary/`

---

## 高成數按揭（HKMC）

| 來源 | URL | 類型 | 頻率 | 備註 |
|------|-----|------|------|------|
| 香港按證 | hkmc.com.hk | PDF | 按更新 | 合資格準則 + 保費表（7 份） |

**暫存路徑：** `data/staging/mortgage/`  
**下載：** `python run.py ingest --source mortgage`

---

## 注意事項

1. 爬蟲需設置合理請求間隔（建議 ≥ 1 秒）
2. 官方數據有發布延遲，通常滯後 1–2 個月
3. 各來源欄位格式唔同，需透過 ETL 藍圖統一
4. 敏感配置（API key）放 `.env`，唔入 git
5. IRIS 土地查冊 API 僅限銀行業機構；一般用途請用 data.gov.hk 月度 JSON
