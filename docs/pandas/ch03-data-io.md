# Ch03：資料的進與出

> **本章目標**：學會從各種格式讀取資料進 Pandas，也學會把分析結果存出來。

---

## 🚪 資料的大門

在真實工作中，你的資料不會自己跑進 Python。你需要：

1. **讀進來**（Read）：把外部檔案變成 DataFrame
2. **存出去**（Write）：把分析結果存成檔案

```
        外部世界                    Pandas 世界
  ┌──────────────┐   read_xxx()   ┌──────────────┐
  │  CSV 檔案    │ ─────────────→ │              │
  │  Excel 檔案  │ ─────────────→ │  DataFrame   │
  │  JSON 檔案   │ ─────────────→ │              │
  │  SQL 資料庫  │ ─────────────→ │              │
  └──────────────┘                └──────┬───────┘
                                         │
  ┌──────────────┐    to_xxx()           │
  │  輸出檔案    │ ←────────────────────┘
  └──────────────┘
```

---

## 📄 CSV — 最常見的資料格式

### 基本讀取

```python
import pandas as pd

df = pd.read_csv("data/orders.csv")
df.head()
```

### 常用參數

```python
# 指定編碼（中文檔案常見問題）
df = pd.read_csv("data.csv", encoding="utf-8")      # 預設
df = pd.read_csv("data.csv", encoding="big5")        # 繁體中文舊系統
df = pd.read_csv("data.csv", encoding="cp950")       # Windows 繁體

# 指定分隔符號
df = pd.read_csv("data.tsv", sep="\t")               # Tab 分隔
df = pd.read_csv("data.txt", sep="|")                 # 管線分隔

# 指定標題列
df = pd.read_csv("data.csv", header=0)                # 第 0 列是標題（預設）
df = pd.read_csv("data.csv", header=None)              # 沒有標題列
df = pd.read_csv("data.csv", names=["A", "B", "C"])   # 自訂欄位名稱

# 指定索引欄
df = pd.read_csv("data.csv", index_col="order_id")

# 只讀取特定欄位
df = pd.read_csv("data.csv", usecols=["order_id", "unit_price", "quantity"])

# 指定資料型態
df = pd.read_csv("data.csv", dtype={"order_id": str, "quantity": int})

# 處理日期欄位
df = pd.read_csv("data.csv", parse_dates=["order_date"])
```

### 🔥 最常遇到的問題：編碼錯誤

```python
# 狀況：UnicodeDecodeError: 'utf-8' codec can't decode byte...

# 解法 1：換編碼
df = pd.read_csv("data.csv", encoding="big5")

# 解法 2：跳過有問題的字元
df = pd.read_csv("data.csv", encoding="utf-8", errors="replace")

# 解法 3：自動偵測編碼（需安裝 chardet）
# pip install chardet
import chardet
with open("data.csv", "rb") as f:
    result = chardet.detect(f.read(10000))
    print(result["encoding"])
```

### 存成 CSV

```python
df.to_csv("output.csv", index=False)              # 不存索引
df.to_csv("output.csv", index=False, encoding="utf-8-sig")  # Excel 可正確開啟中文
```

> 💡 **小技巧**：如果你的 CSV 要用 Excel 開，記得用 `encoding="utf-8-sig"`，
> 否則 Excel 會把中文顯示成亂碼。

---

## 📗 Excel

### 讀取

```python
# 需安裝 openpyxl：pip install openpyxl
df = pd.read_excel("data.xlsx")

# 指定工作表
df = pd.read_excel("data.xlsx", sheet_name="Sheet2")
df = pd.read_excel("data.xlsx", sheet_name=0)          # 第一個工作表

# 讀取所有工作表（回傳 dict）
all_sheets = pd.read_excel("data.xlsx", sheet_name=None)
for name, sheet_df in all_sheets.items():
    print(f"工作表：{name}，共 {len(sheet_df)} 列")

# 指定範圍
df = pd.read_excel("data.xlsx", usecols="A:D", nrows=100)
```

### 存成 Excel

```python
df.to_excel("output.xlsx", index=False, sheet_name="銷售資料")

# 多個工作表存成同一個 Excel
with pd.ExcelWriter("report.xlsx") as writer:
    df_orders.to_excel(writer, sheet_name="訂單", index=False)
    df_summary.to_excel(writer, sheet_name="摘要", index=False)
```

---

## 🔗 JSON

### 讀取

```python
# 標準 JSON
df = pd.read_json("data.json")

# 巢狀 JSON（需要展平）
import json

with open("nested.json") as f:
    raw = json.load(f)

# 用 json_normalize 展平巢狀結構
from pandas import json_normalize
df = json_normalize(raw, record_path="orders", meta=["customer_id"])
```

### 常見 JSON 格式

```python
# 格式 1：records（最常見）
# [{"name": "小明", "score": 85}, {"name": "小華", "score": 92}]
df = pd.read_json("data.json", orient="records")

# 格式 2：columns
# {"name": ["小明", "小華"], "score": [85, 92]}
df = pd.read_json("data.json", orient="columns")
```

### 存成 JSON

```python
df.to_json("output.json", orient="records", force_ascii=False, indent=2)
# force_ascii=False → 中文不會變成 \uXXXX
```

