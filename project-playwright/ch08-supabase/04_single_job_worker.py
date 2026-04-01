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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
from utils.logger import setup_logger
from utils.supabase_client import get_crawler_table, get_supabase

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"

logger = setup_logger("ch08-worker")


# ── 時間工具 ──────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def finish_run(run_id: str, stats: dict) -> None:
    """更新 crawl_runs 的最終統計與狀態。"""
    get_crawler_table("crawl_runs").update({
        "run_status": CrawlRunStatus.SUCCESS.value,
        "finished_at": now_iso(),
        **stats,
    }).eq("id", run_id).execute()
    logger.info("crawl_run 完成：%s %s", run_id, stats)


# ── Step 2: crawl_queue（lease） ──────────────────────────────────

def lease_next_job(source_id: str) -> dict | None:
    """從 crawl_queue 搶一筆 pending 任務（lease）。

    使用 crawler.lease_next_crawl_job() RPC，內部以
    FOR UPDATE SKIP LOCKED 實現多 Worker 並行安全搶單。

    Returns:
        搶到的佇列列（dict），或 None（佇列空）
    """
    result = (
        get_supabase()
        .schema("crawler")
        .rpc("lease_next_crawl_job", {"p_worker_id": WORKER_ID})
        .execute()
    )
    jobs = result.data or []
    if not jobs:
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

def extract_hn_articles(page) -> list[dict]:
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


def run_single_job(source_code: str) -> None:
    """執行一次完整的 Worker 流程（消費一筆 crawl_queue 任務）。"""

    # ── 取得 source 設定 ──────────────────────────────────────────
    source = get_source(source_code)
    source_id = source["id"]
    logger.info("來源：%s（%s）", source["name"], source_id)

    # ── Step 1: 建立 crawl_run ────────────────────────────────────
    run_id = start_run(source_id)

    stats = {"pages_fetched": 0, "articles_extracted": 0, "error_count": 0}

    # ── Step 2: 搶一筆任務 ────────────────────────────────────────
    job = lease_next_job(source_id)
    if job is None:
        logger.info("佇列空，無任務可執行（請先執行 03_enqueue_urls.py）")
        get_crawler_table("crawl_runs").update({
            "run_status": CrawlRunStatus.SUCCESS.value,
            "finished_at": now_iso(),
        }).eq("id", run_id).execute()
        return

    url = job["url"]
    page_type = job["page_type"]

    # lease → running（對應佇列狀態機：leased → running → done/failed）
    get_crawler_table("crawl_queue").update({
        "status": CrawlQueueStatus.RUNNING.value,
    }).eq("id", job["id"]).eq("lease_token", job["lease_token"]).execute()
    logger.info("開始處理：%s", url)

    # ── Step 3: 開啟瀏覽器 ───────────────────────────────────────
    try:
        with BrowserManager(headless=True, stealth=True) as bm:
            page = bm.new_page()

            # 阻擋不必要資源（加速）
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "font", "media", "stylesheet")
                else route.continue_(),
            )

            response = page.goto(url, timeout=15000, wait_until="domcontentloaded")
            http_status = response.status if response else None
            title = page.title()
            html = page.content()

            # 收集頁面所有連結（供 snapshot 記錄）
            links = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.href)"
            )

            # ── Step 4: 存 source_pages ──────────────────────────
            source_page_id = save_page(
                run_id, source_id, url, page_type,
                title=title,
                html=html,
                http_status=http_status,
                links=links,
            )
            stats["pages_fetched"] += 1
            logger.info("source_page 已儲存：%s（HTTP %s）", source_page_id, http_status)

            # ── Step 5 & 6: 擷取 + upsert 文章 ──────────────────
            articles_data = []
            if page_type == CrawlPageType.LIST.value:
                articles_data = extract_hn_articles(page)
                logger.info("擷取到 %d 篇文章", len(articles_data))

            new_urls_to_enqueue = []
            for article_data in articles_data:
                article_id, updated = upsert_article(
                    source_id, source_page_id, article_data
                )
                if updated:
                    stats["articles_extracted"] += 1
                    logger.info(
                        "  [%s] %s",
                        "新增" if updated else "跳過",
                        article_data["title"][:50],
                    )
                    # 收集外部文章 URL 以便後續排入佇列
                    if article_data["source_url"].startswith("http"):
                        new_urls_to_enqueue.append(article_data["source_url"])

            # 將發現的文章 URL 塞入 crawl_queue（priority 較低）
            if new_urls_to_enqueue:
                new_jobs = [
                    to_insert_dict(CrawlQueueInsert(
                        project_id=PROJECT_ID,
                        source_id=source_id,
                        url=u,
                        page_type=CrawlPageType.ARTICLE,
                        priority=50,
                        payload=CrawlQueuePayload(
                            discovered_from="list",
                            referrer_url=url,
                            depth=1,
                        ),
                    ))
                    for u in new_urls_to_enqueue[:20]  # 每次最多加 20 筆
                ]
                get_crawler_table("crawl_queue").insert(
                    new_jobs, ignore_duplicates=True
                ).execute()
                logger.info("已將 %d 個文章 URL 加入佇列", len(new_urls_to_enqueue[:20]))

        # ── Step 7: 任務完成 ─────────────────────────────────────
        finish_job(job, CrawlQueueStatus.DONE)
        logger.info("任務完成：%s", job["id"])

    except Exception as e:
        stats["error_count"] += 1
        logger.error("任務失敗：%s — %s", job["id"], e, exc_info=True)
        finish_job(job, CrawlQueueStatus.FAILED, error_msg=str(e))

    # ── Step 8: 更新 crawl_run ────────────────────────────────────
    finish_run(run_id, stats)

    # ── 結果摘要 ─────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("執行摘要")
    print("=" * 50)
    print(f"  source     : {source['name']}")
    print(f"  url        : {url}")
    print(f"  run_id     : {run_id}")
    print(f"  pages      : {stats['pages_fetched']}")
    print(f"  articles   : {stats['articles_extracted']} 筆新增/更新")
    print(f"  errors     : {stats['error_count']}")


def main():
    parser = argparse.ArgumentParser(description="執行一次 Playwright Worker")
    parser.add_argument(
        "--source", default="hacker-news",
        help="source code（預設：hacker-news）"
    )
    args = parser.parse_args()

    print("=" * 50)
    print(f"Ch08-04 — Single Job Worker（{WORKER_ID}）")
    print("=" * 50)

    try:
        run_single_job(args.source)
    except ValueError as e:
        print(f"[✗] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
