# Spec-26：查詢轉換（HyDE / Step-Back / Decompose）

## 背景

使用者輸入通常短而口語化，直接 embed 後在向量空間與知識庫文字有距離。本 spec 引入三種互補的查詢轉換技術，統一包裝成 `query_transform_node`，可按 config 選擇策略。

| 技術 | 核心概念 | 適用場景 |
|------|---------|---------|
| **HyDE** | 先生成「假設性解答」，embed 解答而非問題 | 知識庫是陳述句段落；使用者問題是疑問句 |
| **Step-Back Prompting** | 把具體問題抽象化 → 撈背景知識 | 問題太具體、上層知識需先鋪陳 |
| **Query Decomposition** | 把複合問題拆成 2–4 個子問題 | 一個問題同時包含多個獨立子條件 |

---

## 設計

### 1. Config 新增

`app/config.py`：

```python
QUERY_TRANSFORM_STRATEGY: Literal["none", "hyde", "step_back", "decompose"] = Field(
    default="none", alias="QUERY_TRANSFORM_STRATEGY"
)
HYDE_MODEL: str = Field(default="gpt-4o-mini", alias="HYDE_MODEL")
HYDE_MAX_TOKENS: int = Field(default=150, alias="HYDE_MAX_TOKENS")
STEP_BACK_MODEL: str = Field(default="gpt-4o-mini", alias="STEP_BACK_MODEL")
DECOMPOSE_MAX_SUBQUERIES: int = Field(default=3, alias="DECOMPOSE_MAX_SUBQUERIES")
```

### 2. State 新增欄位

`app/graph/state.py`：

```python
class RAGState(TypedDict):
    # ... existing fields ...
    transformed_queries: list[str]   # transform 後展開的查詢列表（含原始 query）
    hyde_doc: str | None             # HyDE 產出的假設性解答
    transform_strategy: str | None  # 本次使用的策略，供 log
```

### 3. 新增模組 `app/graph/query_transform.py`

```python
from __future__ import annotations

from app.config import Settings
from app.graph.state import RAGState


async def hyde_transform(query: str, settings: Settings) -> tuple[str, str]:
    """回傳 (hypothetical_doc, embedding_text)。"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model=settings.HYDE_MODEL,
        messages=[
            {"role": "system", "content": "你是一位專家。請以解答的形式寫出一段回覆（不要提問題本身）。"},
            {"role": "user", "content": query},
        ],
        max_tokens=settings.HYDE_MAX_TOKENS,
        temperature=0.3,
    )
    hyde_doc = resp.choices[0].message.content.strip()
    return hyde_doc, hyde_doc  # embedding_text = hypothetical doc


async def step_back_transform(query: str, settings: Settings) -> list[str]:
    """回傳 [抽象問題, 原始問題]。"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model=settings.STEP_BACK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "將以下具體問題轉換成更廣泛的背景問題（一句話，不超過 30 字）。"
                    "只輸出問題，不加說明。"
                ),
            },
            {"role": "user", "content": query},
        ],
        max_tokens=60,
        temperature=0.2,
    )
    abstract_q = resp.choices[0].message.content.strip()
    return [abstract_q, query]


async def decompose_transform(query: str, settings: Settings) -> list[str]:
    """回傳 [子問題1, 子問題2, ...（最多 DECOMPOSE_MAX_SUBQUERIES 個）]。"""
    import json
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"將問題分解成最多 {settings.DECOMPOSE_MAX_SUBQUERIES} 個獨立的子問題。"
                    "輸出 JSON 陣列，每個元素是一個子問題字串。"
                    "若問題本身簡單不需分解，回傳只含原問題的陣列。"
                ),
            },
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
        temperature=0.2,
    )
    data = json.loads(resp.choices[0].message.content)
    subqueries = data.get("questions") or data.get("subqueries") or [query]
    return subqueries[: settings.DECOMPOSE_MAX_SUBQUERIES]


async def query_transform_node(state: RAGState, settings: Settings) -> dict:
    """
    按 QUERY_TRANSFORM_STRATEGY 轉換查詢。
    結果存入 state["transformed_queries"]，供後續 expand_seeds 使用。
    原始 query 永遠保留在列表中（fallback）。
    """
    strategy = settings.QUERY_TRANSFORM_STRATEGY
    query: str = state["query"]

    if strategy == "hyde":
        hyde_doc, embed_text = await hyde_transform(query, settings)
        return {
            "transformed_queries": [embed_text, query],
            "hyde_doc": hyde_doc,
            "transform_strategy": "hyde",
        }

    if strategy == "step_back":
        queries = await step_back_transform(query, settings)
        return {
            "transformed_queries": queries,
            "hyde_doc": None,
            "transform_strategy": "step_back",
        }

    if strategy == "decompose":
        subqueries = await decompose_transform(query, settings)
        return {
            "transformed_queries": subqueries,
            "hyde_doc": None,
            "transform_strategy": "decompose",
        }

    # strategy == "none" 或未知
    return {
        "transformed_queries": [query],
        "hyde_doc": None,
        "transform_strategy": "none",
    }
```

