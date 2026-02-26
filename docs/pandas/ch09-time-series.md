# Ch09：時間序列處理

> **本章目標**：學會在 Pandas 中處理日期時間資料 — 解析、轉換、重採樣、移動平均。

---

## ⏰ 為什麼時間序列很重要？

商業分析中，幾乎每個問題都有「時間」維度：

- 這個月比上個月好嗎？（**趨勢**）
- 每年哪個月份賣最好？（**季節性**）
- 行銷活動前後銷售有變化嗎？（**事件影響**）
- 未來三個月營收會是多少？（**預測**）

```
營收
 ▲
 │        ╱╲     ╱╲
 │   ╱╲  ╱  ╲   ╱  ╲    ← 趨勢 + 季節性
 │  ╱  ╲╱    ╲ ╱    ╲
 │ ╱           ╲      ╲
 └──────────────────────→ 時間
  1月  2月  3月  4月  5月
```

---

## 📦 準備資料

```python
import pandas as pd
import numpy as np

orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])

print(f"日期範圍：{orders['order_date'].min()} ~ {orders['order_date'].max()}")
print(f"資料型態：{orders['order_date'].dtype}")
```

---

## 1️⃣ 日期時間基礎

### 建立日期時間

```python
# 字串轉日期
pd.to_datetime("2024-01-15")
pd.to_datetime("2024/01/15")
pd.to_datetime("Jan 15, 2024")
pd.to_datetime("15-01-2024", format="%d-%m-%Y")

# 整個欄位轉換
orders["order_date"] = pd.to_datetime(orders["order_date"])

# 處理混合格式
orders["order_date"] = pd.to_datetime(orders["order_date"], format="mixed")

# 處理錯誤
orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
```

### 日期的組件提取

```python
# .dt 存取器：提取日期的各個部分
orders["year"] = orders["order_date"].dt.year           # 年
orders["month"] = orders["order_date"].dt.month          # 月
orders["day"] = orders["order_date"].dt.day              # 日
orders["weekday"] = orders["order_date"].dt.day_name()   # 星期幾
orders["quarter"] = orders["order_date"].dt.quarter      # 季度
orders["week"] = orders["order_date"].dt.isocalendar().week  # 第幾週
orders["day_of_week"] = orders["order_date"].dt.dayofweek    # 0=Monday

# 是否為週末？
orders["is_weekend"] = orders["order_date"].dt.dayofweek >= 5
```

### 常用 `.dt` 屬性

| 屬性 | 回傳 | 範例 |
|------|------|------|
| `.year` | 年份 | 2024 |
| `.month` | 月份 | 1~12 |
| `.day` | 日 | 1~31 |
| `.hour` | 時 | 0~23 |
| `.dayofweek` | 星期 | 0(Mon)~6(Sun) |
| `.day_name()` | 星期名稱 | Monday |
| `.quarter` | 季度 | 1~4 |
| `.is_month_end` | 是否月底 | True/False |
| `.date` | 只取日期 | 2024-01-15 |

---

## 2️⃣ 日期篩選

### 用條件篩選

```python
# 特定月份
jan_orders = orders[orders["order_date"].dt.month == 1]

# 日期範圍
q1_orders = orders[
    (orders["order_date"] >= "2024-01-01") &
    (orders["order_date"] < "2024-04-01")
]

# 特定日期之後
recent = orders[orders["order_date"] >= "2024-03-01"]
```

### 用 DatetimeIndex 篩選（更方便）

```python
# 把日期設為索引
orders_ts = orders.set_index("order_date").sort_index()

# 用字串切片（超方便！）
orders_ts["2024-01"]           # 2024 年 1 月的所有資料
orders_ts["2024-01":"2024-03"] # 2024 年 1-3 月
orders_ts["2024"]              # 整個 2024 年
```

---

## 3️⃣ 重採樣（Resample）

**Resample = 改變時間粒度**

就像你看地圖可以放大看街道、縮小看城市，
resample 讓你可以從「每天」看到「每月」、「每季」。

### 基本用法

```python
# 先設定日期為索引
orders_ts = orders.set_index("order_date").sort_index()

# 每月加總
monthly = orders_ts["total_price"].resample("ME").sum()
print(monthly)
```

```
order_date
2024-01-31    85300.0
2024-02-29   101600.0
2024-03-31    72856.0
Freq: ME, Name: total_price, dtype: float64
```

### 常用頻率代碼

| 代碼 | 意義 | 範例 |
|------|------|------|
| `D` | 每天 | 日報 |
| `W` | 每週 | 週報 |
| `ME` | 每月（月底） | 月報 |
| `MS` | 每月（月初） | 月報 |
| `QE` | 每季 | 季報 |
| `YE` | 每年 | 年報 |
| `h` | 每小時 | 即時監控 |

### 多種聚合

```python
# 每月的多項統計
monthly_stats = orders_ts["total_price"].resample("ME").agg(["sum", "mean", "count"])
monthly_stats.columns = ["月營收", "平均客單價", "訂單數"]
print(monthly_stats)
```

### 多欄位 resample

```python
monthly = orders_ts.resample("ME").agg({
    "order_id": "count",
    "total_price": "sum",
    "quantity": "sum",
    "discount": "mean"
})
```

---

## 4️⃣ 移動平均（Rolling）

移動平均可以**平滑波動**，讓你看到潛在趨勢。

```
原始資料（波動大）        7 日移動平均（趨勢明顯）
  ▲                        ▲
  │ /\  /\/\               │
  │/  \/    \              │    ___/‾‾‾
  │          \/\           │ __/
  └───────────→            └───────────→
```

