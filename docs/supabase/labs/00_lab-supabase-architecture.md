# 實驗 1：理解 Supabase 與 PostgreSQL 的關係

---

## 實驗目標

1. 理解 Supabase 架構
2. 認識 PostgreSQL 在 Supabase 中的位置
3. 能在 Supabase 建立資料表並操作 SQL

---

## 1.1 Supabase 架構概念

![Supabase 架構圖](https://supabase.com/docs/img/supabase-architecture--light.svg)

![Supabase 生態系](https://media.licdn.com/dms/image/v2/D5612AQGU4nNCHYETDg/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1673532136828?e=2147483647&t=e_9QB5to6LNSUUaGSYArRh2YyLEQsh63GXX29fibqSY&v=beta)

![Table View](https://supabase.com/docs/img/table-view.png)

![Supabase Admin](https://cdn.prod.website-files.com/6542d8f9e468531067fe9978/6949440ba5b181a03b4e9167_supabase-admin-min.png)

### 架構說明

Supabase =

```
PostgreSQL（核心資料庫）
+ PostgREST（自動產生 API）
+ Auth（身份驗證）
+ Storage（檔案儲存）
+ Realtime（即時推送）
```

重點：

- Supabase 沒有自創資料庫
- 它 100% 使用 PostgreSQL
- 你學的 SQL 完全通用

---

## 1.2 建立 Supabase 專案

### 步驟

1. 前往 [https://supabase.com](https://supabase.com)
2. 建立 Project
3. 記錄：
   - Project URL
   - anon public key
   - service role key

---

## 1.3 操作練習

### 練習 A：進入 SQL Editor

1. 在 Supabase Dashboard 左側選單找到 **SQL Editor**
2. 嘗試執行以下查詢：

```sql
SELECT version();
```

你應該看到 PostgreSQL 的版本資訊。

### 練習 B：瀏覽 Table Editor

1. 在左側選單找到 **Table Editor**
2. 觀察預設的 schema 結構
3. 理解 `public` schema 的意義

### 練習 C：查看 API 設定

1. 進入 **Settings → API**
2. 記錄你的 Project URL 和 anon key
3. 理解這些 key 的用途

---

## 實驗檢核

完成以下項目打勾：

- [ ] 已建立 Supabase 專案
- [ ] 已成功執行 `SELECT version()`
- [ ] 已記錄 Project URL 和 anon key
- [ ] 能說明 Supabase 架構中各元件的功能
