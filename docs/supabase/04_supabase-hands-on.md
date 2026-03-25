# 第三章：Supabase 實作（從 0 到完成）

---

## 3.1 建立專案

步驟：

1. 建立 Supabase 帳號（前往 [https://supabase.com](https://supabase.com)）
2. 新增 Project
3. 取得：
   - Project URL
   - anon key
   - service role key

---

## 3.2 建立資料表（資料科學案例）

案例：分析 YouTube 影片資料

```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  views INTEGER,
  tags TEXT[],
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3.3 用 Python 連接 Supabase

```python
from supabase import create_client

url = "https://xxxx.supabase.co"
key = "anon-key"

supabase = create_client(url, key)

data = supabase.table("videos").select("*").execute()
print(data)
```

---

## 3.4 建立 RLS

啟用：

```sql
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
```

建立 Policy：

```sql
CREATE POLICY "Users can insert own videos"
ON videos
FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

---

## 本章重點回顧

| 步驟 | 操作 | 說明 |
|------|------|------|
| 1 | 建立專案 | 取得 URL + Key |
| 2 | 建立資料表 | SQL DDL |
| 3 | Python 連線 | supabase-py SDK |
| 4 | 啟用 RLS | 資料層安全 |
