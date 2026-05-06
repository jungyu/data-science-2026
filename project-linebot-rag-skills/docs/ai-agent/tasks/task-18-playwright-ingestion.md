# task-18：Playwright 資料收集

> 規格詳見 [spec-18](../specs/spec-18-playwright-ingestion.md)

---

實作 Playwright crawler + 強化 `ingest_markdown.py` 認 frontmatter。最終學生能用一行指令把網頁變 markdown，再用一行指令入 Supabase。

> 實作前**先讀** [project-playwright/ch05-data-extraction](../../../../project-playwright/ch05-data-extraction/) 與 [ch08-supabase](../../../../project-playwright/ch08-supabase/)，本 task 是其簡化教學版。

## 前置

- pyproject.toml 加入：
  ```toml
  "playwright>=1.40",
  "markdownify>=0.11",
  "readability-lxml>=0.8",
  "pyyaml>=6.0",
  ```
- 安裝瀏覽器：
  ```bash
  python -m pip install -e ".[dev]"
  python -m playwright install chromium
  ```

## 步驟 1：site_rules

新增 `scripts/site_rules.py`：

```python
"""領域特化的內容抽取規則。學生轉題目時把自己的站加進來。"""

from __future__ import annotations

from urllib.parse import urlparse


DEFAULT_RULE = {
    "main_selector": None,             # None = 用 readability 自動推
    "remove_selectors": [],
    "wait_selector": None,             # 等這個 selector 出現才視為載完
}


SITE_RULES: dict[str, dict] = {
    "nextjs.org": {
        "main_selector": "main article",
        "remove_selectors": ["nav", ".sidebar", "[class*='Toc']"],
        "wait_selector": "main article",
    },
    # 範例：學生新增自己的站
    # "your-domain.com": {...},
}


def rule_for(url: str) -> dict:
    host = urlparse(url).netloc.replace("www.", "")
    return {**DEFAULT_RULE, **SITE_RULES.get(host, {})}
```

## 步驟 2：crawler

新增 `scripts/crawl_to_markdown.py`：

```python
"""Playwright crawler：URL list → markdown 檔（含 frontmatter）。

用法：
    python scripts/crawl_to_markdown.py \
      --urls urls.txt --out docs/RAG/crawled \
      --category nextjs --concurrency 3
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import yaml
from markdownify import markdownify
from playwright.async_api import async_playwright
from readability import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.site_rules import rule_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("crawler")

USER_AGENT = "linebot-rag-skills-edu-crawler/0.1 (+contact: edu@example.com)"
REQUEST_DELAY = 1.0


async def fetch_html(browser, url: str, *, wait_selector: str | None) -> tuple[str, str]:
    """回傳 (html, page_title)。"""
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=15_000)
        html = await page.content()
        title = await page.title()
        return html, title
    finally:
        await context.close()


def html_to_markdown(html: str, *, rule: dict) -> str:
    if rule.get("main_selector"):
        # readability 仍是備援；先試 selector，失敗才整篇
        from lxml import html as lxml_html
        tree = lxml_html.fromstring(html)
        # 移除指定 selector
        for sel in rule.get("remove_selectors", []):
            for el in tree.cssselect(sel):
                el.getparent().remove(el)
        nodes = tree.cssselect(rule["main_selector"])
        if nodes:
            main_html = "".join(lxml_html.tostring(n, encoding="unicode") for n in nodes)
            return markdownify(main_html, heading_style="ATX")

    # fallback: readability
    doc = Document(html)
    return markdownify(doc.summary(), heading_style="ATX")


def make_frontmatter(*, url: str, title: str, category: str, content_hash: str) -> str:
    fm = {
        "source_url": url,
        "source_title": title,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "category": category,
        "tags": [urlparse(url).netloc.replace("www.", "")],
    }
    return "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n"


def url_to_filename(url: str) -> str:
    """URL → 安全檔名。同 path 結構保持可讀。"""
    parsed = urlparse(url)
    safe_path = parsed.path.strip("/").replace("/", "_") or "index"
    host = parsed.netloc.replace("www.", "").replace(".", "_")
    return f"{host}__{safe_path}.md"[:200]


async def is_allowed(url: str, *, rp_cache: dict) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in rp_cache:
        rp = robotparser.RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            logger.warning("robots.txt fetch failed for %s, allowing by default", base)
            rp = None
        rp_cache[base] = rp
    rp = rp_cache[base]
    return rp.can_fetch(USER_AGENT, url) if rp else True


async def crawl_one(
    browser, url: str, *, out_dir: Path, category: str, rp_cache: dict, lock: asyncio.Lock
) -> str:
    if not await is_allowed(url, rp_cache=rp_cache):
        logger.info("skipped by robots.txt: %s", url)
        return "skipped_robots"

    rule = rule_for(url)
    try:
        html, title = await fetch_html(browser, url, wait_selector=rule.get("wait_selector"))
    except Exception as e:
        logger.error("fetch failed %s: %s", url, e)
        return "failed"

    content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
    out_path = out_dir / url_to_filename(url)

    # 去重：相同 hash 跳過
    if out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        if content_hash in existing.split("---\n", 2)[1]:
            logger.info("unchanged, skipped: %s", url)
            return "unchanged"

    md = html_to_markdown(html, rule=rule)
    fm = make_frontmatter(url=url, title=title, category=category, content_hash=content_hash)
    async with lock:
        out_path.write_text(fm + md, encoding="utf-8")
    logger.info("wrote %s (%d chars)", out_path.name, len(md))
    await asyncio.sleep(REQUEST_DELAY)
    return "wrote"


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True, help="URL list 檔，每行一個")
    p.add_argument("--out", required=True, help="輸出 markdown 目錄")
    p.add_argument("--category", required=True, help="分類，會寫入 frontmatter")
    p.add_argument("--concurrency", type=int, default=3)
    args = p.parse_args()

    urls = [
        u.strip() for u in Path(args.urls).read_text(encoding="utf-8").splitlines()
        if u.strip() and not u.startswith("#")
    ]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    rp_cache: dict = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            async def bounded(u: str):
                async with sem:
                    return await crawl_one(
                        browser, u, out_dir=out_dir, category=args.category,
                        rp_cache=rp_cache, lock=lock,
                    )
            results = await asyncio.gather(*[bounded(u) for u in urls], return_exceptions=False)
        finally:
            await browser.close()

    summary = {k: results.count(k) for k in set(results)}
    logger.info("done: %s", summary)


if __name__ == "__main__":
    asyncio.run(main())
```

