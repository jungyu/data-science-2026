# Ch08：樞紐分析表

> **本章目標**：用 pivot_table 和 crosstab 做出交叉分析報表，這是做商業報告的核心技能。

---

## 📊 什麼是樞紐分析表？

如果你用過 Excel 的樞紐分析表（Pivot Table），你就知道它有多強大。

它能讓你一眼看到：

> 「**各地區** × **各月份** 的 **銷售額** 分別是多少？」

```
           1月      2月      3月
台北    45,000   52,000   48,000
台中    28,000   31,000   35,000
高雄    35,000   38,000   42,000
```

Pandas 的 `pivot_table()` 就是 Excel 樞紐分析表的程式版本。

---

## 📦 準備資料

```python
import pandas as pd
import numpy as np

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])
orders["month"] = orders["order_date"].dt.month

# 合併商品類別
products = pd.read_csv("data/products.csv")
orders = orders.merge(products[["product_id", "category"]], on="product_id", how="left")
```

---

## 1️⃣ 基本 pivot_table

### 最簡單的用法

```python
# 各地區 × 各月份的銷售總額
pd.pivot_table(
    orders,
    values="total_price",     # 要計算的值
    index="region",           # 列（Y 軸）
    columns="month",          # 欄（X 軸）
    aggfunc="sum"             # 聚合函式
)
```

```
month     1         2         3
region
台中    12500.0   15800.0   14700.0
台北    38200.0   42100.0   29156.0
台南     8900.0   11200.0    8250.0
新竹     3200.0    4500.0    1750.0
高雄    22500.0   28000.0   19000.0
```

### 參數解說

| 參數 | 說明 | 類比 |
|------|------|------|
| `values` | 要聚合的數值欄位 | Excel：值區域 |
| `index` | 放在列（左邊）的分類 | Excel：列標籤 |
| `columns` | 放在欄（上面）的分類 | Excel：欄標籤 |
| `aggfunc` | 聚合方式 | Excel：值的摘要方式 |
| `fill_value` | 空值填充 | — |
| `margins` | 加上合計列/欄 | Excel：總計 |

---

## 2️⃣ 常用聚合方式

### 單一聚合

```python
# 合計
pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="sum")

# 平均
pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="mean")

# 計數
pd.pivot_table(orders, values="order_id", index="region", columns="month", aggfunc="count")
```

### 多重聚合

```python
pd.pivot_table(
    orders,
    values="total_price",
    index="region",
    aggfunc=["sum", "mean", "count"]
)
```

### 加上合計行

```python
pd.pivot_table(
    orders,
    values="total_price",
    index="region",
    columns="month",
    aggfunc="sum",
    margins=True,           # 加上合計
    margins_name="合計"      # 合計的名稱
)
```

```
month     1         2         3        合計
region
台中    12500.0   15800.0   14700.0    43000.0
台北    38200.0   42100.0   29156.0   109456.0
台南     8900.0   11200.0    8250.0    28350.0
新竹     3200.0    4500.0    1750.0     9450.0
高雄    22500.0   28000.0   19000.0    69500.0
合計    85300.0  101600.0   72856.0   259756.0
```

---

## 3️⃣ 多層 pivot_table

### 多個列標籤

```python
# 地區 × 付款方式，看銷售額
pd.pivot_table(
    orders,
    values="total_price",
    index=["region", "payment_method"],
    aggfunc="sum"
)
```

### 多個值

```python
pd.pivot_table(
    orders,
    values=["total_price", "quantity"],
    index="region",
    columns="month",
    aggfunc="sum"
)
```

---

## 4️⃣ crosstab：交叉表

`crosstab` 是 `pivot_table` 的簡化版，專門用來做**計數交叉表**。

### 基本用法

```python
# 各地區 × 各付款方式的訂單數
pd.crosstab(orders["region"], orders["payment_method"])
```

```
payment_method  LinePay  信用卡  貨到付款
region
台中                  8     10        2
台北                 12     15        5
台南                  5      8        2
新竹                  2      4        1
高雄                  8     13        4
```

### 加上比例

```python
# 列比例（每個地區的付款方式佔比）
pd.crosstab(
    orders["region"],
    orders["payment_method"],
    normalize="index"        # 每列加總 = 1
).round(3)
```

```
payment_method  LinePay   信用卡  貨到付款
region
台中             0.400   0.500    0.100
台北             0.375   0.469    0.156
台南             0.333   0.533    0.133
新竹             0.286   0.571    0.143
高雄             0.320   0.520    0.160
```

### 其他 normalize 選項

```python
normalize="columns"  # 欄比例（每種付款方式的地區佔比）
normalize="all"      # 全表比例（每格佔總數的比例）
```

---

## 5️⃣ 資料重塑：melt 與 stack/unstack

### `melt()`：寬表轉長表

```python
# 寬表格（pivot_table 的結果）
wide = pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="sum")

# 轉成長表格（適合繪圖和進一步分析）
long = wide.reset_index().melt(
    id_vars="region",        # 保留的欄位
    var_name="month",        # 原本的欄名變成值
    value_name="total_sales" # 值的欄位名稱
)
print(long)
```

