# Ch 01：Graph 起步

> **本章對應**：[task-18](../ai-agent/tasks/task-18-playwright-ingestion.md)（知識庫入庫）+
> [task-12](../ai-agent/tasks/task-12-graph-refactor.md)（graph 等價重構）
>
> **本章目標**：把現有的線性 webhook 重構成 LangGraph，
> 並讓它能從你自己抓的知識庫回答問題。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 知識庫有 ≥ 5 份你自己領域的 markdown 文件            ║
║  ✅ graph 端對端跑通（LINE 或 /api/chat 擇一）           ║
║  ✅ 問一個知識庫涵蓋的問題，回覆內容和知識庫相關         ║
╚══════════════════════════════════════════════════════════╝
```

---

## 1-1  你現在拿到的程式是什麼

打開 `app/line/webhook.py`，找到 `process_text_event` 函式。
它現在做的事（簡化版）：

```python
async def process_text_event(event, services):
    # 1. 決定要走哪個 skill（route）
    router_result = await services.router.route_message(text, history)

    # 2. 從知識庫撈資料（retrieve）
    chunks = await services.retriever.retrieve(query, categories)

    # 3. 生成回覆（generate）
    responses = await services.responder.generate_response(...)

    # 4. 推到 LINE（push）
    await services.line_client.push_text(user_id, responses)
```

四個步驟，直接串在一個函式裡。能跑，但有問題：

```
問題 1：要加「資料不夠時誠實追問」，得在 step 2 和 step 3 之間插 if/else。
問題 2：要加「品質不夠時重新生成」，得在 step 3 後面加一個 while 迴圈。
問題 3：複雜度越來越高，測試越來越難寫。
```

**解法：把這四步變成 graph 的四個節點。**

---

## 1-2  LangGraph 的三個核心概念

### 概念 1：State（狀態）

想像一張「流程記錄表」，在每個節點之間傳遞：

```python
class RAGState(TypedDict, total=False):
    user_input: str               # 使用者說了什麼
    external_user_id: str         # 誰說的（channel 無關的識別碼）
    channel: OutputChannel        # 表達層（LINE / HTTP / Telegram）

    router_result: ...            # route 節點填入
    rag_chunks: list[...]         # retrieve 節點填入
    rag_context: str              # retrieve 節點填入
    responses: list[str]          # generate 節點填入
```

`external_user_id` 和 `channel` 都是 channel 無關的欄位：
LINE 傳 `U_abc123`，HTTP 傳 `web_user_001`，Telegram 傳 chat_id——
`push_node` 一視同仁，透過 `OutputChannel` Protocol 推出去。

每個節點從 state 讀它需要的欄位，寫入它產生的結果。
節點之間不直接呼叫彼此——都透過 state 溝通。

> 💡 **為什麼用 TypedDict 而不是普通 dict？**
>
> 型別標注讓 IDE 自動補全，讓你在 `state["wrong_field"]` 時就報錯，
> 而不是等到 runtime 才發現。

---

### 概念 2：Node（節點）

每個節點是一個函式，接受 state，回傳**部分更新**：

```python
async def route_node(state: RAGState, services) -> dict:
    result = await services.router.route_message(
        state["user_input"],
        state.get("recent_history", ""),
    )
    return {"router_result": result, "skill": skill}
    #       ↑ 只回傳這個節點負責的欄位
```

LangGraph 把回傳的 dict **merge 進 state**，不覆蓋其他欄位。

---

### 概念 3：Edge（邊）

邊決定節點的執行順序：

```python
g.add_edge("route", "retrieve")     # route 執行完 → 執行 retrieve
g.add_edge("retrieve", "generate")  # retrieve 完 → generate
```

Ch01 的 graph 是純線性的，只有普通邊。
Ch03 才會加入**條件邊**（根據結果選不同路徑）。

---

## 1-3  動手重構：四步變四個節點

### Step 1：建 `app/graph/state.py`

```python
# app/graph/state.py（對照實際檔案 app/graph/state.py）
from __future__ import annotations
from typing import TypedDict
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.registry import Skill
from app.channels.base import OutputChannel


class RAGState(TypedDict, total=False):
    # ── 輸入（channel 填入）──────────────────
    user_input: str
    external_user_id: str      # channel 無關的使用者 ID
    channel: OutputChannel     # LINE / HTTP / Telegram 均可
    recent_history: str
    skill: Skill

    # ── route 節點輸出 ──────────────────────
    router_result: RouterResult

    # ── retrieve 節點輸出 ───────────────────
    rag_chunks: list[KnowledgeChunk]
    rag_context: str

    # ── generate 節點輸出 ───────────────────
    responses: list[str]
