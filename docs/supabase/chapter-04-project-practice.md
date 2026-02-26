# 第四章：資料科學專案實戰

---

## 專案題目：建立一個模型預測平台

流程：

1. 使用 Python 訓練模型
2. 把模型結果存入 Supabase
3. 使用 REST API 提供查詢
4. 用 RLS 控制使用者資料

---

## 4.1 存模型預測結果

```sql
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  input_data JSONB,
  output_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4.2 Python 寫入

```python
result = model.predict(data)

supabase.table("predictions").insert({
    "user_id": user_id,
    "input_data": input_json,
    "output_data": result_json
}).execute()
```

---

## 4.3 REST API 查詢

Supabase 自動產生 API：

```
GET https://project.supabase.co/rest/v1/predictions
```

加入 Header：

```
apikey: anon-key
Authorization: Bearer <user-jwt>
```

---

## 4.4 RLS 保護預測結果

```sql
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own predictions"
ON predictions
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own predictions"
ON predictions
FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

---

## 完整流程圖

```
Python 模型訓練
    ↓
模型預測結果（JSON）
    ↓
supabase.table("predictions").insert()
    ↓
Supabase PostgreSQL 儲存
    ↓
REST API 自動產生
    ↓
前端 / 其他服務查詢
    ↓
RLS 確保只看到自己的資料
```

---

## 本章重點回顧

| 步驟 | 技術 | 說明 |
|------|------|------|
| 模型訓練 | Python / sklearn | 產出預測結果 |
| 資料儲存 | JSONB | 彈性儲存模型輸出 |
| API 查詢 | PostgREST | 自動產生，免寫後端 |
| 權限控制 | RLS | 資料列層級安全 |
