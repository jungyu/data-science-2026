# 作業四：RLS 進階 — 多租戶設計

---

## 題目

設計一個多租戶的資料存取控制系統，實現：

- 每個使用者只能看到自己的資料
- 禁止讀取他人資料
- 管理員可看到所有資料

---

## 要求

1. 建立含 `user_id` 的資料表
2. 啟用 RLS
3. 建立至少 2 條 Policy
4. 測試並說明 RLS 的效果

---

## 資料表設計

```sql
CREATE TABLE user_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  model_name TEXT,
  input_data JSONB,
  output_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## RLS 設定

### 啟用 RLS

```sql
ALTER TABLE user_predictions ENABLE ROW LEVEL SECURITY;
```

### Policy 1：使用者只能讀取自己的資料

```sql
CREATE POLICY "Users can read own data"
ON user_predictions
FOR SELECT
USING (auth.uid() = user_id);
```

### Policy 2：使用者只能寫入自己的資料

```sql
CREATE POLICY "Users can insert own data"
ON user_predictions
FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

### Policy 3（進階）：使用者可以更新自己的資料

```sql
CREATE POLICY "Users can update own data"
ON user_predictions
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

### Policy 4（進階）：使用者可以刪除自己的資料

```sql
CREATE POLICY "Users can delete own data"
ON user_predictions
FOR DELETE
USING (auth.uid() = user_id);
```

---

## 測試方式

### 方式 1：Supabase Dashboard

1. 建立兩個測試使用者
2. 分別以不同使用者身份查詢
3. 確認只能看到自己的資料

### 方式 2：Python 測試

```python
# 使用者 A 的 JWT
supabase_a = create_client(url, key)
# 設定使用者 A 的 session

# 使用者 B 的 JWT
supabase_b = create_client(url, key)
# 設定使用者 B 的 session

# 使用者 A 只能看到自己的資料
response_a = supabase_a.table("user_predictions").select("*").execute()

# 使用者 B 只能看到自己的資料
response_b = supabase_b.table("user_predictions").select("*").execute()
```

---

## 繳交內容

1. 完整的 SQL（DDL + RLS Policy）
2. 測試結果截圖或說明
3. 回答以下問題：
   - RLS 與後端 API 權限控制有什麼不同？
   - 為什麼 RLS 在資料科學場景中特別重要？
   - 如果不用 RLS，要怎麼實現相同的功能？

---

## 評分標準（20 分）

| 項目 | 分數 | 說明 |
|------|------|------|
| DDL 正確 | 5 | 資料表設計合理 |
| RLS Policy 正確 | 5 | Policy 語法正確且有效 |
| 測試完成 | 5 | 有測試結果佐證 |
| 問答品質 | 5 | 理解 RLS 的原理與意義 |
