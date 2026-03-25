# Head First Supabase Studio — 你的資料庫控制塔

> **"看得見的系統，才是你真正理解的系統。"**

你已經讀完了資料庫基礎，知道什麼是正規化、什麼是 ER Diagram。你也把 Docker 跑起來了。

現在，打開瀏覽器，輸入 `http://localhost:54323`。

你看到了什麼？一個漂亮的 Dashboard。左邊有 Table Editor、SQL Editor、Authentication、Storage⋯⋯

**但它不只是一個漂亮的網頁。**

它是 15+ 個 Docker 容器的控制塔。你在上面點的每一個按鈕，背後都有一條 SQL 在跑、一個服務在動。

這份指南會帶你走過 Studio 的五大模組，讓你從「會操作」進化到「知道背後發生什麼事」。

---

## 這份指南適合誰？

你如果符合以下條件，這份指南就是為你寫的：

- 已讀完資料庫基礎（正規化、ER Diagram）
- Docker 已跑起來（`supabase start` 成功）
- 想把正規化觀念「實際動手建出來」
- 想搞懂 Studio 每個面板背後在做什麼

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `03_what-is-supabase.md` | 前置知識（Supabase 整體架構） |
| `labs/05_lab-docker-supabase.md` | Docker 環境設定 |
| `labs/00_lab-supabase-architecture.md` | 架構理解（服務對照表） |
| `e-Commerce/00_README.md` | 下一步：用 Studio 蓋電商資料庫 |

**使用方式**：邊讀指南，邊打開 `http://localhost:54323` 實際操作。讀到哪裡，做到哪裡。

---

## 開場：打開 http://localhost:54323

### 你看到的不只是一個網頁

你以為 Studio 只是一個 GUI 工具？讓我們看看它背後連了什麼：

```
你的瀏覽器 (localhost:54323)
        │
        ▼
┌──────────────────────────────┐
│      Supabase Studio         │  ← 控制塔
│  ┌────────────────────────┐  │
│  │   Table Editor         │──┼──→ PostgreSQL (port 54322)
│  │   SQL Editor           │──┼──→ PostgreSQL
│  │   Authentication       │──┼──→ GoTrue (port 9999)
│  │   API Docs             │──┼──→ PostgREST (port 54321)
│  │   Storage              │──┼──→ S3/MinIO
│  │   Edge Functions       │──┼──→ Deno Runtime
│  │   Realtime             │──┼──→ Realtime Service (port 4000)
│  └────────────────────────┘  │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│   docker-compose services    │  ← 後端服務群
│   (15+ containers)           │
└──────────────────────────────┘
```

每個面板不是獨立的工具。它們是同一個 PostgreSQL 的不同面向，透過不同的微服務暴露出來。

> **腦筋急轉彎**：Studio 裡點一個按鈕「Enable RLS」，背後實際執行了什麼 SQL？
>
> 答案：`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` — 就一行。但如果你不知道這行 SQL 的存在，你就永遠只是「會點按鈕的人」。

---

### 四個你必須記住的本地埠口

在本地開發時，你會一直跟這四個埠口打交道：

| 埠口 | 服務 | 你什麼時候會用到 |
|------|------|------------------|
| `54321` | PostgREST（REST API） | 前端呼叫 API、curl 測試 |
| `54322` | PostgreSQL（直接連線） | psql、DBeaver、資料庫 migration |
| `54323` | Studio（管理介面） | 你現在正在看的這個 |
| `54324` | Inbucket（本地郵件） | 測試註冊驗證、密碼重設 |

> 把這張表貼在螢幕旁邊。你之後會一直回來看。

---

## 模組一：Table Editor — 無程式碼的資料庫設計

> **你的大腦在想**：「我會寫 SQL，為什麼還要用 GUI？」
>
> **答案**：Table Editor 不是給不會 SQL 的人用的。它是讓你「看見」schema 的工具。你學的正規化，現在可以用拖拉的方式驗證。當你在 Table Editor 建立一個 Foreign Key，它會幫你寫出正確的 SQL。但重點是——你要知道它寫了什麼。

### 學習重點

- [x] 建立資料表並設定欄位型別
- [x] 理解 Schema 隔離（public vs 其他）
- [x] 建立 Foreign Key 關聯
- [x] 開啟 Realtime 與理解 WAL
- [x] 設定 Column Constraints

---

### Schema 隔離 — 為什麼有這麼多「房間」？

