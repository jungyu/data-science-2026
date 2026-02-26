# Ch07：分組聚合的力量 — GroupBy

> **本章目標**：掌握 Pandas 最核心的分析技能 — 把資料分組、計算、再合併。

---

## 💡 什麼是 GroupBy？

想像你是一個電商老闆，你想知道：

> 「**各地區**的平均銷售額是多少？」

用 Excel 的話，你可能會用篩選一個一個看。
用 Pandas 的話：

```python
orders.groupby("region")["total_price"].mean()
```

一行搞定。

### GroupBy 的三步驟

```
原始資料                    Split                     Apply                    Combine
┌──────┬───────┐      ┌──────┬───────┐        ┌──────┬───────┐       ┌──────┬───────┐
│ 地區 │ 金額  │      │ 台北 │ 1000  │  mean  │ 台北 │ 1500  │       │ 台北 │ 1500  │
│ 台北 │ 1000  │  ──→ │ 台北 │ 2000  │  ───→  │      │       │  ──→  │ 台中 │  800  │
│ 台中 │  800  │      ├──────┼───────┤        ├──────┼───────┤       │ 高雄 │ 1200  │
│ 台北 │ 2000  │      │ 台中 │  800  │  mean  │ 台中 │  800  │       └──────┴───────┘
│ 高雄 │ 1200  │      ├──────┼───────┤        ├──────┼───────┤
└──────┴───────┘      │ 高雄 │ 1200  │  mean  │ 高雄 │ 1200  │
                      └──────┴───────┘        └──────┴───────┘
      全部                  分組                    聚合                   結果
```

這就是經典的 **Split → Apply → Combine** 模式。

---

## 📦 準備資料

```python
import pandas as pd
import numpy as np

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")
```

---

## 1️⃣ 基本 GroupBy

### 單一分組 + 單一聚合

```python
# 各地區的平均金額
orders.groupby("region")["total_price"].mean()
```

```
region
台中    2150.00
台北    3420.50
台南    1890.00
新竹    1350.00
高雄    2780.00
Name: total_price, dtype: float64
```

### 單一分組 + 多個聚合

```python
# 各地區的多項統計
orders.groupby("region")["total_price"].agg(["count", "mean", "sum", "min", "max"])
```

```
        count     mean       sum      min      max
region
台中       20  2150.00   43000.0   450.00  8500.00
台北       32  3420.50  109456.0   299.00  9800.00
台南       15  1890.00   28350.0   299.00  5600.00
新竹        7  1350.00    9450.0   450.00  3200.00
高雄       25  2780.00   69500.0   350.00  8900.00
```

### 多欄位分組

```python
# 各地區 × 付款方式的訂單數
orders.groupby(["region", "payment_method"])["order_id"].count()
```

```
region  payment_method
台中    LinePay           8
        信用卡            10
        貨到付款           2
台北    LinePay           12
        信用卡            15
        貨到付款           5
...
```

---

## 2️⃣ 聚合函式大全

### 內建聚合函式

| 函式 | 功能 | SQL 對應 |
|------|------|----------|
| `count()` | 計數（不含 NaN） | COUNT |
| `sum()` | 加總 | SUM |
| `mean()` | 平均 | AVG |
| `median()` | 中位數 | — |
| `min()` | 最小值 | MIN |
| `max()` | 最大值 | MAX |
| `std()` | 標準差 | STDDEV |
| `var()` | 變異數 | VARIANCE |
| `first()` | 第一筆 | — |
| `last()` | 最後一筆 | — |
| `nunique()` | 不重複值數量 | COUNT DISTINCT |

### 用 `agg()` 做複合聚合

```python
# 不同欄位用不同聚合
orders.groupby("region").agg(
    訂單數=("order_id", "count"),
    顧客數=("customer_id", "nunique"),
    平均金額=("total_price", "mean"),
    總金額=("total_price", "sum"),
    平均出貨天數=("shipping_days", "mean")
).round(2)
```

```
        訂單數  顧客數  平均金額      總金額  平均出貨天數
region
台中        20       8   2150.00   43000.00         3.10
台北        32      12   3420.50  109456.00         2.30
台南        15       6   1890.00   28350.00         2.80
新竹         7       3   1350.00    9450.00         3.20
高雄        25      10   2780.00   69500.00         1.90
```

### 自訂聚合函式

```python
# 用 lambda
orders.groupby("region")["total_price"].agg(lambda x: x.max() - x.min())

# 用自訂函式
def price_range(series):
    return f"{series.min():.0f} ~ {series.max():.0f}"

orders.groupby("region")["total_price"].agg(price_range)
```

---

## 3️⃣ 進階技巧

### `transform()`：保持原本的 DataFrame 形狀

```python
# 問題：我想知道每筆訂單在其地區中的排名

# groupby + mean 會「壓縮」資料
orders.groupby("region")["total_price"].mean()  # 5 列

# transform 不會壓縮，回傳跟原本一樣多列
orders["region_avg"] = orders.groupby("region")["total_price"].transform("mean")
# 每一列都填上「該地區的平均」

# 計算：每筆訂單比地區平均高/低多少
orders["vs_region_avg"] = orders["total_price"] - orders["region_avg"]
```

```
   order_id  region  total_price  region_avg  vs_region_avg
0    O1001    台北     2322.00    3420.50      -1098.50
1    O1002    台中      890.00    2150.00      -1260.00
2    O1003    高雄     1282.50    2780.00      -1497.50
```

