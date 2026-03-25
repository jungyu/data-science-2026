# Head First Auth & RLS — 安全不是選配，是標配

> **"如果你的 API 沒有 RLS，任何人都能讀到所有人的資料。"**
>
> 這不是誇張。Supabase 的 `anon` key 是公開的（會放在前端 JavaScript 裡）。
> 沒有 RLS 的表 + anon key = **裸奔**。
>
> 你的大腦在想：「真的有這麼嚴重嗎？」
>
> 是的。任何人打開瀏覽器 DevTools，找到你的 anon key 和 Supabase URL，
> 就可以用 `supabase.from('orders').select('*')` 撈到**所有人的訂單**。
> 除非你有 RLS。

---

## 前置要求

- 已完成 `03_sql-editor-mastery.md`（會用 SQL Editor、建過 Function 和 Trigger）
- 已建立 `generate_ulid()` 和 `set_updated_at()` function（03 的 Part 5）
- Docker 跑著（`supabase start`）
- 瀏覽器打開 Studio `http://localhost:54323`

> 如果要跑電商 RLS 範例，需先執行 `../migrations/002_shop_schema.sql`。

---

## Part 1: 理解 Supabase Auth 架構

先看全貌。Supabase 的認證流程長這樣：

```
使用者註冊/登入
       │
       ▼
┌──────────────┐
│   GoTrue     │  ← Auth 服務 (Docker 內部 port 9999，經 API gateway 暴露於 54321)
│  (Auth API)  │     處理註冊、登入、JWT 簽發
└──────┬───────┘
       │ 寫入
       ▼
┌──────────────┐
│ auth.users   │  ← Supabase 管理的 schema（你不能改）
│ (UUID PK)    │     存放 email, password hash, metadata
└──────┬───────┘
       │ trigger
       ▼
┌──────────────┐
│ public.users │  ← 你的 Bridge Table (ULID PK)
│ (Auth Bridge)│     存放自訂欄位：display_name, avatar, role...
└──────────────┘
```

### 三層架構拆解

| 層級 | Schema | 誰管 | 你能改嗎 |
|------|--------|------|----------|
| GoTrue API | — | Supabase | 不能 |
| `auth.users` | `auth` | Supabase | 不能（只能讀） |
| `public.users` | `public` | 你 | 可以隨便改 |

> **腦筋急轉彎：「為什麼不直接用 `auth.users`？」**
>
> 因為：
> 1. 你**不能**改 `auth` schema（不能加欄位）
> 2. `auth.users` 的主鍵是 UUID，你的系統可能用 ULID
> 3. 你需要自訂欄位（display_name, role, preferences...）
> 4. Bridge table 讓你**解耦** — auth 系統換了，你的 public.users 不用動
>
> 結論：`auth.users` 是 Supabase 的事。`public.users` 是你的事。中間用 Trigger 同步。

---

## Part 2: 在 Studio 中管理 Authentication

### Step by Step

1. **打開 Authentication 模組**：左側選單點「Authentication」（🔐 鎖頭圖示）
2. **Users 列表**：你會看到所有已註冊的使用者
3. **手動新增使用者**：點 "Add user" → 輸入 email + password → "Create user"
4. **查看使用者詳情**：點任一使用者 → 看到 UUID、email、metadata、登入時間
5. **Providers 設定**：左側 "Providers" → 啟用 Email、Google、GitHub 等登入方式

### 你的大腦在想：「本地開發需要設定 OAuth Provider 嗎？」

不用。本地開發用 **Email + Password** 就夠了。而且 Supabase 本地版內建了一個超好用的工具：**Inbucket**。

---

## Part 3: Inbucket — 本地認證測試神器 (port 54324)

Inbucket 是一個假的 email 伺服器。你在本地註冊帳號時，驗證信不會真的寄出去，而是被 Inbucket 攔截。

```bash
# 打開 Inbucket
open http://localhost:54324
```

### 完整測試流程

```
1. 在 Studio Authentication → "Add user"
   → email: alice@test.com / password: test1234
   → 勾選 "Auto Confirm"（或不勾，用 Inbucket 驗證）

2. 如果沒勾 Auto Confirm：
   → 打開 Inbucket (localhost:54324)
   → 在左側找到 alice@test.com 的信箱
   → 打開驗證信 → 點擊 "Confirm your mail"

3. 回到 Studio Authentication
   → alice 的狀態變成 "Confirmed" ✅

4. 重複步驟，建立更多測試帳號
```

#### 動手做

