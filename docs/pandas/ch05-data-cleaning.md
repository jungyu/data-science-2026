# Ch05：資料清理的藝術

> **本章目標**：學會處理缺失值、重複值、異常值和型態問題 — 真實世界資料必經之路。

---

## 🧹 為什麼資料需要清理？

> **真實世界的資料，從來就不是乾淨的。**

```
你以為的資料：             實際拿到的資料：
┌────┬──────┬────┐       ┌────┬──────┬────────┐
│ ID │ 金額 │地區│       │ ID │ 金額 │ 地區   │
├────┼──────┼────┤       ├────┼──────┼────────┤
│ 01 │ 1000 │台北│       │ 01 │ 1000 │ 台北   │
│ 02 │ 2000 │台中│       │ 02 │      │ 台中   │  ← 空值
│ 03 │ 3000 │高雄│       │ 03 │ -500 │ 高熊   │  ← 負數？錯字？
└────┴──────┴────┘       │ 03 │ 3000 │ 高雄   │  ← 重複
                         │ 04 │ 2千  │ NaN    │  ← 格式錯誤
                         └────┴──────┴────────┘
```

資料清理通常佔整個分析流程的 **60-80%** 時間。這不是浪費時間，這**就是**工作的一部分。

---

## 📦 準備工作

```python
import pandas as pd
import numpy as np

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

# 先了解資料品質
print("=== 訂單資料品質報告 ===")
print(f"總筆數：{len(orders)}")
print(f"\n缺失值：")
print(orders.isnull().sum()[orders.isnull().sum() > 0])
print(f"\n重複值：{orders.duplicated().sum()} 筆")
```

---

## 1️⃣ 缺失值處理

### 偵測缺失值

```python
# 哪些欄位有空值？
orders.isnull().sum()

# 空值的比例
(orders.isnull().sum() / len(orders) * 100).round(2)

# 視覺化看整體空值分佈
orders.isnull().any()  # 哪些欄位有空值

# 找出「有空值的那些列」
orders[orders.isnull().any(axis=1)]
```

### 策略一：刪除（簡單粗暴）

```python
# 刪除有任何空值的列
df_clean = orders.dropna()
print(f"刪除前：{len(orders)} 筆")
print(f"刪除後：{len(df_clean)} 筆")

# 只刪除「特定欄位」有空值的列
df_clean = orders.dropna(subset=["product_id", "region"])

# 刪除空值超過一定比例的欄位
threshold = len(orders) * 0.5  # 超過 50% 空值就刪
df_clean = orders.dropna(axis=1, thresh=threshold)
```

> ⚠️ **什麼時候適合刪除？**
> - 空值很少（< 5%）
> - 資料量很大（刪了影響不大）
> - 空值是隨機分佈的（不是系統性遺失）

### 策略二：填補

```python
# 用固定值填補
orders["region"] = orders["region"].fillna("未知")
orders["shipping_days"] = orders["shipping_days"].fillna(0)

# 用平均值填補（數值欄位）
mean_days = orders["shipping_days"].mean()
orders["shipping_days"] = orders["shipping_days"].fillna(mean_days)

# 用中位數填補（對異常值較穩健）
median_days = orders["shipping_days"].median()
orders["shipping_days"] = orders["shipping_days"].fillna(median_days)

# 用眾數填補（類別欄位）
mode_region = orders["region"].mode()[0]
orders["region"] = orders["region"].fillna(mode_region)

# 用前一筆值填補（時間序列常用）
orders["shipping_days"] = orders["shipping_days"].ffill()  # forward fill

# 用後一筆值填補
orders["shipping_days"] = orders["shipping_days"].bfill()  # backward fill
```

### 策略選擇指南

| 情境 | 建議策略 | 原因 |
|------|----------|------|
| 缺失 < 5% | 刪除 | 影響小 |
| 數值欄位 | 填中位數 | 穩健性好 |
| 類別欄位 | 填眾數或「未知」 | 保留資料 |
| 時間序列 | 前值填補 (ffill) | 保持連續性 |
| 重要分析欄位 | 不要隨便填！ | 可能誤導分析 |

---

## 2️⃣ 重複值處理

### 偵測重複

```python
# 完全重複的列
orders.duplicated().sum()

# 看看重複的是哪些（保留所有重複組）
orders[orders.duplicated(keep=False)]

# 以特定欄位判斷重複（例如同一個 order_id 出現兩次）
orders.duplicated(subset=["order_id"]).sum()

# 找出重複的 order_id
dup_ids = orders[orders.duplicated(subset=["order_id"], keep=False)]
print(dup_ids.sort_values("order_id"))
```

