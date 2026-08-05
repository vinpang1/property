# 操作區域

日後嘅報告集中放喺呢度管理，同 `output/` 自動輸出分開，方便人手編輯同歸檔。

## 報告工作區

| 子目錄 | 路徑 | 用途 |
|--------|------|------|
| 進行中嘅報告 | `workspace/reports/in_progress/` | 草稿、未完成、待審核嘅報告 |
| 保留報告 | `workspace/reports/archived/` | 已確認、封存嘅最終版本 |
| 製造報告 | `workspace/reports/manufacturing/` | 生成報告用嘅 skill 同 Python 腳本 |

## 工作流程

```
製造報告 (manufacturing/) → 進行中 (in_progress/) → 保留 (archived/)
```

1. 用 `python run.py report` 或 `workspace/reports/manufacturing/build_report.py` 生成報告
2. 新報告預設寫入 `in_progress/`
3. 確認無誤後執行 `python run.py archive <檔名>` 移至 `archived/`

## 相關指令

```bash
python run.py report              # 生成月度報告到進行中
python run.py workspace list      # 列出工作區報告
python run.py workspace archive <檔名>  # 歸檔報告
```
