# Ch11：進階技巧與效能優化

> **本章目標**：掌握 merge/join、apply 的替代方案、多層索引、大資料效能技巧。

---

## 🔗 1. 合併資料：merge 與 join

### 為什麼需要合併？

真實世界的資料通常分散在多張表：

```
orders.csv          customers.csv       products.csv
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│ order_id      │   │ customer_id  │   │ product_id   │
│ customer_id ──┼──→│ gender       │   │ category     │
│ product_id ──┼───┼──────────────┼──→│ product_name │
│ quantity      │   │ age          │   │ cost         │
│ unit_price    │   │ city         │   └──────────────┘
└───────────────┘   └──────────────┘
```

要回答「女性顧客最愛買什麼類別？」，你需要**合併**這三張表。

### 基本 merge

```python
import pandas as pd

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

# 合併訂單和顧客
orders_customers = orders.merge(customers, on="customer_id")

# 合併訂單和商品
orders_products = orders.merge(products, on="product_id")

# 一次合併三張表
full = (orders
    .merge(customers, on="customer_id")
    .merge(products, on="product_id")
)
print(f"合併後：{full.shape}")
```

### 四種合併方式

```python
# inner（預設）：只保留兩邊都有的
orders.merge(customers, on="customer_id", how="inner")

# left：保留左表所有列
orders.merge(customers, on="customer_id", how="left")

# right：保留右表所有列
orders.merge(customers, on="customer_id", how="right")

# outer：保留兩邊所有列
orders.merge(customers, on="customer_id", how="outer")
```

```
        Left                    Right
   ┌──────────┐           ┌──────────┐
   │ A  B  C  │           │ B  C  D  │
   └──────────┘           └──────────┘

inner: B  C        ← 交集
left:  A  B  C     ← 左邊全保留
right: B  C  D     ← 右邊全保留
outer: A  B  C  D  ← 聯集
```

### 欄位名稱不同時

```python
# 兩邊 key 名稱不一樣
orders.merge(customers, left_on="cust_id", right_on="customer_id")

# 多個 key
orders.merge(inventory, on=["product_id", "region"])
```

### 處理重複欄位名

```python
# 兩張表有同名欄位時
result = orders.merge(products, on="product_id", suffixes=("_order", "_product"))
# unit_price_order, unit_price_product
```

### 驗證合併結果

```python
# 確認合併是否產生意外的列數膨脹
print(f"合併前 orders: {len(orders)}")
result = orders.merge(customers, on="customer_id")
print(f"合併後: {len(result)}")

# 使用 validate 參數（Pandas 1.5+）
orders.merge(customers, on="customer_id", validate="many_to_one")
# many_to_one：orders 的 customer_id 可重複，customers 的不可
# one_to_one：兩邊都不可重複
# one_to_many：左邊不可重複
```

---

## 📐 2. 多層索引（MultiIndex）

### 什麼時候會遇到？

```python
# groupby 多個欄位時，自動產生多層索引
result = orders.groupby(["region", "payment_method"])["total_price"].sum()
print(result)
```

```
region  payment_method
台中    LinePay            8500.0
        信用卡            22000.0
        貨到付款           12500.0
台北    LinePay           15000.0
        信用卡            68000.0
        貨到付款           26456.0
...
```

### 存取多層索引

```python
# 取第一層
result.loc["台北"]

# 取特定組合
result.loc[("台北", "信用卡")]

# 交叉切片
result.loc[["台北", "高雄"], :]

# 用 xs 方法
result.xs("信用卡", level="payment_method")  # 所有地區的信用卡
```

### 重設索引

```python
# 多層索引不好操作時，壓平它
result = result.reset_index()
# 變回普通的 DataFrame

# 或者一開始就避免
result = orders.groupby(["region", "payment_method"], as_index=False)["total_price"].sum()
```

---

## ⚡ 3. 效能優化

### 原則：能向量化就不要用迴圈

```python
import numpy as np

# 🐌 慢：Python 迴圈
total = []
for i, row in orders.iterrows():
    total.append(row["quantity"] * row["unit_price"] * (1 - row["discount"]))
orders["total"] = total

# 🐢 中等：apply
orders["total"] = orders.apply(
    lambda row: row["quantity"] * row["unit_price"] * (1 - row["discount"]),
    axis=1
)

# 🚀 快：向量化運算
orders["total"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])
```

