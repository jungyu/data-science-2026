# evaluate-skill — 知識庫品質評估技能

## 概要

評估知識庫的檢索品質與完整性，產出可量化的品質報告。

## 觸發條件

- 新文件攝取完成後（自動觸發）
- 定期品質掃描（週排程）
- 手動呼叫 `/evaluate`

## 執行步驟

1. **選擇評測集**：從 namespace 的標準測試問題中取樣
2. **執行 Hit@5 測試**：對每個問題查詢 top-5，確認目標文件出現
3. **Namespace 隔離測試**：確認跨 namespace 查詢不會洩漏
4. **新鮮度檢查**：掃描 deprecated / expired 文件比例
5. **產出報告**：輸出品質分數與建議改善方向
6. **記錄 Action Log**

## 品質標準

| 指標 | Lite | Standard | Full |
|------|------|----------|------|
| Hit@5 | N/A | >= 2/3 | >= 4/5 |
| Namespace 隔離 | N/A | 通過 | 通過 |
| 文件新鮮度 | N/A | >= 75% | >= 90% |

## 相關模組

- `src/governance/drift_detector.py` — 知識漂移偵測
- `src/retrieval/retrieval_gate.py` — 檢索品質閘門
- `.agent/skills/rag-workflow/04-eval-gate.md` — 評測閘門定義