## 步驟 3：強化 ingest_markdown.py 認 frontmatter

修改 `scripts/ingest_markdown.py`：

```python
import yaml

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """回傳 (frontmatter dict, body)。沒有 frontmatter 時 dict 為空。"""
    if not text.startswith("---\n"):
        return {}, text
    try:
        _, fm_raw, body = text.split("---\n", 2)
        return yaml.safe_load(fm_raw) or {}, body
    except ValueError:
        return {}, text
```

改寫 `ingest_path()`：

```python
async def ingest_path(path: Path, *, category: str) -> int:
    settings = get_settings()
    client = SupabaseRestClient(settings)
    embedder = OpenAICompatibleEmbedder(settings)

    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)

    # frontmatter 優先於 CLI category
    effective_category = fm.get("category") or category
    tags_from_fm = fm.get("tags") or [path.stem]

    rows = []
    for index, chunk in enumerate(chunk_markdown(body), start=1):
        embedding = await embedder.embed_query(chunk)
        content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        metadata = {
            "path": str(path),
            "chunk_index": index,
            **({"source_url": fm["source_url"]} if "source_url" in fm else {}),
            **({"source_title": fm["source_title"]} if "source_title" in fm else {}),
            **({"crawled_at": fm["crawled_at"]} if "crawled_at" in fm else {}),
        }
        rows.append({
            "source_id": fm.get("source_url") or str(path),
            "source_type": "web" if "source_url" in fm else "markdown",
            "title": fm.get("source_title") or f"{path.stem} #{index}",
            "content": chunk,
            "content_hash": content_hash,
            "category": effective_category,
            "tags": tags_from_fm,
            "metadata": metadata,
            "embedding": embedding,
        })
    await client.upsert("private_knowledge", rows, on_conflict="content_hash")
    return len(rows)
```

`source_type="web"` 是新增的型別值，後續可在 retriever log / Citation.source 區分來源。

## 步驟 4：教學配套範例

新增 `docs/ai-agent/examples/crawl-recipe-nextjs.md`：

```markdown
# 範例：抓 Next.js 官方 docs 入庫

## 1. 準備 URL 清單

`urls/nextjs.txt`：

    https://nextjs.org/docs/app/building-your-application/rendering
    https://nextjs.org/docs/app/building-your-application/rendering/server-components
    https://nextjs.org/docs/app/building-your-application/rendering/client-components
    # ... 共 50 行

## 2. 跑 crawler

    python scripts/crawl_to_markdown.py \
      --urls urls/nextjs.txt \
      --out docs/RAG/crawled/nextjs \
      --category nextjs \
      --concurrency 3

預期 log：

    INFO wrote nextjs_org__docs_app_building-your-application_rendering.md (12483 chars)
    INFO unchanged, skipped: ...
    INFO done: {'wrote': 47, 'unchanged': 2, 'skipped_robots': 1}

## 3. 人工 review（重要！）

打開幾個 markdown 檔，確認：
- 沒有 nav / sidebar 殘渣（若有，去 site_rules.py 加 remove_selectors）
- 程式碼區塊有正確的 ``` 標記
- 標題層級合理

