# Ch10：實戰專案 — 電商銷售分析

> **本章目標**：整合前九章所學，從頭到尾完成一個完整的資料分析專案。

---

## 🎯 專案背景

你是「台灣好物」電商公司的資料分析師。

老闆在月會上問了五個問題：

> 1. 我們的整體營運狀況如何？
> 2. 哪些地區和商品是我們的主力？
> 3. 顧客的消費行為有什麼特徵？
> 4. 行銷活動有效嗎？
> 5. 你有什麼建議？

你有 3 小時。開始吧。

---

## 📋 分析流程

```
┌──────────────┐
│ 1. 讀取資料  │  Ch03
├──────────────┤
│ 2. 資料清理  │  Ch05
├──────────────┤
│ 3. EDA 概覽  │  Ch04
├──────────────┤
│ 4. 深度分析  │  Ch06-09
├──────────────┤
│ 5. 商業洞察  │  綜合
├──────────────┤
│ 6. 報告產出  │  整合
└──────────────┘
```

---

## Step 1：讀取資料

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 設定中文顯示
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]  # macOS
# plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]  # Windows
plt.rcParams["axes.unicode_minus"] = False

# 讀取所有資料表
orders = pd.read_csv("data/orders.csv", parse_dates=["order_date"])
customers = pd.read_csv("data/customers.csv", parse_dates=["join_date"])
products = pd.read_csv("data/products.csv", parse_dates=["launch_date"])
campaigns = pd.read_csv("data/campaigns.csv", parse_dates=["start_date", "end_date"])
returns = pd.read_csv("data/returns.csv", parse_dates=["return_date"])

# 快速確認
for name, df in [("orders", orders), ("customers", customers),
                 ("products", products), ("campaigns", campaigns),
                 ("returns", returns)]:
    print(f"{name}: {df.shape[0]} 列 × {df.shape[1]} 欄")
```

---

## Step 2：資料清理

```python
# === 訂單資料清理 ===

# 2.1 檢查缺失值
print("缺失值：")
print(orders.isnull().sum()[orders.isnull().sum() > 0])

# 2.2 處理缺失值
orders["region"] = orders["region"].fillna("未知")
orders["shipping_days"] = orders["shipping_days"].fillna(orders["shipping_days"].median())
orders = orders.dropna(subset=["product_id"])  # 沒有商品的訂單無法分析

# 2.3 移除重複
before = len(orders)
orders = orders.drop_duplicates(subset=["order_id"])
print(f"移除重複：{before - len(orders)} 筆")

# 2.4 異常值檢查
print(f"\nquantity 範圍：{orders['quantity'].min()} ~ {orders['quantity'].max()}")
print(f"unit_price 範圍：{orders['unit_price'].min()} ~ {orders['unit_price'].max()}")
print(f"discount 範圍：{orders['discount'].min()} ~ {orders['discount'].max()}")

# 移除不合理的值
orders = orders[orders["quantity"] > 0]
orders = orders[orders["unit_price"] > 0]
orders = orders[orders["discount"].between(0, 1)]

# 2.5 新增計算欄位
orders["total_price"] = orders["quantity"] * orders["unit_price"] * (1 - orders["discount"])
orders["month"] = orders["order_date"].dt.to_period("M")
orders["weekday"] = orders["order_date"].dt.day_name()

print(f"\n清理後：{len(orders)} 筆有效訂單")
```

---

## Step 3：EDA 概覽

```python
# === 整體營運指標 ===

total_revenue = orders["total_price"].sum()
total_orders = len(orders)
unique_customers = orders["customer_id"].nunique()
avg_order_value = orders["total_price"].mean()

print("=" * 50)
print("📊 整體營運概覽")
print("=" * 50)
print(f"總營收：${total_revenue:,.0f}")
print(f"總訂單數：{total_orders}")
print(f"不重複顧客：{unique_customers}")
print(f"平均客單價：${avg_order_value:,.0f}")
print(f"平均每客訂單數：{total_orders / unique_customers:.1f}")
print(f"日期範圍：{orders['order_date'].min().date()} ~ {orders['order_date'].max().date()}")
```

---

## Step 4：深度分析

### 4.1 地區分析

```python
# 各地區營運表現
region_analysis = orders.groupby("region").agg(
    訂單數=("order_id", "count"),
    顧客數=("customer_id", "nunique"),
    總營收=("total_price", "sum"),
    平均客單價=("total_price", "mean"),
    平均出貨天數=("shipping_days", "mean")
).round(0)

region_analysis["營收佔比%"] = (region_analysis["總營收"] / region_analysis["總營收"].sum() * 100).round(1)
region_analysis = region_analysis.sort_values("總營收", ascending=False)

