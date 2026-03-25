---
name: supabase-query-basics
description: "查詢基礎規範：明確欄位、禁止 SELECT *、基礎分頁、Index 入門"
triggers:
  - "SELECT"
  - "query"
  - "查詢"
  - "分頁"
  - "index"
finish_conditions:
  - "查詢使用明確欄位（非 SELECT *）"
  - "列表查詢有 ORDER BY + LIMIT"
  - "FK 欄位有 index"
references:
  - docs/supabase/labs/lab-02-postgresql-core.md
  - docs/supabase/assignments/hw-01-sql-basics.md
  - docs/supabase/chapter-04-project-practice.md
---

# Query Basics（基礎）

> 寫查詢的最低紀律：說清楚你要什麼、排好序、設上限。

---

## 快速開始

```python
# ✅ 好的查詢：明確欄位 + 排序 + 上限
response = supabase.table('predictions') \
    .select('id, model_name, score, created_at') \
    .eq('user_id', user_id) \
    .order('created_at', desc=True) \
    .limit(50) \
    .execute()
```

---

## 目的 / 能解決什麼問題

防止常見的查詢效能問題：全表掃描、傳輸過多資料、結果不確定排序。

## 何時該用 / 何時不該用

| 該用 | 不該用 |
|------|--------|
| 寫任何 SELECT 查詢 | DDL（CREATE TABLE 等）|
| API 資料讀取 | 一次性的探索分析（Notebook 中允許較寬鬆）|

## Repo Reality

- `docs/supabase/labs/lab-02-postgresql-core.md` — 基礎 SELECT、JOIN、聚合
- `docs/supabase/assignments/hw-01-sql-basics.md` — 電商查詢練習
- `docs/supabase/chapter-04-project-practice.md` — Python + Supabase 查詢

---

## 核心規則

### 1. 禁止 SELECT *

```sql
-- ❌ 錯誤：傳輸所有欄位，包括大型 JSONB
SELECT * FROM predictions;

-- ✅ 正確：只取需要的欄位
SELECT id, model_name, score, created_at FROM predictions;
```

**為什麼**：`SELECT *` 會傳輸你不需要的大欄位（JSONB payload 可能幾 KB），浪費網路和記憶體。

**例外**：在 Jupyter Notebook 做探索分析時，`SELECT *` 配 `LIMIT 5` 可以接受。

### 2. 列表查詢必須有 ORDER BY + LIMIT

```sql
-- ❌ 錯誤：無排序、無上限
SELECT id, name FROM products;

-- ✅ 正確：有排序 + 有上限
SELECT id, name, price FROM products
ORDER BY created_at DESC
LIMIT 50;
```

**為什麼**：沒有 ORDER BY，Postgres 不保證順序（每次可能不同）。沒有 LIMIT，資料量大時會拖垮前端。

### 3. 篩選用明確條件

```python
# ✅ 好：用 eq 篩選特定使用者
response = supabase.table('predictions') \
    .select('id, score, created_at') \
    .eq('user_id', user_id) \
    .execute()

# ❌ 差：撈全部再用 Python 篩選
response = supabase.table('predictions') \
    .select('*') \
    .execute()
filtered = [r for r in response.data if r['user_id'] == user_id]
```

**讓資料庫做篩選，不要讓 Python 做**。資料庫有 index，Python 沒有。

### 4. FK 欄位必須加 Index

```sql
-- 每個 FK 欄位都需要 index
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
```

**為什麼**：沒有 index 的 FK，每次 JOIN 都是全表掃描。Lab-02 只教了一個 index 範例，但**每個 FK 都需要**。

### 5. JOIN 用明確條件

```sql
-- ✅ 好：明確 ON 條件
SELECT o.id, c.name, o.total_amount
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
ORDER BY o.created_at DESC
LIMIT 20;

-- ❌ 差：CROSS JOIN（忘記 ON 條件）
SELECT * FROM orders, customers;  -- 笛卡爾積！
```

### 6. 聚合查詢基礎

```sql
-- hw-01 風格：訂單統計
SELECT
  customer_id,
  COUNT(*) AS order_count,
  SUM(total_amount) AS total_spent
FROM orders
GROUP BY customer_id
ORDER BY total_spent DESC
LIMIT 10;
```

**進階提醒**：當資料量大時，聚合查詢應加時間邊界（見 `production/query-patterns.md`）。

---

## Python (supabase-py) 常用查詢模式

### 單筆查詢

```python
response = supabase.table('products') \
    .select('id, name, price') \
    .eq('id', product_id) \
    .single() \
    .execute()
```

### 列表查詢

```python
response = supabase.table('orders') \
    .select('id, status, total_amount, created_at') \
    .eq('customer_id', customer_id) \
    .order('created_at', desc=True) \
    .limit(20) \
    .execute()
```

### 篩選 + 排序

```python
response = supabase.table('predictions') \
    .select('id, model_name, score') \
    .eq('user_id', user_id) \
    .gte('score', 0.8) \
    .order('score', desc=True) \
    .limit(10) \
    .execute()
```

---

## 常見錯誤與排除

| 錯誤 | 原因 | 解決方式 |
|------|------|---------|
| 查詢很慢 | FK 沒有 index | 加 `CREATE INDEX` |
| 結果順序不穩定 | 缺 ORDER BY | 加 `ORDER BY created_at DESC` |
| 傳輸量太大 | 用了 SELECT * | 改為明確欄位 |
| Python 篩選很慢 | 應該在 DB 層篩選 | 用 `.eq()` / `.gte()` 等 |

## 進階學習

完成基礎後，進入 `production/query-patterns.md` 學習：
- Cursor Pagination（取代 OFFSET）
- Batch ETL Insert（分批匯入）
- 時序聚合查詢（Time Bucket）
- Window Functions（排名、移動平均）

## 參考來源

- `docs/supabase/labs/lab-02-postgresql-core.md` — SELECT、JOIN、聚合實驗
- `docs/supabase/assignments/hw-01-sql-basics.md` — 電商查詢練習
- `docs/supabase/chapter-04-project-practice.md` — Python + Supabase
