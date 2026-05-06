# Spec-18：Playwright 資料收集（P0 前置 / P5 選修）

## 背景

現有 `scripts/ingest_markdown.py` 假設 markdown 檔案已存在，假設知識庫資料已備好。但學生轉題目時面對的真實問題是：「**資料從哪裡來？**」最常見來源是網頁——技術文件、官方教學、blog、wiki 等。

本 spec 加入一條 **Playwright 資料收集支線**，補完從「URL → markdown → Supabase」的完整 ingestion pipeline。設計刻意保持簡單（單 process、URL list 驅動），讓學生看清資料流；若需生產級的 queue + worker + dedup，**指向 [project-playwright/ch08-supabase](../../../../project-playwright/ch08-supabase/)** 作為進階版本。

> 借鑑：[project-playwright/ch05-data-extraction](../../../../project-playwright/ch05-data-extraction/)（內容抽取）、[ch08-supabase](../../../../project-playwright/ch08-supabase/)（lease-based queue、content_hash 去重——本 spec 簡化為單檔 hash）。

## 設計

### 資料流（兩階段解耦）

```
[urls.txt]                 # 學生維護的 URL 清單
     ↓
[crawl_to_markdown.py]     # Playwright 抓頁 → 抽取內容 → 寫 markdown 檔
     ↓
docs/RAG/crawled/*.md      # 帶 frontmatter 的 markdown
     ↓ （人工 review）
[ingest_markdown.py]       # 既有腳本，加強支援 frontmatter
     ↓
Supabase private_knowledge # pgvector + tsvector
```

兩層解耦的理由：

1. **crawl 一次，ingest 多次**：改 chunk 策略不需重抓
2. **人工可介入**：抓下來的 markdown 可手動修剪雜訊（廣告、導航）再入庫
3. **失敗隔離**：抓站失敗不影響既有 markdown 入庫

### Markdown 檔格式（含 frontmatter）

```markdown
---
source_url: https://nextjs.org/docs/app/building-your-application/rendering
source_title: Rendering | Next.js
crawled_at: 2026-05-05T10:30:00Z
content_hash: 8f2c...   # 從原始 HTML 算出，用於 ingest 端去重
category: nextjs
tags: [rendering, ssr, app-router]
---

# Rendering

Next.js offers...
```

frontmatter 由 crawler 自動產生；`category` 與 `tags` 可由 URL→category 的 mapping 決定（學生自訂）。

### Crawler 架構（教學版簡化）

| 元素 | 教學版（本 spec）| 進階版（project-playwright/ch08）|
|---|---|---|
| 任務來源 | `urls.txt` 純文字檔 | `crawler.crawl_queue` table |
| 並行 | `asyncio.gather` 控制併發數 | `lease_next_crawl_job()` 多 worker |
| 去重 | URL 對應檔名 + content_hash 比對 | partial unique index + content_hash |
| 失敗處理 | log + 跳過 | retry_count + dead-letter |
| 寫入位置 | 本機 `docs/RAG/crawled/*.md` | Supabase `crawler.pages` table |

學生先學會教學版，要做生產系統再讀 ch08。**不在本專案複製 ch08 的 queue 架構**——那會稀釋 graph 教學的主線。

### 內容抽取策略

預設用 `playwright` 取 HTML → `readability-lxml` 抽 main content → `markdownify` 轉 markdown：

```
HTML → readability（去除 nav/footer/ads）→ markdownify → 後處理（移除空連結、合併段落）
```

支援領域特化的 selector 覆寫（學生轉題目時主要替換點）：

```python
SITE_RULES = {
    "nextjs.org": {
        "main_selector": "main article",
        "remove_selectors": [".sidebar", "nav.docs-nav"],
    },
    # 學生新增自己領域的站
}
```

### 與既有 ingest_markdown.py 的整合

**最小修改**：讓 `ingest_markdown.py` 支援讀 frontmatter，把 `source_url`、`crawled_at` 寫進 `private_knowledge.metadata`。

frontmatter 不存在時行為不變（向後相容）。

不需動 Supabase schema——`private_knowledge.metadata` 是 jsonb，自由欄位。

### Crawler 倫理 / 邊界

教學內建以下檢查（學生轉題目時必須遵守）：

- 預設 `User-Agent: linebot-rag-skills-edu-crawler/0.1`
- 預設 `request_delay_seconds=1.0`（節流）
- robots.txt 檢查（用 `urllib.robotparser`）
- 跳過 robots disallow 的 URL，**並 log 顯示**
- 不抓需要登入的頁面（簡化教學；進階版可用 ch07 testing 的登入 fixture）

## 介面契約

**新增**：`scripts/crawl_to_markdown.py`

```bash
# 用法
python scripts/crawl_to_markdown.py \
  --urls urls.txt \
  --out docs/RAG/crawled \
  --category nextjs \
  --concurrency 3
```

**新增**：`scripts/site_rules.py`（site-specific selector 覆寫表）

**修改**：`scripts/ingest_markdown.py`

- 加 `parse_frontmatter()`：若檔頭有 `---`，解析 yaml，把 `source_url` / `crawled_at` 等欄位寫入 `metadata`
- frontmatter 中的 `category` / `tags` 覆寫 CLI 參數（讓 crawler 決定分類，CLI 參數退為 fallback）

**新增 dependency**：

```toml
"playwright>=1.40",
"markdownify>=0.11",
"readability-lxml>=0.8",
"pyyaml>=6.0",
```

playwright browser 安裝：

```bash
python -m playwright install chromium
```

**新增範例**：`docs/ai-agent/examples/crawl-recipe-nextjs.md`

完整走過一個案例：Next.js 官方 docs 的 50 個 URL → crawl → review → ingest → 用 LINE 問 RAG 命中。

## 驗收標準

- 給一個 `urls.txt` 含 5 個合法 URL → 跑完產出 5 份 markdown 檔，frontmatter 完整
- robots.txt disallow 的 URL **不抓**且 log 明示「skipped by robots.txt」
- 同一個 URL 跑第二次：若 content_hash 未變，跳過寫入並 log「unchanged, skipped」
- markdown 經 `ingest_markdown.py` 入庫後，`private_knowledge.metadata` 包含 `source_url`
- 用 LINE 問該知識庫涵蓋的問題，graph retriever 能命中對應 chunk，且回覆 citations 帶 source URL（搭配 task-16 的 `Citation.source` 欄位）
