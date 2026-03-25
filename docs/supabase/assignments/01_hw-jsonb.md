# 作業二：JSONB 應用 — AI 模型結果資料庫

---

## 題目

建立一個「AI 模型結果資料庫」，能夠：

- 儲存模型的 input JSON
- 儲存模型的 output JSON
- 能查詢特定欄位

---

## 要求

1. 建立 `predictions` 資料表，包含 JSONB 欄位
2. 插入至少 5 筆模型預測資料
3. 使用 JSONB 查詢語法進行篩選

---

## 資料表設計建議

```sql
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_name TEXT NOT NULL,
  input_data JSONB NOT NULL,
  output_data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 測試資料範例

```sql
INSERT INTO predictions (model_name, input_data, output_data)
VALUES
  ('linear_regression',
   '{"features": ["age", "income"], "values": [25, 50000]}',
   '{"prediction": 0.85, "confidence": 0.92}'),
  ('random_forest',
   '{"features": ["age", "income", "score"], "values": [30, 75000, 88]}',
   '{"prediction": 0.95, "confidence": 0.97}');
```

---

## 必須完成的查詢

### 查詢 1：取出 output 中的 score

```sql
SELECT model_name, output_data->>'prediction' AS prediction
FROM predictions;
```

### 查詢 2：篩選高分預測

```sql
SELECT *
FROM predictions
WHERE (output_data->>'confidence')::NUMERIC > 0.9;
```

### 查詢 3：查詢使用特定 feature 的預測

```sql
SELECT *
FROM predictions
WHERE input_data->'features' ? 'income';
```

---

## 繳交內容

1. 完整的 `CREATE TABLE` SQL
2. 至少 5 筆測試資料
3. 至少 3 個 JSONB 查詢（包含篩選條件）
4. 簡短說明 JSONB 在資料科學中的應用場景

---

## 評分標準（20 分）

| 項目 | 分數 | 說明 |
|------|------|------|
| 資料表設計 | 5 | JSONB 欄位設計合理 |
| 測試資料品質 | 5 | 資料有意義，結構一致 |
| JSONB 查詢 | 5 | 語法正確，使用多種運算子 |
| 應用說明 | 5 | 能連結資料科學實務場景 |
