"""
Ch08-04 — 完整單次 Worker：lease → fetch → persist。

這是 ch01-ch07 所有技能的整合終點，也是
docs/supabase/04_crawler/06_worker-consume-loop-python.md 的同步簡化版。

Pipeline 流程：
    1. start_run()      → 建立 crawl_runs 記錄
    2. lease_next_job() → 從 crawl_queue 搶一筆任務（原子操作）
    3. BrowserManager   → 開啟瀏覽器、goto URL
    4. save_page()      → 存 raw HTML 到 source_pages
    5. extract_articles() → 從頁面擷取文章列表（HN 首頁）
    6. upsert_article() → 每篇文章 upsert 到 articles（content_hash 去重）
    7. finish_job()     → 更新 crawl_queue 狀態（done / failed）
    8. finish_run()     → 更新 crawl_runs 統計

執行方式：
    python ch08-supabase/04_single_job_worker.py

    # 重複執行消費更多任務
    python ch08-supabase/04_single_job_worker.py --source hacker-news
"""

import argparse
import hashlib
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass

from playwright.sync_api import Page

from utils.browser import BrowserManager
from utils.db_types import (
    ArticleExtractionData,
    ArticleInsert,
    ArticleMeta,
    CrawlPageType,
    CrawlQueueInsert,
    CrawlQueuePayload,
    CrawlQueueStatus,
    CrawlRunInsert,
    CrawlRunStatus,
    SourcePageInsert,
    SourcePageSnapshot,
    to_insert_dict,
)
from utils.config import DISCOVERY_BATCH_LIMIT, TEACHING_NAV_TIMEOUT_MS
from utils.crawl_queue import insert_new_pending_jobs
from utils.logger import setup_logger
from utils.supabase_client import get_crawler_table, get_supabase
from utils.time_helpers import now_iso

_BLOCKED_RESOURCES = frozenset({"image", "font", "media", "stylesheet"})


@dataclass
class _FetchedPage:
    """單次導航回傳的原始資料載荷。"""

    http_status: int | None
    title: str
    html: str
    links: list[str]

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"

logger = setup_logger("ch08-worker")


# ── Step 1: crawl_runs ────────────────────────────────────────────

def start_run(source_id: str) -> str:
    """建立 crawl_runs 記錄，回傳 run_id。"""
    insert = CrawlRunInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        run_status=CrawlRunStatus.RUNNING,
        started_at=now_iso(),
    )
    result = get_crawler_table("crawl_runs").insert(to_insert_dict(insert)).execute()
    run_id = result.data[0]["id"]
    logger.info("crawl_run 開始：%s", run_id)
    return run_id


def finish_run(run_id: str, stats: dict, *, run_status: CrawlRunStatus) -> None:
    """更新 crawl_runs 的最終統計與狀態。

    run_status 由呼叫端根據 error_count 決定：
      - SUCCESS：任務完成，無錯誤
      - PARTIAL ：任務完成，但 error_count > 0（有部分失敗）
      - FAILED  ：任務本身未執行（極少發生）
    不在這裡硬寫 SUCCESS，讓 crawl_runs 的狀態真實反映爬取結果。
    """
    get_crawler_table("crawl_runs").update({
        "run_status": run_status.value,
        "finished_at": now_iso(),
        **stats,
    }).eq("id", run_id).execute()
    logger.info("crawl_run 完成：%s status=%s %s", run_id, run_status.value, stats)


# ── Step 2: crawl_queue（lease） ──────────────────────────────────

def lease_next_job(source_id: str) -> dict | None:
    """從 crawl_queue 搶一筆屬於指定 source 的 pending 任務（lease）。

    使用 crawler.lease_next_crawl_job(source_id, worker_id) RPC，
    DB 內部直接過濾 source_id，以 FOR UPDATE SKIP LOCKED 原子搶單，
    無需應用層 retry / release loop。

    Returns:
        搶到的佇列行（dict），或 None（佇列空 / 無該 source 的 pending 任務）
    """
    result = (
        get_supabase()
        .schema("crawler")
        .rpc("lease_next_crawl_job", {
            "p_source_id": source_id,
            "p_worker_id": WORKER_ID,
        })
        .execute()
    )
    jobs = result.data or []
    if not jobs:
        logger.info("佇列已空，無 source='%s' 的待執行任務", source_id)
        return None

    job = jobs[0]
    logger.info("lease 成功：job_id=%s url=%s", job["id"], job["url"])
    return job


