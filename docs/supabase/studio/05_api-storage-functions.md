# Head First API、Storage 與 Edge Functions — 你的資料庫自帶後端

> **「Supabase 最神奇的地方：你建完表，API 就自動長出來了。」**
>
> 你的大腦在想：「我還要自己寫 CRUD API？」
>
> 不用。PostgREST 幫你寫好了。你要做的是理解它、測試它、保護它。

---

## Part 1: API Docs — 動態文件的魔法

### 自動生成的原理

你有沒有想過，為什麼你在 Table Editor 加一個欄位，API 就自動多了一個欄位？

秘密在這裡：

1. **PostgREST** 讀取 PostgreSQL 的 `information_schema`
2. 它把你的 `public` schema 裡的每張表 → 變成一個 REST 端點
3. 你在 Table Editor 改了什麼 → API Docs **即時更新**
4. 只有 `public` schema 會被暴露（其他 schema 不會出現在 API 中）

> 腦筋急轉彎：「如果我建了一個 `crawler.raw_pages` 表，它會出現在 API Docs 嗎？」
>
> 不會！因為它在 `crawler` schema，不在 `public`。PostgREST 預設只暴露 `public`。

### 在 Studio 中使用 API Docs

這是你第一次感受到「零程式碼後端」的魔力：

1. 點進左側選單的 **API**
2. 選擇一張表（例如 `orders`）
3. 你會看到自動生成的程式碼片段：
   - **JavaScript** — 用 `supabase-js` 的寫法
   - **Dart** — Flutter 開發者的最愛
   - **Bash/curl** — 最原始、最直接的測試方式

> 你的大腦在想：「所以我不用寫任何 backend code？」
>
> 對於基本的 CRUD 操作 — 完全不用。PostgREST 幫你搞定了。

### curl 測試大全

curl 是你最好的朋友。不需要前端、不需要 SDK，直接跟 API 對話：

```bash
# 查詢（GET）— 取得 orders 的 id, total, status
curl 'http://localhost:54321/rest/v1/orders?select=id,total,status' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# 篩選（PostgREST 語法）— 找出待處理且金額 > 500 的訂單
curl 'http://localhost:54321/rest/v1/orders?status=eq.pending&total=gt.500' \
  -H "apikey: YOUR_ANON_KEY"

# 新增（POST）— 建立一筆新訂單
curl 'http://localhost:54321/rest/v1/orders' \
  -X POST \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "01HXY...", "total": 999}'

# 更新（PATCH）— 把訂單狀態改成已出貨
curl 'http://localhost:54321/rest/v1/orders?id=eq.01HXY...' \
  -X PATCH \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "shipped"}'

# 刪除（DELETE）— 刪除一筆訂單
curl 'http://localhost:54321/rest/v1/orders?id=eq.01HXY...' \
  -X DELETE \
  -H "apikey: YOUR_ANON_KEY"
```

> 你的大腦在想：「等等，那個 `YOUR_ANON_KEY` 在哪裡？」
>
> 在 Studio 左側選單的 **Project Settings → API**，或者在終端機跑：

```bash
supabase status
# 輸出範例：
#   API URL: http://localhost:54321
#   anon key: eyJhbGciOiJIUzI1NiIs...（這就是你的 ANON_KEY）
#   service_role key: eyJhbGciOiJIUzI1NiIs...（後台管理用，別放前端！）
```

### PostgREST 篩選語法速查

這張表你會用到爛，先存起來：

| 語法 | 意義 | 範例 |
|------|------|------|
| `eq.` | 等於 | `status=eq.pending` |
| `neq.` | 不等於 | `status=neq.cancelled` |
| `gt.` / `lt.` | 大於 / 小於 | `total=gt.500` |
| `gte.` / `lte.` | 大於等於 / 小於等於 | `total=gte.100` |
| `like.` | 模糊比對 | `name=like.*apple*` |
| `in.` | 包含在列表中 | `status=in.(pending,processing)` |
| `is.` | NULL 檢查 | `deleted_at=is.null` |
| `order` | 排序 | `order=created_at.desc` |
| `limit` | 限制筆數 | `limit=10` |
| `offset` | 偏移 | `offset=20` |

> 腦筋急轉彎：「如果表有 RLS，用 anon key 的 curl 會回傳什麼？」
>
> 空陣列 `[]`。因為 `anon` 角色沒有對應的 `auth.uid()`，RLS policy 會擋住所有資料。
> 這不是 bug — 這是**安全機制在正常運作**。