```
📝 Exercise 3.1: 建立測試帳號
1. 在 Studio Authentication 新增 3 個使用者：
   - alice@test.com (password: test1234)
   - bob@test.com (password: test1234)
   - admin@test.com (password: test1234)
2. 打開 Inbucket (localhost:54324)
3. 確認每個帳號都收到驗證信
4. 點擊驗證連結，確認帳號
5. 回到 Studio → 三個帳號都顯示 Confirmed
```

> **Head First 小技巧**：本地測試帳號的密碼都用一樣的就好（`test1234`）。別浪費腦力在這裡。但千萬不要把這個習慣帶到正式環境。

---

## Part 4: RLS 的本質（一句話版）

RLS = Row Level Security = **資料庫自動幫你加 WHERE 條件**。

看這個對比：

```sql
-- 沒有 RLS
SELECT * FROM orders;
-- 結果：10000 筆（所有人的訂單）

-- 有 RLS + 以 alice 身分查詢
SELECT * FROM orders;
-- 資料庫偷偷變成 ↓
SELECT * FROM orders WHERE user_id = auth.uid();
-- 結果：3 筆（只有 alice 的訂單）
```

**你沒改查詢語句。是資料庫偷偷幫你加了 `WHERE`。這就是 RLS。**

> **你的大腦在想：「那應用程式端也要加 WHERE 嗎？」**
>
> 可以加（效能上沒差），但重點是：**就算你忘了加，RLS 也會幫你擋住。**
> 這就是「Defense in Depth」—— 多層防護，任何一層都能獨立生效。

### RLS 的兩個元件

| 元件 | 做什麼 | 類比 |
|------|--------|------|
| **Enable RLS** | 啟用保護（預設全部拒絕） | 裝鎖 |
| **Policy** | 定義誰能做什麼 | 發鑰匙 |

啟用 RLS 但沒建 Policy = 所有人都被鎖在外面（包括 anon）。
建了 Policy 但沒啟用 RLS = 門沒鎖，Policy 等於裝飾品。

**兩個都要做。**

---

## Part 5: 在 Studio 建立 RLS Policy

### GUI 方式（適合初學）

```
1. Table Editor → 選擇目標表（例如 experiments）
2. 右上角找到 "RLS" 按鈕（或表設定裡的 "Row Level Security"）
3. 點 "Enable RLS"
   → 背後執行了 ALTER TABLE public.experiments ENABLE ROW LEVEL SECURITY;
4. 點 "New Policy"
5. 選擇操作類型（SELECT / INSERT / UPDATE / DELETE）
6. 填寫 USING expression（決定哪些行可見）
7. 給 Policy 取個名字 → 保存
```

### SQL 方式（正式環境推薦）

為什麼用 SQL？因為 SQL 可以放進 migration 檔，可以 version control，可以 code review。

---

### 四種常見 Policy 模式

#### 模式 1：使用者只能看自己的資料

最常見的模式。每筆資料有 `user_id`，使用者只能看到 `user_id` 等於自己的那些行。

```sql
-- 先確保 RLS 啟用
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

-- 建立 SELECT Policy
CREATE POLICY "Users can read own orders"
ON public.orders FOR SELECT
USING (auth.uid()::text = user_id);
```

拆解：
- `FOR SELECT`：這個 Policy 只管 SELECT 操作
- `USING (...)`：回傳 `true` 的行才看得到
- `auth.uid()`：目前登入使用者的 UUID（從 JWT 取得）
- `::text`：型別轉換（因為 `auth.uid()` 是 UUID，`user_id` 可能是 TEXT）

---

#### 模式 2：使用者只能修改自己的資料

```sql
CREATE POLICY "Users can update own orders"
ON public.orders FOR UPDATE
USING (auth.uid()::text = user_id)        -- 哪些行可以被選中修改
WITH CHECK (auth.uid()::text = user_id);  -- 修改後的值也必須符合
```

> **腦筋急轉彎：`USING` 和 `WITH CHECK` 有什麼不同？**
>
> - `USING`：過濾**現有**資料（修改前的行）
> - `WITH CHECK`：驗證**新**資料（修改後的行）
>
> 為什麼兩個都要？防止使用者把 `user_id` 改成別人的 UUID，把資料「轉移」給別人。

---

#### 模式 3：任何人都能讀（公開資料）

```sql
CREATE POLICY "Anyone can read products"
ON public.products FOR SELECT
USING (true);  -- 永遠回傳 true = 所有人都能看
```

適合：商品列表、公開文章、公告。

---

#### 模式 4：Service Role 繞過 RLS

`service_role` key 是後端專用的金鑰，它**自動繞過所有 RLS**。

