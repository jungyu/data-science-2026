# Spec-09：Retrieval Log 分析

> **✅ 已實作（commit `0328e58`）**
>
> - 新建 `app/eval/retrieval_analytics.py`（5 個純函式：empty_hits / low_score / category_stats / filter_query / render_table）
> - 新建 `scripts/analyze_retrieval.py` CLI，4 個模式對應 spec §「分析功能」
> - PostgREST 不支 GROUP BY 與 jsonb path filter，拉 rows 後在 Python 端聚合
> - 驗收測試：`tests/test_retrieval_analytics.py`（12 cases 含 empty rows fallback、flat score dict 相容）

## 背景

`retrieval_logs` 資料表已有記錄（query、category_filter、retrieved_ids、scores），但目前沒有任何查詢或分析工具。ADR-004 明確說明「除錯時需直接查 retrieval_logs」，但手動寫 SQL 不方便。

## 目標

提供一個 CLI 腳本（不是 Web），能回答最常見的幾個分析問題，方便快速排查 RAG 品質問題。

## 分析功能

### 1. 找出「找不到資料」的 query

```bash
.venv/bin/python scripts/analyze_retrieval.py --empty-hits [--days 7]
```

輸出：近 N 天內 `retrieved_ids = []` 的 query，依出現次數排序。

### 2. 找出低分檢索

```bash
.venv/bin/python scripts/analyze_retrieval.py --low-score [--threshold 0.3] [--days 7]
```

輸出：`combined_score` 最高值低於閾值的查詢，依分數升序。

### 3. 按 category 分布

```bash
.venv/bin/python scripts/analyze_retrieval.py --category-stats [--days 30]
```

輸出：各 category 被查詢的次數與平均分數。

### 4. 特定 query 的詳細記錄

```bash
.venv/bin/python scripts/analyze_retrieval.py --query "LangGraph 是什麼"
```

模糊比對 query 欄位，印出對應的 chunk titles 與分數。

## 介面契約

**新增**：`scripts/analyze_retrieval.py`

```python
async def get_empty_hits(supabase, days: int) -> list[dict]:
    # SELECT query, COUNT(*) FROM retrieval_logs
    # WHERE retrieved_ids = '{}' AND created_at > now() - interval 'N days'
    # GROUP BY query ORDER BY count DESC

async def get_low_score_hits(supabase, threshold: float, days: int) -> list[dict]:
    # 查 scores jsonb，找出 max combined_score < threshold 的記錄

async def get_category_stats(supabase, days: int) -> list[dict]:
    # unnest(category_filter) 後 GROUP BY

async def search_query(supabase, query_text: str) -> list[dict]:
    # WHERE query ILIKE '%{query_text}%'
```

## 輸出格式

純文字 table（使用 `tabulate` 或手動對齊），適合在 terminal 閱讀。不需要 JSON 或 CSV 輸出（個人使用）。

## 不做什麼

- 不建立 Web Dashboard（留給 Phase 4 或更後期）
- 不加入告警機制（留給後期）
- 不分析 `line_messages`（只分析 `retrieval_logs`）

## 驗收標準

- `--empty-hits` 能正確列出找不到資料的 query
- `--category-stats` 能顯示各 category 的使用分布
- 全部分析指令在 Supabase 無資料時，輸出「無記錄」而不拋錯
