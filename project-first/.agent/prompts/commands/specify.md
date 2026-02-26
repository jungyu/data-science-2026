# /specify 命令

> 產出 RAG 操作的規格文件（spec.md）

## 用途

當收到新的知識庫操作需求時，使用此命令產出結構化的規格文件。

## 輸出格式

根據複雜度閘門結果選擇模板：

| 複雜度分數 | 模板 |
|-----------|------|
| 0-2 | `.agent/skills/rag-workflow/templates/spec-rag-lite.md` |
| 3-5 | `.agent/skills/rag-workflow/templates/spec-rag-standard.md` |
| 6+ | Full 模式（Standard 模板 + 額外安全/合規章節） |

## 執行步驟

1. 收集需求（目標文件、namespace、操作類型）
2. 執行複雜度評估（`.agent/skills/rag-workflow/00-complexity-gate.md`）
3. 根據分數選擇模板
4. 填寫模板各欄位
5. 提交人工審核（若複雜度 >= 3）

## 範例

```bash
/specify 接入行銷品牌知識庫
```

產出 `spec.md`，包含 namespace 設計、存取控制、成功標準等。