當你第一次打開 Table Editor，左上角有一個下拉選單，預設是 `public`。

點開它，你會看到好幾個 schema：

```
Schema 下拉選單
═══════════════════════════════
  public        ← 你的業務表放這裡
  auth          ← Supabase 的認證系統（別亂改）
  storage       ← 檔案管理
  extensions    ← PostgreSQL 擴充功能
  realtime      ← 即時訂閱系統
  vault         ← 加密金鑰管理
```

把 Schema 想像成一棟大樓裡的不同樓層：

- **`public`** = 你的辦公室。你的 customers、orders、products 都放在這裡。
- **`auth`** = 大樓保全室。Supabase 負責管理的認證系統。裡面有 `auth.users` 表，儲存所有登入的使用者。你可以讀，但別直接改。
- **`storage`** = 倉庫。管理上傳的檔案、圖片、附件。
- **`extensions`** = 機房。PostgreSQL 的擴充功能（pgcrypto、pg_trgm 等）裝在這裡。

> **腦筋急轉彎**：「為什麼 `auth.users` 和 `public.users` 要分開？」
>
> 因為 `auth.users` 的 ID 是 UUID（Supabase 決定的格式），而你的業務表可能想用 ULID 或其他格式。如果所有業務表都直接 FK 到 `auth.users`，你就被 UUID 綁死了。
>
> 解法？建一個 `public.users` 當橋接表，把 `auth.users` 的 UUID 轉成你自己的 ULID。這就是電商 Stage 2 的 **Auth Bridge 模式**。
>
> → 詳見 [e-Commerce/00_README.md](e-Commerce/00_README.md) Stage 2

---

### Foreign Key — 點擊建立關聯

現在來實際操作。我們要建立兩張表，然後用 Foreign Key 把它們連起來。

**Step 1：建立 `customers` 表**

1. 點擊 Table Editor 左上角的 "New Table"
2. 表名輸入 `customers`
3. 加入欄位：
   - `id` → Type: `text` → Primary Key: ✅
   - `name` → Type: `text`
   - `email` → Type: `text`
4. 點擊 "Save"

**Step 2：建立 `orders` 表**

1. 再點 "New Table"
2. 表名輸入 `orders`
3. 加入欄位：
   - `id` → Type: `text` → Primary Key: ✅
   - `customer_id` → Type: `text`
   - `total` → Type: `numeric`
4. 點擊 "Save"

**Step 3：在 `orders.customer_id` 建立 Foreign Key**

1. 點擊 `orders` 表
2. 找到 `customer_id` 欄位，點擊編輯
3. 找到 "Add Foreign Key Relation"
4. 選擇目標表 `customers`，目標欄位 `id`
5. 儲存

這個操作背後，Studio 幫你執行了這段 SQL：

```sql
ALTER TABLE public.orders
ADD CONSTRAINT orders_customer_id_fkey
FOREIGN KEY (customer_id) REFERENCES public.customers(id);
```

> **Head First 原則**：每個 GUI 操作背後都是 SQL。Studio 幫你寫 SQL，但你要知道它寫了什麼。如果哪天 Studio 壞了、或你需要寫 migration 腳本，你得能自己寫出來。

你可以切到 SQL Editor，貼上面那段 SQL，結果完全一樣。Table Editor 不是取代 SQL，而是讓你「先看見、再動手」。

---

### Realtime 開關與 WAL

在 Table Editor 裡點擊一張表的設定，你會看到一個 "Enable Realtime" 的開關。

這個開關做了什麼？讓我們拆解：

```
INSERT INTO orders (...) VALUES (...)
        │
        ▼
┌──────────────┐
│  WAL (disk)  │  ← PostgreSQL 寫入交易日誌
└──────┬───────┘
       │ replication slot
       ▼
┌──────────────┐
│  Realtime    │  ← 監聽 WAL 變更
│  Service     │
└──────┬───────┘
       │ WebSocket
       ▼
┌──────────────┐
│  前端瀏覽器  │  ← 即時收到新訂單通知
└──────────────┘
```

**WAL 是什麼？** Write Ahead Log，預寫式日誌。PostgreSQL 在真正把資料寫進表之前，會先把這筆操作記錄到 WAL。這原本是為了 crash recovery（資料庫崩潰後可以重播 WAL 恢復資料），但 Supabase 拿它做了一件聰明的事：

**用 replication slot 監聽 WAL 的變更，然後透過 WebSocket 推送到前端。**