### 移除重複

```python
# 保留第一筆，刪除後續重複
df_clean = orders.drop_duplicates()

# 以特定欄位去重
df_clean = orders.drop_duplicates(subset=["order_id"])

# 保留最後一筆（例如以最新的資料為準）
df_clean = orders.drop_duplicates(subset=["order_id"], keep="last")
```

### 重複值的進階判斷

```python
# 有時候「部分重複」才是問題
# 例如：同一個顧客在同一天買了同一個商品 → 可能是重複下單

possible_dup = orders.duplicated(
    subset=["customer_id", "order_date", "product_id"],
    keep=False
)
orders[possible_dup]
```

---

## 3️⃣ 型態轉換

### 偵測型態問題

```python
# 先看目前的型態
print(orders.dtypes)

# 常見問題：數值被讀成 object
# 原因：欄位中混了非數值字元（例如 "N/A", "無", "1,290"）
```

### 字串轉數值

```python
# 基本轉換
orders["quantity"] = orders["quantity"].astype(int)
orders["unit_price"] = orders["unit_price"].astype(float)

# 安全轉換（遇到無法轉換的值不會報錯）
orders["unit_price"] = pd.to_numeric(orders["unit_price"], errors="coerce")
# errors="coerce" → 無法轉換的變成 NaN

# 處理千分位逗號
# "1,290" → 1290
orders["unit_price"] = orders["unit_price"].str.replace(",", "").astype(float)
```

### 字串轉日期

```python
# 自動解析
orders["order_date"] = pd.to_datetime(orders["order_date"])

# 指定格式（更快更準確）
orders["order_date"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d")

# 處理混合格式
orders["order_date"] = pd.to_datetime(orders["order_date"], format="mixed")

# 處理錯誤的日期
orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
# 無法解析的變成 NaT（Not a Time）
```

### 轉成 category（節省記憶體）

```python
# 重複值多的欄位，轉成 category 可以大幅省記憶體
print(f"轉換前：{orders["region"].memory_usage(deep=True)} bytes")

orders["region"] = orders["region"].astype("category")
orders["payment_method"] = orders["payment_method"].astype("category")

print(f"轉換後：{orders["region"].memory_usage(deep=True)} bytes")
```

---

## 4️⃣ 異常值處理

### 什麼是異常值？

```
正常分佈                          有異常值
    ▲                               ▲
    │   ████                         │   ████
    │  ██████                        │  ██████
    │ ████████                       │ ████████
    │██████████                      │██████████
    └──────────→                     └──────────────────→ ← 這個
                                                    ↑
                                                  異常值
```

### 偵測方法一：統計方法

```python
# 用 describe() 看 min 和 max 是否合理
orders["unit_price"].describe()

# IQR 方法（四分位距）
Q1 = orders["unit_price"].quantile(0.25)
Q3 = orders["unit_price"].quantile(0.75)
IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

print(f"合理範圍：{lower} ~ {upper}")

# 找出異常值
outliers = orders[(orders["unit_price"] < lower) | (orders["unit_price"] > upper)]
print(f"異常值筆數：{len(outliers)}")
print(outliers)
```

### 偵測方法二：商業邏輯

```python
# 折扣不應該超過 1（100%）
orders[orders["discount"] > 1]

# 數量不應該是負數
orders[orders["quantity"] < 0]

# 出貨天數不應該超過 30
orders[orders["shipping_days"] > 30]
```

### 處理異常值

```python
# 方法 1：刪除
df_clean = orders[(orders["unit_price"] >= lower) & (orders["unit_price"] <= upper)]

# 方法 2：替換成邊界值（Winsorize / Clipping）
orders["unit_price"] = orders["unit_price"].clip(lower=lower, upper=upper)

# 方法 3：標記（不刪除，留給後續分析判斷）
orders["is_outlier"] = (
    (orders["unit_price"] < lower) | (orders["unit_price"] > upper)
)
```

---

## 5️⃣ 字串清理

### 常見的字串問題

```python
# 問題 1：前後空白
orders["region"] = orders["region"].str.strip()

# 問題 2：大小寫不一致
customers["gender"] = customers["gender"].str.upper()

# 問題 3：全半形混用
# "台北" vs "台北"（全形 vs 半形）
import unicodedata
def normalize_str(s):
    if pd.isna(s):
        return s
    return unicodedata.normalize("NFKC", s)

orders["region"] = orders["region"].apply(normalize_str)

# 問題 4：替換特定字串
orders["region"] = orders["region"].replace({"高熊": "高雄", "台IP": "台北"})
```

