# 🧠 PostgreSQL vs Supabase
## 你以為你在學資料庫，其實你在用後端平台

---

> 💬 **你有沒有這種感覺？**
>
> 「我幾乎沒裝過 PostgreSQL，
> 但 Supabase 在 Docker 上超簡單——
> 這正常嗎？」
>
> **完全正常。因為你碰到的根本是兩個不同層級的東西。**

---

## 🎯 本章你會學到什麼

```
✅ PostgreSQL 和 Supabase 的本質差異
✅ 為什麼 Supabase 感覺比 PostgreSQL 簡單
✅ 先會 Supabase 的人，該怎麼補 PostgreSQL
✅ Supabase 開發者必學的 7 個 PostgreSQL 技能
✅ 2 週學習計畫
```

---

## 🔥 先問一個關鍵問題

**PostgreSQL 和 Supabase 是競爭關係嗎？**

```
❌ 不是。
```

正確理解：

```
┌─────────────────────────────────────────┐
│              Supabase                   │
│                                         │
│  Auth  │  Storage  │  Realtime  │  API  │
│                                         │
│         ┌───────────────────┐           │
│         │    PostgreSQL     │           │
│         │  (真正的資料庫)    │           │
│         └───────────────────┘           │
└─────────────────────────────────────────┘
```

> 💡 **Supabase 官方定義自己是「Postgres development platform」。**
> 每個 Supabase 專案底層就是一個完整的 PostgreSQL 資料庫，
> 不是「像 PostgreSQL」——**就是 PostgreSQL。**

---

## 🚗 用車子比喻，一次搞懂

```
PostgreSQL = 引擎（核心）

Supabase   = 整輛車
           （引擎 + 變速箱 + 儀表板 + 冷氣 + 導航都裝好）
```

你如果自己安裝 PostgreSQL，你只拿到：

```
一顆很強的引擎
```

其他你要自己處理：

```
❌ Auth 系統         → 要自己接
❌ REST API          → 要自己建
❌ Realtime          → 要自己裝
❌ Storage           → 要自己搞
❌ 管理介面          → 要自己找
❌ 連線池            → 要自己設定
```

而 Supabase 幫你全部裝好了：

```
✅ Auth（GoTrue）
✅ REST API（PostgREST）
✅ Realtime
✅ Storage API
✅ 管理介面
✅ 連線池（Supavisor）
```

---

## 🐳 為什麼 Supabase + Docker 感覺特別簡單？

自己裝 PostgreSQL 的痛點：

```
1. 作業系統差異
2. 套件版本衝突
3. 設定檔位置搞不清楚
4. 權限與資料目錄
5. port 衝突
6. 還要再裝 pgAdmin、PostgREST、Auth……
```

Supabase 的思路：

```bash
# 這一行等於起來整個後端平台
docker compose up
```

結果：

```
= Auth 服務 ✅
= REST API ✅
= 資料庫 ✅
= Storage ✅
= Realtime ✅
```

> 💡 **你碰到的不是「資料庫安裝問題」，
> 你碰到的是「被平台封裝過的資料庫開發體驗」。**

---

## 🧩 兩者關心的問題根本不一樣

| PostgreSQL 關心的 | Supabase 關心的 |
|------------------|----------------|
| Schema 設計 | 如何快速上線 API |
| Normalization | 前端如何直接存取資料 |
| Index 與效能 | 如何整合 Auth + RLS |
| Transaction | 如何降低全端開發摩擦 |
| Query Plan | 如何快速做出 SaaS |
| Function / Trigger | 如何整合 Storage / Realtime |
| Backup / Replication | 如何管理 migration |

---

## ⚠️ 最重要的警告

```
┌─────────────────────────────────────────────┐
│                                             │
│   學 Supabase ≠ 學會 PostgreSQL             │
│                                             │
│   但懂 PostgreSQL → 讓你用 Supabase 更穩    │
│                                             │
└─────────────────────────────────────────────┘
```

很多人用 Supabase 初期很順，後來卡在：

```
❓ Schema 怎麼設才不會爛掉？
❓ RLS policy 怎麼寫才真的安全？
❓ Join 和 View 怎麼整理？
❓ Migration 怎麼控管？
❓ Index 沒設好為什麼變慢？
❓ 要不要用 Trigger / Function？
```

這些問題的答案都在 **PostgreSQL 基礎**，不在 Supabase 文件。

---

## 🌳 Supabase 開發者的 PostgreSQL 技能樹

```
Level 1  ★ 必備（不補就危險）
├── SQL 基本查詢（select / join / group by）
├── Table 設計（primary key / foreign key）
├── Constraint（unique / check）
└── Index 基礎

Level 2  ★★ 實戰（做 SaaS 必須）
├── Join（inner / left / right）
├── View（簡化前端查詢）
├── Transaction
└── Migration 概念

Level 3  ★★★ 進階（讓系統更穩）
├── RLS（Row Level Security）
├── Functions（自訂邏輯）
├── Triggers（自動化）
└── Materialized View（效能優化）

Level 4  ★★★★ 架構（大型系統）
├── Partition
├── Logical Replication
├── Performance Tuning
└── Extension 生態
```

> 🎯 **到 Level 2，你已經能做 90% 的 SaaS 產品。**

---

## 🛠️ 7 個你現在就要補的技能

### 1️⃣ Schema 設計

