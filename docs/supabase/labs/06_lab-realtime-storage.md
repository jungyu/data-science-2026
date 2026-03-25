# Lab：Realtime 即時訂閱 + Storage 檔案管理

---

## 實驗目標

- 理解 Supabase Realtime 三種模式及其適用場景
- 啟用 Postgres Changes 並用 JavaScript Client 接收即時推送
- 建立 Storage Buckets 並設定 RLS 權限控制
- 掌握 Public URL / Signed URL 的差異與使用方式

---

## 前置準備

確認 Docker 正在執行，Supabase 本地環境已啟動：

```bash
supabase status
```

應看到所有服務 running。如果沒有：

```bash
supabase start
```

### 執行 Migration

本次實驗需要兩個 migration 檔案：

```bash
# 在 SQL Editor 或 psql 中依序執行
psql -h localhost -p 54322 -U postgres -f docs/supabase/migrations/007_realtime.sql
psql -h localhost -p 54322 -U postgres -f docs/supabase/migrations/008_storage_buckets.sql
```

> 也可以在 Studio SQL Editor（http://localhost:54323）中貼上執行。

### 開啟瀏覽器

- Studio：http://localhost:54323
- 準備兩個分頁（後面測試 Realtime 會用到）

---

## Stage 1：理解 Realtime 三種模式

Supabase Realtime 提供三種即時通訊模式：

| 模式 | 原理 | 需要 DDL？ | 適用場景 |
|------|------|-----------|---------|
| **Postgres Changes** | 監聽 WAL → Publication → WebSocket | 是 | 訂單狀態、庫存變動 |
| **Broadcast** | 低延遲 pub/sub，不經資料庫 | 否（純 SDK） | 系統通知、即時聊天 |
| **Presence** | 線上狀態追蹤 | 否（純 SDK） | 在線人數、協作編輯 |

### 關鍵觀念

```
Postgres Changes 的資料流：

  INSERT/UPDATE/DELETE
        ↓
  PostgreSQL WAL（Write-Ahead Log）
        ↓
  Publication: supabase_realtime
        ↓
  Realtime Server（解析 WAL）
        ↓
  WebSocket → 前端 Client
```

Broadcast 和 Presence 完全不碰資料庫，只走 WebSocket。
因此 **只有 Postgres Changes 需要寫 migration**（也就是 007_realtime.sql 做的事）。

---

## Stage 2：啟用 Realtime

### 2.1 查看 007_realtime.sql 做了什麼

核心語法只有一行：

```sql
-- 把 shop.orders 加入 Realtime publication
ALTER PUBLICATION supabase_realtime ADD TABLE shop.orders;
```

我們的 migration 一共啟用了 8 張表：

| Schema | Table | 即時場景 |
|--------|-------|---------|
| shop | orders | 訂單狀態追蹤 |
| shop | stocks | 庫存低水位警告 |
| shop | payments | 付款狀態回饋 |
| shop | reviews | 新評論通知 |
| crawler | crawl_runs | 爬蟲執行進度 |
| crawler | crawl_queue | Worker 搶工作 |
| rag | documents | 文件處理進度 |
| analytics | events | 即時儀表板 |

### 2.2 驗證 Publication 設定

在 SQL Editor 執行：

```sql
-- 確認哪些表已加入 Realtime
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
ORDER BY schemaname, tablename;
```

預期結果（8 筆）：

```
 schemaname |  tablename
------------+-------------
 analytics  | events
 crawler    | crawl_queue
 crawler    | crawl_runs
 rag        | documents
 shop       | orders
 shop       | payments
 shop       | reviews
 shop       | stocks
```

### 2.3 為什麼不全部啟用？

> 每張加入 publication 的表，PostgreSQL 都會額外解碼 WAL 記錄。
> 表越多 → WAL 解碼負擔越重 → 可能影響寫入效能。
>
> **原則：只在「真正需要即時通知」的表啟用。**

---