### 效能比較

| 方法 | 10 萬列速度 | 適用場景 |
|------|------------|----------|
| 向量化運算 | ~1ms | 數學運算、比較 |
| `np.where()` | ~2ms | 條件賦值 |
| `np.select()` | ~3ms | 多條件賦值 |
| `.str` 方法 | ~50ms | 字串操作 |
| `apply()` | ~500ms | 複雜自訂邏輯 |
| `iterrows()` | ~5000ms | 幾乎不應該用 |

### apply 的替代方案

```python
# ❌ apply（慢）
orders["level"] = orders["total_price"].apply(
    lambda x: "高" if x > 5000 else ("中" if x > 1000 else "低")
)

# ✅ np.select（快 100 倍）
conditions = [
    orders["total_price"] > 5000,
    orders["total_price"] > 1000,
]
choices = ["高", "中"]
orders["level"] = np.select(conditions, choices, default="低")

# ✅ pd.cut（數值分箱專用）
orders["level"] = pd.cut(
    orders["total_price"],
    bins=[0, 1000, 5000, float("inf")],
    labels=["低", "中", "高"]
)
```

### 記憶體優化

```python
# 查看記憶體使用
print(orders.memory_usage(deep=True).sum() / 1024 / 1024, "MB")

# 方法 1：降低數值精度
orders["quantity"] = orders["quantity"].astype("int16")         # int64 → int16
orders["unit_price"] = orders["unit_price"].astype("float32")   # float64 → float32

# 方法 2：類別型態
orders["region"] = orders["region"].astype("category")
orders["payment_method"] = orders["payment_method"].astype("category")

# 方法 3：讀取時就指定型態
dtypes = {
    "quantity": "int16",
    "unit_price": "float32",
    "region": "category",
    "payment_method": "category"
}
orders = pd.read_csv("data/orders.csv", dtype=dtypes)

print(orders.memory_usage(deep=True).sum() / 1024 / 1024, "MB")
```

### 大檔案處理策略

```python
# 策略 1：只讀需要的欄位
df = pd.read_csv("big_file.csv", usecols=["order_id", "total_price", "region"])

# 策略 2：分批處理
total_by_region = pd.Series(dtype="float64")

for chunk in pd.read_csv("big_file.csv", chunksize=50000):
    chunk_result = chunk.groupby("region")["total_price"].sum()
    total_by_region = total_by_region.add(chunk_result, fill_value=0)

print(total_by_region)

# 策略 3：用 Parquet 格式（比 CSV 快 5-10 倍）
# 存成 Parquet
orders.to_parquet("data/orders.parquet")

# 讀取 Parquet
orders = pd.read_parquet("data/orders.parquet")

# 策略 4：用 SQL 做前處理，只把結果讀進 Pandas
import sqlite3
conn = sqlite3.connect("data.db")
df = pd.read_sql("""
    SELECT region, SUM(total_price) as revenue
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY region
""", conn)
```

---

## 🔧 4. 實用進階技巧

### pipe()：鏈式操作

```python
def add_total(df):
    df["total_price"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
    return df

def filter_valid(df):
    return df[df["total_price"] > 0]

def add_month(df):
    df["month"] = df["order_date"].dt.to_period("M")
    return df

# 用 pipe 串起來，可讀性更好
result = (orders
    .pipe(add_total)
    .pipe(filter_valid)
    .pipe(add_month)
)
```

### assign()：不修改原始 DataFrame

```python
# assign 回傳新的 DataFrame，不影響原本的
result = (orders
    .assign(total=lambda df: df["quantity"] * df["unit_price"] * (1 - df["discount"]))
    .assign(month=lambda df: df["order_date"].dt.month)
    .query("total > 1000")
    .groupby("month")["total"]
    .sum()
)
```

### eval()：高效能欄位計算

```python
# 用 eval 直接在 DataFrame 內計算（比向量化還快一點，大資料時有感）
orders.eval("total_price = quantity * unit_price * (1 - discount)", inplace=True)
orders.eval("profit = total_price - quantity * 500", inplace=True)
```

### 字串方法進階

