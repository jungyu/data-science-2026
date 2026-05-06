# task-26：查詢轉換（HyDE / Step-Back / Decompose）

> 規格詳見 [spec-26](../specs/spec-26-query-transform.md)

---

本 task 在 `query_transform_node` 中實作 HyDE、Step-Back Prompting、Query Decomposition 三種策略，統一接在 `route` 之後、`extract_features` 之前。

## 前置

- P2（spec-14 multi-seed）已完成
- `app/graph/state.py` 與 `app/graph/rag_graph.py` 已存在

## 前置安裝

無額外依賴（使用現有 OpenAI SDK）。

---

## 步驟 1：State 新增欄位

`app/graph/state.py`：

```python
class RAGState(TypedDict):
    # ... existing fields ...
    transformed_queries: list[str]   # 轉換後的查詢列表（含原始）
    hyde_doc: str | None             # HyDE 假設性解答
    transform_strategy: str | None  # 本次策略名稱
```

## 步驟 2：Config 新增

`app/config.py` 新增：

```python
QUERY_TRANSFORM_STRATEGY: Literal["none", "hyde", "step_back", "decompose"] = Field(
    default="none", alias="QUERY_TRANSFORM_STRATEGY"
)
HYDE_MODEL: str = Field(default="gpt-4o-mini", alias="HYDE_MODEL")
HYDE_MAX_TOKENS: int = Field(default=150, alias="HYDE_MAX_TOKENS")
STEP_BACK_MODEL: str = Field(default="gpt-4o-mini", alias="STEP_BACK_MODEL")
DECOMPOSE_MAX_SUBQUERIES: int = Field(default=3, alias="DECOMPOSE_MAX_SUBQUERIES")
```

## 步驟 3：新增 `app/graph/query_transform.py`

參照 spec-26 § 設計 → 3，實作：
- `hyde_transform(query, settings) → (hyde_doc, embed_text)`
- `step_back_transform(query, settings) → list[str]`
- `decompose_transform(query, settings) → list[str]`
- `query_transform_node(state, settings) → dict`

## 步驟 4：修改 `expand_seeds_node`

`app/graph/nodes.py` 的 `expand_seeds_node`：讀取 `state["transformed_queries"]` 代替直接讀 `state["query"]`。詳見 spec-26 § 設計 → 5。

## 步驟 5：Graph 接線

每個 variant builder（`build_basic_graph`、`build_selfrag_graph`、`build_reflection_graph`）：

```python
from app.graph.query_transform import query_transform_node

builder.add_node("query_transform", partial(query_transform_node, settings=settings))
# 插入 route → query_transform → extract_features
builder.add_edge("route", "query_transform")
builder.add_edge("query_transform", "extract_features")
```

（移除原本 `route → extract_features` 的 edge）

## 步驟 6：撰寫測試

新增 `tests/test_query_transform.py`：

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_none_strategy(settings_none):
    from app.graph.query_transform import query_transform_node
    result = await query_transform_node({"query": "hello"}, settings_none)
    assert result["transformed_queries"] == ["hello"]
    assert result["transform_strategy"] == "none"


@pytest.mark.asyncio
async def test_hyde_strategy(settings_hyde, mock_openai):
    # mock_openai 回傳固定假設性解答
    from app.graph.query_transform import query_transform_node
    result = await query_transform_node({"query": "什麼是 RAG？"}, settings_hyde)
    assert result["hyde_doc"] is not None
    assert len(result["transformed_queries"]) == 2  # [hyde_doc, original]


@pytest.mark.asyncio
async def test_decompose_compound_query(settings_decompose, mock_openai_decompose):
    from app.graph.query_transform import query_transform_node
    result = await query_transform_node(
        {"query": "React 18 的 concurrent mode 和 Next.js 的 SSR 如何搭配？"},
        settings_decompose,
    )
    assert len(result["transformed_queries"]) >= 2
```

## 步驟 7：`.env.example` 補充

```dotenv
# 查詢轉換（none / hyde / step_back / decompose）
QUERY_TRANSFORM_STRATEGY=none
HYDE_MODEL=gpt-4o-mini
HYDE_MAX_TOKENS=150
DECOMPOSE_MAX_SUBQUERIES=3
```

---

## 里程碑 ✅

- [ ] `QUERY_TRANSFORM_STRATEGY=none` → `transformed_queries == [query]`，其他 test 全綠
- [ ] `QUERY_TRANSFORM_STRATEGY=hyde` → `state["hyde_doc"]` 非 None
- [ ] `QUERY_TRANSFORM_STRATEGY=decompose` → 複合問題展開為 ≥ 2 子問題
- [ ] 切換策略不需改 graph 結構
- [ ] `pytest tests/test_query_transform.py` 全綠