## Stage 3：JavaScript Client 訂閱

### 3.1 基本訂閱：監聽 shop.orders 變更

在瀏覽器 Console（或獨立 HTML 檔）中執行：

```javascript
// 引入 Supabase Client（CDN 方式）
// <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>

const supabase = supabase.createClient(
  'http://localhost:54321',       // API URL
  'YOUR_ANON_KEY'                 // 在 supabase status 中取得
)

// 訂閱 shop.orders 的所有變更
const channel = supabase
  .channel('order-watcher')       // 自訂 channel 名稱
  .on(
    'postgres_changes',
    {
      event: '*',                 // 監聽所有事件：INSERT, UPDATE, DELETE
      schema: 'shop',
      table: 'orders',
    },
    (payload) => {
      console.log('事件類型:', payload.eventType)
      console.log('新資料:', payload.new)
      console.log('舊資料:', payload.old)
    }
  )
  .subscribe((status) => {
    console.log('訂閱狀態:', status)  // 應顯示 SUBSCRIBED
  })
```

### 3.2 篩選特定事件類型

只監聽新訂單（INSERT）：

```javascript
const insertChannel = supabase
  .channel('new-orders')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',            // 只聽 INSERT
      schema: 'shop',
      table: 'orders',
    },
    (payload) => {
      console.log('新訂單！', payload.new)
    }
  )
  .subscribe()
```

### 3.3 篩選特定欄位值

只監聽某個顧客的訂單更新：

```javascript
const myOrdersChannel = supabase
  .channel('my-orders')
  .on(
    'postgres_changes',
    {
      event: 'UPDATE',
      schema: 'shop',
      table: 'orders',
      filter: 'customer_id=eq.some-user-id',  // 用 PostgREST 語法篩選
    },
    (payload) => {
      console.log('訂單狀態變更:', payload.new.status)
    }
  )
  .subscribe()
```

### 3.4 動手測試：雙分頁驗證

**分頁 A**（接收端）：在 Console 貼上 3.1 的訂閱程式碼

**分頁 B**（發送端）：在 SQL Editor 插入一筆訂單

```sql
-- 在 SQL Editor 執行（如果 shop.orders 需要外鍵，先確認有對應資料）
INSERT INTO shop.orders (customer_id, status, total_amount)
VALUES ('test-user-id', 'pending', 999.00);
```

切回 **分頁 A** 的 Console → 應看到即時推送的 payload。

> 如果沒收到，檢查：
> 1. `supabase status` 確認 Realtime 服務運行中
> 2. `pg_publication_tables` 確認表已加入
> 3. ANON_KEY 是否正確

---

## Stage 4：Storage Buckets

### 4.1 查看 008_storage_buckets.sql 建立的 Bucket

```sql
-- 確認 bucket 設定
SELECT id, name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
ORDER BY id;
```

預期結果（3 個 bucket）：

| id | public | file_size_limit | 說明 |
|----|--------|----------------|------|
| crawler-assets | FALSE | 10,485,760 (10MB) | 爬蟲截圖，私有 |
| product-images | TRUE | 5,242,880 (5MB) | 商品圖片，公開 |
| rag-documents | FALSE | 52,428,800 (50MB) | RAG 文件，私有 |

### 4.2 Public vs Private

| 屬性 | Public Bucket | Private Bucket |
|------|--------------|----------------|
| `public` 欄位 | TRUE | FALSE |
| 匿名 GET | 允許（不需 token） | 拒絕（需 auth token） |
| URL 格式 | `/storage/v1/object/public/{bucket}/{path}` | 需要 Signed URL |
| 適用場景 | 商品圖、頭像 | 機密文件、內部資源 |

### 4.3 file_size_limit 與 allowed_mime_types

```sql
-- product-images 只接受圖片，最大 5MB
-- allowed_mime_types:
--   image/jpeg, image/png, image/webp, image/gif, image/svg+xml

-- rag-documents 接受文件格式，最大 50MB
-- allowed_mime_types:
--   application/pdf, text/plain, text/markdown, text/html, .docx
```

