# Stage 10：Automation — Triggers, Realtime, Storage

> **對應 SQL**：[`002_shop_schema.sql`](../migrations/002_shop_schema.sql) 第 1015-1091 行
>
> 這一章你會學到三件事：
> 1. 如何用迴圈批量建立 Trigger（不用手寫 16 次）
> 2. Supabase Realtime 該開在哪些表、不該開在哪些表
> 3. Storage bucket 的 RLS 怎麼寫

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| moddatetime Triggers | 1025-1045 | 批量建立 `updated_at` 自動更新 |
| Audit Fields Triggers | 1047-1064 | 自動填入 `created_by` / `updated_by` |
| Supabase Realtime | 1066-1072 | 即時訂閱（commented out） |
| Supabase Storage | 1074-1091 | 產品圖片 bucket + RLS |

---

## 10.1 moddatetime Triggers — 批量建立 `updated_at`（SQL 第 1025-1045 行）

### 你的大腦在想 🧠

> 「16 張表都需要 `updated_at` 自動更新，難道我要寫 16 次 CREATE TRIGGER？」

不用。用 PL/pgSQL 的 `FOREACH` 迴圈，一段 anonymous block 搞定全部。

---

### 程式碼解析

```sql
-- SQL 第 1026-1045 行
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'stocks', 'coupons',
    'orders', 'order_items', 'addresses', 'payments', 'reviews',
    'terms', 'term_taxonomy'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_updated_at on shop.%1$s;
      create trigger trg_%1$s_updated_at
        before update on shop.%1$s
        for each row execute function moddatetime(updated_at);
    ', tbl);
  end loop;
end;
$$;
```

逐行拆解：

| 行為 | 說明 |
|------|------|
| `do $$ ... $$;` | Anonymous block — 不建立 function，直接跑一段 PL/pgSQL |
| `foreach tbl in array array[...]` | 迴圈走過 16 個表名 |
| `format('...', tbl)` | 把表名填入 SQL 字串。`%1$s` 就是第一個參數（`tbl`） |
| `drop trigger if exists` | 先刪再建 = **冪等**（idempotent），跑幾次結果都一樣 |
| `before update` | 在 UPDATE **之前**觸發，修改同一列的 `updated_at` |
| `moddatetime(updated_at)` | Supabase 內建 extension，自動設定 `updated_at = now()` |

### moddatetime 是什麼？

它是 PostgreSQL 的 `contrib` 模組，Supabase 已預裝。你不需要自己寫 trigger function：

```sql
-- 你不需要寫這個：
create function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end; $$ language plpgsql;

-- moddatetime 替你做了同樣的事，而且更可靠
```

在 `001_extensions.sql` 裡我們已經啟用了：

```sql
create extension if not exists moddatetime schema extensions;
```

---

### 哪些表**有** moddatetime？哪些**沒有**？

| 有 moddatetime（16 張） | 沒有 moddatetime（4 張） | 原因 |
|:-------------------------|:-------------------------|:-----|
| users, profiles, companies, stores, store_staff, products, product_images, stocks, coupons, orders, order_items, addresses, payments, reviews, terms, term_taxonomy | inventory_movements | **Append-only**，永遠不 UPDATE |
| | point_rewards | **Append-only**，永遠不 UPDATE |
| | order_coupons | Junction table，沒有 `updated_at` 欄位 |
| | term_relationships | Junction table，沒有 `updated_at` 欄位 |

### 你的大腦在想 🧠

> 「為什麼 append-only 的表不需要 `updated_at`？」
>
> 因為它們就像**帳本**——寫了就不改。如果發現錯誤，你寫一筆新的修正紀錄，
> 不是回去改舊的。既然永遠不 UPDATE，trigger 就永遠不會觸發，建了也沒用。

---

## 10.2 Audit Fields Triggers — 自動填入操作者（SQL 第 1047-1064 行）

```sql
-- SQL 第 1048-1064 行
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'companies', 'stores', 'products', 'coupons', 'orders', 'payments'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_audit on shop.%1$s;
      create trigger trg_%1$s_audit
        before insert or update on shop.%1$s
        for each row execute function shop.handle_audit_fields();
    ', tbl);
  end loop;
end;
$$;
```

### 跟 moddatetime 有什麼不同？

| 比較 | moddatetime | handle_audit_fields |
|------|-------------|---------------------|
| **來源** | Supabase 內建 extension | 我們自己在 Stage 1 寫的 function |
| **觸發時機** | `BEFORE UPDATE` | `BEFORE INSERT OR UPDATE` |
| **設定欄位** | `updated_at` | `created_by` + `updated_by` |
| **適用表數** | 16 張 | 6 張（只有這 6 張有 `created_by`/`updated_by` 欄位） |
| **取得使用者** | 不需要 | 呼叫 `shop.get_current_user_id()` |