```
anon key        → 受 RLS 限制（前端用）
authenticated   → 受 RLS 限制（登入後的前端用）
service_role    → 繞過 RLS（後端用）
```

> **重要**：`service_role` key **絕對不能**放在前端。它有上帝視角，能看到所有資料。
> 只能放在後端伺服器或 Edge Functions 裡。

---

### 電商 RLS 實戰 — 從 Shop Schema 學 Policy 設計

> 以下範例來自 `../migrations/002_shop_schema.sql` Stage 9。
> 這是真正生產級的 RLS，不是教科書範例。

#### Auth Bridge Helper（最關鍵的函數）

```sql
-- auth UUID → 業務 ULID（所有 RLS Policy 都用這個）
CREATE OR REPLACE FUNCTION public.get_current_user_id()
RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$ SELECT id FROM public.users WHERE auth_user_id = (SELECT auth.uid()) LIMIT 1 $$;
```

> 為什麼不直接在 Policy 裡寫 `auth.uid()`？因為業務表的 FK 是 ULID（TEXT），
> auth.uid() 回傳 UUID。每次 Policy 都做 JOIN 轉換 = N+1 效能災難。
> Helper function + STABLE 快取 = 一個 transaction 只查一次。

#### 電商 Policy 範例：多角色分層

```sql
-- 1. 商品：所有人都能看已上架的（公開資料）
CREATE POLICY "Anyone can view published products"
ON public.products FOR SELECT
USING (status = 'publish' AND deleted_at IS NULL);

-- 2. 商品：作者可以看自己的草稿
CREATE POLICY "Authors can view own drafts"
ON public.products FOR SELECT
USING (author_id = public.get_current_user_id());

-- 3. 訂單：顧客只能看自己的訂單
CREATE POLICY "Customers view own orders"
ON public.orders FOR SELECT
USING (customer_id = public.get_current_user_id());

-- 4. 訂單：店員可以看自己店的訂單
CREATE POLICY "Staff view store orders"
ON public.orders FOR SELECT
USING (
  store_id IN (
    SELECT store_id FROM public.store_staff
    WHERE staff_id = public.get_current_user_id()
      AND deleted_at IS NULL
  )
);

-- 5. 評論：顧客只能新增自己的評論
CREATE POLICY "Customers create own reviews"
ON public.reviews FOR INSERT
WITH CHECK (customer_id = public.get_current_user_id());

-- 6. service_role：後台管理全權限
CREATE POLICY "Service role full access"
ON public.products FOR ALL
USING (auth.role() = 'service_role');
```

> **腦筋急轉彎：Policy 4 裡的子查詢會不會很慢？**
>
> 會。如果 store_staff 很大又沒有 Index，每次 SELECT orders 都要全掃 store_staff。
> 解法：確保 `idx_store_staff_staff` Index 存在（電商 schema 已建好）。

#### GRANT — 別忘了權限

```sql
-- RLS Policy 定義「誰能看什麼」
-- GRANT 定義「誰能碰這張表」
GRANT SELECT ON public.products TO anon;       -- 未登入也能瀏覽商品
GRANT SELECT ON public.products TO authenticated;
GRANT ALL ON public.products TO service_role;

-- 訂單只有登入使用者能看
GRANT SELECT, INSERT ON public.orders TO authenticated;
GRANT ALL ON public.orders TO service_role;
```

> **Head First 原則**：RLS Policy + GRANT 是兩道鎖。Policy 控制行級別（哪些 rows），GRANT 控制表級別（能不能碰這張表）。兩個都要設。

---

### 完整的 INSERT + SELECT 範例

```sql
-- 建立 notes 表
CREATE TABLE public.notes (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 啟用 RLS
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- Policy: 使用者只能 SELECT 自己的 notes
CREATE POLICY "Users read own notes"
ON public.notes FOR SELECT
USING (auth.uid()::text = user_id);

-- Policy: 使用者只能 INSERT 自己的 notes
CREATE POLICY "Users insert own notes"
ON public.notes FOR INSERT
WITH CHECK (auth.uid()::text = user_id);
```

> 注意 INSERT 只有 `WITH CHECK`，沒有 `USING`。因為 INSERT 沒有「現有資料」可以過濾。

---

## Part 6: Helper Function（避免 N+1 和遞迴問題）

當你的 RLS Policy 需要查詢另一張表（例如從 `public.users` 查角色），很容易遇到兩個問題：

1. **N+1 問題**：每一行都觸發一次子查詢
2. **無限遞迴**：RLS Policy 查的表本身也有 RLS → 觸發另一個 Policy → 又查表 → 迴圈

解法：用 `SECURITY DEFINER` function。

