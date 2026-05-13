# task-11：實作 LangGraph Reflection Node

> **⚠️ 已被 task-17 取代（superseded by task-17-judge-reflection）**
>
> 本 task 對應的 [spec-11](../specs/spec-11-reflection.md) 已被 [spec-17](../specs/spec-17-judge-reflection.md) 取代；
> 實作改採 4 軸結構化 Judge（groundedness / completeness / faithfulness / tone），
> 不再使用本 task 描述的單一 reflection_score 自評欄位。
>
> 本文件保留作為設計演進記錄。

> 規格詳見 [spec-11](../specs/spec-11-reflection.md)

---

請在 task-10 的 LangGraph graph 中，於 `generate` → `push` 之間插入 `reflect` 條件節點，支援低品質回覆自動重新生成。

## 前提

task-10（Self-RAG）必須已完成，LangGraph graph 已運作正常。

## 步驟 1：擴充 `app/graph/state.py`

在 `RAGState` 中新增三個欄位：

```python
class RAGState(TypedDict):
    # ...（既有欄位）
    reflection_score: float      # 自評分數，初始 1.0（不觸發）
    reflection_reason: str       # 自評原因，初始 ""
    reflection_retry: int        # 反思重試次數，初始 0，上限 1
```

初始 state 中加入：
```python
"reflection_score": 1.0,
"reflection_reason": "",
"reflection_retry": 0,
```

## 步驟 2：新增 `node_reflect` 與 `node_generate_with_feedback` 至 `app/graph/nodes.py`

```python
import json

REFLECTION_THRESHOLD = 0.6
REFLECTION_SKIP_SKILLS = frozenset({"emotional_calibration"})

async def node_reflect(state: RAGState, *, llm_client, model: str) -> dict:
    """對 is_rag_required=True 的回覆進行自評；情緒 skill 跳過"""
    router_result = state["router_result"]

    # 不對閒聊或指定 skill 啟用 reflection
    if not router_result.is_rag_required or router_result.target_skill in REFLECTION_SKIP_SKILLS:
        logger.info("reflection skip: skill=%s", router_result.target_skill)
        return {"reflection_score": 1.0, "reflection_reason": "skipped"}

    response_text = "\n".join(state.get("responses", []))
    rag_available = bool(state.get("rag_chunks"))

    prompt = (
        "你是一個回覆品質評審。請評估以下回覆是否達標。\n\n"
        f"問題：{state['user_input']}\n"
        f"回覆：{response_text}\n"
        f"Skill：{router_result.target_skill}\n"
        f"RAG 資料是否足夠：{rag_available}\n\n"
        "評分標準（0.0 ~ 1.0）：\n"
        "- 0.8+：清楚、準確、符合問題、格式合適\n"
        "- 0.5–0.8：大致正確但不夠完整或格式不佳\n"
        "- <0.5：答非所問、過於模糊、或格式完全不對\n\n"
        '只輸出 JSON：{"score": 0.0, "reason": "..."}'
    )
    try:
        response = await llm_client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=200,
        )
        data = json.loads(response.output_text.strip())
        score = float(data.get("score", 1.0))
        reason = str(data.get("reason", ""))
        logger.info("reflection score=%.2f reason=%s", score, reason)
        return {"reflection_score": score, "reflection_reason": reason}
    except Exception:
        logger.exception("reflection LLM failed, skipping")
        return {"reflection_score": 1.0, "reflection_reason": "error"}


def edge_check_reflection(state: RAGState) -> str:
    """score < threshold 且尚未重試 → regenerate；否則 → push"""
    score = state.get("reflection_score", 1.0)
    retry = state.get("reflection_retry", 0)
    if score < REFLECTION_THRESHOLD and retry < 1:
        logger.info("reflection retry: score=%.2f", score)
        return "regenerate"
    logger.info("reflection pass: score=%.2f", score)
    return "push"


async def node_regenerate(state: RAGState, *, generator, knowledge_version: int = 0) -> dict:
    """帶上 reflection_reason 重新生成"""
    reason = state.get("reflection_reason", "")
    # 在 user_input 附加改善提示，讓 generator 知道問題所在
    augmented_input = (
        f"{state['user_input']}\n\n"
        f"[系統提示：上一次回覆的問題：{reason}，請改善這個部分]"
    )
    augmented_state = {**state, "user_input": augmented_input}
    responses = await generator.generate_response(
        user_input=augmented_state["user_input"],
        router_result=state["router_result"],
        skill=None,
        rag_chunks=state.get("rag_chunks", []),
        rag_context=state.get("rag_context", ""),
        recent_history=state.get("recent_history", ""),
        knowledge_version=knowledge_version,
    )
    return {
        "responses": responses,
        "reflection_retry": state.get("reflection_retry", 0) + 1,
    }
```

