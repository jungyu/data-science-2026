# Head First API 設計模式 — Gateway Architecture

> **"你不會讓客人直接走進廚房點菜。你給他一份菜單，他點了，廚房做好送出來。Public function 就是那份菜單。"**

這份指南涵蓋 [`006_public_api.sql`](../migrations/006_public_api.sql) 的**設計哲學**。
不講個別 function，講的是「為什麼每一個 function 都長這個樣子」。

---

## 搭配閱讀

| 你在讀的 | 學什麼 |
|----------|--------|
| PostgREST Gateway Pattern | 為什麼用 function 而不是直接 SELECT |
| SECURITY DEFINER | 為什麼 function 要用 owner 權限執行 |
| search_path 防禦 | 為什麼每個 function 都 SET search_path |
| 命名慣例 | 為什麼叫 `api_{domain}_{action}` |
| GRANT 策略 | 誰能呼叫什麼 |

---

## 1. PostgREST Gateway Pattern

### 問題：前端怎麼碰到資料？

在 Supabase 裡，PostgREST 是連接前端和 PostgreSQL 的 HTTP 閘道。它有一個關鍵限制：

> **PostgREST 只暴露 `public` schema 的 table、view、function。**

我們的業務表全部在 `shop.*`、`crawler.*`、`rag.*`、`analytics.*`。
前端**完全看不到**這些表。這是故意的。

### 解法：薄包裝 Function

```
前端 (supabase.rpc)
   ↓ HTTP POST
PostgREST
   ↓ 只看得到 public schema
public.api_shop_list_products()     ← 這就是「窗口」
   ↓ 內部呼叫
shop.products (JOIN shop.product_images, shop.reviews)
   ↓ 回傳整理好的 TABLE
前端拿到乾淨的 JSON
```

每個 `public.api_*` function 做三件事：

1. **存取控制**——透過 GRANT 決定 anon / authenticated 誰能呼叫
2. **資料整形**——JOIN、聚合、JSON 打包，前端不用自己拼
3. **邏輯封裝**——改 schema 不影響前端，只要 function 簽名不變

> ### 🧠 你的大腦在想…
>
> 「這不就是 API controller 嗎？」
>
> 對。你可以把 `public` schema 想成你的 controller 層，
> 把 `shop.*` 想成 service / repository 層。
> 差別是：這裡沒有 Node.js / Express / NestJS——
> 全部在資料庫裡完成，PostgREST 自動幫你產生 HTTP endpoint。

---

## 2. SECURITY DEFINER — 為什麼每個 function 都有這行？

打開 SQL 任何一個 function，你都會看到這個組合：

```sql
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
```

一行一行拆解：

### `LANGUAGE SQL`

這個 function 的 body 是純 SQL。不是 PL/pgSQL（不需要 `BEGIN...END`、變數宣告）。

**為什麼不用 PL/pgSQL？** 因為這些 function 都是「SELECT → 回傳」，不需要條件分支、迴圈、例外處理。純 SQL 更快（PostgreSQL 可以 inline 優化），也更好讀。

### `STABLE`

告訴 PostgreSQL：「這個 function 在同一個 transaction 內，對同樣的參數會回傳同樣的結果。」

**效果**：PostgreSQL 可以在同一個 query 裡快取結果，避免重複執行。所有讀取型 API 都應該標 `STABLE`。（寫入型用 `VOLATILE`。）

### `SECURITY DEFINER` — 重點中的重點

```
┌─────────────────────────────────────────────────┐
│  預設模式：SECURITY INVOKER                       │
│  → function 用「呼叫者」的權限執行                   │
│  → anon 呼叫 = anon 權限 = 碰不到 shop.products   │
│  → 結果：Permission denied ❌                     │
├─────────────────────────────────────────────────┤
│  我們用：SECURITY DEFINER                         │
│  → function 用「function owner」的權限執行          │
│  → owner 通常是 postgres（superuser）              │
│  → 可以讀 shop.products，但只回傳 function 定義的欄位│
│  → 結果：前端拿到精確控制的資料 ✅                   │
└─────────────────────────────────────────────────┘
```

