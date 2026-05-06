# task-19：三種 LangGraph 變體並陳

> 規格詳見 [spec-19](../specs/spec-19-graph-variants.md)

---

把 P1 / P3 / P4 完成時的三個 graph 形態保留為三個獨立 builder，並提供切換與比較示範。本 task 屬於**橫向整合**，不引入新 RAG 功能。

## 前置

- task-12 / 14 / 15 / 16 / 17 全部完成
- 已熟悉 [docs/RAG/LangGraph/ch06](../../RAG/LangGraph/ch06-rag-vs-selfrag-vs-reflection.md)

## 步驟 1：建立 variants 目錄

```
app/graph/
├── state.py           # 共用
├── nodes.py           # 共用 node 函式庫
├── feature_extractor.py
├── seed_expander.py
├── sufficiency.py
├── clarifier.py
├── rag_graph.py       # 改為 thin wrapper，內部 dispatch 到 variants/
└── variants/
    ├── __init__.py    # 註冊表
    ├── basic.py       # build_basic_graph
    ├── selfrag.py     # build_selfrag_graph
    └── reflection.py  # build_reflection_graph
```

## 步驟 2：variant 1 — basic（對應 ch06 §1）

新增 `app/graph/variants/basic.py`：

```python
"""Variant 1: Basic RAG（線性，無反思）

對應 docs/RAG/LangGraph/ch06 §1。
最接近 P1 task-12 完成時的形態。
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.dependencies import RuntimeServices
from app.graph.nodes import (
    generate_node,        # P1 的單階段 generator
    push_node,
    retrieve_node,        # P1 的單 seed retrieve
    route_node,
)
from app.graph.state import RAGState


def build_basic_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route", partial(route_node, services=services))
    g.add_node("retrieve", partial(retrieve_node, services=services))
    g.add_node("generate", partial(generate_node, services=services))
    g.add_node("push", partial(push_node, services=services))

    g.add_edge(START, "route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "push")
    g.add_edge("push", END)
    return g.compile()
```

> 重要：`retrieve_node` 與 `generate_node` 是 P1 原版（單 seed、單階段 LLM），P2/P3 不能直接覆寫——若已覆寫，把原版以 `_basic` 後綴保留：`retrieve_basic_node`、`generate_basic_node`。

## 步驟 3：variant 2 — selfrag（對應 ch06 §2）

新增 `app/graph/variants/selfrag.py`：

```python
"""Variant 2: Self-RAG（多 seed + sufficiency 分支）

對應 docs/RAG/LangGraph/ch06 §2。
P3 task-15 / task-16 完成時的形態。
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.dependencies import RuntimeServices
from app.graph.nodes import (
    build_answer_contract_node,
    check_sufficiency_node,
    clarify_node,
    expand_seeds_node,
    extract_features_node,
    fuse_scores_node,
    push_node,
    render_narrative_node,
    retrieve_one_node,
    route_node,
    route_by_sufficiency,
)
from app.graph.state import RAGState


def fan_out_to_retrieve(state: RAGState):
    return [
        Send("retrieve_one", {"seed": s, "_index": i, "_state": state})
        for i, s in enumerate(state["seeds"])
    ]


def build_selfrag_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route", partial(route_node, services=services))
    g.add_node("extract_features", partial(extract_features_node, services=services))
    g.add_node("expand_seeds", partial(expand_seeds_node, services=services))
    g.add_node("retrieve_one", partial(retrieve_one_node, services=services))
    g.add_node("fuse_scores", partial(fuse_scores_node, services=services))
    g.add_node("check_sufficiency", partial(check_sufficiency_node, services=services))
    g.add_node("clarify", partial(clarify_node, services=services))
    g.add_node("build_answer_contract", partial(build_answer_contract_node, services=services))
    g.add_node("render_narrative", partial(render_narrative_node, services=services))
    g.add_node("push", partial(push_node, services=services))

    g.add_edge(START, "route")
    g.add_edge("route", "extract_features")
    g.add_edge("extract_features", "expand_seeds")
    g.add_conditional_edges("expand_seeds", fan_out_to_retrieve, ["retrieve_one"])
    g.add_edge("retrieve_one", "fuse_scores")
    g.add_edge("fuse_scores", "check_sufficiency")
    g.add_conditional_edges(
        "check_sufficiency",
        route_by_sufficiency,
        {"sufficient": "build_answer_contract", "insufficient": "clarify"},
    )
    g.add_edge("build_answer_contract", "render_narrative")
    g.add_edge("render_narrative", "push")
    g.add_edge("clarify", "push")
    g.add_edge("push", END)
    return g.compile()
```

## 步驟 4：variant 3 — reflection（對應 ch06 §3）

新增 `app/graph/variants/reflection.py`：