### RPC — 呼叫 Database Function

PostgREST 不只能操作表，還能呼叫你寫的 Database Function：

```bash
# 呼叫 public.get_crawler_stats()
curl 'http://localhost:54321/rest/v1/rpc/get_crawler_stats' \
  -X POST \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

重點：
- Function 必須在 `public` schema
- 用 `POST` 方法呼叫
- 參數放在 JSON body 裡
- 回傳值自動序列化成 JSON

> 你的大腦在想：「所以我寫的那些 SQL function，全部都能當 API 用？」
>
> 只要它在 `public` schema — 是的。這就是 PostgREST 的強大之處。

---

## Part 2: Storage — S3 相容的檔案管理

### 概念

你的應用程式不只有文字資料，還有圖片、PDF、影片。這些東西不適合存在 PostgreSQL 裡。

Supabase Storage 就是為此而生：

- **Storage** = S3 相容的存儲服務（底層用 MinIO）
- **Bucket** = 一個獨立的檔案容器（像資料夾的最上層）
- **Public bucket** = 任何人都能透過 URL 存取
- **Private bucket** = 受 RLS 保護，需要授權才能存取

### 在 Studio 中操作

動手試試看：

1. 點進左側選單的 **Storage**
2. 點 **"New bucket"**
3. 輸入名稱（例如 `avatars`）
4. 選擇 **Public** 或 **Private**
5. 拖曳檔案上傳

> 你的大腦在想：「Public 和 Private 的差別只是 URL 不同嗎？」
>
> 不只。Private bucket 的每一次存取都會經過 RLS 檢查。
> Public bucket 的檔案則是任何人只要有 URL 就能下載。

### Storage RLS Policy

這是最關鍵的部分 — 用 RLS 控制「誰能存取哪些檔案」：

```sql
-- 使用者只能上傳到自己的資料夾
CREATE POLICY "Users upload to own folder"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'avatars'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 使用者只能讀取自己的檔案
CREATE POLICY "Users read own files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'avatars'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

這裡的魔法：`storage.foldername(name)` 會把檔案路徑拆成陣列。
所以 `avatars/user123/photo.jpg` 的第一層資料夾就是 `user123`。

> 腦筋急轉彎：「如果我上傳到 `avatars/別人的uid/hack.jpg` 會怎樣？」
>
> 被 RLS 擋下來。`WITH CHECK` 會驗證資料夾名稱必須等於你的 `auth.uid()`。

### 檔案 URL 結構

```
Public:  http://localhost:54321/storage/v1/object/public/avatars/image.png
Private: http://localhost:54321/storage/v1/object/sign/avatars/user123/image.png
```

- **Public URL** — 直接存取，不需要 token
- **Signed URL** — 帶有時效性的授權 URL，過期就失效

---

## Part 3: Edge Functions — 伺服器端邏輯

### Database Function vs Edge Function

這是很多人搞混的地方。讓我們一次搞清楚：

| | Database Function | Edge Function |
|--|--|--|
| **執行環境** | PostgreSQL 內部 | Deno Runtime（V8 引擎） |
| **適合做** | 資料驗證、Trigger、RLS helper | 呼叫外部 API、發通知、複雜商業邏輯 |
| **語言** | SQL / PL/pgSQL | TypeScript |
| **速度** | 極快（在 DB 裡，零網路延遲） | 需要網路往返 |
| **核心用途** | 靠近**資料**的邏輯 | 靠近**外部世界**的邏輯 |

> 你的大腦在想：「那我什麼時候該用哪個？」
>
> 問自己一個問題：**「這個邏輯需要跟外部世界溝通嗎？」**
> - 需要呼叫 Stripe API？→ Edge Function
> - 需要計算訂單總金額？→ Database Function
> - 需要發 Email 通知？→ Edge Function
> - 需要在 INSERT 時自動填入欄位？→ Database Function（Trigger）

### 建立 Edge Function

```bash
# 建立新的 Edge Function
supabase functions new hello-world

# 本地開發 & 測試
supabase functions serve hello-world
```

這會在 `supabase/functions/hello-world/index.ts` 建立一個模板檔案。

### Studio 中的 Edge Functions 頁面

