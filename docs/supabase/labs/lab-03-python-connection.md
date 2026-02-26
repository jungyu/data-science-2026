# 實驗 3：Python 連接 Supabase

---

## 實驗目標

- 使用 Python 存取 Supabase
- 將模型預測寫入資料庫
- 熟悉 CRUD 操作

---

## 3.1 安裝套件

```bash
pip install supabase
```

---

## 3.2 連線範例

```python
from supabase import create_client

url = "YOUR_URL"
key = "YOUR_ANON_KEY"

supabase = create_client(url, key)

# 查詢所有影片
response = supabase.table("videos").select("*").execute()
print(response.data)
```

---

## 3.3 插入資料

```python
supabase.table("videos").insert({
    "title": "New Video from Python",
    "channel": "PythonLab",
    "views": 5000,
    "likes": 200,
    "tags": ["Python", "Tutorial"],
    "metadata": {"model": "test", "score": 0.75}
}).execute()
```

---

## 3.4 條件查詢

```python
# 查詢觀看數大於 10000 的影片
response = (
    supabase.table("videos")
    .select("title, views")
    .gt("views", 10000)
    .execute()
)
print(response.data)
```

---

## 3.5 更新資料

```python
supabase.table("videos").update({
    "views": 20000
}).eq("title", "AI Revolution").execute()
```

---

## 3.6 刪除資料

```python
supabase.table("videos").delete().eq(
    "title", "New Video from Python"
).execute()
```

---

## 3.7 模擬模型預測寫入

```python
# 模擬模型預測
prediction = {
    "model": "linear_regression",
    "score": 0.92,
    "features": ["views", "likes", "tags_count"]
}

supabase.table("videos").insert({
    "title": "Prediction Result",
    "channel": "AI Lab",
    "views": 12000,
    "likes": 600,
    "metadata": prediction
}).execute()
```

---

## 3.8 與 Pandas 整合

```python
import pandas as pd

response = supabase.table("videos").select("*").execute()
df = pd.DataFrame(response.data)

print(df.head())
print(df.describe())
```

---

## 實驗檢核

完成以下項目打勾：

- [ ] 已安裝 `supabase` 套件
- [ ] 已成功連線並查詢資料
- [ ] 已完成插入、更新、刪除操作
- [ ] 已成功將模型預測結果寫入資料庫
- [ ] 已將查詢結果轉為 Pandas DataFrame
