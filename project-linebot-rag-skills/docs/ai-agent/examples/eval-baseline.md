# Eval Baseline 範本

> 對應 [task-20](../tasks/task-20-evaluation.md)、[doc-01 §Tier 1](../guides/doc-01-transferability-guide.md#tier-1換領域留-line--supabase) 的「T1 必交」artifact。
> 學生轉題目時把這份檔複製出去、用真實跑出的數字填空。本檔示意格式與預期觀察。

## 元資訊

- 跑於：`<YYYY-MM-DD>`
- Case set：`tests/cases/golden.yaml`（N=10）
- Embedder / LLM provider：`<例：openai gpt-4.1 + text-embedding-3-small>`
- Knowledge store backend：`<supabase | sqlite_vec | pinecone>`
- 知識庫資料量：`<chunks 數>`

## 三變體 metric 對比

> 用 `python scripts/eval.py --output baseline.json --format json` 拿到原始資料，
> 然後 markdown table 直接複製 `python scripts/eval.py` 的 stdout：

```
| metric | basic | selfrag | reflection |
| --- | --- | --- | --- |
| chunk_recall_avg | 0.62 | 0.81 | 0.81 |
| citation_accuracy_avg | n/a | 0.95 | 0.97 |
| forbidden_phrase_rate | 0.20 | 0.05 | 0.00 |
| clarification_rate | n/a | 0.20 | 0.20 |
| judge_pass_rate | n/a | n/a | 0.85 |
| latency_ms_median | 3200 | 5100 | 7400 |

Failed cases:
  basic: ['gap-001', 'ground-001']
  selfrag: ['ground-002']
  reflection: []
```

## 預期觀察

對照 `docs/RAG/LangGraph/ch06` 三模式表，**reflection ≥ selfrag ≥ basic** 在品質側、
**latency 反向**。具體地：

| 比對 | 預期方向 | 你跑的數字 | 是否符合 |
|------|---------|-----------|---------|
| chunk_recall: basic vs selfrag | selfrag ≥ basic（multi-seed 贏在 multi-* case）| | ☐ |
| citation_accuracy: selfrag vs reflection | 接近，差距 < 5% | | ☐ |
| forbidden_phrase_rate | basic > selfrag > reflection | | ☐ |
| latency: basic < selfrag < reflection | basic 最快 | | ☐ |
| judge_pass_rate（reflection only）| ≥ 0.7 | | ☐ |

**若觀察與預期不符**，至少需在 commit 訊息或 PR 描述中說明可能原因（例：知識庫 chunks 太少、judge 模型太嚴格、case set 偏向某類）。

## 失敗案例分析

針對每個 `failed` 列表中的 case 寫一段：

### `gap-001`（basic）
- query：`怎麼用 LangGraph 接 Kubernetes Operator？`
- 失敗原因：`expected clarify but went to generate`
- 原因：basic variant 無 sufficiency check，會強行生成
- 行動：升級到 selfrag 即可解（spec 已預期）

### `ground-001`（basic / selfrag）
- query：`請列出 RAG 系統的所有評估指標`
- 失敗原因：`hit forbidden phrase: ['所有', '完全', '無一例外']`
- 觀察：basic 因無 grounded constraint 易說「所有」；selfrag 偶爾仍誤觸
- 行動：reflection 通過（judge 4 軸抓到 uncertainty_honesty 不足）；
  若必須用 selfrag，調 narrative prompt 加強限制

## 結論摘要

- 對本領域 baseline，建議生產走 `<variant 名稱>`，理由：`<...>`
- 已知盲區：`<...>`
- 下一輪改進重點：`<例如：knowledge_top_k 提到 12、sufficiency_min_top_score 升到 0.5>`

---

*學生複製此檔到自己 fork 的 `docs/eval-baseline.md`，作為 T1 結束時的可審計交付物。*