> 上傳不符合 MIME type 或超過大小的檔案會被 Storage 直接拒絕，不需要額外寫驗證。

### 4.4 ON CONFLICT 冪等設計

```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('product-images', 'product-images', TRUE, 5242880, ...)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;
```

> `ON CONFLICT ... DO UPDATE` 讓 migration 可以重複執行不會報錯。這是冪等（idempotent）設計。

---

## Stage 5：Storage RLS

### 5.1 storage.objects 表結構

Storage 的權限控制建立在 `storage.objects` 表的 RLS 上：

| 欄位 | 說明 |
|------|------|
| `bucket_id` | 所屬 bucket |
| `name` | 檔案完整路徑（含資料夾） |
| `owner` | 上傳者的 `auth.uid()` |
| `metadata` | 自訂 metadata（JSONB） |

### 5.2 storage.foldername() 輔助函式

```sql
-- 範例：name = 'collection-1/doc-42/report.pdf'
-- storage.foldername(name) 回傳 ARRAY['collection-1', 'doc-42']
-- [1] = 'collection-1'（第一層資料夾）
-- [2] = 'doc-42'（第二層資料夾）
```

> 利用資料夾路徑做權限判斷，是 Supabase Storage RLS 的常見模式。

### 5.3 三種 Policy 模式

**模式 1：Public Read（公開讀取）**

```sql
-- 任何人都能讀取 product-images
CREATE POLICY "product_images_public_read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'product-images');
```

**模式 2：Role-Based（角色控制上傳）**

```sql
-- 只有 staff 才能上傳商品圖片
CREATE POLICY "product_images_staff_upload"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'product-images'
    AND shop.is_staff()           -- 自訂函式檢查角色
  );
```

**模式 3：Owner-Based（資料夾路徑 = 擁有者）**

```sql
-- RAG 文件：只有 collection owner 可以上傳
CREATE POLICY "rag_documents_upload"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'rag-documents'
    AND (storage.foldername(name))[1] IN (
      SELECT c.id FROM rag.collections c
      WHERE c.owner_id = (SELECT auth.uid())::TEXT
    )
  );
```

> 路徑慣例：`rag-documents/{collection_id}/{document_id}/{filename}`
> 第一層資料夾就是 collection_id，用來比對 owner。

---

## Stage 6：上傳與 Signed URL

### 6.1 Python SDK 上傳範例

```python
from supabase import create_client

# 初始化 client
url = "http://localhost:54321"
key = "YOUR_SERVICE_ROLE_KEY"     # 上傳私有 bucket 需要 service_role
supabase = create_client(url, key)

# 上傳商品圖片（public bucket）
with open("photo.jpg", "rb") as f:
    res = supabase.storage.from_("product-images").upload(
        path="prod-001/main.jpg",  # bucket 內的路徑
        file=f,
        file_options={
            "content-type": "image/jpeg",
            "upsert": "true",      # 同名覆蓋
        },
    )
    print("上傳結果:", res)
```

### 6.2 取得 Public URL

```python
# Public bucket 不需要 token 就能存取
public_url = supabase.storage.from_("product-images").get_public_url(
    "prod-001/main.jpg"
)
print("公開 URL:", public_url)
# → http://localhost:54321/storage/v1/object/public/product-images/prod-001/main.jpg
```

### 6.3 取得 Signed URL（私有 Bucket）

```python
# Private bucket 需要 signed URL，設定過期時間（秒）
signed = supabase.storage.from_("rag-documents").create_signed_url(
    path="collection-1/doc-42/report.pdf",
    expires_in=3600,               # 1 小時有效
)
print("簽名 URL:", signed["signedURL"])
# URL 包含 token 參數，過期後自動失效
```

### 6.4 cURL 測試 Public Bucket