**類比**：SECURITY DEFINER 就像餐廳的服務生。客人（anon）不能進廚房，但服務生可以。客人透過菜單點餐，服務生進廚房拿菜，端出來的是整理好的盤子，不是整鍋原料。

> ### ⚠️ 安全警告
>
> SECURITY DEFINER 是強力工具。用錯了等於開後門。
>
> **安全使用守則**：
> 1. function body 裡只做 SELECT，不做 INSERT / UPDATE / DELETE
> 2. WHERE 條件嚴格過濾（`status = 'publish'`、`deleted_at IS NULL`）
> 3. 只回傳前端需要的欄位，不回傳整張表
> 4. 搭配 `SET search_path` 防止注入（下一節）

---

## 3. SET search_path — 防止什麼？

每個 function 都有這行：

```sql
SET search_path = public
```

### 攻擊場景

PostgreSQL 的 `search_path` 決定了「unqualified name（沒寫 schema 的名字）」去哪裡找。
預設的 search_path 是 `"$user", public`，而且**隱含包含 `pg_temp`**——
PostgreSQL 會優先在當前 session 的臨時 schema（`pg_temp`）裡找物件。

這代表任何有 session 的使用者（包括 `anon`）可以這樣攻擊：

```sql
-- 攻擊者在自己的 session 建立臨時物件
CREATE TEMP TABLE products AS SELECT ... ;  -- 假資料，存在 pg_temp 裡

-- 如果 SECURITY DEFINER function 沒有 SET search_path，
-- 而且 body 裡寫 `FROM products`（沒加 schema prefix）
-- → pg_temp.products 優先於 shop.products
-- → function 用 owner 權限執行，但讀到的是攻擊者的假資料
```

**關鍵**：`pg_temp` 攻擊比建 `public.products` 更危險，因為臨時物件不需要 CREATE 權限，只要有 session 就能建。

### 為什麼 SET 成 `public` 而不是 `shop`？

因為我們的 function body 裡，所有跨 schema 的表都用了**完整路徑**：

```sql
FROM shop.products p                          -- ✅ 完整路徑
LEFT JOIN shop.product_images pi ON ...       -- ✅ 完整路徑
LEFT JOIN shop.reviews r ON ...               -- ✅ 完整路徑
```

`SET search_path = public` 的意思是：「如果有任何 unqualified name，只在 `public` 裡找。」
這樣即使有人在 `pg_temp` schema 放了假物件，也不會被使用到。

> ### 🧠 你的大腦在想…
>
> 「我的 function body 都有寫完整路徑了，SET search_path 還有必要嗎？」
>
> 有。這是**防禦性編程**。今天你確定每個表都寫了 `shop.`，
> 但三個月後你可能加一行忘了寫。`SET search_path` 是你的安全網。
> PostgreSQL 官方文件也建議所有 SECURITY DEFINER function 都要 SET search_path。

---

## 4. 命名慣例 — `api_{domain}_{action}`

```
api_shop_list_products
│    │      │
│    │      └── 動作：list / get / search / my
│    └── 領域：shop / crawler / rag / analytics
└── 前綴：表示這是 public API function
```

### 為什麼這樣命名？

1. **PostgREST API Docs 自動分組**：Supabase Dashboard 的 API Docs 會按字母排序。`api_shop_*` 的 function 自然排在一起，`api_crawler_*` 排在一起

2. **前端語意清楚**：`supabase.rpc('api_shop_list_products')` 一看就知道是「Shop 領域的商品列表」

3. **避免命名衝突**：不同 domain 可能有類似的操作（都有 list、get、search），加 domain 前綴就不怕撞名

### 動作命名規則

| 動作前綴 | 語意 | 例子 |
|----------|------|------|
| `list_` | 取得列表（通常有分頁） | `api_shop_list_products` |
| `get_` | 取得單筆詳情 | `api_shop_get_product` |
| `search_` | 搜尋（有 query 參數） | `api_shop_search_products` |
| `my_` | 當前使用者的資料 | `api_shop_my_orders` |
| `active_` | 篩選有效項目 | `api_shop_active_coupons` |
| 無前綴 | 統計或儀表板 | `api_crawler_stats` |

---

## 5. 參數命名慣例 — `p_` 前綴