print("\n📍 地區分析")
print(region_analysis)
```

### 4.2 商品分析

```python
# 合併商品資訊
orders_products = orders.merge(products, on="product_id", how="left")

# 各商品類別銷售
category_analysis = orders_products.groupby("category").agg(
    訂單數=("order_id", "count"),
    銷售數量=("quantity", "sum"),
    總營收=("total_price", "sum"),
    平均單價=("unit_price", "mean")
).round(0).sort_values("總營收", ascending=False)

print("\n🛍 商品類別分析")
print(category_analysis)

# 各商品銷售排名
product_ranking = orders_products.groupby(["product_id", "product_name"]).agg(
    訂單數=("order_id", "count"),
    總營收=("total_price", "sum")
).round(0).sort_values("總營收", ascending=False)

print("\n🏆 商品銷售排名")
print(product_ranking)
```

### 4.3 商品毛利分析

```python
# 計算毛利
orders_products["revenue"] = orders_products["total_price"]
orders_products["cost_total"] = orders_products["quantity"] * orders_products["cost"]
orders_products["gross_profit"] = orders_products["revenue"] - orders_products["cost_total"]
orders_products["gross_margin"] = (orders_products["gross_profit"] / orders_products["revenue"] * 100)

# 各類別毛利
margin_by_category = orders_products.groupby("category").agg(
    總營收=("revenue", "sum"),
    總成本=("cost_total", "sum"),
    總毛利=("gross_profit", "sum")
).round(0)
margin_by_category["毛利率%"] = (margin_by_category["總毛利"] / margin_by_category["總營收"] * 100).round(1)

print("\n💰 商品毛利分析")
print(margin_by_category.sort_values("毛利率%", ascending=False))
```

### 4.4 顧客分析

```python
# 合併顧客資訊
orders_customers = orders.merge(customers, on="customer_id", how="left")

# 各會員等級分析
member_analysis = orders_customers.groupby("member_level").agg(
    顧客數=("customer_id", "nunique"),
    訂單數=("order_id", "count"),
    總消費=("total_price", "sum"),
    平均消費=("total_price", "mean")
).round(0)

print("\n👤 會員等級分析")
print(member_analysis)

# RFM 分析（簡化版）
rfm = orders.groupby("customer_id").agg(
    最後消費日=("order_date", "max"),
    訂單次數=("order_id", "count"),
    總消費額=("total_price", "sum")
)

# Recency：距離最後一次消費的天數
latest_date = orders["order_date"].max()
rfm["Recency"] = (latest_date - rfm["最後消費日"]).dt.days
rfm = rfm.rename(columns={"訂單次數": "Frequency", "總消費額": "Monetary"})

print("\n📊 RFM 分析（前 10 名 VIP）")
print(rfm.sort_values("Monetary", ascending=False).head(10)[["Recency", "Frequency", "Monetary"]])
```

### 4.5 時間趨勢分析

```python
# 月度趨勢
monthly_trend = orders.set_index("order_date")["total_price"].resample("ME").agg(["sum", "count", "mean"])
monthly_trend.columns = ["月營收", "訂單數", "平均客單價"]

# 月對月成長率
monthly_trend["MoM成長率%"] = (monthly_trend["月營收"].pct_change() * 100).round(1)

print("\n📈 月度趨勢")
print(monthly_trend.round(0))

# 星期幾分析
weekday_analysis = orders.groupby("weekday").agg(
    訂單數=("order_id", "count"),
    平均金額=("total_price", "mean")
).round(0)

day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekday_analysis = weekday_analysis.reindex(day_order)

print("\n📅 各星期訂單分佈")
print(weekday_analysis)
```

### 4.6 行銷活動效果分析

```python
print("\n📣 行銷活動效果")
print("=" * 50)

for _, campaign in campaigns.iterrows():
    # 活動期間
    during = orders[
        (orders["order_date"] >= campaign["start_date"]) &
        (orders["order_date"] <= campaign["end_date"])
    ]

    # 活動前同等天數
    duration = (campaign["end_date"] - campaign["start_date"]).days + 1
    before_start = campaign["start_date"] - pd.Timedelta(days=duration)
    before = orders[
        (orders["order_date"] >= before_start) &
        (orders["order_date"] < campaign["start_date"])
    ]

    print(f"\n活動 {campaign['campaign_id']}（{campaign['start_date'].date()} ~ {campaign['end_date'].date()}）")
    print(f"  折扣率：{campaign['discount_rate']:.0%}")
    print(f"  活動前：{len(before)} 筆訂單，營收 ${before['total_price'].sum():,.0f}")
    print(f"  活動中：{len(during)} 筆訂單，營收 ${during['total_price'].sum():,.0f}")
    if before["total_price"].sum() > 0:
        growth = (during["total_price"].sum() / before["total_price"].sum() - 1) * 100
        print(f"  成長率：{growth:+.1f}%")
