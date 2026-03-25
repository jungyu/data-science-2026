# Head First Migration 流程 — 從實驗到正式的橋樑

> **「在 SQL Editor 做實驗，用 Migration 上正式。這是唯一正確的流程。」**
>
> 你的大腦在想：「我在 Studio 改了 schema，為什麼不算數？」
>
> 因為 Studio 的改動不會被記錄。下次跑 `supabase db reset`，你的改動就消失了。

![Migrations](https://supabase.com/images/blog/lw12/day-1/migrations.png)

---

## Part 1: 為什麼需要 Migration

> **Studio 只是 UI，不是主戰場。**

想像一下這個場景：你在 Table Editor 開開心心地加了三個欄位、改了兩個型別、刪了一個 index。一切看起來很完美。

然後你的隊友早上上班，跑了 `supabase db reset`。

他的資料庫 — 乾乾淨淨，什麼都沒有。你的心血全部消失。

為什麼？因為 `db reset` 只認 migration 檔案。你在 GUI 上的操作，**從未被記錄下來**。

### 三個致命問題

1. **不可重現** — 你在 GUI 點了什麼，沒人知道（包括未來的你）
2. **不可追蹤** — 無法 `git diff`，無法 code review
3. **不可協作** — 隊友無法重現你的環境

> 腦筋急轉彎：「你在 Table Editor 加了一個 `category` 欄位。隊友 pull 最新程式碼後跑 `supabase db reset`。他的 DB 有這個欄位嗎？」
>
> **沒有！** 因為 migration 裡沒有記錄這件事。在 Git 的世界裡，這個欄位不存在。

---

## Part 2: Migration 基本流程

三步驟，記住就好：

### Step 1: 建立新 migration

```bash
supabase migration new create_experiments_table
```

這會在 `supabase/migrations/` 目錄下產生一個帶時間戳的空檔案：

```
supabase/migrations/20260325120000_create_experiments_table.sql
```

> 你的大腦在想：「那個 `20260325120000` 是什麼？」
>
> 是時間戳。Migration 按照時間順序執行，先建的先跑。這個順序非常重要。

### Step 2: 寫 migration SQL

打開那個 `.sql` 檔案，把你在 SQL Editor 測試成功的 SQL 貼進去：

```sql
-- supabase/migrations/20260325120000_create_experiments_table.sql

CREATE TABLE IF NOT EXISTS public.experiments (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  name TEXT NOT NULL,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_experiments_updated
BEFORE UPDATE ON public.experiments
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

注意那個 `IF NOT EXISTS` — 這是安全網，後面會詳細講。

### Step 3: 套用 migration

```bash
# 方法 A：重建整個 DB + 跑所有 migration（開發時最常用）
supabase db reset

# 方法 B：只跑還沒跑過的 migration（部署時用）
supabase migration up
```

> 你的大腦在想：「`db reset` 和 `migration up` 差在哪？」
>
> `db reset` = 把 DB 砍掉重建，從第一個 migration 開始跑。適合開發。
> `migration up` = 只跑新的 migration，不動現有資料。適合正式環境。

---

## Part 3: 正確的開發流程

這張圖要刻在你的腦子裡：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SQL Editor  │     │  Migration  │     │  Git Repo   │
│  (實驗場)    │ ──→ │  (.sql 檔)  │ ──→ │  (版本控制)  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
   實驗成功              複製 SQL             commit + push
   ↓ 失敗                過去                 隊友 pull
   丟掉重來                                   db reset ✅
```

流程是：

1. 在 **SQL Editor** 裡隨便實驗（寫錯沒關係，這是沙盒）
2. 實驗成功後 → 用 `supabase migration new` 建立 migration 檔
3. 把測試成功的 SQL **複製**到 migration 檔裡
4. 跑 `supabase db reset` 驗證整個流程能跑通
5. `git add` + `git commit`
6. 隊友 `git pull` + `supabase db reset` → 環境完全一致

> Head First 原則：**SQL Editor 是你的實驗室。Migration 是你的正式紀錄。Git 是你的保險箱。**

---

## Part 4: Studio 的角色定位

搞清楚每個工具的正確用途：

| 操作 | 正確工具 | 為什麼 |
|------|---------|--------|
| 瀏覽資料 | Table Editor | 快速查看、篩選、排序 |
| 實驗 SQL | SQL Editor | 快速驗證語法和邏輯 |
| 建立/修改 schema | **Migration** | 可追蹤、可重現、可協作 |
| Debug 查詢效能 | SQL Editor | `EXPLAIN ANALYZE` |
| 管理測試用戶 | Authentication | 建立/刪除測試帳號 |
| 改 production schema | **Migration ONLY** | 絕對不要用 GUI 改 |

> 腦筋急轉彎：「我在 Table Editor 按了 'Add column'，這算 migration 嗎？」
>
> 不算。Table Editor 的操作是直接執行 SQL 到資料庫，不會產生 migration 檔案。
> 你的改動存在於資料庫中，但不存在於程式碼中。這就是 **drift**（漂移）。

---

## Part 5: Schema 分層的 Migration 策略

當你的專案越來越大，migration 的組織方式就很重要：

```bash
# 建議的 migration 命名與順序
supabase migration new 000_extensions_and_functions
supabase migration new 001_create_public_schema
supabase migration new 002_create_crawler_schema
supabase migration new 003_create_rag_schema
supabase migration new 004_rls_policies
supabase migration new 005_seed_data
```

### 順序為什麼重要？

Migration 是按照**檔名的時間戳順序**執行的。順序錯了，整個系統就崩了。

正確的順序邏輯：

1. **Extensions 和共用 functions 最先** — 因為後面的表可能依賴 `uuid-ossp`、`pgvector` 等 extension
2. **Schema 建立次之** — 先有表，才能有 RLS
3. **RLS policies 在表建完之後** — policy 綁定在表上，表不存在就報錯
4. **Seed data 最後** — 表和 policy 都建好了，再塞測試資料

> 你的大腦在想：「如果我把 RLS policy 放在建表之前會怎樣？」
>
> 會噴錯：`relation "xxx" does not exist`。因為 policy 要綁定到一張已經存在的表。

---

## Part 6: 避免踩坑

這三個坑，每個初學者都會踩至少一次。提前知道，少走彎路。

### 坑 1: Studio 改了 schema 但沒寫 migration

你在 Table Editor 手動加了一個欄位，忘了寫 migration。幾天後跑 `db reset`，欄位消失了。

**解法：定期檢查 drift**

```bash
# 比對「資料庫現況」和「migration 紀錄」的差異
supabase db diff
```

如果有 diff 輸出 → 趕快把那些變更補進新的 migration 裡。

> 養成習慣：**每次在 Studio 做完任何 schema 變更，立刻跑 `supabase db diff`。**

### 坑 2: Migration 順序錯了

有 Foreign Key 依賴的表，被引用的表要先建立。

```sql
-- ❌ 如果 orders 先跑，customers 還不存在
CREATE TABLE orders (
  customer_id TEXT REFERENCES customers(id)  -- 爆炸！
);

-- ✅ 確保 customers 的 migration 時間戳比 orders 早
-- 20260325100000_create_customers.sql  ← 先
-- 20260325100001_create_orders.sql     ← 後
```

同理：**Function 要在 Trigger 之前**建立。Trigger 引用不存在的 function 一樣會報錯。

### 坑 3: 非冪等 migration

「冪等」的意思是：**跑一次和跑十次，結果一樣**。

```sql
-- ❌ 跑兩次會爆（因為表已經存在）
CREATE TABLE experiments (
  id TEXT PRIMARY KEY
);

-- ✅ 安全的寫法
CREATE TABLE IF NOT EXISTS experiments (
  id TEXT PRIMARY KEY
);
```

其他常見的冪等寫法：

```sql
-- 新增欄位
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS category TEXT;

-- 建立 index
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);

-- 刪除表
DROP TABLE IF EXISTS temp_data;
```

> Head First 原則：**每一條 migration SQL 都要加上 `IF NOT EXISTS` 或 `IF EXISTS`。**
> 這是你的安全網。

---

## Part 7: 架構級建議總結

五條黃金法則，貼在螢幕旁邊：

### 1. Studio 只是 UI，不是主戰場
Migration + CLI 才是正途。Studio 是給你看資料、做實驗用的，不是拿來改 schema 的。

### 2. SQL Editor 用來實驗 + debug
寫 SQL、跑 `EXPLAIN ANALYZE`、測試 function — 這些都適合。但不要直接用它來改 production schema。

### 3. 一定要建立 migration 流程
`supabase migration new` 是你最常打的指令。每一次 schema 變更都要有對應的 migration 檔案。

### 4. Schema 分層
`public` / `crawler` / `rag` / `analytics` — 每個 domain 有自己的 schema，migration 也按照 domain 分層管理。

### 5. 避免 Table Editor 做結構變更
Table Editor 的操作無法 version control，容易造成 drift。你改了什麼，Git 不知道，隊友不知道，未來的你也不知道。

---

## 動手做：完整 Migration 流程

```
📝 Exercise: 從零到 Migration

1. 打開 SQL Editor，實驗建表語法：
   CREATE TABLE IF NOT EXISTS public.notes (
     id TEXT PRIMARY KEY DEFAULT generate_ulid(),
     title TEXT NOT NULL,
     content TEXT,
     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );

2. 測試成功後，回到終端機建立 migration：
   $ supabase migration new create_notes_table

3. 打開產生的 .sql 檔，把 SQL 貼進去

4. 跑 supabase db reset 驗證
   $ supabase db reset

5. 確認表存在後，commit：
   $ git add supabase/migrations/
   $ git commit -m "feat: add notes table migration"

6. 回到 SQL Editor，實驗加一個欄位：
   ALTER TABLE public.notes ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'general';

7. 測試成功後，建立新 migration：
   $ supabase migration new add_notes_category

8. 把 ALTER TABLE SQL 貼到新的 migration 檔

9. 再跑一次驗證：
   $ supabase db reset

10. commit：
    $ git add supabase/migrations/
    $ git commit -m "feat: add category column to notes"
```

> 恭喜！你剛剛完成了一個完整的「實驗 → migration → 驗證 → 版本控制」循環。
> 這個流程會成為你日常開發的肌肉記憶。

---

## 自我檢查清單

```
□ 我知道 Studio 的 schema 改動不會被 migration 記錄
□ 我能用 supabase migration new 建立 migration 檔案
□ 我知道 migration 的正確執行順序（extensions → tables → RLS → seed）
□ 我能用 supabase db diff 檢查 drift
□ 我的 migration 全部是冪等的（IF NOT EXISTS / IF EXISTS）
□ 我知道 supabase db reset 和 migration up 的差別
□ 我的開發流程是：SQL Editor 實驗 → Migration 檔案 → Git 版本控制
□ 我不會在 Table Editor 做 schema 結構變更
```

---

## 下一步

> 基礎操作學完了。但 Studio 還有進階能力等著你：
>
> → [07_analytics-and-matview.md](07_analytics-and-matview.md) — 跨域分析 + Materialized View
> → [08_cron-webhook-vault.md](08_cron-webhook-vault.md) — 生產運維三件套
> → [09_api-gateway-pattern.md](09_api-gateway-pattern.md) — 用 Database Function 當 API
>
> 或者直接進入實戰專案：
> - [電商資料庫](../shop/00_README.md) — 完整的 Shop schema 設計
> - [爬蟲資料庫](../crawler/00_README.md) — Crawler ETL pipeline
> - [RAG 資料庫](../RAG/00_README.md) — 向量搜尋與知識庫
>
> **記住：從現在開始，每一次 schema 變更都要有 migration。沒有例外。**