所以當你在 Table Editor 開啟 "Enable Realtime"，你做了這幾件事：

1. 告訴 Realtime Service「請監聽這張表的 WAL 變更」
2. 任何對這張表的 INSERT / UPDATE / DELETE 都會被即時推送
3. 前端只要訂閱這張表，就能即時收到通知

> **腦筋急轉彎**：如果你有 20 張表但只有 3 張需要即時更新，你應該全開 Realtime 嗎？
>
> **不要！** 每張開啟 Realtime 的表都會增加 WAL 監聽的負擔。Replication slot 要追蹤更多變更、佔用更多記憶體。只開需要即時通知的表（例如聊天訊息、訂單狀態、庫存變動），其他表用傳統的 polling 就好。

---

### Column Constraints — 讓錯誤在源頭被攔截

在 Table Editor 新增或編輯欄位時，你可以設定以下限制：

| Constraint | 作用 | 範例 |
|-----------|------|------|
| **NOT NULL** | 不允許空值 | 名字不能空白 |
| **UNIQUE** | 不允許重複 | email 必須唯一 |
| **DEFAULT** | 自動填入預設值 | `created_at` 預設 `now()` |
| **CHECK** | 自定義驗證規則 | `price > 0` |

在 Table Editor 裡設定 CHECK constraint：

1. 編輯 `products` 表的 `price` 欄位
2. 在 Check Constraint 輸入：`price > 0`
3. 儲存

背後的 SQL：

```sql
ALTER TABLE public.products
ADD CONSTRAINT products_price_check
CHECK (price > 0);
```

現在試著插入一筆 `price = -10` 的商品——資料庫會直接擋住你。

> **連結回基礎觀念**：還記得「讓錯誤在最靠近源頭的地方被攔截」嗎？CHECK constraint 就是這個原則的實踐。
>
> 你的前端可以做 validation，但使用者可以用 DevTools 繞過。你的後端可以做 validation，但其他微服務可能忘記。但 CHECK constraint 在資料庫層，**任何人、任何管道寫入的資料都必須通過**。

---

### 動手練習 1：用 Table Editor 重現正規化範例

```
📝 Practice 1: 建立一個迷你電商 Schema

1. 建立 customers 表
   - id (text, PK)
   - name (text, NOT NULL)
   - email (text, UNIQUE, NOT NULL)
   - phone (text)

2. 建立 products 表
   - id (text, PK)
   - name (text, NOT NULL)
   - price (numeric, CHECK > 0)

3. 建立 orders 表
   - id (text, PK)
   - customer_id (text, FK → customers.id)
   - ordered_at (timestamptz, DEFAULT now())

4. 建立 order_items 表
   - id (text, PK)
   - order_id (text, FK → orders.id)
   - product_id (text, FK → products.id)
   - quantity (integer, CHECK > 0)

5. 驗證：
   ✅ 試著在 order_items 插入 quantity = -1，觀察錯誤訊息
   ✅ 試著在 orders 插入一個不存在的 customer_id，觀察錯誤訊息
   ✅ 試著在 customers 插入重複的 email，觀察錯誤訊息
```

> 如果這三個驗證都失敗了（意思是錯誤操作都被擋住了），恭喜——你的 schema 設計是正確的。

---

## 模組二：SQL Editor — 邏輯掌控者的主場

> **你的大腦在想**：「終於，可以寫 SQL 了！」
>
> 沒錯。Table Editor 讓你看見 schema，但 SQL Editor 讓你**掌控邏輯**。Function、Trigger、EXPLAIN ANALYZE——這些都是 SQL Editor 的地盤。

### 學習重點

- [x] 使用內建 SQL 範本
- [x] 執行 EXPLAIN ANALYZE 優化查詢
- [x] 定義 Function 和 Trigger
- [x] 理解「邏輯下沉到資料庫層」的策略

---

### 內建範本 — 別從零開始

打開 SQL Editor，你會看到一排範本按鈕和一個空白的編輯區。

點擊「Templates」或左側面板，Supabase 提供了好幾組預設範本：

```
SQL Editor 範本分類
═══════════════════════════════
  📌 Quick Start       → 基本 CRUD 範例
  🔒 RLS Policies     → 常見的權限設定模板
  🔍 Full-Text Search → 全文搜尋設定（tsvector + GIN）
  👥 RBAC Setup       → 角色權限系統範本
  📊 Functions        → 常用函數模板
```