```sql
CREATE OR REPLACE FUNCTION public.api_shop_list_products(
  p_limit    INTEGER DEFAULT 20,
  p_offset   INTEGER DEFAULT 0,
  p_sort_by  TEXT DEFAULT 'created_at',
  p_sort_dir TEXT DEFAULT 'desc'
)
```

絕大多數參數都用 `p_` 前綴。為什麼？

**避免與欄位名衝突。** PostgreSQL 裡，如果你的參數叫 `limit`，它會跟 SQL 的 `LIMIT` 關鍵字撞。如果參數叫 `title`，它會跟 `p.title` 欄位混淆。`p_` 前綴一勞永逸地解決這個問題。

> ### ⚠️ 例外：RAG bridge function
>
> `api_rag_search` 和 `api_rag_hybrid_search` 的部分參數沒有 `p_` 前綴：
> `query_embedding`、`query_text`。
> 這是因為它們直接透傳給底層的 `rag.match_chunks_with_document()` /
> `rag.hybrid_search()`，保持參數名一致可以減少混淆。
> 注意前端呼叫時要用**原始名稱**，不加 `p_`。

> ### 💡 前端呼叫時的注意事項
>
> `supabase.rpc()` 的參數名要**完全對應** function 的參數名：
> ```ts
> // ✅ 正確——參數名要帶 p_ 前綴
> supabase.rpc('api_shop_list_products', {
>   p_limit: 20,
>   p_offset: 0,
>   p_sort_by: 'price',
>   p_sort_dir: 'asc'
> })
>
> // ❌ 錯誤——PostgREST 找不到對應參數
> supabase.rpc('api_shop_list_products', {
>   limit: 20,    // 少了 p_
>   offset: 0
> })
> ```

---

## 6. RETURNS TABLE — 嚴格定義回傳型別

每個 function 都明確宣告回傳的欄位：

```sql
RETURNS TABLE (
  id          TEXT,
  title       TEXT,
  slug        TEXT,
  price       NUMERIC,
  ...
)
```

### 為什麼不用 `RETURNS SETOF shop.products`？

| | RETURNS TABLE | RETURNS SETOF |
|---|---|---|
| **欄位控制** | 只回傳你列出的欄位 | 回傳整張表的所有欄位 |
| **安全性** | 不會意外暴露敏感欄位 | 可能暴露 `deleted_at`、`internal_notes` |
| **穩定性** | 加欄位到 table 不影響 API | 加欄位到 table 會改變 API 回傳 |
| **文件化** | 看 function 就知道回傳什麼 | 要去查 table schema |

**一句話**：RETURNS TABLE = API 契約（contract）。前端依賴的是這個契約，不是底層的 table 結構。

---

## 7. GRANT 策略 — 誰能呼叫什麼

SQL 最後一段（第 650–682 行）是 GRANT：

```sql
-- Public APIs：anon + authenticated 都能呼叫
GRANT EXECUTE ON FUNCTION public.api_shop_list_products(...) TO anon, authenticated;

-- Private APIs：只有 authenticated 能呼叫
GRANT EXECUTE ON FUNCTION public.api_shop_my_orders(...) TO authenticated;
```

### 權限矩陣

```
                    anon        authenticated
                  (未登入)        (已登入)
  ┌─────────────┬──────────────┬──────────────┐
  │ 瀏覽商品     │     ✅       │     ✅       │
  │ 搜尋商品     │     ✅       │     ✅       │
  │ 查看評論     │     ✅       │     ✅       │
  │ 語意搜尋     │     ✅       │     ✅       │
  ├─────────────┼──────────────┼──────────────┤
  │ 我的訂單     │     ❌       │     ✅       │
  │ 我的地址     │     ❌       │     ✅       │
  │ 我的點數     │     ❌       │     ✅       │
  │ 爬蟲統計     │     ❌       │     ✅       │
  │ 儀表板      │     ❌       │     ✅       │
  └─────────────┴──────────────┴──────────────┘
```

### 「my_」前綴的 function 怎麼知道「我是誰」？

它們內部都用 `auth.uid()` 取得當前使用者的 UUID：

```sql
WHERE u.auth_user_id = (SELECT auth.uid())
```

