# Ch06：篩選、排序與欄位操作

> **本章目標**：精準地從 DataFrame 中取出你需要的資料，進行排序和欄位操作。

---

## 🎯 為什麼需要篩選？

你的資料通常有幾百、幾千、甚至幾百萬列。你不可能一次看完所有的。

```
全部 10 萬筆訂單
        │
        │ 篩選：region == "台北"
        ▼
    3 萬筆台北訂單
        │
        │ 篩選：unit_price > 1000
        ▼
    8 千筆高單價台北訂單
        │
        │ 排序：按 total_price 降序
        ▼
    Top 10 最高金額訂單 ← 你真正要看的
```

---

## 📦 準備資料

```python
import pandas as pd

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])
```

---

## 1️⃣ 條件篩選（Boolean Indexing）

### 基本篩選

```python
# 單一條件
taipei = orders[orders["region"] == "台北"]
high_value = orders[orders["total_price"] > 5000]
credit_card = orders[orders["payment_method"] == "信用卡"]
```

### 背後原理：布林遮罩

```python
# 這行產生一個 True/False 的 Series
mask = orders["region"] == "台北"
print(mask)
# 0     True
# 1    False
# 2    False
# 3     True
# ...

# 用這個 mask 來篩選
orders[mask]  # 只保留 True 的列
```

### 多條件篩選

```python
# AND：兩個條件都要滿足（用 &）
orders[(orders["region"] == "台北") & (orders["total_price"] > 5000)]

# OR：任一條件滿足（用 |）
orders[(orders["region"] == "台北") | (orders["region"] == "高雄")]

# NOT：反轉條件（用 ~）
orders[~(orders["region"] == "台北")]  # 不是台北的
```

> ⚠️ **重要**：多條件篩選時，每個條件都要**用小括號包起來**！
>
> ```python
> # ❌ 會報錯
> orders[orders["region"] == "台北" & orders["total_price"] > 5000]
>
> # ✅ 正確
> orders[(orders["region"] == "台北") & (orders["total_price"] > 5000)]
> ```

### 進階篩選方法

```python
# isin()：值在清單中
orders[orders["region"].isin(["台北", "台中", "高雄"])]

# between()：範圍篩選
orders[orders["unit_price"].between(500, 1500)]

# str 方法：字串篩選
orders[orders["payment_method"].str.contains("Pay")]
orders[orders["order_id"].str.startswith("O10")]

# query() 方法：更直覺的寫法
orders.query("region == '台北' and total_price > 5000")
orders.query("quantity >= 3 and discount > 0")
```

### `query()` vs 傳統寫法

| 特性 | 傳統布林索引 | `query()` |
|------|-------------|-----------|
| 可讀性 | 長條件時難讀 | 接近 SQL，直覺 |
| 效能 | 略快 | 略慢（需解析字串） |
| 變數引用 | 直接使用 | 用 `@` 引用外部變數 |
| 適用場景 | 程式化操作 | 互動式探索 |

```python
# query() 引用外部變數
min_price = 1000
orders.query("unit_price > @min_price")
```

---

## 2️⃣ 排序

### 基本排序

```python
# 單一欄位排序（預設升序）
orders.sort_values("total_price")

# 降序
orders.sort_values("total_price", ascending=False)

# 多欄位排序
orders.sort_values(["region", "total_price"], ascending=[True, False])
# 先按地區升序，再按金額降序
```

### 排序後重設索引

```python
# 排序後 index 會亂掉
sorted_df = orders.sort_values("total_price", ascending=False)
print(sorted_df.index)  # [45, 12, 78, 3, ...]

# 重設索引
sorted_df = sorted_df.reset_index(drop=True)
print(sorted_df.index)  # [0, 1, 2, 3, ...]
```

### 取 Top N

```python
# 最高的 10 筆
top10 = orders.nlargest(10, "total_price")

# 最低的 5 筆
bottom5 = orders.nsmallest(5, "unit_price")
```

---

## 3️⃣ 欄位操作

### 新增欄位

```python
# 直接計算
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])

# 條件新增
orders["is_high_value"] = orders["total_price"] > 5000

# 用 np.where（類似 Excel 的 IF）
import numpy as np
orders["price_level"] = np.where(
    orders["total_price"] > 5000, "高", "一般"
)

# 用 np.select（多條件）
conditions = [
    orders["total_price"] > 10000,
    orders["total_price"] > 5000,
    orders["total_price"] > 1000,
]
choices = ["VIP", "高", "中"]
orders["price_level"] = np.select(conditions, choices, default="低")

# 用 cut（數值分箱）
orders["price_bin"] = pd.cut(
    orders["total_price"],
    bins=[0, 1000, 3000, 5000, float("inf")],
    labels=["低", "中", "高", "超高"]
)
```

### 修改欄位名稱

```python
# 改單一欄位
orders = orders.rename(columns={"unit_price": "單價", "quantity": "數量"})

# 改多個欄位
orders = orders.rename(columns={
    "order_id": "訂單編號",
    "order_date": "訂單日期"
})

# 全部改（用函式）
orders.columns = orders.columns.str.lower()  # 全部轉小寫
orders.columns = orders.columns.str.replace("_", " ")  # 底線轉空格
```

### 刪除欄位

```python
# 刪除單一欄位
orders = orders.drop(columns=["is_high_value"])

# 刪除多個欄位
orders = orders.drop(columns=["price_level", "price_bin"])
```

### 調整欄位順序