```bash
# 直接用 cURL 存取公開 bucket（不需 token）
curl -I http://localhost:54321/storage/v1/object/public/product-images/prod-001/main.jpg

# 預期回應：HTTP/1.1 200 OK（如果檔案存在）
# 或 HTTP/1.1 400（檔案不存在）
```

```bash
# 嘗試存取私有 bucket（不帶 token → 應被拒絕）
curl -I http://localhost:54321/storage/v1/object/crawler-assets/screenshots/test.png

# 預期回應：HTTP/1.1 400 Bad Request 或 401 Unauthorized
```

---

## Stage 7：整合驗證

### 7.1 上傳檔案 → Studio 確認

1. 用 Python SDK（Stage 6.1）上傳一張圖片到 `product-images`
2. 打開 Studio → 左側選 **Storage**
3. 點進 `product-images` bucket → 應看到剛上傳的檔案

### 7.2 Realtime 訂閱 → Console 確認

1. 分頁 A：在 Console 貼上 Stage 3.1 的訂閱程式碼
2. 分頁 B：在 SQL Editor 執行 INSERT
3. 切回分頁 A → Console 應顯示 payload

### 7.3 Storage RLS 測試

```bash
# 測試 1：匿名讀取 public bucket（應成功）
curl http://localhost:54321/storage/v1/object/public/product-images/prod-001/main.jpg \
  -o /dev/null -w "%{http_code}"
# 預期：200

# 測試 2：匿名上傳到 private bucket（應失敗）
curl -X POST http://localhost:54321/storage/v1/object/crawler-assets/test.txt \
  -H "Content-Type: text/plain" \
  -d "test content"
# 預期：401 或 403

# 測試 3：帶 anon key 上傳 product-images（非 staff → 應失敗）
curl -X POST http://localhost:54321/storage/v1/object/product-images/test.jpg \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -F "file=@photo.jpg"
# 預期：403（因為 anon 不是 staff）
```

---

## 驗收清單

完成以下所有項目，本次實驗即為通過：

- [ ] `pg_publication_tables` 查到 8 張表（shop 4 + crawler 2 + rag 1 + analytics 1）
- [ ] JavaScript Client 成功收到 Realtime 推送（Console 有 payload）
- [ ] 3 個 Storage Bucket 建立成功（`storage.buckets` 查到 3 筆）
- [ ] Public Bucket（product-images）可匿名 GET 讀取
- [ ] Private Bucket（crawler-assets, rag-documents）需要 auth token
- [ ] Storage RLS Policy 生效（非 staff 無法上傳 product-images）
- [ ] Signed URL 能存取私有 bucket 的檔案

---

## 延伸挑戰

### 挑戰 1：Broadcast 即時通知

用 Broadcast 模式實作「管理員公告」功能：

```javascript
// 發送端
supabase.channel('announcements').send({
  type: 'broadcast',
  event: 'maintenance',
  payload: { message: '系統將於 10 分鐘後維護' },
})

// 接收端
supabase
  .channel('announcements')
  .on('broadcast', { event: 'maintenance' }, (payload) => {
    alert(payload.payload.message)
  })
  .subscribe()
```

### 挑戰 2：Presence 在線人數

用 Presence 模式顯示目前在線的使用者數量：

```javascript
const channel = supabase.channel('online-users')

channel
  .on('presence', { event: 'sync' }, () => {
    const state = channel.presenceState()
    console.log('在線人數:', Object.keys(state).length)
  })
  .subscribe(async (status) => {
    if (status === 'SUBSCRIBED') {
      await channel.track({
        user_id: 'test-user',
        online_at: new Date().toISOString(),
      })
    }
  })
```

### 挑戰 3：停用 Realtime

嘗試移除一張表的 Realtime，並驗證不再收到推送：

```sql
-- 移除 shop.reviews 的 Realtime
ALTER PUBLICATION supabase_realtime DROP TABLE shop.reviews;

-- 確認剩 7 張表
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime';
```
