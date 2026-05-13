# Spec-11：LangGraph Reflection Node

> **⚠️ 已被 spec-17 取代（superseded by spec-17-judge-reflection）**
>
> 本 spec 原設計單一 `reflection_score` / `reflection_reason` 自評欄位。
> 後續改採 spec-17 的 4 軸 judge（groundedness / completeness / faithfulness /
> tone）+ contract-based 評分，提供更可解釋的品質訊號。
>
> 實作對應：`app/judge/` 與 `app/graph/nodes.py::judge_node`，state 沒有
> `reflection_score`/`reflection_reason` 是設計選擇而非缺漏。
>
> 本文件保留作為設計演進記錄，請以 spec-17 為準。

## 背景

目前 Generator 單次生成後直接送出，沒有任何自我評估機制。對於重要的技術問題，回覆品質可能不穩定。Reflection Node 讓模型先對自己的回覆評分，不足時重新生成。

## 前提

- spec-10（Self-RAG）已完成
- LangGraph 已整合

## 設計

在 `generate` → `push` 之間插入 `reflect` 條件節點：

```
[generate]
   ↓
[reflect]        ← 自評節點
   ↓ (score >= threshold)    ↓ (score < threshold，且 retry < 1)
[push]              [generate]（重新生成，帶自評回饋）
                       ↓
                    [reflect]（再評一次）
                       ↓
                    [push]（無論分數，強制送出）
```

## 自評 Prompt

```
你是一個回覆品質評審。請評估以下回覆是否達標。

問題：{user_input}
回覆：{response_text}
Skill：{skill_name}
RAG 資料是否足夠：{rag_available}

評分標準（0.0 ~ 1.0）：
- 0.8+：清楚、準確、符合問題、格式合適
- 0.5–0.8：大致正確但不夠完整或格式不佳
- <0.5：答非所問、過於模糊、或格式完全不對

只輸出 JSON：{"score": 0.0, "reason": "..."}
```

## State 新增欄位

```python
class RAGState(TypedDict):
    ...（既有欄位）
    reflection_score: float      # 自評分數
    reflection_reason: str       # 自評原因
    reflection_retry: int        # 反思重試次數，上限 1
```

## 觸發條件

- 只對 `is_rag_required=True` 的回覆啟用 Reflection（一般閒聊不自評）
- `reflection_score < 0.6` 且 `reflection_retry < 1` → 重新生成
- 重新生成時，把 `reflection_reason` 附加到 synthesis prompt：「上一次回覆的問題：{reason}，請改善這個部分。」

## 不做什麼

- 不做多輪 reflection（最多 1 次重試）
- 不對 `emotional_calibration` skill 啟用（情緒回應不適合自評）
- 不把 `reflection_score` 存入資料庫（只用於當次請求）

## 驗收標準

- 模擬一個會觸發低分評估的回覆，log 顯示「reflection retry」
- 正常品質的回覆，log 顯示「reflection pass」，不觸發重試
- reflection LLM 呼叫失敗時，直接送出原始回覆（不 crash）
