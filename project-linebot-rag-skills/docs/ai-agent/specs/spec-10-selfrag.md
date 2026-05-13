# Spec-10：LangGraph Self-RAG

> **⚠️ 已被 spec-15 取代（superseded by spec-15-sufficiency-clarify）**
>
> 本 spec 原設計「無資料 → rewrite_query → 重試 retrieve」的 retry 路徑。
> 後續改採 spec-15 的 sufficiency + clarify 流程：偵測資料不足時不自動改寫
> 重試，而是回頭向使用者要求澄清，避免幻覺。
>
> 實作對應：`app/graph/variants/selfrag.py` 走的是 `check_sufficiency → clarify`，
> 不是本文件描述的 `check_retrieval → rewrite_query → retrieve`。
>
> 本文件保留作為設計演進記錄，請以 spec-15 為準。

## 背景

現行 pipeline 是線性的：route → retrieve → generate。若第一次 RAG 找不到資料，直接加前綴「目前知識庫沒有足夠資料」後生成，不會嘗試改寫 query 重試。Self-RAG 引入條件分支：找不到資料時，自動改寫 query 並重試一次。

## 前提

- P1–P3 已穩定完成
- 安裝 `langgraph` 套件

## 設計

```
[START]
   ↓
[route]              router 決定 skill + rag_query + categories
   ↓
[retrieve]           embed + RPC + rerank
   ↓
[check_retrieval]    ← 條件節點
   ↓ (有資料)                ↓ (無資料，且未重試過)
[generate]            [rewrite_query]   改寫 query，標記 retry=true
   ↓                         ↓
[push]              [retrieve]（第二次，用改寫後的 query）
                             ↓
                    [generate]（無論有無資料都生成）
                             ↓
                          [push]
```

## State Schema

```python
class RAGState(TypedDict):
    user_input: str
    recent_history: str
    line_user_id: str
    router_result: RouterResult
    rag_chunks: list[KnowledgeChunk]
    rag_context: str
    responses: list[str]
    retry_count: int         # 最多重試 1 次
    rewritten_query: str     # 改寫後的 query
```

## 節點定義

| 節點 | 輸入 | 輸出 | 備註 |
|------|------|------|------|
| `route` | `user_input`, `recent_history` | `router_result` | 呼叫現有 IntentRouter |
| `retrieve` | `router_result`, `rewritten_query` | `rag_chunks`, `rag_context` | 呼叫現有 RAGRetriever |
| `check_retrieval` | `rag_chunks`, `retry_count` | edge decision | 有資料→generate；無資料且 retry<1→rewrite；否則→generate |
| `rewrite_query` | `router_result`, `user_input` | `rewritten_query`, `retry_count` | 用 LLM 改寫，retry_count+1 |
| `generate` | `rag_context`, `router_result` | `responses` | 呼叫現有 ResponseGenerator |
| `push` | `responses`, `line_user_id` | — | 呼叫 LINE Push API |

## 介面契約

**新增**：`app/graph/rag_graph.py`

```python
from langgraph.graph import StateGraph, END

def build_rag_graph(services: RuntimeServices) -> CompiledGraph: ...
```

**修改**：`app/line/webhook.py`
- `process_text_event()` 改為呼叫 `graph.ainvoke(state)` 而非線性函式

## Rewrite Query 提示

```
原始 query：{rag_query}
未找到相關資料，請用不同的詞彙或更廣泛的描述改寫這個 query，以提高檢索命中率。
只輸出改寫後的 query 字串，不要解釋。
```

## 不做什麼

- 重試上限固定為 1 次（不做無限重試）
- 不改變 route 節點的邏輯
- 不改變 generate 節點的邏輯（仍用現有 ResponseGenerator）

## 驗收標準

- 問一個知識庫沒有的問題，log 顯示「retry: rewriting query」
- 問一個知識庫有的問題，不觸發重試
- 重試後仍找不到資料，仍能正常生成回覆（不 crash）
