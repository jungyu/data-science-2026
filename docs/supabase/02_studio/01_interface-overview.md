# Head First Studio 介面總覽 — 六大模組快速導航

> **"工具箱裡有六把工具，你得先知道哪把是螺絲起子、哪把是榔頭。"**

打開 `http://localhost:54323`，左邊的 sidebar 就是你的主選單。

別急著亂點——先花 10 分鐘，跟著這份指南把六大模組走一遍。等你知道「什麼東西在哪裡」，後面的學習速度會快三倍。

![Studio 總覽](https://supabase.com/_next/image?q=75&url=%2Fimages%2Fblog%2Flaunch-week-three%2Fstudio%2Fopen-source-studio-thumb.png&w=3840)

---

## 模組 1：Table Editor（你最常用的）

**用途**：像 Excel 一樣看資料、新增欄位、修改 schema、做 CRUD 操作。

你在 Table Editor 做的每一件事，背後都是 SQL。只是 Studio 幫你把 SQL 藏起來了。

```
┌─────────────────────────────────────────┐
│  Table Editor                           │
│  ┌─────────┬──────────┬───────────────┐ │
│  │ id          │ name     │ email         │ │
│  ├─────────────┼──────────┼───────────────┤ │
│  │ 01HXY8Z3K4… │ Alice    │ a@example.com │ │
│  │ 01HXY8Z5M7… │ Bob      │ b@example.com │ │
│  │ + Insert row...                    │ │
│  └────────────────────────────────────┘ │
│  ← 看起來像 Excel，背後全是 SQL         │
└─────────────────────────────────────────┘
```

**對應 SQL**：

| 你在 GUI 做的事 | 背後跑的 SQL |
|-----------------|-------------|
| 看資料列表 | `SELECT * FROM public.users LIMIT 100;` |
| 新增一筆 | `INSERT INTO public.users (name, email) VALUES (...);` |
| 修改欄位型別 | `ALTER TABLE public.users ALTER COLUMN name TYPE varchar(100);` |
| 刪除一筆 | `DELETE FROM public.users WHERE id = 1;` |
| 加欄位 | `ALTER TABLE public.users ADD COLUMN avatar_url TEXT;` |

> ### 腦筋急轉彎 🧠
>
> **Q：你在 Table Editor 改了一個欄位型別從 `text` 變成 `integer`，背後跑了什麼 SQL？**
>
> A：`ALTER TABLE ... ALTER COLUMN ... TYPE integer USING ...::integer;`
>
> 注意那個 `USING` — 如果欄位裡有不能轉成數字的值，這條 SQL 會直接報錯。
> Table Editor 會幫你提示，但你得知道它在做什麼。

**什麼時候用 Table Editor**：
- 查看資料、快速驗證 INSERT 是否成功
- 建立 Foreign Key 關聯（GUI 操作比手寫 SQL 直覺）
- 快速新增測試欄位

**什麼時候不要用 Table Editor**：
- 正式的結構變更（用 Migration）
- 批量資料操作（用 SQL Editor）
- 需要 version control 的改動（GUI 操作不留紀錄！）

---

## 模組 2：SQL Editor（工程師主戰場）

**用途**：寫 SQL、建表、跑 migration、debug、設計 index。

這是你在 Studio 裡最強大的武器。Table Editor 能做的，SQL Editor 都能做。反過來不成立。

```
┌──────────────────────────────────────────┐
│  SQL Editor                              │
│  ┌──────────────────────────────────┐    │
│  │ SELECT                           │    │
│  │   u.name,                        │    │
│  │   count(o.id) AS order_count     │    │
│  │ FROM users u                     │    │
│  │ LEFT JOIN orders o ON o.user_id  │    │
│  │   = u.id                         │    │
│  │ GROUP BY u.name;                 │    │
│  └──────────────────────────────────┘    │
│  [▶ Run]  [💾 Save]  [📋 Templates]      │
└──────────────────────────────────────────┘
```

**內建範本（Templates）寶庫**：

點擊 SQL Editor 右上角的 Templates 按鈕，你會看到一堆現成的 SQL 範本：

| 範本 | 幹嘛用的 |
|------|---------|
| Quick Start | 快速建表、插入資料 |
| RBAC | Role-Based Access Control 範本 |
| Full-Text Search | 全文檢索的 `tsvector` + `tsquery` |
| RLS Policies | Row Level Security 常見 pattern |
| Functions | PL/pgSQL function 範例 |

> ### 腦筋急轉彎 🧠
>
> **Q：為什麼 SQL Editor 比 Table Editor 重要？**
>
> A：因為 SQL 可以 version control，GUI 操作不行。
>
> 你在 Table Editor 點點點建了一張表，這些操作不會出現在你的 git repo 裡。
> 但你在 SQL Editor 寫的 `CREATE TABLE`，可以存成 `.sql` 檔，放進 migration，團隊每個人都能重現。

**SQL Editor 的隱藏技巧**：
- `Cmd + Enter`（Mac）或 `Ctrl + Enter`（Windows）：執行選取的 SQL
- 可以同時寫多段 SQL，只選取要執行的那段
- 執行結果會以表格顯示，可以直接複製

---

## 模組 3：Database（結構管理）

**用途**：檢視 Tables、Views、Functions、Triggers、Extensions——這是做「架構審查」的地方。

Table Editor 讓你看「資料」，Database 頁面讓你看「結構」。

```
┌─────────────────────────────────────┐
│  Database                           │
│  ├── Tables                         │
│  │   ├── public.users              │
│  │   ├── public.orders             │
│  │   └── public.products           │
│  ├── Views                          │
│  ├── Functions                      │
│  ├── Triggers                       │
│  ├── Extensions                     │
│  │   ├── uuid-ossp     ✅ enabled  │
│  │   ├── pgvector       ❌ disabled │
│  │   └── pg_trgm        ❌ disabled │
│  └── Roles                          │
└─────────────────────────────────────┘
```

**你能在 Database 頁面看到什麼**：

| 子分頁 | 顯示內容 | 常見用途 |
|--------|---------|---------|
| Tables | 每張表的 Columns、Indexes、Policies | 檢查欄位型別、確認 index 是否建好 |
| Views | 所有 View 的定義 | 審查查詢邏輯 |
| Functions | PL/pgSQL / SQL functions | 確認 function 簽名和權限 |
| Triggers | 觸發器列表 | 檢查自動化邏輯 |
| Extensions | 已啟用 / 可啟用的 PostgreSQL 擴充 | 開啟 `pgvector`、`pg_trgm` 等 |
| Roles | 資料庫角色 | 確認 `anon`、`authenticated` 權限 |

> ### 你的大腦在想 🧠
>
> 「Table Editor 和 Database 頁面不是在看一樣的東西嗎？」
>
> 不一樣。Table Editor 是「操作資料」，Database 是「審查結構」。
> 就像 Excel 讓你填數字，但你需要另一個地方看「這個欄位是什麼型別、有沒有加 index」。

---

## 模組 4：Authentication

**用途**：管理使用者、測試登入流程、查看 JWT token。

Supabase 把認證做成一個獨立的服務（GoTrue），Studio 的 Authentication 頁面就是這個服務的管理介面。

```
┌──────────────────────────────────────┐
│  Authentication                      │
│  ├── Users          → 使用者列表     │
│  ├── Policies       → RLS 政策管理   │
│  ├── Providers      → OAuth 設定     │
│  ├── Email Templates → 郵件模板      │
│  └── URL Configuration → 重導向設定  │
└──────────────────────────────────────┘
```

**本地測試的關鍵**：所有認證郵件（註冊確認、密碼重設）都會寄到 **Inbucket**。

```bash
# 認證郵件在這裡收
open http://localhost:54324
```

> ### 腦筋急轉彎 🧠
>
> **Q：為什麼 `auth.users` 在 Studio 的 Authentication 頁面，不在 Table Editor？**
>
> A：因為 `auth` schema 是 Supabase 管理的，不是你的 `public` schema。
>
> 你不應該直接改 `auth.users`。如果你需要存額外的使用者資料（暱稱、頭像），
> 正確做法是在 `public` schema 建一張 `profiles` 表，用 FK 關聯到 `auth.users.id`。

**Authentication 頁面能做什麼**：
- 手動建立測試使用者
- 查看每個使用者的 metadata、最後登入時間
- 設定 OAuth providers（Google、GitHub 等）
- 自訂認證郵件的模板

---

## 模組 5：Storage

**用途**：存圖片、檔案（S3 相容的物件儲存）。

Storage 不是資料庫——它是一個獨立的檔案儲存系統，但它的存取權限可以透過 RLS 控制。

```
┌──────────────────────────────────────┐
│  Storage                             │
│  ├── Buckets                         │
│  │   ├── avatars     (public)  🌐   │
│  │   └── documents   (private) 🔒   │
│  │                                   │
│  │   Public bucket:  任何人都能讀     │
│  │   Private bucket: 受 RLS 保護     │
│  └───────────────────────────────────┘
```

**Public vs Private Bucket**：

| | Public Bucket | Private Bucket |
|--|--------------|----------------|
| 讀取 | 任何人都能用 URL 直接存取 | 需要 JWT token |
| 適合 | 使用者頭像、公開圖片 | 私人文件、付費內容 |
| RLS | 不受 RLS 限制 | 受 RLS 保護 |
| URL 格式 | `/storage/v1/object/public/bucket/file` | `/storage/v1/object/sign/bucket/file` |

> ### 你的大腦在想 🧠
>
> 「我的圖片放 Storage，那圖片的 metadata（檔名、上傳者、大小）存在哪？」
>
> 答案：`storage.objects` 表。對，Storage 背後還是 PostgreSQL。
> 每個上傳的檔案，都會在 `storage.objects` 留一筆紀錄。

---

## 模組 6：API

**用途**：自動生成的 REST API 文件——加一個欄位，API 文件自動更新。

這是 Supabase 最神奇的地方之一：你不需要手寫任何 API endpoint。PostgREST 會把你的 `public` schema 直接變成 REST API。

```
┌──────────────────────────────────────────┐
│  API Docs                                │
│                                          │
│  Tables:                                 │
│  ├── users        GET POST PATCH DELETE  │
│  ├── orders       GET POST PATCH DELETE  │
│  └── products     GET POST PATCH DELETE  │
│                                          │
│  Code Examples:                          │
│  ┌──────────────────────────────────┐    │
│  │ // JavaScript                    │    │
│  │ const { data } = await supabase  │    │
│  │   .from('users')                 │    │
│  │   .select('*')                   │    │
│  └──────────────────────────────────┘    │
│                                          │
│  [JavaScript] [Dart] [cURL]              │
└──────────────────────────────────────────┘
```

**API 頁面能做什麼**：
- 查看每張表的 REST endpoint
- 複製 JavaScript / Dart / cURL 程式碼片段
- 查看 `anon` key 和 `service_role` key
- 確認哪些表有被暴露（只有 `public` schema）

**用 cURL 快速測試**：

```bash
# 取得 users 表的所有資料
curl 'http://localhost:54321/rest/v1/users' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

> `YOUR_ANON_KEY` 在哪裡找？打開 API 頁面，第一行就是。
> 或者跑 `supabase status`，會列出所有 key。

---

## 六大模組協作圖

這六個模組不是各自獨立的——它們共同構成一個完整的開發流程：

```
                    ┌─────────────┐
                    │  你（開發者） │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │  Table   │  │   SQL    │  │ Database │
      │  Editor  │  │  Editor  │  │  (結構)  │
      │ (資料)   │  │ (開發)   │  │ (審查)   │
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           │              │              │
           └──────────────┼──────────────┘
                          │
                ┌─────────┼─────────┐
                ▼         ▼         ▼
          ┌─────────┐ ┌───────┐ ┌─────┐
          │  Auth   │ │Storage│ │ API │
          │(認證)   │ │(檔案) │ │(文件)│
          └────┬────┘ └───┬───┘ └──┬──┘
               │          │        │
               ▼          ▼        ▼
      ┌──────────────────────────────────┐
      │     PostgreSQL（一切的根基）       │
      │  docker-compose: supabase-db     │
      └──────────────────────────────────┘
```

**對應的 Docker 服務**：

| 模組 | Docker 服務 | 說明 |
|------|------------|------|
| Table Editor / SQL Editor / Database | `supabase-db` | PostgreSQL 本身 |
| Authentication | `supabase-auth` (GoTrue) | 認證服務 |
| Storage | `supabase-storage` | S3 相容儲存 |
| API | `supabase-rest` (PostgREST) | 自動 REST API |
| Studio 本身 | `supabase-studio` | 你看到的 Web UI |

---

## 動手做：5 分鐘快速巡禮

```
📝 Exercise: Studio 快速巡禮（預計 5 分鐘）

確認你的 Studio 已經跑在 http://localhost:54323，然後照做：

1. 點進 Table Editor
   → 觀察上方的 schema 選擇器（你應該看到 public, auth, storage, extensions）
   → 預設顯示 public schema

2. 點進 SQL Editor
   → 在編輯區貼上這段 SQL，然後按 Cmd+Enter（Mac）或 Ctrl+Enter（Win）：

   SELECT version();

   → 你應該看到 PostgreSQL 的版本號

3. 點進 Database → Extensions
   → 找到 uuid-ossp，確認它是 enabled
   → 找到 pgvector，看看它目前是 enabled 還是 disabled

4. 點進 Authentication → Users
   → 查看目前有多少 users（新環境應該是 0）

5. 點進 Storage
   → 查看是否有任何 bucket（新環境應該是空的）

6. 點進 API Docs
   → 找到頁面上的 anon key
   → 把它複製下來，等等測試會用到
```

> ### 完成檢查 ✅
>
> 如果你在 SQL Editor 成功跑了 `SELECT version();` 並看到結果，恭喜——你的 Studio 環境是正常的。
>
> 如果哪個步驟卡住了，回去看 `../labs/05_lab-docker-supabase.md` 確認 Docker 服務都有跑起來。

---

## 你的大腦在想：「所以我平常開發該用哪個模組？」

```
日常開發流程：

寫新功能的 SQL    → SQL Editor（寫完存成 .sql 檔）
驗證資料正不正確  → Table Editor（像 Excel 一樣瀏覽）
檢查結構和 index  → Database 頁面
測試認證流程      → Authentication + Inbucket
上傳測試圖片      → Storage
前端串接前確認    → API Docs（複製 curl 指令先測）
```

**下一步**：打開 `02_schema-strategy.md`，學會用 Schema 分區管理你的多個專案。
