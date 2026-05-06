# Ch 01：爬網頁 → Markdown

> 核心檔案：[`scripts/site_rules.py`](../../scripts/site_rules.py)、
> [`app/ingest/ingesters/web.py`](../../app/ingest/ingesters/web.py)

---

## 開始之前：安裝 crawler 相依套件

Playwright 和 html-to-markdown 的相依套件不在預設安裝裡，需要手動加上 `crawler` extra：

```bash
# 在專案根目錄執行
pip install -e ".[dev,crawler]"

# 第一次用 Playwright 還要安裝 browser binary
playwright install chromium
```

確認安裝成功：

```bash
python -c "from playwright.sync_api import sync_playwright; print('ok')"
# 輸出 ok → 安裝正確
```

> ⚠️ 如果看到 `ModuleNotFoundError: No module named 'playwright'`，
> 代表只執行了 `pip install -e "."` 沒有帶 `[dev,crawler]`，重跑上面的指令即可。

---

## 1-1  為什麼用 Playwright 而不是 requests？

現代網站大量使用 JavaScript 渲染內容。

```
requests.get("https://nextjs.org/docs/app")
→ 拿到空的 HTML 殼，內容還沒渲染

Playwright（headless Chrome）
→ 等 JS 執行完，拿到完整的 DOM
```

[`app/ingest/ingesters/web.py` 第 107–124 行](../../app/ingest/ingesters/web.py)：

```python
async def fetch_html(browser, url, *, wait_selector):
    context = await browser.new_context(user_agent=USER_AGENT)
    page    = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    if wait_selector:
        await page.wait_for_selector(wait_selector, timeout=15_000)  # 等動態內容
    html  = await page.content()   # 完整 DOM
    title = await page.title()
    return html, title
```

---

## 1-2  `site_rules.py`：告訴爬蟲要拿哪一塊

原始 HTML 包含 nav、sidebar、footer——這些對 RAG 毫無價值。
[`scripts/site_rules.py`](../../scripts/site_rules.py) 讓你為每個網站定義 CSS selector：

```python
# scripts/site_rules.py 第 23–36 行（現有的兩個範例）
SITE_RULES: dict[str, dict] = {
    "nextjs.org": {
        "main_selector":    "main article",                      # 只拿這個 DOM 節點
        "remove_selectors": ["nav", ".sidebar", "[class*='Toc']"],  # 移除這些
        "wait_selector":    "main article",                      # 等這個出現才截取
    },
    "react.dev": {
        "main_selector":    "article",
        "remove_selectors": ["nav", "[class*='Toc']"],
        "wait_selector":    "article",
    },
}
```

**加你自己的站**，在最後面新增：

```python
SITE_RULES: dict[str, dict] = {
    "nextjs.org": { ... },
    "react.dev":  { ... },

    # ↓ 加在這裡
    "docs.python.org": {
        "main_selector":    "div.body",
        "remove_selectors": ["div.sphinxsidebar", "div.related"],
        "wait_selector":    "div.body",
    },
    "tw.mofa.gov.tw": {
        "main_selector":    "div#content",
        "remove_selectors": ["header", "footer", "nav"],
        "wait_selector":    None,   # 靜態頁面，不需要等
    },
}
```

**怎麼找 selector**：在 Chrome 開 DevTools，右鍵目標文章區塊 → Inspect，
找出包住主要內容的 CSS class 或 ID。

---

## 1-3  `html_to_markdown`：HTML → 乾淨的 Markdown

[`app/ingest/ingesters/web.py` 第 72–101 行](../../app/ingest/ingesters/web.py)：

```python
def html_to_markdown(html: str, *, rule: dict) -> str:
    # 優先用 site rule 的 CSS selector 抽主內容
    if rule.get("main_selector"):
        nodes = tree.cssselect(rule["main_selector"])
        if nodes:
            return markdownify(main_html, heading_style="ATX").strip()

    # 沒有 selector 就用 readability 自動推斷主內容
    doc = ReadabilityDocument(html)
    return markdownify(doc.summary(), heading_style="ATX").strip()
```

轉換後的效果：

```
原始 HTML：
<h1>App Router</h1>
<p>Next.js 14 引入了 <strong>App Router</strong>，基於 <em>React Server Components</em>。</p>
<nav>首頁 | 文件 | API</nav>  ← 被 remove_selectors 移除

→ Markdown：
# App Router

Next.js 14 引入了 **App Router**，基於 *React Server Components*。
```

---

## 1-4  兩階段模式 vs 一步到位

專案提供兩種爬取方式：

**方式 A：兩階段（教學用，先看到 Markdown 再決定要不要入庫）**

```bash
# 第一步：爬 → 存成 .md 檔案
python scripts/crawl_to_markdown.py \
  --urls https://nextjs.org/docs/app \
         https://nextjs.org/docs/app/building-your-application/routing \
  --out  docs/RAG/crawled/nextjs/ \
  --category nextjs

# 第一步完成後，先打開 docs/RAG/crawled/nextjs/ 看內容對不對
# 確認無誤後才做第二步

# 第二步：.md 檔 → embed → Supabase
python scripts/ingest.py \
  --source docs/RAG/crawled/nextjs/ \
  --type   markdown \
  --category nextjs
```

**方式 B：一步到位（熟悉後用這個）**

```python
# 用 WebIngester 直接進 IngestionPipeline（Ch 03 會示範）
from app.ingest.ingesters.web import WebIngester
ingester = WebIngester(
    urls=["https://nextjs.org/docs/app"],
    category="nextjs",
    get_rule=rule_for,   # 套用 site_rules.py
)
# 直接進 pipeline，不產生中介檔案
```

> 💡 **新手建議先用方式 A**
>
> 看到 Markdown 檔案可以確認爬蟲有沒有抓到正確內容，
> 避免爛資料默默入庫。確認沒問題再改用方式 B 提高效率。

---

## 1-5  robots.txt：爬蟲禮儀

[`app/ingest/ingesters/web.py` 第 54–69 行](../../app/ingest/ingesters/web.py) 有 `is_allowed_by_robots()`，
`WebIngester` 預設 `respect_robots=True`，會自動跳過禁止爬的頁面。

```python
# 如果你確定這個站允許爬（或是自己的站），可以關掉
WebIngester(urls=[...], category="...", respect_robots=False)
```

---

## ✏️ 本章任務

1. 選你領域的一個網站，在 `scripts/site_rules.py` 新增它的規則
2. 用方式 A 爬 2–3 個頁面，打開 `.md` 檔確認內容乾淨
3. 如果內容有多餘的 nav/sidebar，調整 `remove_selectors` 直到乾淨為止

下一章 → [Ch 02：Document 格式 + Chunking](ch02-document-chunking.md)