在 Studio 裡你可以：
- 看到所有已部署的 Functions 列表
- 監控每個 Function 的 **invocation count**（呼叫次數）
- 查看 **errors**（錯誤紀錄）
- 閱讀 **logs**（執行日誌）

你**不能**在 Studio 裡直接編輯 Edge Function 的程式碼。這是故意的設計 — 程式碼應該在本地編輯、用 Git 管理、透過 CLI 部署。

> 腦筋急轉彎：「Edge Function 可以直接存取 PostgreSQL 嗎？」
>
> 可以！Edge Function 內建 `supabase-js`，可以用 Service Role Key 繞過 RLS 做管理操作。
> 但要小心 — Service Role Key 是「上帝模式」，不受 RLS 限制。

---

## Part 4: 三大服務的協作

把所有東西串在一起，你的架構長這樣：

```
前端應用
   │
   ├── REST API ──→ PostgREST ──→ PostgreSQL
   │   (自動 CRUD)     (54321)      (54322)
   │
   ├── Storage API ──→ Storage ──→ S3/MinIO
   │   (檔案管理)
   │
   └── Edge Function ──→ Deno ──→ 外部 API
       (自訂邏輯)
```

它們各司其職：
- **PostgREST** 處理資料的 CRUD — 自動、快速、受 RLS 保護
- **Storage** 處理檔案的上傳下載 — S3 相容、受 RLS 保護
- **Edge Functions** 處理外部整合 — 彈性最大、你完全掌控

> Head First 原則：**能用 Database Function 解決的，不要用 Edge Function。能用 PostgREST 自動 API 解決的，不要自己寫 endpoint。**
>
> 為什麼？因為每多一層，就多一個可能出錯的地方。簡單就是美。

---

## 動手做：API + Storage 完整練習

```
📝 Exercise: 打造一個簡易部落格 API

1. 建立 public.posts 表
   - id (TEXT, PK, default generate_ulid())
   - title (TEXT, NOT NULL)
   - body (TEXT)
   - image_url (TEXT)
   - user_id (TEXT, NOT NULL)
   - created_at (TIMESTAMPTZ, default NOW())

2. 建立 Storage bucket "post-images"（Private）

3. 用 curl POST 新增一筆 post
   $ curl 'http://localhost:54321/rest/v1/posts' \
     -X POST \
     -H "apikey: YOUR_ANON_KEY" \
     -H "Content-Type: application/json" \
     -d '{"title": "我的第一篇文章", "body": "Hello World!", "user_id": "test-user"}'

4. 在 Storage 上傳一張圖片到 post-images bucket

5. 用 curl GET 查詢所有 posts
   $ curl 'http://localhost:54321/rest/v1/posts?select=*&order=created_at.desc' \
     -H "apikey: YOUR_ANON_KEY"

6. 建立一個 RPC function：取得最新 5 篇 posts
   CREATE OR REPLACE FUNCTION public.get_recent_posts()
   RETURNS SETOF public.posts
   LANGUAGE sql STABLE
   AS $$
     SELECT * FROM public.posts
     ORDER BY created_at DESC
     LIMIT 5;
   $$;

7. 用 curl 呼叫 RPC
   $ curl 'http://localhost:54321/rest/v1/rpc/get_recent_posts' \
     -X POST \
     -H "apikey: YOUR_ANON_KEY" \
     -H "Content-Type: application/json" \
     -d '{}'
```

---

## 自我檢查清單

```
□ 我知道 PostgREST 只暴露 public schema
□ 我能用 curl 執行 GET / POST / PATCH / DELETE
□ 我知道 PostgREST 的篩選語法（eq, gt, in, like...）
□ 我能用 curl 呼叫 RPC function
□ 我知道 RLS 啟用後 anon key 查詢會回傳空陣列
□ 我能建立 Storage bucket 並設定 Public/Private
□ 我知道 Storage RLS 怎麼寫（storage.objects + foldername）
□ 我能分辨 Database Function 和 Edge Function 的使用場景
□ 我知道「能用 DB Function 就不用 Edge Function」的原則
□ 我能在 Studio 的 API Docs 頁面找到自動生成的程式碼片段
```

---

> **下一章**：[Migration 流程 — 從實驗到正式的橋樑](./06_migration-workflow.md)
>
> 你已經學會了怎麼用 API、Storage 和 Edge Functions。
> 但如果你所有的 schema 變更都在 Studio 裡點來點去 — 那些改動遲早會消失。
> 下一章教你正確的做法。