```

### Step 2：建 `app/graph/nodes.py`

```python
# app/graph/nodes.py
from app.graph.state import RAGState
from app.dependencies import RuntimeServices


async def route_node(state: RAGState, services: RuntimeServices) -> dict:
    result = await services.router.route_message(
        state["user_input"],
        state.get("recent_history", "No recent conversation."),
    )
    skill = (
        services.skill_registry.get(result.target_skill)
        or services.skill_registry.require("general_chat")
    )
    return {"router_result": result, "skill": skill}


async def retrieve_node(state: RAGState, services: RuntimeServices) -> dict:
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"rag_chunks": [], "rag_context": "No retrieved context."}

    chunks = await services.retriever.retrieve(
        router_result.rag_query or state["user_input"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
        external_user_id=state["external_user_id"],
        skill_id=router_result.target_skill,
    )
    context = services.retriever.build_context(chunks)
    return {"rag_chunks": chunks, "rag_context": context}


async def generate_node(state: RAGState, services: RuntimeServices) -> dict:
    try:
        responses = await services.responder.generate_response(
            user_input=state["user_input"],
            router_result=state["router_result"],
            skill=state["skill"],
            rag_chunks=state.get("rag_chunks", []),
            rag_context=state.get("rag_context", ""),
            recent_history=state.get("recent_history", ""),
        )
    except Exception:
        responses = ["系統暫時無法完成此請求，請稍後再試。"]
    return {"responses": responses}


async def push_node(state: RAGState, services: RuntimeServices) -> dict:
    # channel 可以是 LINE、HTTP、Telegram——graph 不需要知道是哪個
    channel: OutputChannel = state["channel"]
    messages = channel.format("\n\n".join(state["responses"]))
    await channel.push(
        recipient_id=state["external_user_id"],
        messages=messages,
    )
    return {}
```

### Step 3：建 `app/graph/rag_graph.py`

```python
# app/graph/rag_graph.py
from functools import partial
from langgraph.graph import END, START, StateGraph
from app.dependencies import RuntimeServices
from app.graph.nodes import generate_node, push_node, retrieve_node, route_node
from app.graph.state import RAGState


def build_rag_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route",    partial(route_node,    services=services))
    g.add_node("retrieve", partial(retrieve_node, services=services))
    g.add_node("generate", partial(generate_node, services=services))
    g.add_node("push",     partial(push_node,     services=services))

    g.add_edge(START,      "route")
    g.add_edge("route",    "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "push")
    g.add_edge("push",     END)

    return g.compile()
```

Mermaid 長這樣：

```
__start__ → route → retrieve → generate → push → __end__
```

### Step 4：入口點呼叫 graph

Graph 入口和具體 channel 無關。下面以 HTTP endpoint 為例（LINE 類似）：

```python
# app/api/chat.py（HTTP channel 入口）
initial_state: RAGState = {
    "user_input": body.message,
    "external_user_id": body.user_id,
    "channel": services.channel,   # 由 app/dependencies.py 依 CHANNEL env 決定
    "recent_history": recent_history,
}
final_state = await services.rag_graph.ainvoke(initial_state)
```

LINE channel 的入口（`app/line/webhook.py`）一樣：

```python
initial_state: RAGState = {
    "user_input": event.message.text,
    "external_user_id": event.source.user_id,
    "channel": services.channel,   # 此時 channel = LineChannelAdapter
    "recent_history": recent_history,
}
final_state = await services.rag_graph.ainvoke(initial_state)
```

**重點**：graph 程式碼完全不變，換 channel 只需要改 `.env` 的 `CHANNEL=line` / `CHANNEL=http`。

---

## 1-4  等價性測試

```bash
pytest tests/test_rag_graph_equivalence.py -v
```

三個測試：
1. 四個節點依序執行，state 有 `responses`
2. `generate_node` 失敗時回傳預設錯誤訊息（不 crash）
3. `is_rag_required=False` 時，`rag_chunks` 為空

> ⚠️ **等價重構的硬要求**
>
> 重構前後，同一則訊息的回覆內容必須一致。
> 如果出現行為差異——你有了新功能，但也引入了 bug。
> 先讓三個測試全綠，再進下一步。

---

## 1-5  建立你的知識庫

### 什麼是 frontmatter？

每個抓進來的 markdown 檔案頂端都有一個 YAML 區塊：

```markdown
---
title: "Next.js App Router 介紹"
source_url: "https://nextjs.org/docs/app"
category: "nextjs"
crawled_at: "2026-05-01"
content_hash: "a3f9..."
---

# App Router

Next.js 14 引入了 App Router...
```

`category` 和 `skill` 的 `rag_categories` 必須**完全一致**，
否則 retriever 查不到任何 chunk。

---

### 抓網頁並入庫

```bash
# Step 1：確認你的 skill 用哪個 category
grep -r "rag_categories" skills/

# Step 2：爬你領域的頁面
python scripts/crawl_to_markdown.py \
  --urls urls/<你的領域>.txt \
  --out docs/RAG/crawled/<你的領域> \
  --category <和 skill 一樣的 category>

# Step 3：入庫
python scripts/ingest_markdown.py \
  docs/RAG/crawled/<你的領域>/

# Step 4：確認 chunk 數量
# 在 Supabase Dashboard 執行：
# SELECT count(*) FROM private_knowledge;
```

urls 檔案格式（一行一個 URL）：

```
# urls/nextjs.txt
https://nextjs.org/docs/app
https://nextjs.org/docs/app/building-your-application/routing
https://nextjs.org/docs/app/building-your-application/data-fetching
```

---

> ⚠️ **W1 最常撞到的三個坑**
>
> **坑 1：category 不對齊**
> skill `rag_categories: ["nextjs"]` 但 crawl 用 `--category javascript`
> → retriever 回傳 0 chunks → bot 進入 clarify 分支
> → 解法：`grep -r "rag_categories" skills/` 確認一致
>
> **坑 2：跨語言 query**
> 你問中文，但知識庫是英文
> → sufficiency 的 `min_feature_overlap` 會是 0（詞彙沒有交集）
> → 解法：設 `SUFFICIENCY_MIN_FEATURE_OVERLAP=0`（Ch03 會深入討論）
>
> **坑 3：router 非確定性**
> 同一個問題，第一次路由到 `tech-architect`，第二次路由到 `general-chat`
> → 解法：設定 `ROUTER_TEMPERATURE=0.0`，Ch05 再用 eval 驗證

---

## 1-6  看一下你的 graph 長什麼樣子

```bash
python scripts/dump_graph_mermaid.py --variant basic
```

輸出貼到 [mermaid.live](https://mermaid.live) 就能看圖。

---

## 📝 沒有蠢問題

**Q：`partial(route_node, services=services)` 是什麼意思？**

A：`functools.partial` 把函式的部分參數先綁定。
LangGraph 呼叫每個節點時只傳入 `state`，不傳 `services`。
用 `partial` 可以讓節點「記得」自己的 services，
同時保持 `state → dict` 的乾淨介面。

**Q：`total=False` 在 TypedDict 裡是什麼意思？**

A：讓所有欄位都變成「非必填」。
如果不加這個，TypedDict 預設要求所有欄位都存在，
但 graph 剛開始時 `router_result` 還不存在——
`total=False` 讓你可以從空的 state 開始執行。

**Q：為什麼把 persistence（落庫訊息）留在 webhook 而不進 graph？**

A：Graph 的每個節點都是「純邏輯」——輸入 → 輸出，沒有 side effect。
把資料庫寫入留在 graph 外，可以讓 graph 的邏輯更容易測試
（用假的 services 跑，不需要真的 DB 連線）。

---

## ✏️ 本章任務

1. 完成 task-12 的所有步驟（state / nodes / rag_graph / webhook 修改）
2. 跑通 `pytest tests/test_rag_graph_equivalence.py`
3. 用 `crawl + ingest` 建立自己領域的知識庫（至少 5 個頁面）
4. 問一個知識庫涵蓋的問題，確認回覆有引用你抓的內容
5. 在 `WEEK1.md` 記錄：你問了什麼、graph 跑了多久（看 log）

---

## 🧠 腦力激盪

> 現在的 graph 是完全等價重構——行為和之前一樣，只是結構不同。
>
> 如果一開始就直接把 multi-seed 功能加進去（不先做等價重構），
> 測試失敗時你怎麼判斷是「重構出了問題」還是「新功能出了問題」？
>
> 等價重構的意義，就是把「結構的變化」和「功能的變化」分開——
> 讓每一步都可以獨立驗證。

---

## 🎯 本章里程碑

```
問一個你抓進來的文件涵蓋的問題。
回覆內容至少有一處與你抓的內容相關。
截圖存在 WEEK1.md。
```

---

下一章 → [Ch 02：Multi-seed 檢索](ch02-multi-seed.md)