```python
# 指定順序
orders = orders[["order_id", "order_date", "customer_id", "total_price", "region"]]

# 把某欄移到最前面
col = orders.pop("total_price")
orders.insert(0, "total_price", col)
```

---

## 4️⃣ 字串操作（`.str` 存取器）

```python
# 所有字串方法都在 .str 底下
orders["region"].str.upper()         # 轉大寫
orders["region"].str.lower()         # 轉小寫
orders["region"].str.len()           # 字串長度
orders["region"].str.contains("台")  # 是否包含
orders["region"].str.replace("台", "臺")  # 替換
orders["region"].str.strip()         # 去除前後空白
orders["order_id"].str[1:]           # 切片（去掉第一個字元）
orders["order_id"].str.extract(r"(\d+)")  # 正則提取數字部分
```

---

## 5️⃣ 實用的 `apply()` 與 `map()`

### `map()`：一對一轉換

```python
# 用字典對照
level_map = {"Gold": "金", "Silver": "銀", "Bronze": "銅", "Platinum": "白金"}
customers["會員等級中文"] = customers["member_level"].map(level_map)
```

### `apply()`：套用自訂函式

```python
# 對單一欄位
def classify_age(age):
    if age < 25:
        return "年輕"
    elif age < 40:
        return "中年"
    else:
        return "資深"

customers["age_group"] = customers["age"].apply(classify_age)

# 用 lambda 更簡潔
customers["age_group"] = customers["age"].apply(
    lambda x: "年輕" if x < 25 else ("中年" if x < 40 else "資深")
)

# 對整個 DataFrame（逐列）
def order_summary(row):
    return f"{row['order_id']}: {row['quantity']}件, ${row['total_price']:.0f}"

orders["summary"] = orders.apply(order_summary, axis=1)
```

> ⚠️ **效能提醒**：`apply()` 其實蠻慢的（因為是逐列執行 Python）。
> 能用向量化運算（如 `np.where`、`pd.cut`）就優先用。

---

## 🧪 動手練習

### 練習 1：篩選組合技

```python
orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])

# 1. 找出台北地區、信用卡付款、金額 > 2000 的訂單
# 2. 找出 2024 年 1 月份的所有訂單
# 3. 找出 quantity >= 3 且有折扣的訂單
# 4. 找出不是「台北」和「高雄」的訂單
# 5. 用 query() 重寫上面的篩選
```

### 練習 2：新增分析欄位

```python
# 1. 新增「是否有折扣」布林欄位
# 2. 新增「折扣金額」= quantity * unit_price * discount
# 3. 新增「訂單月份」（從 order_date 提取）
# 4. 新增「出貨速度」：1-2 天=快, 3-4 天=中, 5+ 天=慢
# 5. 按 total_price 降序排列，取出 Top 5
```

### 練習 3：商業問題

```python
# 用篩選和排序回答：
# 1. 最貴的 3 筆訂單是什麼？
# 2. 有折扣的訂單佔幾 %？
# 3. 台北地區平均出貨天數是多少？
# 4. 哪種付款方式的平均訂單金額最高？（提示：下一章的 GroupBy 更適合）
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：忘記用小括號包條件

```python
# ❌ 運算子優先順序問題
orders[orders["region"] == "台北" & orders["quantity"] > 2]
# 實際上被解讀為：orders["region"] == ("台北" & orders["quantity"]) > 2

# ✅
orders[(orders["region"] == "台北") & (orders["quantity"] > 2)]
```

### 陷阱 2：用 `and` / `or` 而不是 `&` / `|`

```python
# ❌ Python 的 and/or 不能用在 Series 上
orders[(orders["region"] == "台北") and (orders["quantity"] > 2)]
# ValueError: The truth value of a Series is ambiguous

# ✅ 用 & 和 |
orders[(orders["region"] == "台北") & (orders["quantity"] > 2)]
```

### 陷阱 3：連續篩選產生 SettingWithCopyWarning

```python
# ❌
taipei = orders[orders["region"] == "台北"]
taipei["new_col"] = 1  # Warning!

# ✅
taipei = orders[orders["region"] == "台北"].copy()
taipei["new_col"] = 1
```

---

## 🔑 本章重點回顧

| 操作 | 方法 | 範例 |
|------|------|------|
| 單條件篩選 | `df[condition]` | `df[df["col"] > 5]` |
| 多條件 AND | `&` + 小括號 | `df[(A) & (B)]` |
| 多條件 OR | `\|` + 小括號 | `df[(A) \| (B)]` |
| 值在清單中 | `isin()` | `df[df["col"].isin([1,2,3])]` |
| 範圍篩選 | `between()` | `df[df["col"].between(1,10)]` |
| SQL 風格 | `query()` | `df.query("col > 5")` |
| 排序 | `sort_values()` | `df.sort_values("col")` |
| Top N | `nlargest()` | `df.nlargest(10, "col")` |
| 新增欄位 | 直接賦值 | `df["new"] = ...` |
| 條件新增 | `np.where()` | 二元分類 |
| 多條件新增 | `np.select()` | 多分類 |
| 數值分箱 | `pd.cut()` | 連續變離散 |

---

## ⏭️ 下一章預告

> **Ch07：分組聚合的力量 — GroupBy**
>
> 篩選能讓你「看到」資料，但 GroupBy 能讓你「理解」資料。
> 它是 Pandas 最強大的功能之一。

---

[← Ch05：資料清理的藝術](ch05-data-cleaning.md) | [Ch07：分組聚合的力量 →](ch07-groupby.md)
