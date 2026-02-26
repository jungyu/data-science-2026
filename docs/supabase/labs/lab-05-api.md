# 實驗 5：建立簡易資料科學 API

---

## 實驗目標

- 理解 Supabase 自動產生 API 的機制
- 使用 REST API 查詢資料
- 建立可供外部存取的資料科學 API

---

## 5.1 Supabase 自動產生 API

Supabase 使用 PostgREST 自動為每個資料表產生 REST API。

你建立的 `videos` 資料表，自動產生以下端點：

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/rest/v1/videos` | 查詢所有影片 |
| POST | `/rest/v1/videos` | 新增影片 |
| PATCH | `/rest/v1/videos?id=eq.xxx` | 更新影片 |
| DELETE | `/rest/v1/videos?id=eq.xxx` | 刪除影片 |

---

## 5.2 使用 curl 測試

### 查詢所有資料

```bash
curl 'https://YOUR_PROJECT.supabase.co/rest/v1/videos' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### 條件查詢

```bash
# 查詢觀看數大於 10000 的影片
curl 'https://YOUR_PROJECT.supabase.co/rest/v1/videos?views=gt.10000' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### 選擇欄位

```bash
curl 'https://YOUR_PROJECT.supabase.co/rest/v1/videos?select=title,views' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

---

## 5.3 PostgREST 查詢語法

| 運算子 | 說明 | 範例 |
|--------|------|------|
| `eq` | 等於 | `?title=eq.AI Revolution` |
| `gt` | 大於 | `?views=gt.10000` |
| `lt` | 小於 | `?views=lt.5000` |
| `gte` | 大於等於 | `?likes=gte.500` |
| `like` | 模糊比對 | `?title=like.*AI*` |
| `order` | 排序 | `?order=views.desc` |
| `limit` | 限制筆數 | `?limit=10` |

---

## 5.4 用 Python requests 呼叫 API

```python
import requests

url = "https://YOUR_PROJECT.supabase.co/rest/v1/videos"
headers = {
    "apikey": "YOUR_ANON_KEY",
    "Authorization": "Bearer YOUR_ANON_KEY"
}
params = {
    "select": "title,views,metadata",
    "views": "gt.10000",
    "order": "views.desc"
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

---

## 5.5 資料科學 API 應用場景

### 場景 A：模型預測 API

```
前端提交資料 → Supabase 儲存 → Python 模型預測 → 結果寫回 Supabase → 前端查詢結果
```

### 場景 B：即時儀表板

```
資料持續寫入 Supabase → REST API 查詢最新資料 → 前端儀表板即時更新
```

### 場景 C：資料共享平台

```
分析師上傳結果 → RLS 控制權限 → 各部門透過 API 查詢自己的資料
```

---

## 期末整合實驗

### 專題：建立「模型預測平台」

需求：

1. 建立 `users` 表
2. 建立 `predictions` 表
3. 每個 user 只能看到自己的預測（RLS）
4. 用 Python 存資料
5. 使用 REST API 查詢

```sql
-- users 表
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE,
  name TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- predictions 表
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  model_name TEXT,
  input_data JSONB,
  output_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 啟用 RLS
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- 使用者只能讀取自己的預測
CREATE POLICY "Users read own predictions"
ON predictions
FOR SELECT
USING (auth.uid() = user_id);
```

---

## 實驗檢核

完成以下項目打勾：

- [ ] 理解 PostgREST 自動產生 API 的機制
- [ ] 已使用 curl 或瀏覽器測試 API
- [ ] 理解查詢參數語法
- [ ] 已使用 Python requests 呼叫 API
- [ ] 能說明至少一個資料科學 API 應用場景
