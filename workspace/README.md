# 操作區域

日後嘅報告集中放喺呢度管理，方便人手編輯同歸檔。

## 報告工作區

| 子目錄 | 路徑 | 用途 |
|--------|------|------|
| 進行中嘅報告 | `workspace/reports/in_progress/` | 草稿、未完成、待審核嘅報告 |
| 保留報告 | `workspace/reports/archived/` | 已確認、封存嘅最終版本 |
| 規格文檔 | `workspace/reports/manufacturing/` | SKILL、格式說明（Python 腳本已搬至 `src/reporting/cli/`） |

## 工作流程

```
src/reporting/cli/ 或 run.py report → 進行中 (in_progress/) → 保留 (archived/)
```

1. 用 `python run.py report` 或 `python run.py report monthly` 生成報告
2. 新報告預設寫入 `in_progress/`
3. 確認無誤後執行 `python run.py workspace archive <檔名>` 移至 `archived/`

## 相關指令

```bash
python run.py report                      # 月度報告
python run.py report recent --days 14     # 屯門最近成交
python run.py report fetch-recent         # 採集 + 入庫 + 出報告
python run.py workspace list              # 列出工作區報告
python run.py workspace archive <檔名>    # 歸檔報告
```

## 格式變更記錄

報告欄位變更同用戶需求記錄喺：

- [workspace/reports/manufacturing/FORMAT_CHANGELOG.md](reports/manufacturing/FORMAT_CHANGELOG.md)

完整重整方案見 [docs/RESTRUCTURE_PLAN.md](../../docs/RESTRUCTURE_PLAN.md)。