```sql
-- 基礎但最重要
CREATE TABLE users (
  id   UUID PRIMARY KEY,
  email TEXT UNIQUE
);

CREATE TABLE posts (
  id      UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  title   TEXT,
  content TEXT
);
```

**核心概念：** primary key、foreign key、unique、constraint

---

### 2️⃣ SQL 查詢

至少要熟練：

```sql
SELECT
  posts.title,
  users.email
FROM posts
JOIN users
  ON posts.user_id = users.id
WHERE posts.title ILIKE '%AI%'
ORDER BY posts.created_at DESC
LIMIT 10;
```

> 💡 這比很多 ORM 更清楚，AI agent 也更容易理解。

---

### 3️⃣ Index（效能關鍵）

```sql
-- 沒有 index，查詢就慢
CREATE INDEX idx_posts_user
  ON posts(user_id);
```

**記住：** 很多 Supabase 專案變慢，根本原因是沒設 index。

---

### 4️⃣ View（簡化 API）

```sql
-- 建一個 View
CREATE VIEW post_summary AS
SELECT
  posts.id,
  users.email,
  posts.title
FROM posts
JOIN users
  ON posts.user_id = users.id;
```

Supabase API 會**直接 expose 這個 View**。
前端不用再寫複雜 join。

---

### 5️⃣ Row Level Security（RLS）

```sql
-- 資料庫層級 ACL
CREATE POLICY "users can read own posts"
  ON posts
  FOR SELECT
  USING (auth.uid() = user_id);
```

```
這不是應用層 ACL
這是資料庫層級 ACL
更安全，更難繞過
```

---

### 6️⃣ Functions

```sql
CREATE FUNCTION post_count(uid UUID)
RETURNS INT
LANGUAGE SQL
AS $$
  SELECT COUNT(*) FROM posts
  WHERE user_id = uid
$$;
```

Supabase API 可以直接呼叫 Function。

---

### 7️⃣ Triggers

```sql
-- 自動更新 timestamp
CREATE TRIGGER update_timestamp
  BEFORE UPDATE ON posts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();
```

用途：
```
✅ audit log
✅ 自動 timestamp
✅ 資料同步觸發
```

---

## 📦 Supabase 常用 PostgreSQL Extension

Supabase 預設開好很多 extension，你要知道它們：

| Extension | 用途 |
|-----------|------|
| `uuid-ossp` | 生成 UUID |
| `pgcrypto` | 加密 / hash |
| `pgvector` | AI 向量搜尋 |
| `postgis` | 地理 GIS 資料 |
| `pg_trgm` | 模糊搜尋 |

```sql
-- 開啟向量搜尋（AI embedding 必備）
CREATE EXTENSION vector;
```

---

## 💻 你應該自己跑一次原生 PostgreSQL

即使你用 Supabase，建議至少跑一次：

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=pass \
  -p 5432:5432 \
  postgres
```

連進去：

```bash
psql -h localhost -U postgres
```

你會看到：

```
postgres=#
```

**那個游標，就是 Supabase 背後每天在跑的東西。**

---

## 📅 2 週最短學習計畫

```
Day 1–3   SQL 基礎
          → SELECT / INSERT / UPDATE / DELETE / JOIN

Day 4–5   Schema 設計
          → PRIMARY KEY / FOREIGN KEY / UNIQUE / INDEX

Day 6–7   View
          → 簡化查詢，直接對應 Supabase API

Day 8–10  RLS（Row Level Security）
          → 這是 Supabase 安全的核心

Day 11–14 Functions + Triggers
          → 商業邏輯移到資料庫層
```

> 🏆 **完成這 2 週，你已經比 90% 的 Supabase 開發者懂得更多。**

---

## 🗺️ 三個學習階段

### 🥉 第一階段：把 Supabase 當「已包好的 Postgres 平台」

先做熟：

```
table / relationship
RLS
auth users
storage
migrations
edge functions
local docker 開發
```

### 🥈 第二階段：補 PostgreSQL 原生能力

補這幾塊最有價值：

```
SQL 查詢與 JOIN
primary / foreign key / index
transaction
views / materialized views
functions / triggers
schema migration 概念
role / privilege 基礎
```

### 🥇 第三階段：再回頭看 Supabase

這時你會看到：

```
不是「很方便的後端工具」
而是「以 PostgreSQL 為中心的工程化開發平台」
```

---

## 📝 本章重點複習

```
□ Supabase = PostgreSQL + 整合好的後端周邊
□ 每個 Supabase 專案就是一個真實的 PostgreSQL DB
□ Docker 簡單 ≠ PostgreSQL 簡單，是封裝層幫你解決了問題
□ 學 Supabase ≠ 學會 PostgreSQL
□ 懂 PostgreSQL → 讓 Supabase 用得更穩
□ Schema 設計是最核心能力
□ 沒有 Index 是大多數效能問題的根源
□ RLS 是資料庫層 ACL，比應用層更安全
□ 到 Level 2（View + Transaction）已能做 90% SaaS
```

---

## 🚀 對你最重要的觀察

你的系統設計偏向：

```
repo-first
stateless
static pipeline
```

而 PostgreSQL 剛好提供：

```
strong consistency
schema control
long-term stability
```

這組合非常適合你正在做的：

```
✅ HR 系統
✅ SaaS backend
✅ 需要長期維運的資料
```

比很多 NoSQL 更穩、更容易維護、更適合 AI agent 操作。

---

*— 基於 PostgreSQL + Supabase 架構原理整理*