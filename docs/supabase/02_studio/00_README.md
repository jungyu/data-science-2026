# Head First Supabase Studio — 實戰操作手冊

> **"不要只看 Schema 設計圖——打開 Studio，自己建一次才算懂。"**

你已經讀完了觀念版的 `01_supabase-studio.md`，知道 Studio 背後是 15+ 個 Docker 容器在協作。

現在，是時候**真的動手做**了。

---

## 這份手冊和 `01_supabase-studio.md` 的差別

| | `01_supabase-studio.md` | `02_studio/` 目錄 |
|--|--|--|
| 定位 | 觀念導向（原理 + 架構） | 實操導向（step-by-step） |
| 適合 | 理解背後發生什麼事 | 打開瀏覽器跟著做 |
| 前置 | 讀完 `00_database-fundamentals.md` | 讀完 `01_supabase-studio.md` |
| 成果 | 知道「為什麼」 | 做出「怎麼做」 |

---

## 前置要求

- Docker 已跑起來（`supabase start` 成功）
- 瀏覽器打開 `http://localhost:54323`
- 已讀完 `01_supabase-studio.md`（了解五大模組原理）

> 還沒跑起來？先去看 `../labs/05_lab-docker-supabase.md`。

---

## 學習路線

```
01 介面總覽        ── 認識六大模組 + 快速導航
02 Schema 策略     ── 怎麼分區？public 還是自訂 schema？
03 SQL Editor 精通 ── CRUD → Index → EXPLAIN ANALYZE → Function
04 Auth & RLS      ── 認證測試 + Policy 實戰
05 API & Storage   ── 自動 API + 檔案管理
06 Migration 流程  ── 從實驗到正式的橋樑
07 Analytics       ── 跨域觀測 + Materialized View
08 運維三件套      ── pg_cron + Webhook + Vault
09 API Gateway     ── Database Function 當 API
```

01-06 是基礎操作，07-09 是進階生產能力。建議按順序走。

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `../01_supabase-studio.md` | 觀念版（先讀這個） |
| `../labs/05_lab-docker-supabase.md` | Docker 環境設定 |
| `../03_shop/00_README.md` | 學完 Studio 後的實戰專案 |

---

## 埠口速查

| 埠口 | 服務 | 你什麼時候用 |
|------|------|-------------|
| 54321 | PostgREST API | curl 測試、前端串接 |
| 54322 | PostgreSQL | psql 直連、DBeaver |
| 54323 | Studio UI | 你現在打開的畫面 |
| 54324 | Inbucket | 接收本地認證信 |

> 記不住？沒關係。`54323` 是你最常用的，其他的用到再查。

---

## 怎麼用這份手冊

```
 ┌─────────────────────────────────┐
 │  1. 讀觀念版（01_supabase-studio.md） │
 │         ↓ 知道「為什麼」            │
 │  2. 打開 Studio（localhost:54323）  │
 │         ↓ 準備好環境               │
 │  3. 跟著 02_studio/ 目錄做          │
 │         ↓ 一步一步操作             │
 │  4. 進入電商實戰（03_shop/）       │
 │         ↓ 用學到的技能蓋真專案      │
 └─────────────────────────────────┘
```

---

## 快速入門：從 0 到能動的最短路徑

在進入六章詳細實操之前，先用 10 分鐘走完一遍最小流程，確認環境能動。

### Step 1：建立專案

**雲端版**：前往 [supabase.com](https://supabase.com) → New Project → 取得 Project URL + anon key + service role key

**本地版**（建議）：`supabase init` → `supabase start` → Studio 在 `localhost:54323`

### Step 2：建立資料表（資料科學案例）

在 SQL Editor 貼上，建一個 YouTube 影片分析表：

```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  views INTEGER,
  tags TEXT[],
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 3：用 Python 連接

```python
from supabase import create_client

url = "https://xxxx.supabase.co"  # 或 http://localhost:54321
key = "anon-key"

supabase = create_client(url, key)
data = supabase.table("videos").select("*").execute()
print(data)
```

### Step 4：啟用 RLS

```sql
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own videos"
ON videos FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

### 快速入門重點

| 步驟 | 操作 | 你驗證了什麼 |
|------|------|-------------|
| 1 | 建立專案 | 環境能跑 |
| 2 | 建立資料表 | SQL Editor 能用 |
| 3 | Python 連線 | SDK 能通 |
| 4 | 啟用 RLS | 安全機制能動 |

> 這四步只是暖身。接下來的六章會帶你深入每個模組的細節。

---

**準備好了？打開 `01_interface-overview.md`，開始你的 Studio 巡禮。**