這些範本的價值不在於複製貼上——而在於**讓你看到 Supabase 推薦的寫法**。尤其是 RLS 和 RBAC 的範本，它們展示了 Supabase 社群的最佳實踐。

---

### EXPLAIN ANALYZE — 你的查詢醫生

寫 SQL 很容易。寫**快的** SQL 很難。EXPLAIN ANALYZE 是你的查詢效能診斷工具。

在 SQL Editor 裡輸入：

```sql
EXPLAIN ANALYZE
SELECT o.id, c.name, o.total
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.total > 1000;
```

你會看到類似這樣的輸出：

```
Hash Join  (cost=1.09..36.59 rows=10 width=68) (actual time=0.045..0.048 rows=3 loops=1)
  Hash Cond: (o.customer_id = c.id)
  ->  Seq Scan on orders o  (cost=0.00..35.50 rows=10 width=46) (actual time=0.012..0.014 rows=3 loops=1)
        Filter: (total > 1000)
        Rows Removed by Filter: 47
  ->  Hash  (cost=1.05..1.05 rows=5 width=36) (actual time=0.008..0.008 rows=5 loops=1)
        ->  Seq Scan on customers c  (cost=0.00..1.05 rows=5 width=36) (actual time=0.003..0.004 rows=5 loops=1)
Planning Time: 0.150 ms
Execution Time: 0.080 ms
```

看不懂？沒關係。你只需要注意這幾個關鍵字：

| 關鍵字 | 意思 | 好 or 壞 |
|--------|------|----------|
| **Seq Scan** | 全表掃描（逐行檢查） | 小表 OK，大表很慢 |
| **Index Scan** | 用索引查找 | 快 |
| **cost** | 估計成本（startup..total） | 越小越好 |
| **actual time** | 實際執行時間（毫秒） | 越小越好 |
| **rows** | 處理的行數 | 越少越好 |
| **Rows Removed by Filter** | 被過濾掉的行數 | 太多代表缺索引 |

> **腦筋急轉彎**：如果 EXPLAIN 顯示 `Seq Scan on orders (cost=0.00..350.00 rows=100000)`，你應該怎麼做？
>
> **加 INDEX！**

```sql
CREATE INDEX idx_orders_total ON orders(total);

-- 再跑一次 EXPLAIN ANALYZE，觀察變化
EXPLAIN ANALYZE
SELECT o.id, c.name, o.total
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.total > 1000;
```

你應該會看到 `Seq Scan` 變成 `Index Scan` 或 `Bitmap Index Scan`。成本和時間都會大幅下降。

> **Head First 原則**：不要猜效能問題。用 EXPLAIN ANALYZE 看數據，讓證據告訴你該優化什麼。

---

### Function & Trigger — 邏輯下沉到資料庫層

這是一個重要的架構決策：**什麼邏輯應該放在應用層（Python/Node.js），什麼應該放在資料庫層？**

判斷標準很簡單：

> **如果一個邏輯「不管從哪裡寫入都要執行」，那它就應該放在資料庫層。**

舉例：每次更新一筆資料時，自動更新 `updated_at` 時間戳。

你可以在 Python 裡寫 `row.updated_at = datetime.now()`——但如果有人用 SQL Editor 直接改資料呢？如果另一個微服務用 PostgREST 改資料呢？

它們全都會繞過你的 Python 程式碼。

但它們繞不過 Trigger。

```sql
-- Step 1: 建立函數
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: 把函數綁到 Trigger
CREATE TRIGGER trg_orders_updated
BEFORE UPDATE ON public.orders
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

現在不管你從哪裡更新 `orders` 表——Studio、PostgREST、psql、Python——`updated_at` 都會自動更新。

在 SQL Editor 裡貼上上面的 SQL，按 "Run"。完成。

---

### generate_ulid() — 你在後面的 schema 都會看到它

在電商 schema 裡，幾乎每張表的 `id` 都用 ULID。生成 ULID 的函數長這樣：

```sql
CREATE OR REPLACE FUNCTION public.generate_ulid()
RETURNS TEXT AS $$
DECLARE
  timestamp  BYTEA = E'\\000\\000\\000\\000\\000\\000';
  unix_time  BIGINT;
  ulid       TEXT;
  encoding   TEXT = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  i          INT;
  byte_val   INT;
