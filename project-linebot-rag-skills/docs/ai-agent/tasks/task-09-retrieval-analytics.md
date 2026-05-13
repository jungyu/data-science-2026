# task-09：實作 Retrieval Log 分析 CLI

> 規格詳見 [spec-09](../specs/spec-09-retrieval-analytics.md)
>
> **✅ 已完成（commit `0328e58`）** — 實作記錄與驗收測試見 spec-09 頂部「實作狀態」段。
---

請新增 `scripts/analyze_retrieval.py`，提供四種 retrieval log 分析功能。

## 使用方式

```bash
.venv/bin/python scripts/analyze_retrieval.py --empty-hits [--days 7]
.venv/bin/python scripts/analyze_retrieval.py --low-score [--threshold 0.3] [--days 7]
.venv/bin/python scripts/analyze_retrieval.py --category-stats [--days 30]
.venv/bin/python scripts/analyze_retrieval.py --query "LangGraph 是什麼"
```

## 請實作 `scripts/analyze_retrieval.py`

```python
#!/usr/bin/env python
"""Retrieval log analyzer — 快速排查 RAG 品質問題"""
import argparse, asyncio
from datetime import datetime, timedelta, timezone
from app.storage.supabase_client import create_supabase_client
from app.config import get_settings

async def get_empty_hits(supabase, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = await supabase.table("retrieval_logs") \
        .select("query") \
        .eq("retrieved_ids", "{}") \
        .gte("created_at", since) \
        .execute()
    # 統計每個 query 出現次數
    from collections import Counter
    counts = Counter(r["query"] for r in result.data)
    return [{"query": q, "count": c} for q, c in counts.most_common(20)]

async def get_low_score_hits(supabase, threshold: float, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = await supabase.table("retrieval_logs") \
        .select("query, scores, created_at") \
        .gte("created_at", since) \
        .neq("retrieved_ids", "{}") \
        .execute()
    low_score = []
    for r in result.data:
        scores = r.get("scores") or {}
        if not scores:
            continue
        max_score = max((v.get("combined_score", 0) for v in scores.values()), default=0)
        if max_score < threshold:
            low_score.append({"query": r["query"], "max_score": round(max_score, 3)})
    return sorted(low_score, key=lambda x: x["max_score"])[:20]

async def get_category_stats(supabase, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = await supabase.table("retrieval_logs") \
        .select("category_filter") \
        .gte("created_at", since) \
        .execute()
    from collections import Counter
    cat_counts: Counter = Counter()
    for r in result.data:
        for cat in (r.get("category_filter") or []):
            cat_counts[cat] += 1
    return [{"category": k, "count": v} for k, v in cat_counts.most_common()]

async def search_query(supabase, query_text: str) -> list[dict]:
    result = await supabase.table("retrieval_logs") \
        .select("query, retrieved_ids, scores, created_at") \
        .ilike("query", f"%{query_text}%") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
    return result.data
```

**輸出格式**：用 `tabulate` 套件格式化（`pip install tabulate`），或手動對齊。無資料時印出「（無記錄）」。

## 請輸出

1. 完整的 `scripts/analyze_retrieval.py`（含 `argparse` CLI 入口與四種分析函式）
2. `pyproject.toml` 的 `[project.optional-dependencies]` dev 加入 `"tabulate"`

## 驗收指令

```bash
pip install -e ".[dev]"

.venv/bin/python scripts/analyze_retrieval.py --empty-hits
# 若無記錄，印出：（無記錄）
# 若有記錄，印出 query 出現次數表格

.venv/bin/python scripts/analyze_retrieval.py --category-stats
```