為什麼只有 6 張表？因為只有**業務核心表**才需要追蹤「誰建的、誰改的」。
像 `profiles`、`addresses` 這些表本身就跟 user 綁定，不需要額外的 audit 欄位。

### 沒有 Dumb Questions :question:

**Q：為什麼不在 application code 裡手動傳 `created_by`？**

A：因為你**會忘記**。不管是你、你的同事、還是三個月後的你——總有人會忘記傳 user ID。Trigger 是**資料庫層面的保證**，比任何 code review 都可靠。

**Q：`handle_audit_fields()` 怎麼知道目前登入的是誰？**

A：它呼叫 `shop.get_current_user_id()`，這個 function 讀取 `auth.uid()`（Supabase 的 JWT 解析結果），
然後查 `shop.users` 拿到對應的 user ID。如果沒登入就回傳 NULL。

**Q：INSERT 時 `updated_by` 會被設定嗎？**

A：會。`handle_audit_fields()` 在 INSERT 和 UPDATE 時都設定 `updated_by`。
所以剛建立的資料，`created_by` 和 `updated_by` 會是同一個人。

---

## 10.3 Trigger 執行順序

當你 UPDATE 一筆 `orders` 資料時，會發生什麼事？

```
UPDATE shop.orders SET status = 'shipped' WHERE id = 'xxx';

  ┌─────────────────────────────────┐
  │ 1. trg_orders_audit             │  ← BEFORE UPDATE
  │    → handle_audit_fields()      │  → 設定 updated_by
  │                                 │
  │ 2. trg_orders_updated_at        │  ← BEFORE UPDATE
  │    → moddatetime(updated_at)    │  → 設定 updated_at = now()
  │                                 │
  │ 3. 實際寫入                      │  ← 兩個欄位都已更新
  └─────────────────────────────────┘
```

**為什麼是這個順序？**

兩個 trigger 都是 `BEFORE UPDATE`，PostgreSQL 按 trigger **名稱的字母順序**執行：

- `trg_orders_audit` （a 在前）
- `trg_orders_updated_at` （u 在後）

這個順序不影響功能，因為兩個 trigger 修改的是不同欄位。但如果你的 trigger 之間有依賴關係，命名時要注意順序。

---

## 10.4 Supabase Realtime — 即時訂閱（SQL 第 1066-1072 行，已註解）

```sql
-- SQL 第 1069-1072 行（commented out）
-- alter publication supabase_realtime add table shop.orders;
-- alter publication supabase_realtime add table shop.stocks;
-- alter publication supabase_realtime add table shop.payments;
-- alter publication supabase_realtime add table shop.reviews;
```

### 什麼是 Realtime？

Supabase Realtime 利用 PostgreSQL 的 **logical replication** 功能，把資料庫的變更即時推送到前端。
前端用 JavaScript SDK 訂閱：

```javascript
const channel = supabase
  .channel('orders')
  .on('postgres_changes',
    { event: 'UPDATE', schema: 'shop', table: 'orders' },
    (payload) => {
      console.log('訂單狀態更新了！', payload.new.status);
    }
  )
  .subscribe();
```

### 該開哪些表？

| 表 | 啟用？ | 理由 |
|:---|:------:|:-----|
| `orders` | Yes | 客戶即時看到訂單狀態變更（處理中 → 出貨 → 送達） |
| `stocks` | Yes | 門市人員即時看到庫存變動（進貨、賣出） |
| `payments` | Yes | 第三方金流回呼（webhook）更新付款狀態，前端即時反映 |
| `reviews` | Yes | 新評論即時出現在商品頁，不用手動重新整理 |
| `companies` | No | 很少變動，沒有即時需求 |
| `profiles` | No | 個人資料不需要廣播給其他人 |
| `products` | Maybe | 如果你有「即時編輯」功能，可以開；否則不需要 |
| `inventory_movements` | No | Append-only 日誌，通常用 API 查詢而非即時訂閱 |

### 你的大腦在想 🧠

> 「為什麼這段 SQL 被註解掉了？直接寫進 migration 不好嗎？」
>
> 因為 `supabase_realtime` 這個 publication 是 Supabase 平台自動建立的。
> 在某些環境（本地開發、CI/CD），這個 publication 可能還不存在，
> migration 就會報錯。最安全的做法是**透過 Dashboard 啟用**，
> 或在確認環境後手動執行。