```sql
CREATE OR REPLACE FUNCTION public.get_current_user_id()
RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT id FROM public.users WHERE auth_user_id = auth.uid()
$$;
```

### 關鍵字拆解

| 關鍵字 | 意思 | 為什麼重要 |
|--------|------|-----------|
| `SECURITY DEFINER` | 用 **function 擁有者**（通常是 superuser）的權限執行 | 繞過 RLS，避免遞迴 |
| `STABLE` | 同一 transaction 內，相同輸入回傳相同結果 | PostgreSQL 可以**快取**結果，避免 N+1 |
| `LANGUAGE sql` | 用純 SQL 寫的 function | 比 plpgsql 簡單，效能也好 |

### 使用方式

```sql
-- 在 RLS Policy 中使用 helper function
CREATE POLICY "Users read own data"
ON public.orders FOR SELECT
USING (user_id = public.get_current_user_id());
```

> **你的大腦在想：「`SECURITY DEFINER` 不危險嗎？」**
>
> 是有風險。它繞過了 RLS 保護。所以要注意：
> 1. Function 內部的查詢要**極度簡單**（只查必要的東西）
> 2. 不要接受使用者輸入當參數（避免 SQL Injection）
> 3. 只在**確實需要繞過 RLS** 的時候使用

---

## Part 7: RLS 測試三步驟

寫好 Policy 之後，怎麼確認它真的有效？

### Step 1: 確認 RLS 已啟用

```sql
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

`rowsecurity = true` 就對了。如果是 `false`，RLS 沒啟用，任何 Policy 都不會生效。

### Step 2: 用 `SET ROLE` 切換角色測試

```sql
-- 切換到 anon 角色（模擬未登入的前端請求）
SET ROLE anon;

-- 查詢 — 如果 RLS 正確，應該看不到任何資料
SELECT * FROM orders;

-- 記得切回來！
RESET ROLE;
```

### Step 3: 模擬已登入使用者

```sql
-- 模擬 alice 登入
SET LOCAL role = 'authenticated';
SET LOCAL request.jwt.claims = '{"sub": "alice-uuid-here"}';

-- 查詢 — 應該只看到 alice 的資料
SELECT * FROM orders;

-- 切回來
RESET ROLE;
```

> **Head First 原則**：每次修改 RLS Policy 後，都要跑這三步驟。自動化測試更好，但手動測試是最低要求。

#### 動手做

```
📝 Exercise 7.1: RLS 測試
1. 確認 experiments 表的 RLS 狀態
2. 如果沒啟用，執行 ALTER TABLE ... ENABLE ROW LEVEL SECURITY
3. 建立一個 SELECT Policy（使用者看自己的實驗）
4. 用 SET ROLE anon 測試 → 應該看不到資料
5. 用 SET ROLE authenticated + JWT claims 測試 → 應該看到對應的資料
6. RESET ROLE 切回管理員
```

---

## Part 8: 常見錯誤排解

| 症狀 | 原因 | 解法 |
|------|------|------|
| API 回傳空陣列 `[]` | RLS 啟用了，但沒有建 SELECT Policy | 建立 `FOR SELECT` Policy |
| 所有人都能看到所有資料 | RLS 根本沒啟用 | `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` |
| Function 報錯 `infinite recursion` | RLS Policy 查了另一張有 RLS 的表 | 用 `SECURITY DEFINER` helper function |
| `service_role` 也被 RLS 擋住 | 不可能（除非你用了 `anon` key） | 檢查你實際使用的 key 是哪一個 |
| INSERT 被拒絕但沒錯誤訊息 | Policy 有 `WITH CHECK` 但條件不符 | 確認插入的 `user_id` 等於 `auth.uid()` |
| UPDATE 部分成功部分失敗 | `USING` 通過但 `WITH CHECK` 沒通過 | 確認更新後的資料也符合 Policy |
| `auth.uid()` 回傳 NULL | JWT 無效或過期 | 重新登入取得新 token |

### 除錯小技巧

```sql
-- 檢查某張表有哪些 Policy
SELECT
  policyname,
  cmd AS operation,
  qual AS using_expression,
  with_check AS with_check_expression
FROM pg_policies
WHERE tablename = 'orders';
```

```sql
-- 確認 auth.uid() 有值
SELECT auth.uid();
-- 如果回傳 NULL，代表你沒有在 authenticated 角色下，或 JWT 無效
```

---

## Part 9: 動手做 — 完整 RLS 端到端練習

```
📝 Exercise 9.1: RLS 完整測試

目標：從零建立一個有 RLS 保護的 notes 表，並驗證安全性。