```python
"""Variant 3: Reflection Agent（selfrag + judge 三向分流）

對應 docs/RAG/LangGraph/ch06 §3。
P4 task-17 完成時的形態。
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.dependencies import RuntimeServices
from app.graph.nodes import (
    build_answer_contract_node,
    check_sufficiency_node,
    clarify_node,
    expand_seeds_node,
    extract_features_node,
    fuse_scores_node,
    increment_retry_node,
    judge_node,
    mark_warning_node,
    push_node,
    render_narrative_node,
    retrieve_one_node,
    route_after_judge,
    route_by_sufficiency,
    route_node,
)
from app.graph.state import RAGState
from app.graph.variants.selfrag import fan_out_to_retrieve


def build_reflection_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    # —— 與 selfrag 相同的前段
    g.add_node("route", partial(route_node, services=services))
    g.add_node("extract_features", partial(extract_features_node, services=services))
    g.add_node("expand_seeds", partial(expand_seeds_node, services=services))
    g.add_node("retrieve_one", partial(retrieve_one_node, services=services))
    g.add_node("fuse_scores", partial(fuse_scores_node, services=services))
    g.add_node("check_sufficiency", partial(check_sufficiency_node, services=services))
    g.add_node("clarify", partial(clarify_node, services=services))
    g.add_node("build_answer_contract", partial(build_answer_contract_node, services=services))
    g.add_node("render_narrative", partial(render_narrative_node, services=services))

    # —— 多出的 reflection 段
    g.add_node("judge", partial(judge_node, services=services))
    g.add_node("increment_retry", partial(increment_retry_node, services=services))
    g.add_node("mark_warning", partial(mark_warning_node, services=services))
    g.add_node("push", partial(push_node, services=services))

    g.add_edge(START, "route")
    g.add_edge("route", "extract_features")
    g.add_edge("extract_features", "expand_seeds")
    g.add_conditional_edges("expand_seeds", fan_out_to_retrieve, ["retrieve_one"])
    g.add_edge("retrieve_one", "fuse_scores")
    g.add_edge("fuse_scores", "check_sufficiency")
    g.add_conditional_edges(
        "check_sufficiency",
        route_by_sufficiency,
        {"sufficient": "build_answer_contract", "insufficient": "clarify"},
    )
    g.add_edge("build_answer_contract", "render_narrative")
    g.add_edge("render_narrative", "judge")
    g.add_conditional_edges(
        "judge",
        route_after_judge,
        {"pass": "push", "retry": "increment_retry", "force_push": "mark_warning"},
    )
    g.add_edge("increment_retry", "render_narrative")  # reflection 迴圈
    g.add_edge("mark_warning", "push")
    g.add_edge("clarify", "push")
    g.add_edge("push", END)
    return g.compile()
```

## 步驟 5：variant 註冊表

新增 `app/graph/variants/__init__.py`：

```python
from app.graph.variants.basic import build_basic_graph
from app.graph.variants.reflection import build_reflection_graph
from app.graph.variants.selfrag import build_selfrag_graph

VARIANT_BUILDERS = {
    "basic": build_basic_graph,
    "selfrag": build_selfrag_graph,
    "reflection": build_reflection_graph,
}

__all__ = ["VARIANT_BUILDERS", "build_basic_graph", "build_selfrag_graph", "build_reflection_graph"]
```

## 步驟 6：config + dependencies 切換

修改 `app/config.py`：

```python
from typing import Literal

class Settings(BaseSettings):
    # ...
    graph_variant: Literal["basic", "selfrag", "reflection"] = "reflection"
```

修改 `app/dependencies.py::get_runtime_services()`：

```python
from app.graph.variants import VARIANT_BUILDERS

@lru_cache(maxsize=1)
def get_runtime_services() -> RuntimeServices:
    settings = get_settings()
    services = RuntimeServices(
        # ...既有欄位
    )
    builder = VARIANT_BUILDERS[settings.graph_variant]
    object.__setattr__(services, "rag_graph", builder(services))
    return services
```

修改 `app/graph/rag_graph.py`（薄包裝、向後相容）：

```python
"""Deprecated: use app.graph.variants.VARIANT_BUILDERS directly.

保留此檔僅為兼容舊 import；內部 dispatch 至預設變體（reflection）。
"""

from app.dependencies import RuntimeServices
from app.graph.variants import build_reflection_graph


def build_rag_graph(services: RuntimeServices):
    return build_reflection_graph(services)
```

## 步驟 7：保留 P1 原版 node（重要！）

P2 ~ P4 的 task 在重構時會修改 `retrieve_node` / `generate_node`。本 task 要把它們的 P1 原始版本**重新存出來**：

修改 `app/graph/nodes.py`，加入：