def finish_job(job: dict, status: CrawlQueueStatus, error_msg: str | None = None) -> None:
    """更新 crawl_queue 任務狀態。

    使用 lease_token 做樂觀鎖：若 Worker 因 lease 過期而被其他 Worker
    接手，此更新會因 lease_token 不符而靜默失效（不覆蓋新 Worker 的工作）。
    """
    update = {
        "status": status.value,
        "finished_at": now_iso(),
    }
    if error_msg:
        update["error_message"] = error_msg
    if status == CrawlQueueStatus.FAILED:
        update["retry_count"] = job["retry_count"] + 1

    get_crawler_table("crawl_queue").update(update).eq(
        "id", job["id"]
    ).eq(
        "lease_token", job["lease_token"]
    ).execute()


# ── Step 4: source_pages ─────────────────────────────────────────

def save_page(
    run_id: str,
    source_id: str,
    url: str,
    page_type: str,
    *,
    title: str | None,
    html: str | None,
    http_status: int | None,
    links: list[str],
) -> str:
    """Upsert 頁面資料到 source_pages，回傳 source_page_id。

    Upsert key：(source_id, url)
    重複爬取相同 URL 時更新 raw_html / fetched_at，不重複插入。
    """
    snapshot = SourcePageSnapshot(
        final_url=url,
        title=title,
        links=links[:100],  # 最多記錄 100 個連結
    )
    insert = SourcePageInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        crawl_run_id=run_id,
        url=url,
        page_type=CrawlPageType(page_type),
        title=title,
        raw_html=html,
        snapshot_json=snapshot,
        http_status=http_status,
        fetched_at=now_iso(),
        last_seen_at=now_iso(),
    )
    result = (
        get_crawler_table("source_pages")
        .upsert(to_insert_dict(insert), on_conflict="source_id,url")
        .execute()
    )
    return result.data[0]["id"]


# ── Step 5: 擷取 HN 文章列表 ─────────────────────────────────────

def extract_hn_articles(page: Page) -> list[dict]:
    """從 Hacker News 首頁擷取文章列表。

    對應 docs 的 extractors/list_extractor.py 的職責：
    給定一個已載入的 page，回傳結構化的文章草稿列表。
    """
    articles = []
    rows = page.locator("tr.athing")

    for i in range(rows.count()):
        row = rows.nth(i)
        title_el = row.locator("td.title span.titleline > a")
        if title_el.count() == 0:
            continue

        title = title_el.first.text_content().strip()
        url = title_el.first.get_attribute("href") or ""

        # 子行：分數（可能不存在）
        row_id = row.get_attribute("id") or ""
        score_el = page.locator(f"#score_{row_id}")
        score_text = score_el.text_content().strip() if score_el.count() > 0 else ""

        # 子行：作者、時間
        subtext = page.locator(f"tr").filter(
            has=page.locator(f"#score_{row_id}")
        )
        author = ""
        author_el = subtext.locator("a.hnuser")
        if author_el.count() > 0:
            author = author_el.first.text_content().strip()

        if title and url:
            articles.append({
                "title": title,
                "source_url": url if url.startswith("http") else f"https://news.ycombinator.com/{url.lstrip('/')}",
                "author_name": author or None,
                "meta_extra": {"score": score_text, "hn_id": row_id},
            })

    return articles


# ── Step 5b: 擷取文章頁內容 ──────────────────────────────────────