## 步驟 3：修改 `app/graph/rag_graph.py`

在 `build_rag_graph` 中，將 `generate → push` 拆成 `generate → reflect → (regenerate | push)`：

```python
from app.graph.nodes import (
    node_route, node_retrieve, edge_check_retrieval,
    node_rewrite_query, node_generate, node_push,
    node_reflect, edge_check_reflection, node_regenerate,
)

def build_rag_graph(services) -> object:
    g = StateGraph(RAGState)

    g.add_node("route",      functools.partial(node_route,       router=services.router))
    g.add_node("retrieve",   functools.partial(node_retrieve,    retriever=services.retriever))
    g.add_node("rewrite",    functools.partial(node_rewrite_query, llm_client=services.llm_client, model=services.llm_model))
    g.add_node("generate",   functools.partial(node_generate,    generator=services.generator))
    g.add_node("reflect",    functools.partial(node_reflect,     llm_client=services.llm_client, model=services.llm_model))
    g.add_node("regenerate", functools.partial(node_regenerate,  generator=services.generator))
    g.add_node("push",       functools.partial(node_push,        line_bot_api=services.line_bot_api))

    g.set_entry_point("route")
    g.add_edge("route", "retrieve")
    g.add_conditional_edges("retrieve", edge_check_retrieval, {"rewrite": "rewrite", "generate": "generate"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("generate", "reflect")
    g.add_conditional_edges("reflect", edge_check_reflection, {"regenerate": "regenerate", "push": "push"})
    g.add_edge("regenerate", "reflect")   # 再評一次，但 reflection_retry=1 後強制 push
    g.add_edge("push", END)

    return g.compile()
```

> **注意**：`regenerate → reflect → push` 路徑：第二次 reflect 時 `reflection_retry` 已為 1，`edge_check_reflection` 必定回傳 `"push"`，避免無限迴圈。

## 請輸出

1. 更新後的 `app/graph/state.py`（加入三個 reflection 欄位）
2. 更新後的 `app/graph/nodes.py`（加入 `node_reflect`、`edge_check_reflection`、`node_regenerate`）
3. 更新後的 `app/graph/rag_graph.py`（加入 reflect / regenerate 節點與邊）
4. 更新後的 `app/line/webhook.py`（initial state 加入三個 reflection 初始值）
5. 測試：
   - mock `node_reflect` 回傳 score=0.3，確認進入 regenerate 路徑
   - mock `node_reflect` 第二次仍回傳 score=0.3，但 reflection_retry=1，確認進入 push（不再重試）
   - mock LLM 拋出例外，確認 reflection_score=1.0（直接 push，不 crash）
   - `emotional_calibration` skill，確認跳過 reflection（直接 push）

## 驗收指令

```bash
pytest tests/ -v -k "reflection"

# 啟動服務後，透過 LINE 傳送一個技術問題
# log 應顯示 "reflection score=X.XX"
# 若分數 >= 0.6：log 顯示 "reflection pass"
# 若分數 < 0.6（模擬情境）：log 顯示 "reflection retry"，後接第二次生成
# reflection LLM 呼叫失敗：log 顯示 exception，但回覆仍正常送出
```