```python
async def retrieve_basic_node(state: RAGState, services: RuntimeServices):
    """P1 原版：單 seed retrieve。給 basic variant 用。"""
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"rag_chunks": [], "rag_context": "No retrieved context."}
    chunks = await services.retriever.retrieve(
        router_result.rag_query or state["user_input"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
        line_user_id=state["line_user_id"],
        skill_id=router_result.target_skill,
    )
    context = services.retriever.build_context(chunks)
    return {"rag_chunks": chunks, "rag_context": context}


async def generate_basic_node(state: RAGState, services: RuntimeServices):
    """P1 原版：單階段 LLM generation。給 basic variant 用。"""
    try:
        responses = await services.responder.generate_response(
            user_input=state["user_input"],
            router_result=state["router_result"],
            skill=state["skill"],
            rag_chunks=state.get("rag_chunks", []),
            rag_context=state.get("rag_context", "No retrieved context."),
            recent_history=state.get("recent_history", "No recent conversation."),
        )
    except Exception:
        logger.exception("generate_response failed")
        responses = ["系統暫時無法完成此請求，請稍後再試。"]
    return {"responses": responses}
```

並把 `variants/basic.py` 中的 `retrieve_node` / `generate_node` import 改為 `retrieve_basic_node` / `generate_basic_node`。

## 步驟 8：比較 demo 腳本

新增 `scripts/demo_compare_variants.py`：

```python
"""對同一個 query，依序在三個變體上跑，輸出對比表。

用法：
    python scripts/demo_compare_variants.py "Next.js SSR hydration mismatch 怎麼處理？"
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.dependencies import (
    get_line_client,
    get_messages_repo,
    get_responder,
    get_retriever,
    get_router,
    get_settings,
    get_skill_registry,
)
from app.dependencies import RuntimeServices  # noqa
from app.graph.variants import VARIANT_BUILDERS


async def run_variant(variant_name: str, services: RuntimeServices, query: str) -> dict:
    builder = VARIANT_BUILDERS[variant_name]
    graph = builder(services)
    initial_state = {
        "user_input": query,
        "line_user_id": "U_demo",
        "recent_history": "",
    }
    t0 = time.time()
    final = await graph.ainvoke(initial_state)
    duration = time.time() - t0
    return {
        "variant": variant_name,
        "duration": duration,
        "chunks": len(final.get("rag_chunks", [])),
        "seeds": final.get("seeds", ["(single)"]),
        "sufficiency": final.get("sufficiency", "(n/a)"),
        "judge_score": final.get("judge_score"),
        "retry": final.get("reflection_retry", 0),
        "response": ("\n\n".join(final.get("responses", [])))[:300],
    }


def print_result(r: dict) -> None:
    print(f"\n[{r['variant']}]")
    print(f"  duration: {r['duration']:.2f}s")
    print(f"  chunks:   {r['chunks']}")
    print(f"  seeds:    {r['seeds']}")
    print(f"  sufficiency: {r['sufficiency']}")
    if r["judge_score"]:
        s = r["judge_score"]
        print(f"  judge:    ground={s.groundedness} cite={s.citation_fidelity} "
              f"format={s.format_completeness} uncert={s.uncertainty_honesty} mean={s.mean:.1f}")
        print(f"  retry:    {r['retry']}")
    print(f"  response (first 300 chars):")
    print("    " + r["response"].replace("\n", "\n    "))


async def main(query: str) -> None:
    # 用一份共用 services，但每個 variant 自己 build graph
    settings = get_settings()
    services = RuntimeServices(
        line_client=get_line_client(),
        messages_repo=get_messages_repo(),
        skill_registry=get_skill_registry(),
        router=get_router(),
        retriever=get_retriever(),
        responder=get_responder(),
        settings=settings,
    )

    print(f"Query: {query}\n" + "=" * 60)
    for name in ["basic", "selfrag", "reflection"]:
        try:
            r = await run_variant(name, services, query)
            print_result(r)
        except Exception as e:
            print(f"\n[{name}] FAILED: {e}")

    print("\n" + "=" * 60)
    print("變體對應關係 — 詳見 docs/RAG/LangGraph/ch06")
    print("  basic      → ch06 §1 基本 RAG")
    print("  selfrag    → ch06 §2 Self-RAG")
    print("  reflection → ch06 §3 Reflection Agent")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/demo_compare_variants.py <query>")
        sys.exit(1)
    asyncio.run(main(" ".join(sys.argv[1:])))
```

> 注意：`push_node` 會真的呼叫 LINE API。Demo 用途**建議 mock 掉**——把 `services.line_client` 換成 stub（或在 `push_node` 內檢查 `state["line_user_id"]` 是否為 `"U_demo"` 跳過實際 push）。

簡單做法：在 `push_node` 開頭加：

```python
if state.get("line_user_id", "").startswith("U_demo"):
    logger.info("(demo mode) skip LINE push, would send: %s", state["responses"])
    return {}
```

