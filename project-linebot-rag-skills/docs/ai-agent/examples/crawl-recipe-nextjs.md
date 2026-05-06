# 範例：抓 Next.js 官方 docs 入庫（端對端）

> 對應 [task-18](../tasks/task-18-playwright-ingestion.md)。本範例用 P0「資料準備支線」走完一遍：URL → markdown → ingest → 在 LINE / Web 問。

## 1. 安裝 + 設定

```bash
python -m pip install -e ".[dev,crawler]"
python -m playwright install chromium
```

> 第一次跑 chromium 安裝會下載 ~150MB；後續沿用。

## 2. 準備 URL 清單

`urls/nextjs.txt`（已附範例）：

```
# Next.js docs 範例 URL list
https://nextjs.org/docs/app/building-your-application/rendering
https://nextjs.org/docs/app/building-your-application/rendering/server-components
https://nextjs.org/docs/app/building-your-application/rendering/client-components
https://nextjs.org/docs/app/building-your-application/data-fetching
https://nextjs.org/docs/app/building-your-application/caching
```

註解行（`#` 開頭）會被 crawler 跳過。

## 3. 跑 crawler

```bash
python scripts/crawl_to_markdown.py \
  --urls urls/nextjs.txt \
  --out docs/RAG/crawled/nextjs \
  --category nextjs \
  --concurrency 3
```

預期 log（首次跑）：

```
INFO wrote nextjs_org__docs_app_building-your-application_rendering.md (12483 chars)
INFO wrote nextjs_org__docs_app_building-your-application_rendering_server-components.md (8231 chars)
...
INFO done: {'wrote': 5}
```

第二次跑同一份 URL list：

```
INFO unchanged, skipped: https://nextjs.org/docs/app/building-your-application/rendering
...
INFO done: {'unchanged': 5}
```

content_hash 一致 → 不重寫；改 chunk 策略不需重抓。

## 4. 人工 review（重要！）

打開幾個 `.md` 檔，確認：

- 沒有 nav / sidebar 殘渣（若有，去 `scripts/site_rules.py` 加 `remove_selectors`）
- 程式碼區塊有正確的 ` ``` ` 標記
- 標題層級合理
- frontmatter 完整，含 `source_url` / `content_hash`

範例 frontmatter：

```yaml
---
source_url: https://nextjs.org/docs/app/building-your-application/rendering
source_title: Rendering | Next.js
crawled_at: 2026-05-05T10:30:00+00:00
content_hash: 8f2c12ab34cd5678
category: nextjs
tags:
- nextjs_org
---
```

## 5. 入 Supabase / sqlite-vec

```bash
# Supabase 路徑
python scripts/ingest.py markdown \
  --paths "docs/RAG/crawled/nextjs/*.md" --category nextjs

# 或離線 sqlite-vec 路徑
KNOWLEDGE_STORE_BACKEND=sqlite_vec \
python scripts/ingest.py markdown \
  --paths "docs/RAG/crawled/nextjs/*.md" --category nextjs
```

> `MarkdownIngester` 會解析 frontmatter，把 `source_url` 寫進
> `KnowledgeChunkInsert.metadata.source_url`；frontmatter 中的 `category` 覆寫 CLI 參數。

> ⚠️ **常見坑：frontmatter `category` vs skill `rag_categories` 不對齊** → retrieval 0 hits
>
> 範例：crawler `--category nextjs` → 檔案 frontmatter 寫 `category: nextjs` → DB 內
> chunks 的 category=nextjs。但 router 路由到 `tech_architect` skill 時會傳
> `rag_categories=[engineering, architecture, code, rag]` → category filter 把 nextjs
> chunks 全濾掉 → graph 看到 0 chunks → sufficiency=insufficient（誤判）。
>
> 解法：先看 skill 的 `rag_categories`，crawler `--category` 對齊它（例如 `--category engineering`）。
> 完整討論見 [W1 e2e 驗收](./w1-e2e-verification.md) §「摩擦 1」。

驗證：

```bash
psql $SUPABASE_DB_URL -c \
    "select metadata->>'source_url' from private_knowledge where category='nextjs' limit 3;"
```

預期：3 個 `https://nextjs.org/docs/...` URL。

## 6. 在 LINE / Web 上問

LINE 傳：「Next.js Server Component 跟 Client Component 差在哪？」

預期回覆（reflection variant）含類似：

```
**Server Components** 在 server 端 render，可直接讀資料庫... [來源 1]
**Client Components** 在 browser render，可用 hooks... [來源 2]

**注意事項**：
- 以下內容依當前知識庫整理...

**來源**：
1. https://nextjs.org/docs/app/building-your-application/rendering/server-components
2. https://nextjs.org/docs/app/building-your-application/rendering/client-components
```

→ Citation 直接帶 URL，學生 / 用戶可點擊追溯來源。

## 7. 學生轉題目要動的地方

`scripts/site_rules.py` 加自己領域目標站：

```python
SITE_RULES["docs.python.org"] = {
    "main_selector": "div.body",
    "remove_selectors": ["div.related", "div.sphinxsidebar"],
    "wait_selector": "div.body",
}
```

URL list 換成自己的 sitemap，跑 crawler、ingest，graph 端零修改。

## 8. 倫理 / 邊界（task-18 內建）

- `User-Agent: linebot-rag-skills-edu-crawler/0.1` 顯示意圖
- robots.txt 自動檢查；disallow 的 URL 自動跳過並 log
- 預設 1 秒節流（`--delay`）
- 不抓需登入頁面（教學版）

> 進階：生產級 queue + worker + dead-letter retry 見 [project-playwright/ch08-supabase](../../../../project-playwright/ch08-supabase/)。