def extract_article_page(page: Page) -> dict:
    """從任意文章頁面擷取最小可用內容。

    HN 的文章 URL 指向外部網站，各站結構差異極大。
    這裡只取三件事：title、meta description、正文前 2000 字。
    生產環境會為各站寫專屬 extractor；此處示範通用最小版。

    對應 docs 的 extractors/article_extractor.py 職責：
    給定已載入的 page，回傳結構化的文章草稿。
    """
    title = page.title() or ""

    # meta description（大多數站都有）
    abstract = ""
    meta_el = page.locator('meta[name="description"]')
    if meta_el.count() > 0:
        abstract = meta_el.get_attribute("content") or ""

    # 正文前段：優先 <article>，其次 <main>，fallback <body>
    # 取前 2000 字避免存入過多雜訊
    content_text = ""
    for selector in ["article", "main", "body"]:
        el = page.locator(selector)
        if el.count() > 0:
            try:
                content_text = el.first.inner_text()[:2000]
            except Exception:
                pass
            if content_text.strip():
                break

    return {
        "title": title,
        "abstract": abstract,
        "content_text": content_text,
    }


# ── Step 6: articles upsert ───────────────────────────────────────

def compute_content_hash(title: str, source_url: str) -> str:
    """計算文章的 content_hash（SHA-256）。

    用於去重：hash 不變表示文章未更新，可跳過 upsert。
    生產環境應用 content_text 的 hash；此處用 title+url 作示範。
    """
    raw = f"{title}|{source_url}"
    return hashlib.sha256(raw.encode()).hexdigest()


def upsert_article(
    source_id: str,
    source_page_id: str,
    article_data: dict,
) -> tuple[str, bool]:
    """Upsert 文章到 crawler.articles，回傳 (article_id, is_new_or_updated)。

    兩道去重：
    1. Upsert key (source_id, source_url)：URL 相同就更新，不重複插入
    2. content_hash：hash 相同就不更新（內容未變）
    """
    new_hash = compute_content_hash(
        article_data["title"],
        article_data["source_url"],
    )

    # 先查是否已存在且 hash 相同
    existing = (
        get_crawler_table("articles")
        .select("id, content_hash")
        .eq("source_id", source_id)
        .eq("source_url", article_data["source_url"])
        .execute()
    )
    if existing.data and existing.data[0]["content_hash"] == new_hash:
        return existing.data[0]["id"], False  # 內容未變，跳過

    insert = ArticleInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        source_page_id=source_page_id,
        title=article_data["title"],
        source_url=article_data["source_url"],
        author_name=article_data.get("author_name"),
        content_hash=new_hash,
        meta=ArticleMeta(
            extra=article_data.get("meta_extra", {}),
        ),
        extraction_data=ArticleExtractionData(
            extractor_version="ch08-v1",
        ),
    )
    result = (
        get_crawler_table("articles")
        .upsert(to_insert_dict(insert), on_conflict="source_id,source_url")
        .execute()
    )
    return result.data[0]["id"], True


def upsert_article_content(
    source_id: str,
    source_page_id: str,
    url: str,
    content: dict,
) -> tuple[str, bool]:
    """用抓到的文章頁面內容更新 articles（以 source_url 定位）。

    列表頁 worker 執行時已建立骨架（title + source_url）；
    文章頁 worker 負責補入 content_text、abstract、content_hash。

    若文章骨架尚未存在（直接 crawl article URL 的情況），
    則插入新記錄。

    使用 content_text 的 hash 做去重：內容未變則不更新。
    """
    content_text = content.get("content_text") or ""
    new_hash = hashlib.sha256(content_text.encode()).hexdigest()

    # 查現有記錄（可能由列表頁 worker 建立）
    existing = (
        get_crawler_table("articles")
        .select("id, content_hash")
        .eq("source_id", source_id)
        .eq("source_url", url)
        .execute()
    )
    if existing.data and existing.data[0]["content_hash"] == new_hash:
        return existing.data[0]["id"], False  # 內容未變，跳過

    title = content.get("title") or url  # fallback to URL if page has no title

    insert = ArticleInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        source_page_id=source_page_id,
        title=title,
        source_url=url,
        abstract=content.get("abstract") or None,
        content_text=content_text or None,
        content_hash=new_hash,
        extraction_data=ArticleExtractionData(extractor_version="ch08-article-v1"),
    )
    result = (
        get_crawler_table("articles")
        .upsert(to_insert_dict(insert), on_conflict="source_id,source_url")
        .execute()
    )
    return result.data[0]["id"], True