## 4. 入 Supabase

    python scripts/ingest_markdown.py \
      docs/RAG/crawled/nextjs/*.md \
      --category nextjs

frontmatter 中的 category 會覆寫 CLI 參數，但 CLI 留作 fallback。

> ⚠️ **frontmatter category vs skill rag_categories 衝突**（[W1 e2e 驗收](../examples/w1-e2e-verification.md) §「摩擦 1」）
>
> Crawler 預設把 frontmatter `category` 寫成 `nextjs`（`--category` CLI 值）；
> 但 router 路由到 `tech_architect` skill 時會傳 `rag_categories=[engineering, architecture, code, rag]`
> 給 retriever，retriever 用 category filter 過濾 chunks → **0 hits（即使內容語意相關）**。
>
> 三種解法（學生選一）：
>
> | 解法 | 動作 | trade-off |
> |------|------|-----------|
> | A | crawler `--category engineering`（與 skill 對齊）| 一次設定 |
> | B | 抓完手動把 frontmatter 的 `category: nextjs` 改成 `category: engineering` | 適合事後修正 |
> | C | 改 skill 的 `rag_categories` 加上 `nextjs` | 對單一 skill 適用，多 skill 不易維護 |
>
> 建議：T1 換領域時 **先檢查目標 skill 的 `rag_categories`**，crawler `--category` 對齊它。

## 5. 在 LINE 上驗證

傳「Next.js Server Component 跟 Client Component 差在哪？」

預期：
- log 顯示 sufficiency=sufficient（task-15）
- 回覆有 [來源 1] [來源 2] 標記（task-16）
- citations 中可看到 source_url 指向 nextjs.org
```

## 步驟 5：把 graph 的 Citation 帶上 URL（小改）

修改 `app/generator/contract.py::AnswerContractBuilder._citations`：

```python
def _citations(self, chunks: list[KnowledgeChunk]) -> list[Citation]:
    out = []
    for c in chunks:
        meta = getattr(c, "metadata", {}) or {}
        source = meta.get("source_url") or getattr(c, "source", "knowledge_base")
        out.append(Citation(
            chunk_id=c.id,
            source=source,
            snippet=c.content[:200],
        ))
    return out
```

讓抓網頁的 chunks 在輸出時帶上原始 URL，學生可以追溯。

## 步驟 6：測試

`tests/test_crawl_to_markdown.py`（用 playwright 的 page mock 或 local fixture HTML）：

```python
def test_html_to_markdown_strips_nav():
    html = '<html><nav>nav</nav><main><article><h1>Title</h1><p>body</p></article></main></html>'
    out = html_to_markdown(html, rule={"main_selector": "main article", "remove_selectors": ["nav"]})
    assert "nav" not in out.lower()
    assert "Title" in out


def test_url_to_filename():
    assert url_to_filename("https://nextjs.org/docs/app/rendering") == "nextjs_org__docs_app_rendering.md"
```

`tests/test_ingest_frontmatter.py`：

```python
def test_parse_frontmatter():
    text = "---\nsource_url: https://example.com\ncategory: x\n---\n\n# Body"
    fm, body = parse_frontmatter(text)
    assert fm["source_url"] == "https://example.com"
    assert body.strip().startswith("# Body")


def test_no_frontmatter():
    fm, body = parse_frontmatter("# Just a heading")
    assert fm == {}
    assert "Just a heading" in body
```

## 請輸出

1. `scripts/crawl_to_markdown.py`
2. `scripts/site_rules.py`
3. 修改後的 `scripts/ingest_markdown.py`（支援 frontmatter）
4. 修改後的 `app/generator/contract.py`（Citation 帶 URL）
5. 修改後的 `pyproject.toml`（加 4 個 dependency）
6. `docs/ai-agent/examples/crawl-recipe-nextjs.md`
7. `tests/test_crawl_to_markdown.py`、`tests/test_ingest_frontmatter.py`
8. `urls/nextjs.txt` 範例 URL 清單（50 個官方 docs URL）
9. README 加「資料準備：用 Playwright 抓網頁」段，連向 [project-playwright](../../../../project-playwright/) 作為進階教材

## 驗收指令

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium

# 跑 crawler
python scripts/crawl_to_markdown.py \
  --urls urls/nextjs.txt --out docs/RAG/crawled/nextjs \
  --category nextjs --concurrency 3
# 預期：
# - 產出 ~47 份 markdown
# - log 中至少有 1 個 "skipped by robots.txt" 或 "unchanged, skipped"

# 第二次跑同一份 urls.txt
# 預期：絕大多數 "unchanged, skipped"

# 入庫
python scripts/ingest_markdown.py docs/RAG/crawled/nextjs/*.md --category nextjs
# 預期：metadata.source_url 寫入 Supabase

# Supabase 端驗證
psql $SUPABASE_DB_URL -c "select metadata->>'source_url' from private_knowledge where category='nextjs' limit 3;"
# 預期：3 個 https://nextjs.org/... URL

# 端對端：LINE 上問
# 預期：回覆含 [來源 1]，citations 中 source 是 https://nextjs.org/... 而非 "knowledge_base"
```

驗收通過條件：

- robots.txt 真正會擋掉 disallow 的 URL（log 看得到）
- 同一份 urls.txt 跑第二次幾乎全部 unchanged（content_hash 去重生效）
- ingest 後 Supabase 中可用 SQL 查到 source_url
- LINE 端的回覆 citations 帶 URL