```python
# 提取模式
orders["order_num"] = orders["order_id"].str.extract(r"O(\d+)").astype(int)

# 分割
name_parts = customers["name"].str.split(" ", expand=True)

# 取代（支援正則）
orders["region_clean"] = orders["region"].str.replace(r"\s+", "", regex=True)
```

---

## 🧪 動手練習

### 練習 1：跨表分析

```python
# 合併三張表，回答：
# 1. 女性顧客最愛買什麼商品類別？
# 2. Gold 會員和 Bronze 會員的平均客單價差多少？
# 3. 各城市最暢銷的商品是什麼？
# 4. 計算每個商品的毛利率，找出最賺錢的商品
```

### 練習 2：效能優化

```python
# 把下面的 apply 改寫成向量化版本：

# 原版（慢）
orders["shipping_speed"] = orders["shipping_days"].apply(
    lambda x: "快速" if x <= 2 else ("標準" if x <= 4 else "慢速")
)

# 你的版本（快）
# ???
```

### 練習 3：大資料模擬

```python
# 1. 生成 10 萬筆模擬訂單資料
# 2. 比較不同方法的執行時間
# 3. 用記憶體優化技巧降低記憶體用量
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：merge 後列數爆炸

```python
# 如果 key 有重複值，merge 會做笛卡爾積
# A 有 3 列 key=1，B 有 2 列 key=1 → 結果有 6 列 key=1

# 解法：先確認 key 的唯一性
print(f"customers key 唯一：{customers['customer_id'].is_unique}")

# 或用 validate 參數
orders.merge(customers, on="customer_id", validate="many_to_one")
```

### 陷阱 2：在迴圈中 append DataFrame

```python
# ❌ 每次 append 都會複製整個 DataFrame（O(n²)）
result = pd.DataFrame()
for chunk in chunks:
    result = pd.concat([result, chunk])

# ✅ 先收集到 list，最後一次 concat
results = []
for chunk in chunks:
    results.append(chunk)
result = pd.concat(results, ignore_index=True)
```

### 陷阱 3：iterrows() 誘惑

```python
# ❌ 看起來直覺，但是超慢
for i, row in df.iterrows():
    df.loc[i, "new_col"] = some_function(row["col1"], row["col2"])

# ✅ 先想想有沒有向量化方案
df["new_col"] = np.where(df["col1"] > 0, df["col1"] * df["col2"], 0)
```

---

## 🔑 本章重點回顧

| 主題 | 關鍵方法 | 使用時機 |
|------|----------|----------|
| 合併資料 | `merge()` | 跨表關聯分析 |
| 合併方式 | inner/left/right/outer | 根據業務需求選擇 |
| 多層索引 | `MultiIndex` | groupby 多欄位後 |
| 向量化 | NumPy 運算 | 任何數值計算 |
| 條件賦值 | `np.select()` | 取代 apply+lambda |
| 記憶體優化 | `category`, `int16` | 大資料場景 |
| 大檔案 | `chunksize`, Parquet | 超過記憶體的資料 |
| 鏈式操作 | `pipe()`, `assign()` | 提高可讀性 |

**效能黃金法則**：向量化 > str/dt 方法 > apply > iterrows

---

## 🎓 結語

恭喜你讀完了整本手冊！

回顧一下你學到的：

```
Ch01  為什麼學 Pandas     → 建立動機和方向
Ch02  Series & DataFrame  → 掌握基礎結構
Ch03  資料讀取與儲存      → 打通資料管道
Ch04  EDA 探索式分析      → 學會觀察資料
Ch05  資料清理            → 處理真實世界的髒資料
Ch06  篩選與欄位操作      → 精準取用資料
Ch07  GroupBy 分組聚合    → 從資料中找洞察
Ch08  樞紐分析表          → 製作商業報表
Ch09  時間序列處理        → 分析時間維度
Ch10  實戰專案            → 整合所有技能
Ch11  進階技巧            → 做得更快更好
```

接下來你可以：

1. **多做專案**：找 Kaggle 資料集練習
2. **學視覺化**：matplotlib + seaborn
3. **學機器學習**：scikit-learn
4. **學大數據**：PySpark, Dask
5. **建立作品集**：把分析結果整理成 GitHub 專案

> 記住：你不是在學函式庫，你是在學**如何與資料對話**。

---

[← Ch10：實戰專案](ch10-real-project.md) | [附錄 A：教學指南 →](appendix-teaching-guide.md)