```

### 4.7 退貨分析

```python
# 退貨率
return_count = len(returns)
return_rate = return_count / len(orders) * 100

print(f"\n🔄 退貨分析")
print(f"退貨筆數：{return_count}")
print(f"退貨率：{return_rate:.1f}%")

# 退貨原因分佈
print("\n退貨原因：")
print(returns["reason"].value_counts())

# 退貨訂單的特徵
return_orders = orders[orders["order_id"].isin(returns["order_id"])]
non_return_orders = orders[~orders["order_id"].isin(returns["order_id"])]

print(f"\n退貨訂單平均金額：${return_orders['total_price'].mean():,.0f}")
print(f"非退貨訂單平均金額：${non_return_orders['total_price'].mean():,.0f}")
```

---

## Step 5：商業洞察與建議

```python
print("\n" + "=" * 60)
print("📋 分析摘要與商業建議")
print("=" * 60)

print("""
📍 地區策略：
   - 台北是營收主力，持續深耕
   - 新竹市場較小，可考慮定向行銷

🛍 商品策略：
   - 3C 產品營收最高，但需關注毛利率
   - 生活用品毛利率高，適合提高銷售比重

👤 顧客策略：
   - Platinum 和 Gold 會員貢獻大部分營收
   - 建議對 Bronze 會員設計升級活動

📈 營運建議：
   - 行銷活動期間訂單明顯增加，建議維持每月一檔
   - 週末訂單量較低，可考慮週末限定促銷
   - 退貨率偏低，維持現有品質控管
""")
```

---

## Step 6：產出報告

```python
# 匯出分析結果到 Excel
with pd.ExcelWriter("data/sales_report.xlsx") as writer:
    region_analysis.to_excel(writer, sheet_name="地區分析")
    category_analysis.to_excel(writer, sheet_name="商品類別")
    member_analysis.to_excel(writer, sheet_name="會員分析")
    monthly_trend.to_excel(writer, sheet_name="月度趨勢")

print("📄 報告已匯出至 data/sales_report.xlsx")
```

---

## 🧪 你的挑戰

### 挑戰 1：延伸分析

以上只是基礎分析。試著加上：

1. **地區 × 商品交叉分析**：哪個地區最愛買什麼類別？
2. **顧客生命週期**：首購到末購的天數分佈
3. **折扣敏感度**：有折扣 vs 無折扣的轉換差異
4. **出貨速度與退貨的關係**：出貨慢是否導致更多退貨？

### 挑戰 2：視覺化

用 matplotlib 或 seaborn 畫出：

1. 月度營收趨勢折線圖
2. 地區營收佔比圓餅圖
3. 商品類別銷售長條圖
4. 客單價分佈直方圖
5. 地區 × 月份的熱力圖

### 挑戰 3：自動化

把整個分析流程包成函式：

```python
def generate_monthly_report(orders_path, customers_path, products_path):
    """自動產出月度分析報告"""
    # 你來寫！
    pass
```

---

## 💡 實戰心得

### 分析不是寫程式，是回答問題

```
❌ 「我用了 groupby 和 pivot_table」
✅ 「台北地區貢獻了 42% 的營收，且客單價高出平均 30%」

❌ 「我畫了一張折線圖」
✅ 「營收呈現月環比 8% 的穩定成長，行銷活動月份成長率達 15%」
```

### 好的分析報告結構

1. **摘要**：一句話說清楚最重要的發現
2. **數據**：用數字支撐你的觀點
3. **洞察**：這些數字代表什麼意義
4. **建議**：基於分析結果，建議怎麼做
5. **下一步**：還有什麼需要進一步研究的

---

## 🔑 本章重點回顧

| 步驟 | 對應章節 | 核心工具 |
|------|----------|----------|
| 讀取資料 | Ch03 | `read_csv()`, `parse_dates` |
| 資料清理 | Ch05 | `dropna()`, `fillna()`, `drop_duplicates()` |
| EDA 概覽 | Ch04 | `describe()`, `info()`, `value_counts()` |
| 篩選操作 | Ch06 | 布林索引, `query()` |
| 分組聚合 | Ch07 | `groupby()`, `agg()` |
| 交叉分析 | Ch08 | `pivot_table()`, `crosstab()` |
| 時間分析 | Ch09 | `resample()`, `rolling()` |
| 合併資料 | Ch11 | `merge()` |

---

## ⏭️ 下一章預告

> **Ch11：進階技巧與效能優化**
>
> 現在你已經能做完整的分析了。
> 下一章教你做得更快、更好、處理更大的資料。

---

[← Ch09：時間序列處理](ch09-time-series.md) | [Ch11：進階技巧與效能優化 →](ch11-advanced.md)
