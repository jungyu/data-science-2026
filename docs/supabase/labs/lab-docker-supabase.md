# Docker + Supabase 完整實驗講義

課程單元：Week 7–8
主題：建立可重現的資料科學後端開發環境

---

## 一、為什麼不用雲端版直接操作？

### 傳統教學問題

- 學生直接用 Supabase Cloud
- 改壞 DB 無法回復
- 結構無法版控
- 無 Migration
- 無 CI/CD

這樣學生學不到「系統」。

### 本單元核心

> 學會本地化
> 學會 Migration
> 學會版本控制
> 學會可重現環境

---

## 二、Docker 基礎

### 2.1 什麼是 Docker？

![Docker 運作原理](https://assets.bytebytego.com/diagrams/0414-how-does-docker-work.png)

![容器 vs 虛擬機](https://www.researchgate.net/publication/369061128/figure/fig2/AS%3A11431281125201275%401678232029210/Docker-Container-vs-Virtual-Machine.png)

![Docker Desktop](https://www.docker.com/app/uploads/2025/05/DD-hiroko.png)

![Docker Dashboard](https://www.docker.com/app/uploads/2022/06/Screen-Shot-2022-06-02-at-9.22.51-AM-1-1110x668.png)

Docker 是：

- 容器技術
- 可重現環境
- 隔離依賴
- 可跨機器部署

資料科學最大問題之一：

> 環境無法重現

Docker 解決這件事。

---

## 三、安裝需求

### 3.1 安裝 Docker Desktop

確認版本：

```bash
docker --version
```

應看到：

```
Docker version 24.x.x
```

### 3.2 安裝 Supabase CLI

Node 環境必須已安裝。

```bash
npm install -g supabase
```

確認：

```bash
supabase --version
```

---

## 四、初始化專案

### 4.1 建立專案資料夾

```bash
mkdir ds-supabase-lab
cd ds-supabase-lab
```

### 4.2 初始化 Supabase

```bash
supabase init
```

產生結構：

```
supabase/
  ├── config.toml
  ├── migrations/
  └── seed.sql
```

---

## 五、啟動本地 Supabase

```bash
supabase start
```

Docker 會建立：

- PostgreSQL
- Auth
- Realtime
- Storage
- Supabase Studio

### 5.1 本地服務資訊

PostgreSQL：

```
Host: localhost
Port: 54322
User: postgres
Password: postgres
```

Studio：

```
http://localhost:54323
```

---

## 六、資料庫操作（本地 PostgreSQL）

### 6.1 建立第一個 Migration

```bash
supabase migration new create_videos_table
```

產生：

```
supabase/migrations/xxxx_create_videos_table.sql
```

### 6.2 撰寫 Migration

編輯產生的 SQL 檔案：

```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  views INTEGER,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 6.3 套用 Migration

```bash
supabase db reset
```

這會：

- 重建 DB
- 套用所有 Migrations
- 執行 seed.sql

這是專業開發流程。

---

## 七、版本控制

將專案加入 Git：

```bash
git init
git add .
git commit -m "Initial supabase project"
```

此時：

> 資料庫結構已可版控

這是傳統資料科學課做不到的。

---

## 八、Python 連接本地 Supabase

### 8.1 安裝套件

```bash
pip install supabase
```

### 8.2 取得本地 API Key

啟動 `supabase start` 後，終端機會顯示：

```
API URL: http://localhost:54321
anon key: eyJhbGci...
service_role key: eyJhbGci...
```

也可執行：

```bash
supabase status
```

### 8.3 Python 連線

```python
from supabase import create_client

url = "http://localhost:54321"
key = "YOUR_LOCAL_ANON_KEY"

supabase = create_client(url, key)

supabase.table("videos").insert({
    "title": "Docker Test",
    "views": 100
}).execute()

response = supabase.table("videos").select("*").execute()
print(response.data)
```

---

## 九、RLS 本地測試

### 9.1 建立新的 Migration

```bash
supabase migration new add_rls_to_videos
```

### 9.2 撰寫 RLS Migration

```sql
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow read"
ON videos
FOR SELECT
USING (true);
```

### 9.3 套用

```bash
supabase db reset
```

---

## 十、Seed 資料

編輯 `supabase/seed.sql`：

```sql
INSERT INTO videos (title, views)
VALUES
  ('Seed Video 1', 500),
  ('Seed Video 2', 1200),
  ('Seed Video 3', 8000);
```

然後：

```bash
supabase db reset
```

這會：

- 重建 DB
- 自動插入 Seed 資料

---

## 十一、雲端部署流程

### 11.1 登入

```bash
supabase login
```

### 11.2 連接專案

```bash
supabase link --project-ref your-project-id
```

### 11.3 部署 Migration

```bash
supabase db push
```

這樣：

> 本地 → 雲端同步完成

---

## 十二、CI/CD 思維

學生應理解：

- DB 結構是程式碼
- Migration 是版本歷史
- `db reset` 是測試工具
- Docker 是環境保障

---

## 十三、常見錯誤排除

### Docker port 被佔用

```bash
docker ps
docker stop <container-id>
```

### 重置失敗

```bash
supabase stop
supabase start
```

### Migration 語法錯誤

```bash
# 查看錯誤訊息
supabase db reset 2>&1
# 修正 migration SQL 後重新 reset
```

### 無法連線本地 Supabase

確認 Docker 正在執行：

```bash
docker ps | grep supabase
```

---

## 十四、期末要求（Docker 版）

期末專題必須：

- 使用 Docker 本地開發
- 使用 Migration
- 使用 RLS
- 使用 JSONB
- 提交完整 repo

---

## 十五、本單元核心收穫

| 能力 | 重要性 |
|------|--------|
| Docker | 極重要 — 環境可重現 |
| DB Migration | 極重要 — 結構可版控 |
| 版本控制 | 極重要 — 團隊協作基礎 |
| 本地可重現 | 極重要 — 不依賴網路 |
| 不依賴 SaaS | 極重要 — 可遷移、可維運 |

---

## 實驗檢核

完成以下項目打勾：

- [ ] 已安裝 Docker Desktop
- [ ] 已安裝 Supabase CLI
- [ ] 已初始化 Supabase 專案
- [ ] 已啟動本地 Supabase
- [ ] 已建立第一個 Migration
- [ ] 已成功 `supabase db reset`
- [ ] 已將專案加入 Git
- [ ] 已使用 Python 連接本地 Supabase
- [ ] 已設定 Seed 資料
