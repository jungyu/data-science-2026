# Action Logs

每次知識操作（攝取、查詢、治理操作）都會在此目錄產生 session log。

## 檔案命名慣例

```
YYYY-MM-DD-{operation}-{namespace}.md
```

例：`2026-02-26-ingest-hr-leaves.md`

## Log 格式

```markdown
# Session: {操作摘要}

- **Date**: YYYY-MM-DD
- **Operator**: {Claude Code / 人類操作者}
- **Duration**: ~N 分鐘
- **Token Budget**: {tier} ({used} / {target})
- **Namespace**: {namespace}

## 操作清單

| 操作 | 文件 / 資源 | 說明 |
|------|------------|------|
| ... | ... | ... |

## 觸發的治理規則

- [x/  ] {規則名稱}：{結果}

## 決策記錄

- {決策內容}

## 驗證結果

{驗證查詢與結果}
```
