# Spec-03：Heuristic Categories 同步

## 背景

`app/router/intent_router.py` 的 heuristic fallback 的 `rag_categories` 與 `app/router/prompts.py` 中 Router prompt 列出的合法 category 清單不一致。若 LLM 路由失敗降回 heuristic，技術問題的 category filter 只有 `["engineering", "architecture", "code", "rag"]`，缺少 `analytics`、`experiments` 等，導致部分知識庫資料永遠找不到。

## 目前不一致之處

**Router prompt 列出的合法 categories（完整）：**
```
rag, engineering, architecture, code, analytics, experiments,
metrics, strategy, market, product, philosophy, notes
```

**intent_router.py heuristic fallback（不完整）：**

| Skill | 目前 categories | 缺少 |
|-------|---------------|------|
| `tech_architect` | `engineering, architecture, code, rag` | — |
| `data_scientist` | `analytics, experiments, metrics` | — |
| `business_strategist` | `strategy, market, product` | — |
| `philosophical_dialectic` | `philosophy, reflection, notes` | `reflection` 不在合法清單裡（應為 `philosophy, notes`）|
| `emotional_calibration` | `[]` | 正確，無需 RAG |
| `general_chat` | `[]` | 正確 |

## 修正目標

1. 移除 `philosophical_dialectic` heuristic 中不合法的 `"reflection"` category
2. 確認所有 heuristic 的 category 值都出現在 Router prompt 的合法清單中
3. 在 `prompts.py` 的 Rule 8 加上完整最新清單（與 heuristic 同步）
4. 新增 `VALID_RAG_CATEGORIES` 常數，在 `intent_router.py` 和 `prompts.py` 都引用同一個 source of truth

## 介面契約

**新增**：`app/router/categories.py`

```python
VALID_RAG_CATEGORIES: frozenset[str] = frozenset({
    "rag", "engineering", "architecture", "code",
    "analytics", "experiments", "metrics",
    "strategy", "market", "product",
    "philosophy", "notes",
})
```

`intent_router.py` 和 `prompts.py` 都從此模組 import，確保單一來源。

## 不做什麼

- 不新增 category 值（現有清單已足夠）
- 不改變 Router LLM 的邏輯
- 不改變資料庫 schema

## 驗收標準

- `VALID_RAG_CATEGORIES` 中的每個值，都能在 Router prompt 的 Rule 8 找到
- `intent_router.py` 中所有 heuristic 的 category 值，都是 `VALID_RAG_CATEGORIES` 的子集
- 加入 `assert` 測試：`set(heuristic_categories) <= VALID_RAG_CATEGORIES`
