# 教學資料集：台灣電商營運資料庫

> 模擬台灣中型電商公司的營運資料，專為 Pandas 教學設計。

---

## 資料表概覽

| 檔案 | 說明 | 筆數 | 主鍵 |
|------|------|------|------|
| orders.csv | 訂單資料（核心主表） | 100 | order_id |
| customers.csv | 顧客資料 | 25 | customer_id |
| products.csv | 商品資料 | 6 | product_id |
| campaigns.csv | 行銷活動 | 6 | campaign_id |
| returns.csv | 退貨紀錄 | 8 | return_id |
| inventory.csv | 庫存資料 | 18 | product_id + warehouse |

---

## 關聯圖

```
orders.csv ──┬── customer_id ──→ customers.csv
             ├── product_id  ──→ products.csv
             └── order_id    ←── returns.csv

products.csv ── product_id ──→ inventory.csv
campaigns.csv（獨立，透過日期範圍與 orders 關聯）
```

---

## 刻意設計的資料品質問題

本資料集**刻意**包含以下問題，供學生練習資料清理：

### orders.csv
- **缺失值**：部分 `shipping_days` 為空、一筆 `region` 為空
- **可疑商品**：O1082 的 product_id 為 P502（不存在於 products 表）
- **折扣範圍**：正常為 0~0.25

### customers.csv
- **缺失值**：一位顧客的 `age` 為空
- **空白值**：一位顧客的 `gender` 為空白（非 NaN）
- **可清理項目**：gender 欄位有 M/F，可以轉成中文

### 其他表
- campaigns.csv 和 returns.csv 是乾淨的
- inventory.csv 是乾淨的

---

## 教學對應

| 週次 | 使用的表 | 練習重點 |
|------|----------|----------|
| 3-4 | orders | 讀取、EDA |
| 5-6 | orders, customers | 清理、篩選 |
| 7-8 | orders | GroupBy、Pivot |
| 9 | 全部 | 期中專案 |
| 10 | orders + customers + products | merge 合併 |
| 11-12 | orders | 時間序列 |
| 13-15 | 全部 | 視覺化 |
| 16-18 | 全部 | 期末專案 |
