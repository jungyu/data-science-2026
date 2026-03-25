# 作業三：Supabase + Python 整合

---

## 題目

使用 Python 操作 Supabase，完成完整的 CRUD 流程。

---

## 要求

使用 `supabase-py` 完成以下操作：

1. **建立資料** — Insert
2. **查詢資料** — Select（含條件篩選）
3. **更新資料** — Update
4. **刪除資料** — Delete

---

## 必須完成的程式碼

### 1. 連線設定

```python
from supabase import create_client

url = "YOUR_URL"
key = "YOUR_ANON_KEY"

supabase = create_client(url, key)
```

### 2. 插入資料

```python
supabase.table("predictions").insert({
    "model_name": "my_model",
    "input_data": {"feature1": 0.5, "feature2": 0.8},
    "output_data": {"prediction": 0.92, "confidence": 0.88}
}).execute()
```

### 3. 查詢資料（含條件）

```python
# 查詢所有資料
response = supabase.table("predictions").select("*").execute()

# 條件查詢
response = (
    supabase.table("predictions")
    .select("model_name, output_data")
    .eq("model_name", "my_model")
    .execute()
)
```

### 4. 更新資料

```python
supabase.table("predictions").update({
    "output_data": {"prediction": 0.95, "confidence": 0.93}
}).eq("model_name", "my_model").execute()
```

### 5. 刪除資料

```python
supabase.table("predictions").delete().eq(
    "model_name", "my_model"
).execute()
```

---

## 進階要求（加分）

### 與 Pandas 整合

```python
import pandas as pd

response = supabase.table("predictions").select("*").execute()
df = pd.DataFrame(response.data)

# 進行分析
print(df.describe())
```

### 批次寫入

```python
records = [
    {"model_name": f"model_{i}", "input_data": {"x": i}, "output_data": {"y": i * 2}}
    for i in range(10)
]

supabase.table("predictions").insert(records).execute()
```

---

## 繳交內容

1. 完整的 Python 程式碼（`.py` 或 `.ipynb`）
2. 執行結果截圖或輸出
3. 簡短說明每個操作的用途

---

## 評分標準（20 分）

| 項目 | 分數 | 說明 |
|------|------|------|
| Insert 正確 | 5 | 資料成功寫入 |
| Select 正確 | 5 | 查詢結果正確，含條件篩選 |
| Update 正確 | 5 | 資料成功更新 |
| Delete 正確 | 5 | 資料成功刪除 |
| 加分：Pandas 整合 | +3 | 成功轉為 DataFrame |
| 加分：批次寫入 | +2 | 成功批次操作 |
