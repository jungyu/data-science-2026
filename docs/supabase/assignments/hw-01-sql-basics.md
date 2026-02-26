# 作業一：基礎 SQL — 電商訂單資料庫

---

## 題目

設計一個「電商訂單資料庫」，包含以下資料表：

- `customers` — 顧客
- `products` — 商品
- `orders` — 訂單
- `order_items` — 訂單明細

---

## 要求

1. 使用 UUID 作為 Primary Key
2. 至少 2 個 Foreign Key
3. 至少 1 個 Index
4. 實作 1 個 JOIN 查詢

---

## 參考架構

```
customers
  ├── id (UUID, PK)
  ├── name (TEXT)
  ├── email (TEXT, UNIQUE)
  └── created_at (TIMESTAMP)

products
  ├── id (UUID, PK)
  ├── name (TEXT)
  ├── price (NUMERIC)
  └── category (TEXT)

orders
  ├── id (UUID, PK)
  ├── customer_id (UUID, FK → customers)
  ├── total_amount (NUMERIC)
  └── created_at (TIMESTAMP)

order_items
  ├── id (UUID, PK)
  ├── order_id (UUID, FK → orders)
  ├── product_id (UUID, FK → products)
  ├── quantity (INTEGER)
  └── subtotal (NUMERIC)
```

---

## 繳交內容

1. 完整的 `CREATE TABLE` SQL
2. 至少 5 筆測試資料的 `INSERT` SQL
3. 1 個 `CREATE INDEX` SQL 並說明理由
4. 1 個 `JOIN` 查詢並說明用途

---

## 評分標準（20 分）

| 項目 | 分數 | 說明 |
|------|------|------|
| 正確建立表 | 5 | DDL 語法正確，資料型別合理 |
| 關聯設計合理 | 5 | Foreign Key 正確，關係合理 |
| Index 使用 | 5 | Index 選擇有依據，能說明理由 |
| JOIN 查詢正確 | 5 | 查詢語法正確，結果有意義 |