# ── 主流程 ────────────────────────────────────────────────────────

def get_source(source_code: str) -> dict:
    result = (
        get_crawler_table("sources")
        .select("id, name, crawler_url, config, extractor_schema")
        .eq("project_id", PROJECT_ID)
        .eq("code", source_code)
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError(f"找不到 source code='{source_code}'，請先執行 02_seed_source.py")
    return result.data


def _fetch_page(page: Page, url: str) -> _FetchedPage:
    """攔截重量資源後導航 URL，回傳原始 HTML / title / 連結。"""
    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in _BLOCKED_RESOURCES
        else route.continue_(),
    )
    response = page.goto(
        url, timeout=TEACHING_NAV_TIMEOUT_MS, wait_until="domcontentloaded"
    )
    return _FetchedPage(
        http_status=response.status if response else None,
        title=page.title(),
        html=page.content(),
        links=page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)"),
    )


def _extract_and_persist_articles(
    page: Page,
    page_type: str,
    source_id: str,
    source_page_id: str,
    url: str,
    stats: dict,
) -> list[str]:
    """依 page_type 擷取內容並 upsert articles。回傳本次新發現需排隊的 URL。"""
    new_urls: list[str] = []

    if page_type == CrawlPageType.LIST.value:
        articles_data = extract_hn_articles(page)
        logger.info("擷取到 %d 篇文章連結", len(articles_data))
        for article_data in articles_data:
            _, updated = upsert_article(source_id, source_page_id, article_data)
            if updated:
                stats["articles_extracted"] += 1
                logger.info("  [新增/更新] %s", article_data["title"][:50])
                if article_data["source_url"].startswith("http"):
                    new_urls.append(article_data["source_url"])

    elif page_type == CrawlPageType.ARTICLE.value:
        content = extract_article_page(page)
        _, updated = upsert_article_content(source_id, source_page_id, url, content)
        if updated:
            stats["articles_extracted"] += 1
            logger.info("  [內容更新] %s", content["title"][:50])
        else:
            logger.info("  [內容未變，跳過] %s", url)

    return new_urls


def _enqueue_discovered_articles(
    source_id: str, referrer_url: str, urls: list[str]
) -> None:
    """把列表頁發現的文章 URL（受 DISCOVERY_BATCH_LIMIT 限制）塞回 crawl_queue。"""
    if not urls:
        return
    payloads = [
        to_insert_dict(
            CrawlQueueInsert(
                project_id=PROJECT_ID,
                source_id=source_id,
                url=u,
                page_type=CrawlPageType.ARTICLE,
                priority=50,
                payload=CrawlQueuePayload(
                    discovered_from="list",
                    referrer_url=referrer_url,
                    depth=1,
                ),
            )
        )
        for u in urls[:DISCOVERY_BATCH_LIMIT]
    ]
    inserted, _ = insert_new_pending_jobs(source_id, payloads)
    logger.info("已將 %d 個文章 URL 加入佇列", inserted)


