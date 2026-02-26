# 第一章：資料科學為什麼需要 PostgreSQL？

---

## 1.1 為什麼不能只用 CSV / Pandas？

資料科學學生常見狀況：

- 資料存在 CSV
- 用 Pandas 處理
- 做完分析
- 專案結束

問題：

- 無版本管理
- 無多人協作
- 無權限控管
- 無持久化資料模型
- 無 API 供應

真實世界的資料科學一定接資料庫。

---

## 1.2 什麼是 PostgreSQL？

![PostgreSQL Logo](https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Postgresql_elephant.svg/960px-Postgresql_elephant.svg.png)

![PostgreSQL 生態系](https://media.licdn.com/dms/image/v2/D5612AQGU4nNCHYETDg/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1673532136828?e=2147483647&t=e_9QB5to6LNSUUaGSYArRh2YyLEQsh63GXX29fibqSY&v=beta)

![ER Diagram 範例](https://www.datensen.com/images/postgresql-er-diagram.jpg)

![ER Diagram 設計](https://dbschema.com/blog/postgresql/create-er-diagrams/er-diagram-postgres.png)

### PostgreSQL 是：

- 開源關聯式資料庫
- 強型別
- ACID 交易
- 支援 JSONB
- 支援 Index、View、Trigger、Function
- 支援複雜分析查詢

---

## 1.3 PostgreSQL 核心概念（資料科學一定要懂）

### (A) Table — 資料表

```sql
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  name TEXT,
  score NUMERIC,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### (B) Index — 索引

為什麼資料科學需要 Index？

- 大數據查詢加速
- `GROUP BY` / `WHERE` 加速

```sql
CREATE INDEX idx_students_score ON students(score);
```

### (C) JOIN — 資料關聯能力

資料科學常見：多資料表整合

```sql
SELECT s.name, c.course_name
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN courses c ON e.course_id = c.id;
```

### (D) JSONB — 為什麼它對資料科學很重要

PostgreSQL 可以：

- 存半結構資料
- 存模型輸出
- 存 AI metadata

```sql
CREATE TABLE predictions (
  id SERIAL,
  model_output JSONB
);
```

這讓 PostgreSQL 同時兼具 NoSQL 能力。

---

## 本章重點回顧

| 概念 | 說明 | 資料科學應用 |
|------|------|-------------|
| Table | 結構化資料儲存 | 取代 CSV |
| Index | 查詢加速 | 大資料場景 |
| JOIN | 多表關聯 | 資料整合 |
| JSONB | 半結構資料 | 模型輸出、AI metadata |
