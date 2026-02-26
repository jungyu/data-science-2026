# 第二章：Supabase 是什麼？與 PostgreSQL 的關係？

---

## 2.1 Supabase 的本質

![Supabase Logo](https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/supabase.svg)

![Supabase 除錯介面](https://supabase.com/docs/img/troubleshooting/18ed2c88-332e-4e66-b9b4-c37e99a39104.png)

![Supabase 架構圖](https://supabase.com/docs/img/supabase-architecture--light.svg)

![Supabase 系統結構](https://www.workingsoftware.dev/content/images/thumbnail/structurizr-75038-Supabase--7-.png)

### Supabase = PostgreSQL + 後端服務層

Supabase 本質是：

```
PostgreSQL（核心）
+ PostgREST（自動產生 API）
+ Auth（身份驗證）
+ Storage（檔案儲存）
+ Realtime（即時推送）
```

它不是「取代 PostgreSQL」，它是「幫 PostgreSQL 做雲端化包裝」。

---

## 2.2 Supabase 與 PostgreSQL 的關係

| PostgreSQL | Supabase |
|------------|----------|
| 純資料庫引擎 | 包裝好的後端平台 |
| 需要自行架設 | 雲端管理 |
| 無內建 API | 自動產生 REST API |
| 無身份管理 | 內建 Auth |
| 無即時功能 | Realtime |

關係是：

> Supabase 100% 使用 PostgreSQL
> 你學的 SQL 完全通用

---

## 2.3 為什麼資料科學用 Supabase 比直接用 PostgreSQL 好？

### 優勢 1：自動產生 API

不用寫後端：

```
GET /rest/v1/students
```

直接變 API。

### 優勢 2：內建身份驗證

- Google login
- Email login
- JWT

資料科學專案常忽略這塊。

### 優勢 3：RLS（資料科學真正缺的能力）

Row Level Security：

```sql
CREATE POLICY "Users can see own data"
ON students
FOR SELECT
USING (auth.uid() = user_id);
```

資料科學模型可以：

- A 客戶只能看到自己資料
- 不用寫後端權限邏輯

### 優勢 4：JSONB + AI 結構儲存

適合：

- 存 LLM 結果
- 存 embedding
- 存 metadata

---

## 本章重點回顧

| 概念 | 說明 |
|------|------|
| Supabase 本質 | PostgreSQL + 後端服務層 |
| PostgREST | 自動從資料表產生 REST API |
| Auth | 內建身份驗證系統 |
| RLS | 資料列層級的權限控制 |
| Realtime | 即時資料推送 |