def run_single_job(source_code: str) -> None:
    """執行一次完整的 Worker 流程（消費一筆 crawl_queue 任務）。"""
    source = get_source(source_code)
    source_id = source["id"]
    logger.info("來源：%s（%s）", source["name"], source_id)

    run_id = start_run(source_id)
    stats = {"pages_fetched": 0, "articles_extracted": 0, "error_count": 0}

    job = lease_next_job(source_id)
    if job is None:
        logger.info("找不到屬於 source='%s' 的待執行任務（請先執行 03_enqueue_urls.py）", source_code)
        finish_run(run_id, stats, run_status=CrawlRunStatus.SUCCESS)
        raise _QueueEmpty(source_code)

    url = job["url"]
    page_type = job["page_type"]

    # lease → running（對應佇列狀態機：leased → running → done/failed）
    get_crawler_table("crawl_queue").update({
        "status": CrawlQueueStatus.RUNNING.value,
    }).eq("id", job["id"]).eq("lease_token", job["lease_token"]).execute()
    logger.info("開始處理：%s", url)

    try:
        with BrowserManager(headless=True, stealth=True) as bm:
            page = bm.new_page()
            fetched = _fetch_page(page, url)

            source_page_id = save_page(
                run_id, source_id, url, page_type,
                title=fetched.title,
                html=fetched.html,
                http_status=fetched.http_status,
                links=fetched.links,
            )
            stats["pages_fetched"] += 1
            logger.info(
                "source_page 已儲存：%s（HTTP %s）",
                source_page_id, fetched.http_status,
            )

            new_urls = _extract_and_persist_articles(
                page, page_type, source_id, source_page_id, url, stats,
            )
            _enqueue_discovered_articles(source_id, url, new_urls)

        finish_job(job, CrawlQueueStatus.DONE)
        logger.info("任務完成：%s", job["id"])

    except Exception as e:
        stats["error_count"] += 1
        logger.error("任務失敗：%s — %s", job["id"], e, exc_info=True)
        finish_job(job, CrawlQueueStatus.FAILED, error_msg=str(e))

    # error_count > 0 → PARTIAL，讓 crawl_runs 一眼可辨識「跑過但有問題」
    run_status = (
        CrawlRunStatus.PARTIAL if stats["error_count"] > 0 else CrawlRunStatus.SUCCESS
    )
    finish_run(run_id, stats, run_status=run_status)

    print("\n" + "=" * 50)
    print("執行摘要")
    print("=" * 50)
    print(f"  source     : {source['name']}")
    print(f"  url        : {url}")
    print(f"  run_id     : {run_id}")
    print(f"  pages      : {stats['pages_fetched']}")
    print(f"  articles   : {stats['articles_extracted']} 筆新增/更新")
    print(f"  errors     : {stats['error_count']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Playwright Worker")
    parser.add_argument(
        "--source", default="hacker-news",
        help="source code（預設：hacker-news）"
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="持續消費佇列，直到無 pending 任務為止"
    )
    parser.add_argument(
        "--idle-wait", type=int, default=3, metavar="SEC",
        help="--loop 模式下佇列為空時的等待秒數（預設：3）"
    )
    args = parser.parse_args()

    print("=" * 50)
    print(f"Ch08-04 — Worker（{WORKER_ID}）")
    if args.loop:
        print("模式：連續消費（--loop）")
    else:
        print("模式：單次執行")
    print("=" * 50)

    try:
        if args.loop:
            _run_loop(args.source, idle_wait=args.idle_wait)
        else:
            run_single_job(args.source)
    except ValueError as e:
        print(f"[NG] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[停止] 收到中斷信號，Worker 已退出。")


def _run_loop(source_code: str, idle_wait: int = 3) -> None:
    """持續消費佇列，直到連續 idle_wait 秒無任務才停止。

    每跑完一個 job 立即嘗試搶下一個，佇列空時等待後再試。
    按 Ctrl-C 可安全中斷（當前 job 完成後退出）。
    """
    import time

    total_jobs = 0
    consecutive_empty = 0
    # 連續 3 次空佇列（共等 idle_wait*3 秒）才視為佇列耗盡而退出
    _MAX_EMPTY = 3

    print(f"[loop] 開始連續消費 source={source_code}，空佇列等待 {idle_wait}s x {_MAX_EMPTY} 次後退出")

    while True:
        try:
            run_single_job(source_code)
            total_jobs += 1
            consecutive_empty = 0
        except _QueueEmpty:
            consecutive_empty += 1
            if consecutive_empty >= _MAX_EMPTY:
                print(f"\n[loop] 佇列連續空 {_MAX_EMPTY} 次，退出。共處理 {total_jobs} 個任務。")
                return
            logger.info("佇列暫時為空（%d/%d），等待 %ds...", consecutive_empty, _MAX_EMPTY, idle_wait)
            time.sleep(idle_wait)


class _QueueEmpty(Exception):
    """佇列無可用任務時由 run_single_job 拋出，供 loop 模式偵測。"""


if __name__ == "__main__":
    main()