BEGIN
  -- 取得當前 Unix 時間（毫秒）
  unix_time = EXTRACT(EPOCH FROM clock_timestamp()) * 1000;

  -- 將時間戳編碼為 10 個字元
  ulid = '';
  FOR i IN REVERSE 9..0 LOOP
    ulid = ulid || substr(encoding, (unix_time % 32)::int + 1, 1);
    unix_time = unix_time / 32;
  END LOOP;

  -- 加上 16 個隨機字元
  FOR i IN 1..16 LOOP
    byte_val = (random() * 31)::int;
    ulid = ulid || substr(encoding, byte_val + 1, 1);
  END LOOP;

  RETURN ulid;
END;
$$ LANGUAGE plpgsql VOLATILE;
```

用法很簡單：

```sql
CREATE TABLE public.customers (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL
);
```

> **ULID vs UUID vs BIGINT** 的比較表在電商指南的 Stage 1 有完整說明。簡單記：ULID 可排序、比 UUID 短、不需要 sequence。在 Supabase 裡用 ULID 是推薦做法。

---

## 模組三：Authentication & RLS — 安全的事上磨練

> **你的大腦在想**：「RLS 是什麼？聽起來很可怕。」
>
> 其實不可怕。RLS 就是：**資料庫幫你加 WHERE 條件**。就這樣。

### 學習重點

- [x] 理解 RLS 的本質
- [x] 在 Studio 中建立 Policy
- [x] 理解 auth.uid() 的魔法
- [x] 使用 Inbucket (port 54324) 測試認證

---

### RLS 的本質 — 資料庫偷偷加 WHERE

假設你有一張 `orders` 表，裡面有所有使用者的訂單。

沒有 RLS 的時候：

```sql
SELECT * FROM orders;
-- 結果：看到所有人的訂單（100 筆）
```

開啟 RLS 並設定 Policy 之後：

```sql
SELECT * FROM orders;
-- 你寫的 SQL 完全沒變
-- 但結果：只看到自己的訂單（3 筆）
```

**你沒改你的查詢。是資料庫偷偷幫你加了 WHERE。**

```sql
-- 你寫的：
SELECT * FROM orders;

-- 資料庫實際執行的：
SELECT * FROM orders WHERE user_id = auth.uid();
```

這就是 RLS（Row Level Security）的全部概念。不可怕吧？

---

### 在 Studio 建立 Policy — 視覺化操作

**Step 1：啟用 RLS**

1. 到 Table Editor → 點擊 `orders` 表
2. 點擊右上角的 "RLS Disabled" 按鈕（或到 Authentication → Policies）
3. 點擊 "Enable RLS"

> ⚠️ **注意**：啟用 RLS 後，如果你沒有建立任何 Policy，**所有查詢都會回傳空結果**。因為 RLS 的預設行為是「全部禁止」。

**Step 2：建立 SELECT Policy**

1. 點擊 "New Policy"
2. 選擇 "Create a policy from scratch"（或用範本）
3. 設定：
   - Policy name: `Users can view own orders`
   - Allowed operation: `SELECT`
   - USING expression: `auth.uid()::text = user_id`
4. 點擊 "Review" → "Save Policy"

Studio 背後幫你執行了這段 SQL：

```sql
CREATE POLICY "Users can view own orders"
ON public.orders
FOR SELECT
USING (auth.uid()::text = user_id);
```

一行 SQL。但它保護了你所有的訂單資料。

---

### auth.uid() 的魔法

`auth.uid()` 是 Supabase 裡最重要的函數之一。它回傳**目前登入使用者的 UUID**。

但它的值從哪裡來？

```
使用者登入
    │
    ▼
GoTrue 服務產生 JWT Token
    │
    ▼
前端把 JWT 放在 Request Header
  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    │
    ▼
PostgREST 收到 Request
    │ 解析 JWT，取出 sub (user UUID)
    ▼
注入到 PostgreSQL session
    │ SET request.jwt.claim.sub = '...'
    ▼
auth.uid() 讀取這個 session 變數
    │
    ▼