## 步驟 9：產生 graph 視覺化（mermaid）

對每個 variant 產生 mermaid 圖貼進 doc：

新增 `scripts/dump_graph_mermaid.py`：

```python
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.dependencies import get_runtime_services
from app.graph.variants import VARIANT_BUILDERS


def main():
    services = get_runtime_services()
    for name, builder in VARIANT_BUILDERS.items():
        graph = builder(services)
        mermaid = graph.get_graph().draw_mermaid()
        out = Path(f"docs/ai-agent/examples/graph-{name}.mermaid")
        out.write_text(mermaid, encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

## 步驟 10：教學配套

新增 `docs/ai-agent/examples/variants-comparison.md`：

```markdown
# 三種 LangGraph 變體對照（對應 ch06）

| 變體 | ch06 模式 | mermaid 圖 | 適用場景 |
|---|---|---|---|
| basic | §1 RAG | [graph-basic.mermaid](./graph-basic.mermaid) | FAQ、簡單問答 |
| selfrag | §2 Self-RAG | [graph-selfrag.mermaid](./graph-selfrag.mermaid) | 知識庫查詢、技術問答 |
| reflection | §3 Reflection Agent | [graph-reflection.mermaid](./graph-reflection.mermaid) | 高風險領域、需可審計輸出 |

## 三個示範案例

### 案例 1：知識庫充分覆蓋的問題

Query: "什麼是 RAG？"

| | basic | selfrag | reflection |
|---|---|---|---|
| chunks | 4 | 6 | 6 |
| sufficiency | (n/a) | sufficient | sufficient |
| judge | (n/a) | (n/a) | pass |
| retry | 0 | 0 | 0 |
| 回覆風格 | 流水帳 | 帶 [來源 N] | 同 selfrag，多一道審查 |

### 案例 2：複合條件問題

Query: "Next.js 14 SSR hydration mismatch 怎麼處理？"

（同樣呈現三變體輸出 + 觀察）

### 案例 3：知識庫沒涵蓋的問題

Query: "怎麼用 LangGraph 接 Kubernetes Operator？"

| | basic | selfrag | reflection |
|---|---|---|---|
| chunks | 0 | 0 | 0 |
| sufficiency | (n/a) | insufficient | insufficient |
| 回覆 | 「目前知識庫沒有...」+ 強行生成 | 走 clarify 分支，提具體追問 | 同 selfrag |

→ Self-RAG 開始這個 case 才有真正價值。

## 建議學生這樣讀

1. 跑 `scripts/demo_compare_variants.py "你自己的問題"` 三次（換問題）
2. 觀察每個變體的 trade-off
3. 對照 ch06 的「該用哪個」三問題
4. 決定自己的題目該長期維持哪一變體
```

## 請輸出

1. `app/graph/variants/__init__.py`、`basic.py`、`selfrag.py`、`reflection.py`
2. 修改後的 `app/graph/nodes.py`（保留 `retrieve_basic_node`、`generate_basic_node`）
3. 修改後的 `app/graph/rag_graph.py`（薄 wrapper、deprecated 標記）
4. 修改後的 `app/config.py`、`app/dependencies.py`
5. `scripts/demo_compare_variants.py`、`scripts/dump_graph_mermaid.py`
6. `docs/ai-agent/examples/variants-comparison.md` + 三個 mermaid 檔
7. README 加「三變體對照」表，連向 ch06 與 examples

## 驗收指令

```bash
# 切換變體跑
GRAPH_VARIANT=basic ./scripts/run_local.sh
# 確認 log 顯示「graph_variant=basic」、實際 graph 只有 4 個 node

GRAPH_VARIANT=selfrag ./scripts/run_local.sh
# 確認 log 顯示「graph_variant=selfrag」、有 fan-out / fan-in / sufficiency

GRAPH_VARIANT=reflection ./scripts/run_local.sh
# 確認 log 顯示「graph_variant=reflection」、有 judge

# 比較 demo（不會真的推 LINE）
python scripts/demo_compare_variants.py "什麼是 RAG？"
python scripts/demo_compare_variants.py "Next.js SSR hydration mismatch"
python scripts/demo_compare_variants.py "LangGraph 接 Kubernetes 怎麼做？"

# 產生視覺化
python scripts/dump_graph_mermaid.py
# 預期：docs/ai-agent/examples/graph-{basic,selfrag,reflection}.mermaid 三個檔
```

驗收通過條件：

- 三個 variant 都能用 env var 切換並跑通同一輸入
- demo 腳本一次跑完三個 variant，輸出對比結果
- 三個 mermaid 圖能 render（可貼到 mermaid.live 預覽）
- `app/graph/rag_graph.py` 標記 deprecated，但既有 import path 仍可用（向後相容）
- variants-comparison.md 三個示範案例都有實際輸出貼進去