---

## 10.5 Supabase Storage — 產品圖片（SQL 第 1074-1091 行，已註解）

```sql
-- SQL 第 1077-1078 行
-- insert into storage.buckets (id, name, public)
-- values ('product-images', 'product-images', true);

-- SQL 第 1080-1082 行
-- create policy "product_images_public_read"
--   on storage.objects for select
--   using (bucket_id = 'product-images');

-- SQL 第 1084-1086 行
-- create policy "product_images_staff_upload"
--   on storage.objects for insert to authenticated
--   with check (bucket_id = 'product-images' and shop.is_staff());

-- SQL 第 1088-1090 行
-- create policy "product_images_staff_delete"
--   on storage.objects for delete to authenticated
--   using (bucket_id = 'product-images' and shop.is_staff());
```

### Storage 架構圖

```
storage.buckets                      storage.objects
┌────────────────────────┐          ┌──────────────────────────────┐
│ id: 'product-images'   │          │ bucket_id: 'product-images'  │
│ name: 'product-images' │ ← 1:N → │ name: 'iphone-front.jpg'     │
│ public: true           │          │ owner: 'user-abc-123'        │
└────────────────────────┘          └──────────────────────────────┘
         │                                      │
         │ public = true                        │ RLS policies
         ↓                                      ↓
   任何人都能讀圖片 URL               只有 staff 能上傳/刪除
```

### 三條 RLS Policy 拆解

| Policy 名稱 | 操作 | 對象 | 條件 | 白話 |
|:-------------|:----:|:----:|:-----|:-----|
| `product_images_public_read` | SELECT | 所有人 | `bucket_id = 'product-images'` | 任何人都能看產品圖片 |
| `product_images_staff_upload` | INSERT | authenticated | `bucket_id = 'product-images' AND shop.is_staff()` | 只有店員能上傳 |
| `product_images_staff_delete` | DELETE | authenticated | `bucket_id = 'product-images' AND shop.is_staff()` | 只有店員能刪除 |

**關鍵觀念**：

1. **Bucket 設為 `public = true`** — 這表示圖片可以透過公開 URL 直接存取，不需要 JWT。
   適合產品圖片（本來就要給所有人看）。
2. **上傳/刪除靠 RLS** — `public = true` 只影響讀取。寫入和刪除仍然受 RLS 保護。
3. **重用 `shop.is_staff()`** — 跟 Stage 9 的資料庫 RLS 用同一個 helper function！
   Storage RLS 和 Database RLS 是**分開的系統**，但可以共用 helper function。

### 沒有 Dumb Questions :question:

**Q：為什麼 Storage 的 SQL 也被註解掉了？**

A：跟 Realtime 同理。`storage.buckets` 是 Supabase 平台管理的表，在某些環境可能不存在。
最安全的做法是透過 Dashboard 建立 bucket，或在部署腳本中確認環境後再執行。

**Q：`public = true` 不是很危險嗎？**

A：要看場景。產品圖片本來就是要給所有人看的，`public = true` 完全合理。
但如果是使用者的身分證照片，你就**絕對不能**設成 public——要用 private bucket + signed URL。

**Q：為什麼沒有 UPDATE policy？**

A：Storage 的「更新圖片」通常是「刪除舊的 + 上傳新的」，不是原地修改。
所以只需要 INSERT + DELETE policy。

**Q：如果我有多個 bucket（例如 `avatars`、`receipts`），要怎麼管？**

A：每個 bucket 各寫自己的 policy。條件裡用 `bucket_id = 'xxx'` 區分，
不同的 bucket 可以有不同的存取規則。

---

## 10.6 全貌：Automation 怎麼串起來

```
                        ┌──────────────────┐
                        │   Application    │
                        │   (Frontend)     │
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    ↓            ↓            ↓
              Supabase JS    Storage SDK   Realtime SDK
                    │            │            │
         ┌──────────┤      ┌─────┤      ┌─────┤
         ↓          ↓      ↓     ↓      ↓     ↓
     shop.orders  shop.*  bucket  RLS  publication
         │          │       │     │      │
         ↓          ↓      ↓     ↓      ↓
   ┌─────────┐ ┌────────┐ Storage    Realtime
   │ audit   │ │ moddate│ Objects    Channel
   │ trigger │ │ trigger│
   └─────────┘ └────────┘
    updated_by  updated_at
```

每一層都有自動化保護：