### 基本用法

```python
# 先按日加總
daily_sales = orders_ts["total_price"].resample("D").sum().fillna(0)

# 7 日移動平均
daily_sales.rolling(window=7).mean()

# 30 日移動平均
daily_sales.rolling(window=30).mean()
```

### 移動統計

```python
# 移動加總
daily_sales.rolling(7).sum()

# 移動最大值
daily_sales.rolling(7).max()

# 移動標準差（看波動程度）
daily_sales.rolling(7).std()
```

### 指數加權移動平均（EWMA）

```python
# 對近期資料給更高權重
daily_sales.ewm(span=7).mean()
```

---

## 5️⃣ 時間差計算

### Timedelta

```python
# 計算出貨到達日
orders["delivery_date"] = orders["order_date"] + pd.Timedelta(days=3)

# 使用 shipping_days 欄位
orders["delivery_date"] = orders["order_date"] + pd.to_timedelta(orders["shipping_days"], unit="D")

# 計算天數差
orders["days_since_first"] = (orders["order_date"] - orders["order_date"].min()).dt.days
```

### 日期間隔分析

```python
# 顧客的購買間隔
customer_orders = orders.sort_values(["customer_id", "order_date"])
customer_orders["days_since_last"] = (
    customer_orders.groupby("customer_id")["order_date"].diff().dt.days
)

# 平均購買間隔
avg_interval = customer_orders.groupby("customer_id")["days_since_last"].mean()
print(avg_interval.describe())
```

---

## 6️⃣ 商業實戰

### 案例 1：月度營收趨勢

```python
orders_ts = orders.set_index("order_date").sort_index()

monthly_revenue = orders_ts["total_price"].resample("ME").sum()

# 月對月成長率 (MoM)
mom_growth = monthly_revenue.pct_change() * 100
print("月度成長率：")
print(mom_growth.round(2))
```

### 案例 2：行銷活動效果分析

```python
campaigns = pd.read_csv("data/campaigns.csv", parse_dates=["start_date", "end_date"])

# 分析某次活動前後的銷售變化
campaign = campaigns.iloc[0]
before = orders[
    (orders["order_date"] >= campaign["start_date"] - pd.Timedelta(days=7)) &
    (orders["order_date"] < campaign["start_date"])
]["total_price"].sum()

during = orders[
    (orders["order_date"] >= campaign["start_date"]) &
    (orders["order_date"] <= campaign["end_date"])
]["total_price"].sum()

print(f"活動前 7 天營收：{before:,.0f}")
print(f"活動期間營收：{during:,.0f}")
print(f"成長率：{(during/before - 1) * 100:.1f}%")
```

### 案例 3：星期幾最忙？

```python
weekday_sales = orders.groupby(orders["order_date"].dt.day_name()).agg(
    訂單數=("order_id", "count"),
    平均營收=("total_price", "mean")
).round(0)

# 按星期排序
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekday_sales = weekday_sales.reindex(day_order)
print(weekday_sales)
```

---

## 🧪 動手練習

### 練習 1：日期提取

```python
# 1. 從 order_date 提取年、月、星期幾
# 2. 新增「是否為週末」欄位
# 3. 統計平日 vs 週末的訂單數量和平均金額
```

### 練習 2：Resample 分析

```python
# 1. 計算每週的訂單數和營收
# 2. 計算每月的平均客單價
# 3. 計算 7 日和 14 日移動平均
```

### 練習 3：完整時間序列報告

```python
# 產出一份時間序列報告，包含：
# 1. 月度營收趨勢（含 MoM 成長率）
# 2. 各星期幾的銷售模式
# 3. 行銷活動前後比較
# 4. 每月新客戶數
```

---

## ❗ 常見錯誤與陷阱

### 陷阱 1：忘記 `parse_dates`

```python
# ❌ 日期被當成字串
df = pd.read_csv("data.csv")
df["date"].dt.month  # AttributeError!

# ✅ 讀取時就解析
df = pd.read_csv("data.csv", parse_dates=["date"])
```

### 陷阱 2：resample 前忘記設索引

```python
# ❌ resample 需要 DatetimeIndex
orders["total_price"].resample("ME").sum()  # Error!

# ✅ 先設定索引
orders.set_index("order_date")["total_price"].resample("ME").sum()
```

### 陷阱 3：時區問題

```python
# 如果資料有時區資訊
df["date"] = pd.to_datetime(df["date"], utc=True)
df["date"] = df["date"].dt.tz_convert("Asia/Taipei")
```

---

## 🔑 本章重點回顧

| 操作 | 方法 | 用途 |
|------|------|------|
| 字串轉日期 | `pd.to_datetime()` | 解析日期 |
| 提取組件 | `.dt.year/month/day` | 取出年月日 |
| 日期篩選 | 條件 or 字串索引 | 選取時間範圍 |
| 重採樣 | `.resample("ME")` | 改變時間粒度 |
| 移動平均 | `.rolling(7).mean()` | 平滑趨勢 |
| 時間差 | `pd.Timedelta` | 計算日期間隔 |
| 成長率 | `.pct_change()` | 環比成長 |

---

## ⏭️ 下一章預告

> **Ch10：實戰專案 — 電商銷售分析**
>
> 前面九章學到的所有技能，在這一章全部用上。
> 從頭到尾做一個完整的資料分析專案。

---

[← Ch08：樞紐分析表](ch08-pivot-tables.md) | [Ch10：實戰專案 →](ch10-real-project.md)
