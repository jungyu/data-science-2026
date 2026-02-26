# 04 — Eval Gate：RAG 品質評測

> Standard / Full 模式必須通過此閘門。

## 攝取後評測

使用預定義的測試問題集驗證新攝取的文件：

1. **Hit@5 測試**：使用 3-5 個相關問題查詢，確認新文件出現在 top-5 結果中
2. **Namespace 隔離測試**：確認跨 namespace 查詢不會檢索到此文件
3. **新鮮度測試**：確認舊版本已被標記為 deprecated（若有）

## 通過標準

| 指標 | Lite | Standard | Full |
|------|------|----------|------|
| Hit@5 | N/A | >= 2/3 | >= 4/5 |
| Namespace 隔離 | N/A | 通過 | 通過 |
| 版本管理 | N/A | 舊版本 deprecated | 舊版本 deprecated + 快照保留 |

## 失敗處理

若評測未通過：
1. 記錄失敗原因到 Action Log
2. 回滾新版本（恢復舊版本為 active）
3. 通知操作者並建議改善方向
