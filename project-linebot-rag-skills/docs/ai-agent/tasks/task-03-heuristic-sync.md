# task-03：Heuristic Categories 同步

> 規格詳見 [spec-03](../specs/spec-03-heuristic-sync.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-03 頂部「實作狀態」段。
---

請新增 `app/router/categories.py` 作為 category 的單一來源，並修正 `intent_router.py` 與 `prompts.py` 的不一致。

## 步驟 1：新增 `app/router/categories.py`

```python
from __future__ import annotations

VALID_RAG_CATEGORIES: frozenset[str] = frozenset({
    "rag",
    "engineering",
    "architecture",
    "code",
    "analytics",
    "experiments",
    "metrics",
    "strategy",
    "market",
    "product",
    "philosophy",
    "notes",
})
```

## 步驟 2：修改 `app/router/intent_router.py`

從 `categories` 模組 import `VALID_RAG_CATEGORIES`。

修正 heuristic fallback 的 category 清單：

| Skill | 修正後的 rag_categories |
|-------|----------------------|
| `tech_architect` | `["engineering", "architecture", "code", "rag"]` |
| `data_scientist` | `["analytics", "experiments", "metrics"]` |
| `business_strategist` | `["strategy", "market", "product"]` |
| `philosophical_dialectic` | `["philosophy", "notes"]`（移除不合法的 `"reflection"`）|

## 步驟 3：修改 `app/router/prompts.py`

Rule 8 的 category 清單改為從 `VALID_RAG_CATEGORIES` 動態產生（排序後 join 成字串），確保 prompt 與 code 永遠同步。

```python
from app.router.categories import VALID_RAG_CATEGORIES

_CATEGORIES_STR = "、".join(sorted(VALID_RAG_CATEGORIES))
# 在 ROUTER_PROMPT 的 Rule 8 插入 _CATEGORIES_STR
```

## 請輸出

1. `app/router/categories.py` 完整程式碼
2. 修改後的 `app/router/intent_router.py`（只修改必要的部分）
3. 修改後的 `app/router/prompts.py`（Rule 8 動態引用）
4. 新增測試：`tests/test_router.py` 中加入：
   ```python
   def test_heuristic_categories_are_valid():
       # 所有 heuristic fallback 的 rag_categories 都是 VALID_RAG_CATEGORIES 的子集
       from app.router.categories import VALID_RAG_CATEGORIES
       # 測試每個 skill 的 heuristic rag_categories
       ...
   ```

## 驗收指令

```bash
pytest tests/test_router.py::test_heuristic_categories_are_valid -v
```