```
  region  month  total_sales
0   台中      1      12500.0
1   台北      1      38200.0
2   台南      1       8900.0
3   新竹      1       3200.0
4   高雄      1      22500.0
5   台中      2      15800.0
...
```

### `stack()` / `unstack()`

```python
# stack：欄 → 列（寬轉長）
stacked = wide.stack()

# unstack：列 → 欄（長轉寬）
unstacked = stacked.unstack()
```

### 什麼時候用什麼？

```
寬表格（適合報告、閱讀）          長表格（適合分析、繪圖）
┌──────┬─────┬─────┐           ┌──────┬──────┬───────┐
│      │ 1月 │ 2月 │           │ 地區 │ 月份 │ 金額  │
├──────┼─────┼─────┤           ├──────┼──────┼───────┤
│ 台北 │ 100 │ 200 │   melt    │ 台北 │  1月 │  100  │
│ 台中 │ 150 │ 180 │ ←------→ │ 台北 │  2月 │  200  │
└──────┴─────┴─────┘  pivot    │ 台中 │  1月 │  150  │
                               │ 台中 │  2月 │  180  │
                               └──────┴──────┴───────┘
```

---

## 6️⃣ 商業實戰

### 案例：月度地區銷售報告

```python
def generate_sales_report(orders_df):
    """生成月度地區銷售報告"""

    # 1. 樞紐分析表：地區 × 月份
    pivot = pd.pivot_table(
        orders_df,
        values="total_price",
        index="region",
        columns=orders_df["order_date"].dt.to_period("M"),
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="合計"
    ).round(0)

    # 2. 交叉表：地區 × 付款方式
    payment = pd.crosstab(
        orders_df["region"],
        orders_df["payment_method"],
        margins=True,
        margins_name="合計"
    )

    # 3. 地區摘要
    summary = orders_df.groupby("region").agg(
        訂單數=("order_id", "count"),
        顧客數=("customer_id", "nunique"),
        總營收=("total_price", "sum"),
        平均客單價=("total_price", "mean")
    ).round(0)

    return pivot, payment, summary

# 使用
pivot, payment, summary = generate_sales_report(orders)
print("=== 月度營收 ===")
print(pivot)
print("\n=== 付款方式分佈 ===")
print(payment)
print("\n=== 地區摘要 ===")
print(summary)
```

---

## 🧪 動手練習

### 練習 1：基本 pivot_table

```python
# 1. 建立「地區 × 付款方式」的銷售額 pivot_table
# 2. 加上合計列和合計欄
# 3. 改用「平均」取代「加總」
# 4. 同時顯示「加總」和「計數」
```

### 練習 2：crosstab 分析

```python
# 1. 建立「地區 × 付款方式」的計數交叉表
# 2. 顯示列百分比（每個地區各付款方式佔比）
# 3. 找出「最偏好信用卡的地區」
```

### 練習 3：完整報告

```python
# 結合前面學的所有技巧，產出一份包含以下內容的報告：
# 1. 月度營收 pivot_table（地區 × 月份）
# 2. 商品類別營收排名
# 3. 付款方式交叉分析
# 4. 各地區 Top 3 暢銷商品
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：忘記 `fill_value`

```python
# ❌ 有些地區某個月沒有訂單，顯示 NaN
pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="sum")

# ✅ 用 fill_value 填 0
pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="sum", fill_value=0)
```

### 陷阱 2：`pivot` vs `pivot_table`

```python
# pivot()：不做聚合，需要唯一值
# pivot_table()：可以聚合，允許重複值

# 如果每個（地區 × 月份）有多筆訂單：
# ❌ pivot() 會報錯
orders.pivot(index="region", columns="month", values="total_price")

# ✅ pivot_table() 會聚合
pd.pivot_table(orders, values="total_price", index="region", columns="month", aggfunc="sum")
```

### 陷阱 3：多層欄位名稱很醜

```python
# 多重聚合後，欄位名稱會變成多層
result = pd.pivot_table(orders, values=["total_price", "quantity"], index="region", aggfunc="sum")

# 壓平欄位名稱
result.columns = ["_".join(col) for col in result.columns]
```

---

## 🔑 本章重點回顧

| 函式 | 用途 | 適用情境 |
|------|------|----------|
| `pivot_table()` | 交叉聚合表 | 需要 index × columns 的聚合 |
| `crosstab()` | 計數交叉表 | 快速看分類的交叉計數 |
| `melt()` | 寬轉長 | 為了繪圖或進一步分析 |
| `pivot()` | 長轉寬 | 值是唯一的情況 |
| `stack()` | 欄 → 列 | 多層欄位轉索引 |
| `unstack()` | 列 → 欄 | 多層索引轉欄位 |

---

## ⏭️ 下一章預告

> **Ch09：時間序列處理**
>
> 電商資料天生帶有時間軸。
> 下一章學怎麼用 Pandas 做時間序列分析 — 月度趨勢、移動平均、季節性。

---

[← Ch07：分組聚合的力量](ch07-groupby.md) | [Ch09：時間序列處理 →](ch09-time-series.md)