### `filter()`：篩選整個組

```python
# 只保留「訂單數 > 10 的地區」的所有訂單
orders.groupby("region").filter(lambda x: len(x) > 10)

# 只保留「平均金額 > 2000 的地區」
orders.groupby("region").filter(lambda x: x["total_price"].mean() > 2000)
```

### 排序分組結果

```python
# 按照聚合結果排序
region_sales = orders.groupby("region")["total_price"].sum()
region_sales.sort_values(ascending=False)

# 或者用 reset_index 後再排序
region_stats = orders.groupby("region").agg(
    total=("total_price", "sum")
).reset_index().sort_values("total", ascending=False)
```

---

## 4️⃣ 商業分析實戰

### 案例 1：各地區銷售報告

```python
report = orders.groupby("region").agg(
    訂單數=("order_id", "count"),
    不重複顧客=("customer_id", "nunique"),
    總營收=("total_price", "sum"),
    平均客單價=("total_price", "mean"),
    最高單筆=("total_price", "max")
).round(0)

# 加上佔比
report["營收佔比"] = (report["總營收"] / report["總營收"].sum() * 100).round(1)
report = report.sort_values("總營收", ascending=False)
print(report)
```

### 案例 2：付款方式分析

```python
payment_analysis = orders.groupby("payment_method").agg(
    使用次數=("order_id", "count"),
    平均金額=("total_price", "mean"),
    平均折扣=("discount", "mean"),
).round(2)

payment_analysis["使用佔比"] = (
    payment_analysis["使用次數"] / payment_analysis["使用次數"].sum() * 100
).round(1)

print(payment_analysis)
```

### 案例 3：商品類別 × 地區 交叉分析

```python
# 先合併商品資訊
orders_with_product = orders.merge(products[["product_id", "category"]], on="product_id")

# 交叉分析
cross = orders_with_product.groupby(["category", "region"])["total_price"].sum().unstack()
print(cross)
```

```
region       台中      台北      台南     新竹      高雄
category
3C        12000.0  45000.0   8000.0  5000.0  28000.0
家電       8500.0  20000.0   6500.0  2000.0  12000.0
生活用品   5000.0  15000.0   4000.0  1500.0   9000.0
```

### 案例 4：月度趨勢分析

```python
# 加上月份欄位
orders["month"] = orders["order_date"].dt.to_period("M")

# 每月營收
monthly = orders.groupby("month")["total_price"].agg(["sum", "count", "mean"])
monthly.columns = ["月營收", "訂單數", "平均客單價"]
print(monthly)
```

---

## 🧪 動手練習

### 練習 1：基本 GroupBy

```python
# 用 orders.csv 回答：
# 1. 各地區的總營收是多少？
# 2. 各付款方式的訂單數量？
# 3. 各地區的平均出貨天數？
# 4. 哪個地區的折扣率最高？
```

### 練習 2：進階聚合

```python
# 1. 各地區同時計算：訂單數、總營收、平均營收、最高營收
# 2. 各「地區 × 付款方式」組合的訂單數和總營收
# 3. 用 transform 新增一欄「該顧客的累計消費」
```

### 練習 3：商業報告

```python
# 寫一個函式，輸入 DataFrame，輸出以下報告：
# 1. 總營收和訂單數
# 2. 各地區 Top 3 銷售排名
# 3. 各付款方式的使用佔比
# 4. 月度營收趨勢
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：忘記 `reset_index()`

```python
# groupby 的結果，分組欄位會變成 index
result = orders.groupby("region")["total_price"].sum()
print(type(result))  # Series，index 是 region

# 如果你要把結果當 DataFrame 繼續用
result = result.reset_index()
# 或者一開始就設定
result = orders.groupby("region", as_index=False)["total_price"].sum()
```

### 陷阱 2：`count()` vs `size()`

```python
# count() 不計算 NaN
orders.groupby("region")["shipping_days"].count()  # 排除空值

# size() 計算所有（包含 NaN）
orders.groupby("region").size()  # 包含空值
```

### 陷阱 3：對分組結果做運算時忘記對齊

```python
# ❌ 大小不一樣，無法直接運算
region_avg = orders.groupby("region")["total_price"].mean()  # 5 列
orders["diff"] = orders["total_price"] - region_avg  # NaN！

# ✅ 用 transform
orders["diff"] = orders["total_price"] - orders.groupby("region")["total_price"].transform("mean")
```

---

## 🔑 本章重點回顧

| 方法 | 功能 | 回傳形狀 |
|------|------|----------|
| `groupby().mean()` | 分組 + 單一聚合 | 壓縮（每組一列） |
| `groupby().agg()` | 分組 + 多重聚合 | 壓縮（每組一列） |
| `groupby().transform()` | 分組 + 保持原形 | 不壓縮（同原始大小） |
| `groupby().filter()` | 分組 + 篩選整組 | 子集（部分列） |
| `as_index=False` | 分組欄位不變成 index | DataFrame |

**記住**：`GroupBy = Split → Apply → Combine`

---

## ⏭️ 下一章預告

> **Ch08：樞紐分析表**
>
> GroupBy 的升級版 — 用 pivot_table 做出 Excel 那樣的交叉分析表。
> 這是做報告時最常用的功能。

---

[← Ch06：篩選、排序與欄位操作](ch06-filtering-operations.md) | [Ch08：樞紐分析表 →](ch08-pivot-tables.md)