RLS Policy 用 auth.uid() 過濾資料
```

所以 `auth.uid()` 不是魔法——它讀的是 JWT Token 裡的使用者 ID。PostgREST 在每次 API 請求時，自動把 JWT 裡的資訊注入到 PostgreSQL 的 session 變數裡。

> **腦筋急轉彎**：如果你用 `service_role` key 呼叫 API，`auth.uid()` 會回傳什麼？
>
> 答案：**NULL！** `service_role` key 是管理員金鑰，它完全繞過 RLS。這也是為什麼 `service_role` key 絕對不能暴露在前端程式碼裡。

---

### Helper Function — 連結電商 Stage 9

在電商 schema 裡，`auth.users` 的 UUID 和 `public.users` 的 ULID 是不同的。RLS Policy 裡需要一個 helper function 來做轉換：

```sql
CREATE OR REPLACE FUNCTION public.get_current_user_id()
RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT id FROM public.users WHERE auth_user_id = auth.uid()
$$;
```

為什麼用 `SECURITY DEFINER` + `STABLE`？

- **SECURITY DEFINER**：以函數擁有者（通常是 `postgres` 超級使用者）的權限執行。這樣函數可以讀取 `public.users` 表而不受 RLS 限制——否則會出現 RLS 遞迴（查 Policy 需要查 users，查 users 又需要查 Policy⋯⋯無限迴圈）。
- **STABLE**：告訴 PostgreSQL「同一個 transaction 內，這個函數的結果不會變」。PostgreSQL 就可以快取結果，同一次 request 裡不管你的 Policy 調用幾次 `get_current_user_id()`，只需要查一次 `users` 表。

> 這個 helper function 看起來不起眼，但它是整個 RLS 系統的基石。在電商 Stage 9 裡，幾乎每條 Policy 都用到它。

---

### Inbucket — 本地認證測試（port 54324）

在本地開發時，Supabase 不會發真正的 email。所有認證信件（驗證信、密碼重設、Magic Link）都會送到 **Inbucket**——一個本地的假 email 服務。

打開 `http://localhost:54324`，你會看到一個簡單的 email 收件匣。

**測試流程**：

1. 在你的應用（或用 API）執行 Sign Up
2. 打開 Inbucket (`localhost:54324`)
3. 你會看到一封驗證信
4. 點擊信裡的連結完成驗證
5. 使用者現在已認證，可以通過 RLS 檢查

```bash
# 用 curl 測試 Sign Up
curl -X POST 'http://localhost:54321/auth/v1/signup' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

> Inbucket 是本地開發的好朋友。它讓你不需要設定 SMTP 就能測試完整的認證流程。

---

### 動手練習 2：RLS 端到端測試

```
📝 Practice 2: 完整的 RLS 測試流程

1. 建立 users 表
   - id (text, PK, DEFAULT generate_ulid())
   - auth_user_id (uuid, UNIQUE, NOT NULL)
   - created_at (timestamptz, DEFAULT now())

2. 建立 notes 表
   - id (text, PK, DEFAULT generate_ulid())
   - user_id (text, FK → users.id, NOT NULL)
   - content (text, NOT NULL)

3. 對 notes 表啟用 RLS

4. 建立 Policy:
   "Users can view own notes"
   FOR SELECT
   USING (user_id IN (
     SELECT id FROM public.users WHERE auth_user_id = auth.uid()
   ))

5. 測試：
   ✅ 用 Inbucket (54324) 註冊一個測試帳號
   ✅ 用該帳號的 JWT 查詢 notes，驗證只能看到自己的筆記
   ✅ 用 service_role key 查詢，驗證可以看到所有筆記
```

---

## 模組四：API Docs — 資訊架構的自動化

> **你的大腦在想**：「我還要寫 API 文件？」
>
> **不用。Supabase 幫你寫好了。** 你每建一張表、每加一個欄位，API 文件就自動更新。

### 學習重點

- [x] 理解動態 API 文件的原理
- [x] 使用自動生成的程式碼片段
- [x] 用 curl 測試 PostgREST 接口

---

### 動態文件 — 你改 schema，文件自動跟著改

點擊 Studio 左側欄的 "API Docs"。

你會看到左邊列出了你所有的表——`customers`、`orders`、`products`⋯⋯點擊任何一張表，右邊就會顯示：

- **介紹**：表的欄位結構
- **Read rows**：SELECT 的程式碼片段（JavaScript、Dart、curl）
- **Insert rows**：INSERT 的程式碼片段
- **Update rows**：UPDATE 的程式碼片段
- **Delete rows**：DELETE 的程式碼片段

**關鍵點**：這些文件不是靜態的。它們是根據你的 schema **即時生成**的。你加一個欄位 `phone TEXT`，刷新 API Docs，新欄位就會出現在文件裡。

這背後的原理是 PostgREST 會讀取 PostgreSQL 的 `information_schema`（系統目錄），動態產生 API 端點和文件。

---

### curl 測試 — 直接跟 PostgREST 對話

API Docs 裡顯示的程式碼片段可以直接複製使用。但最直接的測試方式是 curl：

```bash
# 查詢 orders 表（所有訂單）
curl 'http://localhost:54321/rest/v1/orders?select=*' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# 查詢 orders 表（只要 total > 1000 的）
curl 'http://localhost:54321/rest/v1/orders?total=gt.1000' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# 新增一筆訂單
curl 'http://localhost:54321/rest/v1/orders' \
  -X POST \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{"customer_id": "01HXY...", "total": 999}'