=== 階段一：建表 ===
1. 打開 SQL Editor，新增 tab "rls_exercise"
2. 建立 public.notes 表：
   - id TEXT PRIMARY KEY DEFAULT generate_ulid()
   - user_id TEXT NOT NULL
   - content TEXT NOT NULL
   - created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

=== 階段二：啟用 RLS + 建立 Policy ===
3. 啟用 RLS：
   ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;
4. 建立 SELECT Policy：使用者只能看自己的 notes
5. 建立 INSERT Policy：使用者只能新增自己的 notes

=== 階段三：準備測試資料 ===
6. 先查出 alice@test.com 和 bob@test.com 的 auth UUID：
   SELECT id, email FROM auth.users;
7. 以管理員身分插入測試資料：
   INSERT INTO notes (user_id, content) VALUES
     ('alice-uuid', 'Alice 的第一則筆記'),
     ('alice-uuid', 'Alice 的第二則筆記'),
     ('bob-uuid',   'Bob 的筆記');

=== 階段四：驗證 RLS ===
8. 模擬 alice 查詢：
   SET LOCAL role = 'authenticated';
   SET LOCAL request.jwt.claims = '{"sub": "alice-uuid"}';
   SELECT * FROM notes;
   → 預期：2 筆（Alice 的兩則筆記）
   RESET ROLE;

9. 模擬 bob 查詢：
   SET LOCAL role = 'authenticated';
   SET LOCAL request.jwt.claims = '{"sub": "bob-uuid"}';
   SELECT * FROM notes;
   → 預期：1 筆（Bob 的筆記）
   RESET ROLE;

10. 模擬 anon（未登入）查詢：
    SET ROLE anon;
    SELECT * FROM notes;
    → 預期：0 筆
    RESET ROLE;

11. 管理員查詢（不切角色）：
    SELECT * FROM notes;
    → 預期：3 筆（全部）

=== 階段五：驗證 INSERT 保護 ===
12. 模擬 alice 嘗試幫 bob 新增 note：
    SET LOCAL role = 'authenticated';
    SET LOCAL request.jwt.claims = '{"sub": "alice-uuid"}';
    INSERT INTO notes (user_id, content) VALUES ('bob-uuid', '假裝是 Bob');
    → 預期：被 WITH CHECK 擋住，INSERT 失敗
    RESET ROLE;
```

> **完成這個練習，你就真正理解 RLS 了。** 不是「知道 RLS 是什麼」，而是「手上做過一遍」。
> Head First 的核心理念：**做過才算懂。**

### 電商 RLS 端到端測試

```
📝 Exercise: 用電商 Schema 測試 RLS
前提：已跑過 ../migrations/002_shop_schema.sql

1. 在 Inbucket 註冊 customer@test.com（模擬顧客）
2. 在 Inbucket 註冊 staff@test.com（模擬店員）
3. 用 SQL Editor（service_role）把 staff 加入 store_staff
4. 用 service_role 建立 3 筆訂單：2 筆屬於 customer，1 筆屬於其他人
5. 模擬 customer 登入 → 查詢 orders → 應只看到 2 筆
6. 模擬 staff 登入 → 查詢 orders → 應看到該店所有訂單
7. 用 anon key 查詢 products → 應只看到 status = 'publish' 的
8. 用 anon key 查詢 orders → 應看到 0 筆（anon 沒有 GRANT）
```

---

## 自我檢查清單

```
□ 我理解 auth.users → public.users 的 Bridge 架構
□ 我能在 Studio Authentication 中新增/管理使用者
□ 我會用 Inbucket 測試本地認證流程
□ 我能用一句話解釋 RLS：「資料庫自動幫你加 WHERE」
□ 我知道 Enable RLS + Policy 兩個都要做
□ 我能寫出四種常見 Policy 模式（讀自己、改自己、公開讀、service_role 繞過）
□ 我理解 USING vs WITH CHECK 的差別
□ 我知道什麼時候需要 SECURITY DEFINER helper function
□ 我能用 SET ROLE + JWT claims 測試 RLS
□ 我能看懂 pg_policies 和 pg_tables 的診斷結果
□ 我知道 anon key vs service_role key 的權限差異
□ 我完成了端到端 RLS 練習（Part 9）
```

---

## 下一步

Auth & RLS 是 Supabase 安全的基石。你現在知道怎麼保護資料了。

接下來學習如何與外界互動：

→ `05_api-storage-functions.md` — 自動產生的 REST API + 檔案儲存管理。

> **最後提醒**：每次建新表，第一件事就是 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`。
> 先鎖門，再決定發給誰鑰匙。這應該變成你的肌肉記憶。
