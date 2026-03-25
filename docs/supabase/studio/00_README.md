# Head First Supabase Studio — 實戰操作手冊

> **"不要只看 Schema 設計圖——打開 Studio，自己建一次才算懂。"**

你已經讀完了觀念版的 `01_supabase-studio.md`，知道 Studio 背後是 15+ 個 Docker 容器在協作。

現在，是時候**真的動手做**了。

---

## 這份手冊和 `01_supabase-studio.md` 的差別

| | `01_supabase-studio.md` | `studio/` 目錄 |
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
```

每一份都是**獨立的實戰練習**，但建議按順序走。

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `../01_supabase-studio.md` | 觀念版（先讀這個） |
| `../labs/05_lab-docker-supabase.md` | Docker 環境設定 |
| `../e-Commerce/00_README.md` | 學完 Studio 後的實戰專案 |

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
 │  3. 跟著 studio/ 目錄做            │
 │         ↓ 一步一步操作             │
 │  4. 進入 e-Commerce 實戰           │
 │         ↓ 用學到的技能蓋真專案      │
 └─────────────────────────────────┘
```

**準備好了？打開 `01_interface-overview.md`，開始你的 Studio 巡禮。**