# 更新訂單
curl 'http://localhost:54321/rest/v1/orders?id=eq.01HXY...' \
  -X PATCH \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"total": 1200}'
```

注意 URL 裡的查詢語法——`?total=gt.1000` 代表 `WHERE total > 1000`。這是 PostgREST 的過濾語法：

| PostgREST 語法 | SQL 等價 |
|----------------|---------|
| `eq.value` | `= value` |
| `gt.value` | `> value` |
| `lt.value` | `< value` |
| `gte.value` | `>= value` |
| `like.*keyword*` | `LIKE '%keyword%'` |
| `is.null` | `IS NULL` |
| `in.(a,b,c)` | `IN ('a','b','c')` |

> **記住埠口分工**：PostgREST 的端口是 **54321**（不是 Studio 的 54323）。
>
> - `54321` = API endpoint（PostgREST）— 你的前端呼叫這裡
> - `54322` = PostgreSQL direct — psql 或 DBeaver 連這裡
> - `54323` = Studio UI — 你現在在看的管理介面
> - `54324` = Inbucket（email）— 驗證信去這裡

> **腦筋急轉彎**：如果你加了 RLS 但用 `anon` key 測試，curl 會回傳什麼？
>
> 答案：**空陣列 `[]`**。因為 `anon` key 沒有對應的使用者身份，`auth.uid()` 回傳 NULL，Policy 的 USING 條件永遠為 false。你需要用已認證使用者的 JWT Token 取代 `anon` key 才能看到資料。

---

## 模組五：Storage & Edge Functions

### Storage — S3 相容的存儲桶

點擊 Studio 左側的 "Storage"，你可以建立和管理存儲桶（Bucket）。

**建立 Bucket**：

1. 點擊 "New bucket"
2. 輸入名稱（例如 `avatars`）
3. 選擇是否公開：
   - **Public**：任何人有 URL 就能存取（適合大頭照、商品圖片）
   - **Private**：需要認證才能存取（適合文件、發票）

公開的 Bucket 可以直接用 URL 存取：
```
http://localhost:54321/storage/v1/object/public/avatars/user123.jpg
```

私有的 Bucket 需要帶 JWT Token：
```bash
curl 'http://localhost:54321/storage/v1/object/avatars/private-doc.pdf' \
  -H "Authorization: Bearer USER_JWT_TOKEN"