`auth.uid()` 是 Supabase 提供的函數，從 JWT token 取出使用者 ID。
如果沒登入（anon），`auth.uid()` 回傳 NULL，WHERE 條件不成立 → 回傳空集合。
加上 GRANT 只給 authenticated，等於**雙重保護**。

> ### 🧠 你的大腦在想…
>
> 「既然 auth.uid() 已經會回傳 NULL 了，為什麼還要 GRANT 限制？」
>
> 因為**防禦深度（Defense in Depth）**。
> GRANT 是第一道門（連呼叫都不行），auth.uid() 是第二道門（呼叫了也拿不到別人的資料）。
> 只靠一道門，萬一那道門有 bug，就全部暴露了。

---

## 8. 邊界情境 — 前端一定會碰到的 edge cases

### 查無資料

```ts
const { data } = await supabase.rpc('api_shop_get_product', {
  p_slug: 'not-exist-slug'
})
// data → []（空陣列），不是 null，不是 error
```

所有 `RETURNS TABLE` 的 function，查無資料時回傳**空結果集**（`[]`）。
前端用 `data.length === 0` 判斷即可。不會拋出例外。

### 無效的排序欄位

```ts
supabase.rpc('api_shop_list_products', { p_sort_by: 'hacked' })
```

CASE WHEN 的所有分支都不匹配 → 排序欄位全部是 NULL → **等於沒排序**（PostgreSQL 用預設的物理順序）。
不會報錯，但結果順序不可預測。前端應做白名單驗證。

### collection_code 不存在

```sql
(SELECT id FROM rag.collections WHERE code = p_collection_code AND is_active = TRUE)
-- → 回傳 NULL
```

底層的 `rag.match_chunks_with_document(query_embedding, NULL, ...)` 收到 NULL 的 collection_id → 回傳空集合。不會報錯。

### 分頁參數極端值

| 情境 | 行為 |
|------|------|
| `p_limit = 0` | 回傳 0 筆（合法，但沒意義） |
| `p_limit = -1` | PostgreSQL 的 `LIMIT` 接受負值時行為等同無限制（依版本） |
| `p_offset` 超過總數 | 回傳空集合 |

**建議**：前端在呼叫前對 `p_limit` 做 `Math.max(1, Math.min(limit, 100))` 夾值。

### 未登入呼叫 authenticated API

```ts
// 未登入狀態
const { data, error } = await supabase.rpc('api_shop_my_orders')
// error → { message: 'permission denied for function api_shop_my_orders', code: '42501' }
```

GRANT 限制 → PostgREST 回傳 HTTP 403 + PostgreSQL error code `42501`。

---

## 9. 共通模式速查表

每個 `api_*` function 都遵循這個模板：

```sql
CREATE OR REPLACE FUNCTION public.api_{domain}_{action}(
  p_param1  TYPE DEFAULT default_value,   -- 1. 參數用 p_ 前綴
  p_param2  TYPE DEFAULT default_value
)
RETURNS TABLE (                            -- 2. 明確定義回傳欄位
  col1  TYPE,
  col2  TYPE
)
LANGUAGE SQL                               -- 3. 純 SQL（不用 PL/pgSQL）
STABLE                                     -- 4. 同 tx 內可快取
SECURITY DEFINER                           -- 5. 用 owner 權限執行
SET search_path = public                   -- 6. 防 search_path 注入
AS $$
  SELECT ...                               -- 7. 只做 SELECT
  FROM schema.table                        -- 8. 完整 schema 路徑
  WHERE ... AND deleted_at IS NULL         -- 9. 軟刪除過濾
  LIMIT p_limit OFFSET p_offset;           -- 10. 分頁
$$;

GRANT EXECUTE ON FUNCTION public.api_{domain}_{action}(...)
  TO anon, authenticated;                  -- 11. 精確授權
```

---

## 接下來

理解了設計模式，現在去看具體的 API：

- [02_shop-api.md](02_shop-api.md)——商城 API（最多、最豐富）
- [03_crawler-api.md](03_crawler-api.md)——爬蟲 API
- [04_rag-api.md](04_rag-api.md)——RAG 語意搜尋 API
- [05_analytics-api.md](05_analytics-api.md)——Analytics 儀表板 API