### 4. Graph 接線

在 **selfrag** 與 **reflection** 變體的 `extract_features` **之前**插入 `query_transform_node`：

```python
# app/graph/variants/{selfrag,reflection}.py
from app.graph.query_transform import query_transform_node

builder.add_node("query_transform", partial(query_transform_node, services=services))

# edge：route → query_transform → extract_features → ...
builder.add_edge("route", "query_transform")
builder.add_edge("query_transform", "extract_features")
```

> **basic 變體不接** `query_transform`：basic 是 P1 線性教學版（route → retrieve → generate → push），不含 multi-seed 與 feature extraction，沒有 `expand_seeds` 可以消化 `transformed_queries`，因此 query transform 對它無實際效益。學生若要在 basic 上做 query transform，建議先升級到 selfrag。

`extract_features` / `expand_seeds` node 讀取 `state["transformed_queries"]`（而非直接讀 `state["user_input"]`）作為展開 seed 的輸入。

### 5. `expand_seeds` 相容改動

`app/graph/nodes.py` 中的 `expand_seeds_node`：

```python
async def expand_seeds_node(state: RAGState, ...) -> dict:
    # 原本：seeds = feature_extractor.expand(state["query"])
    # 改為：先合併 transformed_queries 再展開
    base_queries = state.get("transformed_queries") or [state["query"]]
    seeds = []
    for q in base_queries:
        seeds.extend(feature_extractor.expand(q))
    # 去重保序
    seen = set()
    unique_seeds = [s for s in seeds if not (s in seen or seen.add(s))]
    return {"seeds": unique_seeds}
```

---

## 成本考量

| 策略 | 額外 LLM 呼叫 | 額外 token 成本（估算）|
|------|-------------|----------------------|
| none | 0 | —— |
| hyde | 1 次（generate hypothetical doc）| ≈ 200–400 tokens |
| step_back | 1 次 | ≈ 100–200 tokens |
| decompose | 1 次 | ≈ 150–300 tokens |

建議生產環境只開其中一種；教學演示可用 `QUERY_TRANSFORM_STRATEGY=hyde` 觀察效果。

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| 轉換策略 | ✅ env var 切換 | ❌ `transformed_queries: list[str]` 介面 |
| 使用的模型 | ✅ `HYDE_MODEL` env var | ❌ 輸出必須是純文字（不是 embedding）|
| HyDE prompt | ✅ 可領域化 system prompt | ❌ 輸出不能混入問題本身 |

---

## 驗收標準

- `QUERY_TRANSFORM_STRATEGY=none` 時 `state["transformed_queries"] == [original_query]`
- `QUERY_TRANSFORM_STRATEGY=hyde` 時 `state["hyde_doc"]` 非 None，且 `transformed_queries[0]` 是假設性解答
- `QUERY_TRANSFORM_STRATEGY=decompose` 時，複合問題（含 2+ 子條件）展開為 ≥ 2 個子問題
- 切換策略不需改 graph 結構
- pytest `tests/test_query_transform.py` 全綠（3 個策略各 1 個 smoke test）