---

## 🗃️ SQL 資料庫

### 讀取（以 SQLite 為例）

```python
import sqlite3

# 建立連線
conn = sqlite3.connect("ecommerce.db")

# 方法 1：用 SQL 查詢
df = pd.read_sql("SELECT * FROM orders WHERE region = '台北'", conn)

# 方法 2：讀整張表
df = pd.read_sql_table("orders", conn)

# 記得關連線
conn.close()
```

### 存進 SQL

```python
conn = sqlite3.connect("ecommerce.db")
df.to_sql("orders_clean", conn, if_exists="replace", index=False)
conn.close()
```

> `if_exists` 參數：
> - `"fail"`：表已存在就報錯（預設）
> - `"replace"`：刪掉舊表，建新的
> - `"append"`：附加到舊表後面

---

## 🌐 其他格式

### HTML 表格

```python
# 從網頁讀取表格
tables = pd.read_html("https://example.com/data.html")
df = tables[0]  # 取第一個表格
```

### Parquet（大數據常用）

```python
# 高效能壓縮格式，適合大資料
df = pd.read_parquet("data.parquet")
df.to_parquet("output.parquet")
```

### 剪貼簿

```python
# 直接從剪貼簿貼上（從 Excel 複製後）
df = pd.read_clipboard()
```

---

## 📊 讀取策略：大檔案怎麼辦？

### 問題：檔案太大，記憶體不夠

```python
# 方法 1：只讀取需要的欄位
df = pd.read_csv("big_data.csv", usecols=["order_id", "unit_price"])

# 方法 2：只讀取前 N 筆
df = pd.read_csv("big_data.csv", nrows=1000)

# 方法 3：分批讀取（chunk）
chunks = pd.read_csv("big_data.csv", chunksize=10000)
results = []
for chunk in chunks:
    # 對每個 chunk 做處理
    result = chunk.groupby("region")["unit_price"].sum()
    results.append(result)

# 合併所有結果
final = pd.concat(results).groupby(level=0).sum()

# 方法 4：指定較省記憶體的型態
df = pd.read_csv("big_data.csv", dtype={
    "quantity": "int16",          # 比 int64 省 4 倍記憶體
    "region": "category",         # 重複值多的欄位用 category
})
```

---

## 🧪 動手練習

### 練習 1：讀取教學資料集

```python
# 讀取所有教學資料
orders = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

# 觀察每張表的基本資訊
print(f"訂單：{orders.shape}")
print(f"顧客：{customers.shape}")
print(f"商品：{products.shape}")
```

### 練習 2：存檔練習

```python
# 1. 篩選台北地區的訂單
taipei_orders = orders[orders["region"] == "台北"]

# 2. 存成 CSV（不含索引）
taipei_orders.to_csv("data/taipei_orders.csv", index=False)

# 3. 存成 Excel
taipei_orders.to_excel("data/taipei_orders.xlsx", index=False)

# 4. 存成 JSON
taipei_orders.to_json("data/taipei_orders.json", orient="records", force_ascii=False)
```

### 練習 3：處理編碼問題

```python
# 如果你有一個 Big5 編碼的 CSV，試著：
# 1. 用錯誤的編碼讀取，看看會出什麼錯
# 2. 用正確的編碼讀取
# 3. 存成 UTF-8 格式
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：忘記 `index=False`

```python
# ❌ 預設會把 index 也存進去
df.to_csv("out.csv")
# 下次讀取會多一欄 Unnamed: 0

# ✅ 加上 index=False
df.to_csv("out.csv", index=False)
```

### 陷阱 2：日期沒有自動解析

```python
# ❌ 日期欄位被當成字串
df = pd.read_csv("data.csv")
print(df["order_date"].dtype)  # object 😱

# ✅ 讀取時就解析日期
df = pd.read_csv("data.csv", parse_dates=["order_date"])
print(df["order_date"].dtype)  # datetime64[ns] ✅
```

### 陷阱 3：Excel 用 UTF-8 開啟中文亂碼

```python
# ❌ 這樣存的 CSV，用 Excel 開會亂碼
df.to_csv("out.csv", encoding="utf-8")

# ✅ 加上 BOM（Byte Order Mark）
df.to_csv("out.csv", encoding="utf-8-sig")
```

---

## 🔑 本章重點回顧

| 函式 | 用途 | 最常用參數 |
|------|------|------------|
| `read_csv()` | 讀 CSV | encoding, sep, parse_dates |
| `read_excel()` | 讀 Excel | sheet_name, usecols |
| `read_json()` | 讀 JSON | orient |
| `read_sql()` | 讀 SQL | SQL 查詢語句, 連線物件 |
| `to_csv()` | 存 CSV | index=False, encoding |
| `to_excel()` | 存 Excel | sheet_name, index=False |
| `to_json()` | 存 JSON | orient, force_ascii=False |

---

## ⏭️ 下一章預告

> **Ch04：探索式資料分析 (EDA)**
>
> 資料讀進來了，然後呢？
> 下一章教你怎麼快速「認識」你的資料 — 它長什麼樣子？有多少筆？有沒有問題？

---

[← Ch02：核心概念](ch02-core-concepts.md) | [Ch04：探索式資料分析 →](ch04-eda.md)
