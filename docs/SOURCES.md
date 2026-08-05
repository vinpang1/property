# 數據源說明

> 記錄各數據來源嘅 URL、更新頻率、限制同注意事項。

---

## 屯門區成交

| 來源 | URL | 類型 | 頻率 | 備註 |
|------|-----|------|------|------|
| 中原地產 | centanet.com | 爬蟲 | 每週 | 需遵守 robots.txt |
| 利嘉閣 | ricacorp.com | 爬蟲 | 每週 | |
| 土地註冊處 | landreg.gov.hk | 官方 | 每月 | 權威但延遲 |

**暫存路徑：** `data/staging/tuen_mun/`

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
| 地產代理監管局 | eaa.org.hk | 官方 | 每季 | 成交統計 |

**暫存路徑：** `data/staging/secondary/`

---

## 高成數按揭（按揭保險計劃）

| 來源 | URL | 類型 | 頻率 | 備註 |
|------|-----|------|------|------|
| 香港按證保險有限公司 | hkmc.com.hk | 官方 PDF | 每季 | 高成數按揭合資格準則及保費一覽表 |

### 下載資源

| 類別 | 文件 | 說明 |
|------|------|------|
| 合資格準則 | `iec_80ltv_6mn_chi.pdf` | 80%/90% 按揭（物業上限 600 萬港元） |
| 合資格準則 | `iec_80ltv_1715mn_chi.pdf` | 70%-80% 按揭（物業上限 1,715 萬港元） |
| 合資格準則 | `faq_chi.pdf` | 按揭保險計劃常見問題 |
| 合資格準則 | `owner_occupier_exemption_chi.pdf` | 申請豁免自住要求須知 |
| 按揭保費 | `premium_private_chi.pdf` | 私人住宅按揭保費一覽表（中文） |
| 按揭保費 | `premium_private_eng.pdf` | 私人住宅按揭保費一覽表（英文） |
| 按揭保費 | `premium_subsidised_chi.pdf` | 資助房屋按揭保費一覽表 |

**下載路徑：** `data/downloads/hkmc/`  
**暫存路徑：** `data/staging/mortgage/`（manifest CSV）

**採集命令：**
```bash
python run.py ingest --source mortgage
```

---

## 注意事項

1. 爬蟲需設置合理請求間隔（建議 ≥ 2 秒）
2. 官方數據有發布延遲，通常滯後 1–2 個月
3. 各來源欄位格式唔同，需透過 ETL 藍圖統一
4. 敏感配置（API key）放 `.env`，唔入 git