```

**Storage RLS — 跟 Table 一樣的保護機制**

Storage 的檔案也可以用 RLS 保護。它的 Policy 寫在 `storage.objects` 表上：

```sql
-- 使用者只能上傳到自己的資料夾
CREATE POLICY "Users can upload to own folder"
ON storage.objects
FOR INSERT
WITH CHECK (
  bucket_id = 'avatars'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 使用者只能讀取自己的檔案
CREATE POLICY "Users can view own files"
ON storage.objects
FOR SELECT
USING (
  bucket_id = 'avatars'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

> **注意**：`storage.foldername(name)` 回傳檔案路徑的資料夾名稱陣列。如果檔案路徑是 `user-uuid-123/avatar.jpg`，那 `(storage.foldername(name))[1]` 就是 `user-uuid-123`。

---

### Edge Functions — 靠近外部世界的邏輯

Edge Functions 是用 Deno（TypeScript Runtime）寫的 serverless 函數。它們不在 Studio 裡撰寫，而是用 CLI：

```bash
# 建立新的 Edge Function
supabase functions new hello-world

# 本地啟動（開發模式）
supabase functions serve hello-world
```

但 Studio 提供了 Edge Functions 的**監控界面**：

- 呼叫次數統計
- 錯誤率監控
- 執行日誌查看
- 部署狀態

> **腦筋急轉彎**：什麼邏輯該放 Edge Function，什麼該放 Database Function？

```
判斷標準
═══════════════════════════════════════════════════

  靠近「資料」的邏輯 → Database Function
  ─────────────────────────────────────
  ✅ 資料驗證（CHECK、Trigger）
  ✅ 計算衍生欄位（updated_at、total_amount）
  ✅ RLS helper function（get_current_user_id）
  ✅ 複雜查詢封裝（搜尋、統計報表）

  靠近「外部世界」的邏輯 → Edge Function
  ─────────────────────────────────────
  ✅ 呼叫第三方 API（金流、物流、通知）
  ✅ 發送 email / SMS / Push Notification
  ✅ 處理 Webhook（接收外部系統的事件）
  ✅ 複雜的業務流程（涉及多個外部系統）
```

簡單記：**Database Function 不能上網，Edge Function 可以。** 如果你的邏輯需要跟外部服務溝通，用 Edge Function。如果純粹是資料操作，用 Database Function。

---

## 模組整合：五大模組的協作關係

到這裡，你已經走過了 Studio 的五大模組。讓我們看看它們怎麼協作：

```
                    ┌─────────────────────┐
                    │    Table Editor      │
                    │  (定義 Schema)       │
                    └──────────┬──────────┘
                               │ schema 變更會觸發
                    ┌──────────▼──────────┐
                    │    SQL Editor        │
                    │  (Function/Trigger)  │
                    │  (Index/EXPLAIN)     │
                    └──────────┬──────────┘
                               │ 邏輯就緒
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
    │  Auth & RLS    │ │  API Docs    │ │   Storage    │
    │  (安全策略)    │ │  (自動文件)  │ │  (檔案管理)  │
    └────────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
             └────────────────┼────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Edge Functions     │
                    │  (外部整合)         │
                    └────────────────────┘
```

**它們不是獨立的工具。它們是同一個 PostgreSQL 的不同面向。**

- Table Editor 定義了 schema → API Docs 自動產生 CRUD 文件
- SQL Editor 寫了 RLS helper function → Auth 面板的 Policy 可以使用它
- Table Editor 開啟 Realtime → Realtime Service 開始監聽 WAL
- Storage 的 RLS → 用的是跟 Table 一樣的 Policy 語法
- Edge Functions 呼叫 PostgREST API → 受到跟前端一樣的 RLS 保護

理解這個整體架構，比學會每個按鈕怎麼按更重要。

---

## 總結：Studio 的三層理解

```
Level 1 — 會操作
════════════════════
  「我知道怎麼在 Table Editor 建表、在 SQL Editor 跑查詢。」
  → 大部分人停在這裡

Level 2 — 知道背後發生什麼
════════════════════
  「我知道 Enable RLS 按鈕背後執行了 ALTER TABLE ... ENABLE ROW LEVEL SECURITY。
   我知道 Realtime 開關背後是 WAL + replication slot。
   我知道 API Docs 是 PostgREST 讀 information_schema 動態生成的。」
  → 讀完這份指南，你應該在這裡

Level 3 — 能自己建構
════════════════════
  「我不需要 Studio 也能完成所有操作。
   Studio 壞了，我用 psql + curl 一樣能把系統跑起來。
   Studio 是我的加速器，不是我的拐杖。」
  → 這是你的目標
```

---

## 自我檢查清單

```
□ 我能在 Table Editor 建立表並設定 FK 關聯
□ 我知道 public / auth / storage schema 的分工
□ 我能用 SQL Editor 跑 EXPLAIN ANALYZE 並看懂結果
□ 我能建立一個 Trigger 自動更新 updated_at
□ 我知道 RLS 的本質是「資料庫幫你加 WHERE」
□ 我能在 Studio 中啟用 RLS 並建立 Policy
□ 我理解 auth.uid() 的值從哪裡來（JWT → session 變數）
□ 我用過 Inbucket (54324) 測試本地認證流程
□ 我能用 curl 測試 PostgREST API
□ 我知道四個本地埠口的分工 (54321 / 54322 / 54323 / 54324)
□ 我知道 SECURITY DEFINER 和 STABLE 的用途
□ 我知道 Database Function 和 Edge Function 的分工原則
□ 我理解 Storage RLS 跟 Table RLS 用的是同一套機制
```

如果你能勾完這 13 項，你已經不只是「會用 Studio」——你理解了 Studio 背後的架構。

---

## 下一步

> Studio 操作熟悉了。接下來，我們要用它來蓋一個真正的電商資料庫。
> 10 個 Stage、20 張表、從 ULID 到 RLS 全部實戰。
>
> → [e-Commerce/00_README.md](e-Commerce/00_README.md)
