# 查詢品質評測模板

## 測試集

| # | 問題 | 預期 Namespace | 預期 Doc IDs | 預期行為 |
|---|------|---------------|-------------|---------|
| 1 | {question_1} | {namespace} | {doc_ids} | 命中並回答 |
| 2 | {question_2} | {namespace} | {doc_ids} | 命中並回答 |
| 3 | {off_topic_question} | {namespace} | — | 誠實回應「無法回答」 |

## 評測指標

| 指標 | 目標 | 實際 | 通過？ |
|------|------|------|--------|
| Hit@5 | >= {threshold} | | |
| Retrieval Gate 通過率 | >= 80% | | |
| Hallucination Shield 通過率 | >= 90% | | |
| Namespace 隔離 | 100% | | |

## 失敗處理

若評測未通過：
1. 記錄失敗原因
2. 檢查 chunking 品質（是否需要調整 target_size）
3. 檢查嵌入品質（是否需要重新嵌入）
4. 回報到 Action Log
