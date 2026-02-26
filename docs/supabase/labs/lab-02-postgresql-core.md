# 實驗 2：PostgreSQL 核心操作（資料科學場景）

---

## 實驗目標

1. 建立資料表
2. 設計 Index
3. 使用 JSONB
4. 練習 JOIN

---

## 2.1 建立資料表（YouTube 分析案例）

進入 SQL Editor，執行：

```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  channel TEXT,
  views INTEGER,
  likes INTEGER,
  tags TEXT[],
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 2.2 插入測試資料

```sql
INSERT INTO videos (title, channel, views, likes, tags, metadata)
VALUES
  ('AI Revolution', 'DataLab', 10000, 500, ARRAY['AI','ML'], '{"model":"gpt","score":0.95}'),
  ('SQL Tutorial', 'CodeLab', 8000, 400, ARRAY['SQL','DB'], '{"model":"none","score":0.8}'),
  ('Data Pipeline', 'DataLab', 15000, 700, ARRAY['ETL','Python'], '{"model":"bert","score":0.88}'),
  ('ML Basics', 'AI School', 12000, 600, ARRAY['ML','Tutorial'], '{"model":"sklearn","score":0.92}');
```

---

## 2.3 基本查詢

```sql
-- 查詢所有資料
SELECT * FROM videos;

-- 條件篩選
SELECT title, views FROM videos WHERE views > 10000;

-- 排序
SELECT title, views FROM videos ORDER BY views DESC;

-- 聚合
SELECT channel, AVG(views) AS avg_views
FROM videos
GROUP BY channel;
```

---

## 2.4 查詢 JSONB

```sql
-- 取出 JSONB 欄位值
SELECT title, metadata->>'model' AS model
FROM videos;

-- JSONB 條件篩選
SELECT title, metadata->>'score' AS score
FROM videos
WHERE (metadata->>'score')::NUMERIC > 0.9;
```

---

## 2.5 建立 Index

```sql
CREATE INDEX idx_videos_views ON videos(views);
```

說明：

- 若資料量達百萬筆
- 沒有 Index 查詢會明顯變慢
- 可用 `EXPLAIN ANALYZE` 觀察查詢計畫

```sql
EXPLAIN ANALYZE SELECT * FROM videos WHERE views > 10000;
```

---

## 2.6 建立第二資料表（關聯）

```sql
CREATE TABLE channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE,
  subscribers INTEGER
);

INSERT INTO channels (name, subscribers)
VALUES
  ('DataLab', 50000),
  ('CodeLab', 30000),
  ('AI School', 45000);
```

---

## 2.7 JOIN 練習

```sql
SELECT v.title, v.views, c.subscribers
FROM videos v
JOIN channels c ON v.channel = c.name;
```

進階：

```sql
-- 哪個頻道的影片平均觀看數最高？
SELECT c.name, c.subscribers, AVG(v.views) AS avg_views
FROM channels c
JOIN videos v ON c.name = v.channel
GROUP BY c.name, c.subscribers
ORDER BY avg_views DESC;
```

---

## 實驗檢核

完成以下項目打勾：

- [ ] 已建立 `videos` 資料表
- [ ] 已插入測試資料並成功查詢
- [ ] 已使用 JSONB 查詢語法
- [ ] 已建立 Index
- [ ] 已建立 `channels` 資料表
- [ ] 已完成 JOIN 查詢