- **資料層**：Trigger 自動設定 `updated_at`、`updated_by`
- **儲存層**：Storage RLS 保護上傳/刪除
- **即時層**：Realtime 推送變更到前端

應用程式只需要做「業務邏輯」，不需要操心這些基礎設施。

---

## 重點子彈 🎯

### moddatetime Triggers

- ✅ **批量建立**：用 `FOREACH` 迴圈 + `format()` 一次搞定 16 張表的 `updated_at` trigger
- ✅ **moddatetime 是內建 extension**，比自己寫 trigger function 更簡單可靠
- ✅ **冪等 migration**：`DROP TRIGGER IF EXISTS` 再 `CREATE` = 跑幾次結果都一樣
- ✅ **Append-only 表不需要 moddatetime**：`inventory_movements`、`point_rewards` 永遠不 UPDATE

### Audit Fields Triggers

- ✅ **6 張業務核心表**自動填入 `created_by` / `updated_by`
- ✅ **BEFORE INSERT OR UPDATE** — INSERT 時兩個欄位都設定，UPDATE 時只更新 `updated_by`
- ✅ **Trigger 保證一致性**，比靠 application code 傳 user ID 可靠

### Trigger 執行順序

- ✅ 同一事件（BEFORE UPDATE）的多個 trigger 按**名稱字母順序**執行
- ✅ `trg_xxx_audit` 在 `trg_xxx_updated_at` 之前，因為 `a` < `u`

### Supabase Realtime

- ✅ 只在**需要即時更新的表**啟用：orders、stocks、payments、reviews
- ✅ 不要開在 rarely-changed 或 append-only 的表上，**浪費資源**
- ✅ 通常透過 **Dashboard 啟用**，避免 migration 環境問題

### Supabase Storage

- ✅ `public = true` 的 bucket 讓任何人都能讀取圖片 URL
- ✅ 上傳/刪除靠 **RLS on `storage.objects`** 保護，只有 staff 能操作
- ✅ 重用 `shop.is_staff()` helper — Storage RLS 和 Database RLS **共用 helper function**
- ✅ 透過 Dashboard 建立 bucket 最安全，避免環境相容性問題

---

## 動手做 🛠️

### 練習 1：驗證 moddatetime

更新一筆 `products` 資料，觀察 `updated_at` 是否自動更新：

```sql
-- 1. 查看目前的 updated_at
select id, name, updated_at
from shop.products
limit 1;

-- 2. 更新（不要手動設定 updated_at）
update shop.products
set name = name || ' (edited)'
where id = '你的_PRODUCT_ID';

-- 3. 再查一次——updated_at 應該變了
select id, name, updated_at
from shop.products
where id = '你的_PRODUCT_ID';
```

### 練習 2：驗證 Audit Trigger

插入一筆 `orders`，檢查 `created_by` 是否自動填入：

```sql
-- 用 Supabase SQL Editor（它會帶入你的 JWT）
insert into shop.orders (store_id, user_id, status, total_amount, currency)
values ('你的_STORE_ID', '你的_USER_ID', 'pending', 100, 'TWD');

-- 查看 created_by 和 updated_by 是否被自動設定
select id, status, created_by, updated_by
from shop.orders
order by created_at desc
limit 1;
```

### 練習 3：手動啟用 Realtime

1. 打開 Supabase Dashboard → Database → Replication
2. 找到 `supabase_realtime` publication
3. 把 `shop.orders` 加進去
4. 在前端用以下程式碼測試：

```javascript
const { createClient } = require('@supabase/supabase-js');
const supabase = createClient('YOUR_URL', 'YOUR_ANON_KEY');

const channel = supabase
  .channel('order-updates')
  .on('postgres_changes',
    { event: 'UPDATE', schema: 'shop', table: 'orders' },
    (payload) => console.log('訂單更新：', payload)
  )
  .subscribe();

// 在另一個視窗更新訂單，這裡應該會收到通知
```

### 練習 4：思考題

1. 如果你新增了一張表 `shop.wishlists`，它需要 moddatetime trigger 嗎？需要 audit trigger 嗎？如何判斷？
2. 如果 `trg_orders_audit` 和 `trg_orders_updated_at` 的執行順序反過來，會有什麼影響？
3. 假設你要建一個 `private` bucket 存使用者的收據照片（`receipts`），RLS policy 要怎麼寫？（提示：每個使用者只能存取自己的收據）

---

> **上一章**：[`05_rls-security.md`](05_rls-security.md) — Stage 9：RLS 安全策略

---

[← 05 安全 RLS](05_security-rls.md) | [00_README →](00_README.md)