---

## 🔄 完整清理流程範例

```python
def clean_orders(filepath):
    """清理訂單資料的完整流程"""

    # 1. 讀取
    df = pd.read_csv(filepath)
    print(f"原始資料：{len(df)} 筆")

    # 2. 移除完全重複
    before = len(df)
    df = df.drop_duplicates()
    print(f"移除重複：{before - len(df)} 筆")

    # 3. 型態轉換
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    # 4. 字串清理
    df["region"] = df["region"].str.strip()
    df["payment_method"] = df["payment_method"].str.strip()

    # 5. 缺失值處理
    df["region"] = df["region"].fillna("未知")
    df["shipping_days"] = df["shipping_days"].fillna(df["shipping_days"].median())
    df = df.dropna(subset=["order_id", "customer_id"])  # 關鍵欄位不能空

    # 6. 異常值處理
    df = df[df["quantity"] > 0]
    df = df[df["unit_price"] > 0]
    df = df[df["discount"].between(0, 1)]

    # 7. 新增計算欄位
    df["total_price"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])

    print(f"清理後：{len(df)} 筆")
    return df

# 使用
orders_clean = clean_orders("data/orders.csv")
```

---

## 🧪 動手練習

### 練習 1：清理 customers 資料

```python
customers = pd.read_csv("data/customers.csv")

# 1. 檢查有沒有缺失值
# 2. 檢查 age 有沒有不合理的值（< 0 或 > 120）
# 3. 檢查 gender 有幾種值（可能有大小寫不一致）
# 4. 檢查 member_level 有沒有錯誤的等級名稱
# 5. 把 join_date 轉成日期格式
```

### 練習 2：寫你自己的清理函式

```python
def clean_customers(filepath):
    """你的 customers 清理函式"""
    # 你來寫！
    pass
```

### 練習 3：清理前後的比較報告

```python
# 寫一個函式，比較清理前後的差異
def compare_before_after(df_before, df_after):
    print(f"列數：{len(df_before)} → {len(df_after)}")
    print(f"欄數：{df_before.shape[1]} → {df_after.shape[1]}")
    print(f"空值：{df_before.isnull().sum().sum()} → {df_after.isnull().sum().sum()}")
    print(f"重複：{df_before.duplicated().sum()} → {df_after.duplicated().sum()}")
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：在原始資料上直接修改

```python
# ❌ 清理完才發現搞砸了，原始資料也沒了
orders.dropna(inplace=True)

# ✅ 保留原始資料的副本
orders_raw = pd.read_csv("data/orders.csv")  # 原始
orders_clean = orders_raw.copy()              # 副本，在這上面操作
```

### 陷阱 2：用平均值填補偏態資料

```python
# ❌ 如果資料有極端值，平均值會被拉走
orders["shipping_days"].fillna(orders["shipping_days"].mean())  # mean = 15？

# ✅ 用中位數更穩健
orders["shipping_days"].fillna(orders["shipping_days"].median())
```

### 陷阱 3：沒有記錄清理步驟

```python
# ❌ 半年後回來看，不知道當初做了什麼

# ✅ 把清理邏輯寫成函式，附上註解
# 或者用 Jupyter Notebook 記錄每一步
```

---

## 🔑 本章重點回顧

| 問題 | 偵測方法 | 處理方法 |
|------|----------|----------|
| 缺失值 | `isnull().sum()` | `dropna()` / `fillna()` |
| 重複值 | `duplicated().sum()` | `drop_duplicates()` |
| 型態錯誤 | `dtypes` | `astype()` / `to_numeric()` / `to_datetime()` |
| 異常值 | IQR / 商業邏輯 | 刪除 / `clip()` / 標記 |
| 字串問題 | `value_counts()` | `strip()` / `replace()` / `upper()` |

**黃金法則**：先備份，再清理。永遠保留原始資料的副本。

---

## ⏭️ 下一章預告

> **Ch06：篩選、排序與欄位操作**
>
> 資料清乾淨了，下一步就是「取你需要的部分」。
> 學會精準地從大表格中切出你要的資料。

---

[← Ch04：探索式資料分析](ch04-eda.md) | [Ch06：篩選、排序與欄位操作 →](ch06-filtering-operations.md)
