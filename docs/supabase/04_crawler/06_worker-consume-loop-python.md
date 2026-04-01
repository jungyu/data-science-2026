# Playwright Worker — Consume Loop 與 Browser Pool（Python）

> **前置閱讀**：[05_worker-architecture.md](05_worker-architecture.md) 說明各元件的角色分工。這份文件是那份設計的具體實作。

## 本文件的各部分如何組合？

閱讀本文件之前，先看清楚各元件的呼叫順序：

```
main() 消費迴圈
  │
  ├─ SupabaseQueueConsumer.lease_next_job()   ← 搶一筆任務
  │
  ├─ SourceHealthTracker.is_available()        ← 來源是否在冷卻？（07 的邏輯）
  │
  ├─ DomainLimiter.acquire()                   ← 等待 domain 並行名額
  │
  ├─ PageRunner.process()                      ← 實際爬取（BrowserPool + 擷取 + 存 DB）
  │     └─ 回傳 ProcessResult（Done/Retry/Failed/Skipped）
  │
  ├─ 依 ProcessResult 類型：
  │     Done     → consumer.complete_job()
  │     Retry    → health_tracker.record_failure() + consumer.requeue_job()
  │     Failed   → health_tracker.record_failure() + consumer.fail_job()
  │     Skipped  → consumer.complete_job()（不計統計）
  │
  └─ DomainLimiter.release()
```

`retry_policy.decide_retry()` 在 [07_worker-retry-and-anti-ban.md](07_worker-retry-and-anti-ban.md) 定義，由 `PageRunner._make_retry_or_fail()` 呼叫（在 `process()` 內部，遇到 error 時）。

---

## 主消費迴圈

```python
import asyncio
import logging
import uuid
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from supabase import AsyncClient

from .browser_pool import BrowserPool
from .consumer import SupabaseQueueConsumer
from .page_runner import PageRunner
from .policies.rate_limit_policy import DomainLimiter, SourceHealthTracker
from .types import (
    ProcessResultDone,
    ProcessResultFailed,
    ProcessResultRetry,
    ProcessResultSkipped,
    WorkerError,
    WorkerErrorCode,
)

logger = logging.getLogger(__name__)

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
POLL_INTERVAL_SEC = 5
MAX_EMPTY_POLLS = 60  # 閒置 5 分鐘後停止

async def main(supabase_client: AsyncClient) -> None:
    consumer = SupabaseQueueConsumer(supabase_client)
    health_tracker = SourceHealthTracker()
    domain_limiter = DomainLimiter(default_max=1)

    async with async_playwright() as pw:
        pool = BrowserPool(pw)
        await pool.start()
        runner = PageRunner(pool)

        empty_polls = 0

        while empty_polls < MAX_EMPTY_POLLS:
            # 1. 租用下一個任務
            job = await consumer.lease_next_job(WORKER_ID)

            if job is None:
                empty_polls += 1
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            empty_polls = 0
            domain = urlparse(job.url).netloc

            # 2. 檢查來源健康狀態
            if not health_tracker.is_available(job.source_id):
                logger.info(
                    "Source %s in cooldown, requeuing job %s",
                    job.source_id,
                    job.job_id,
                )
                await consumer.requeue_job(
                    job.job_id,
                    job.lease_token,
                    retry_at=_minutes_from_now(15),
                    error=WorkerError(
                        code=WorkerErrorCode.HTTP_429,
                        message="Source in cooldown",
                        retryable=True,
                    ),
                )
                continue

            # 3. 取得 domain 並行插槽
            await domain_limiter.acquire(domain)

            try:
                # 4. 處理任務
                result = await runner.process(job)

                # 5. 處理結果
                if isinstance(result, ProcessResultDone):
                    await consumer.complete_job(job.job_id, job.lease_token)
                    health_tracker.record_success(job.source_id)
                    logger.info("Job %s done: %s", job.job_id, job.url)

                elif isinstance(result, ProcessResultRetry):
                    if result.error is not None:
                        health_tracker.record_failure(job.source_id, result.error)
                        await consumer.requeue_job(
                            job.job_id,
                            job.lease_token,
                            retry_at=result.retry_at,
                            error=result.error,
                        )
                        logger.warning(
                            "Job %s retry: %s - %s",
                            job.job_id,
                            result.error.code.value,
                            result.error.message,
                        )
                    else:
                        await consumer.requeue_job(
                            job.job_id,
                            job.lease_token,
                            retry_at=result.retry_at,
                            error=WorkerError(
                                code=WorkerErrorCode.UNKNOWN,
                                message="Retry without error context",
                                retryable=True,
                            ),
                        )

                elif isinstance(result, ProcessResultFailed):
                    if result.error is not None:
                        health_tracker.record_failure(job.source_id, result.error)
                        await consumer.fail_job(
                            job.job_id, job.lease_token, result.error
                        )
                        logger.error(
                            "Job %s failed: %s - %s",
                            job.job_id,
                            result.error.code.value,
                            result.error.message,
                        )
                    else:
                        fallback = WorkerError(
                            code=WorkerErrorCode.UNKNOWN,
                            message="Failed without error context",
                            retryable=False,
                        )
                        health_tracker.record_failure(job.source_id, fallback)
                        await consumer.fail_job(
                            job.job_id, job.lease_token, fallback
                        )

                elif isinstance(result, ProcessResultSkipped):
                    await consumer.complete_job(job.job_id, job.lease_token)
                    logger.info("Job %s skipped: %s", job.job_id, result.reason)

            except Exception:
                logger.exception("Unexpected error processing job %s", job.job_id)
                await consumer.fail_job(
                    job.job_id,
                    job.lease_token,
                    WorkerError(
                        code=WorkerErrorCode.UNKNOWN,
                        message="Unexpected exception",
                        retryable=False,
                    ),
                )
            finally:
                domain_limiter.release(domain)

        await pool.stop()
        logger.info("Worker %s shutting down (idle timeout)", WORKER_ID)


def _minutes_from_now(minutes: int) -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


if __name__ == "__main__":
    import os
    from supabase._async.client import AsyncClient, create_client
    client = asyncio.get_event_loop().run_until_complete(
        create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    )
    asyncio.run(main(client))
```

---

## Browser Pool

```python
import logging
from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)


@dataclass
class BrowserPoolConfig:
    max_browsers: int = 2
    max_contexts_per_browser: int = 5
    browser_restart_after_jobs: int = 50


class BrowserPool:
    """管理瀏覽器生命週期。Context 為每個任務短暫建立。"""

    def __init__(
        self,
        pw: Playwright,
        config: BrowserPoolConfig | None = None,
    ) -> None:
        self._pw = pw
        self._config = config or BrowserPoolConfig()
        self._browser: Browser | None = None
        self._jobs_since_restart: int = 0

    async def start(self) -> None:
        self._browser = await self._pw.chromium.launch(headless=True)
        self._jobs_since_restart = 0
        logger.info("Browser launched")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")

    async def new_context(self, **kwargs) -> BrowserContext:
        """建立新的 context。呼叫端使用完畢後須自行關閉。"""
        if self._browser is None:
            await self.start()

        # 處理 N 個任務後重啟瀏覽器，避免累積狀態
        self._jobs_since_restart += 1
        if self._jobs_since_restart >= self._config.browser_restart_after_jobs:
            logger.info("Restarting browser after %d jobs", self._jobs_since_restart)
            await self.stop()
            await self.start()

        return await self._browser.new_context(**kwargs)
```

---

## Page Runner（單一任務處理器）

```python
import logging
import time

from playwright.async_api import BrowserContext, Page, TimeoutError as PwTimeout

from .browser_pool import BrowserPool
from .consumer import SupabaseQueueConsumer
from .db_types import CrawlPageType, SourceRow
from .extractors.article_extractor import ArticleExtractor
from .extractors.list_extractor import ListExtractor
from .persistence.article_repo import SupabaseArticleRepo
from .persistence.source_page_repo import SupabaseSourcePageRepo
from .persistence.source_repo import SupabaseSourceRepo
from .policies.retry_policy import decide_retry
from .service_inputs import (
    EnqueueUrlInput,
    SaveFetchedPageInput,
    UpsertArticleInput,
)
from .types import (
    ExtractedArticleDraft,
    LeasedJob,
    ProcessResult,
    ProcessResultDone,
    ProcessResultFailed,
    ProcessResultRetry,
    RetryContext,
    WorkerError,
    WorkerErrorCode,
)

logger = logging.getLogger(__name__)


class PageRunner:
    def __init__(self, pool: BrowserPool) -> None:
        self._pool = pool
        self._list_extractor = ListExtractor()
        self._article_extractor = ArticleExtractor()
        self._source_repo = SupabaseSourceRepo()
        self._source_page_repo = SupabaseSourcePageRepo()
        self._article_repo = SupabaseArticleRepo()
        self._queue_consumer = SupabaseQueueConsumer()

    async def process(self, job: LeasedJob) -> ProcessResult:
        ctx: BrowserContext | None = None
        try:
            # 載入來源設定供 extractor 使用
            source = await self._source_repo.find_by_id(job.source_id)
            if source is None:
                return ProcessResultFailed(
                    error=WorkerError(
                        code=WorkerErrorCode.UNKNOWN,
                        message=f"Source {job.source_id} not found",
                        retryable=False,
                    )
                )

            ctx = await self._pool.new_context()
            page = await ctx.new_page()

            # 封鎖非必要資源
            await self._setup_blocking(page)

            # 導航至目標頁面
            t0 = time.monotonic()
            response = await page.goto(
                job.url, wait_until="domcontentloaded", timeout=30000
            )
            ttfb_ms = (time.monotonic() - t0) * 1000

            http_status = response.status if response else None

            # 檢查錯誤狀態碼
            if http_status and http_status >= 400:
                error = self._classify_http_error(http_status)
                return self._make_retry_or_fail(error, job)

            # 儲存原始頁面
            html = await page.content()
            title = await page.title()
            await self._source_page_repo.upsert_page(
                SaveFetchedPageInput(
                    source_id=job.source_id,
                    page_type=job.page_type,
                    url=job.url,
                    title=title,
                    raw_html=html,
                    http_status=http_status,
                )
            )

            # 依頁面類型進行抽取
            discovered_urls: list[str] = []

            if job.page_type == CrawlPageType.LIST:
                result = await self._list_extractor.extract_list(page, source)
                discovered_urls = result.discovered_urls
                # 將發現的文章 URL 加入佇列
                for url in discovered_urls:
                    await self._queue_consumer.enqueue(
                        EnqueueUrlInput(
                            source_id=job.source_id,
                            url=url,
                            page_type=CrawlPageType.ARTICLE,
                        )
                    )
                if result.next_page_url:
                    await self._queue_consumer.enqueue(
                        EnqueueUrlInput(
                            source_id=job.source_id,
                            url=result.next_page_url,
                            page_type=CrawlPageType.LIST,
                        )
                    )

            elif job.page_type in (CrawlPageType.ARTICLE, CrawlPageType.DETAIL):
                draft = await self._article_extractor.extract_article(page, source)
                await self._article_repo.upsert_article(
                    UpsertArticleInput(
                        source_id=job.source_id,
                        source_url=job.url,
                        draft=draft,
                    )
                )

            return ProcessResultDone(
                discovered_urls=discovered_urls,
            )

        except PwTimeout:
            error = WorkerError(
                code=WorkerErrorCode.TIMEOUT,
                message=f"Navigation timeout: {job.url}",
                retryable=True,
            )
            return self._make_retry_or_fail(error, job)

        except Exception as exc:
            error = WorkerError(
                code=WorkerErrorCode.UNKNOWN,
                message=str(exc),
                retryable=True,
            )
            return self._make_retry_or_fail(error, job)

        finally:
            if ctx:
                await ctx.close()

    def _make_retry_or_fail(
        self, error: WorkerError, job: LeasedJob
    ) -> ProcessResult:
        decision = decide_retry(
            error,
            RetryContext(
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                source_id=job.source_id,
                url=job.url,
                page_type=job.page_type,
                last_error=error,
            ),
        )
        if hasattr(decision, "retry_at"):
            return ProcessResultRetry(retry_at=decision.retry_at, error=error)
        return ProcessResultFailed(error=error)

    def _classify_http_error(self, status: int) -> WorkerError:
        if status == 403:
            return WorkerError(
                code=WorkerErrorCode.HTTP_403,
                message="Forbidden",
                retryable=True,
            )
        if status == 404:
            return WorkerError(
                code=WorkerErrorCode.HTTP_404,
                message="Not Found",
                retryable=False,
            )
        if status == 429:
            return WorkerError(
                code=WorkerErrorCode.HTTP_429,
                message="Rate Limited",
                retryable=True,
            )
        if 500 <= status < 600:
            return WorkerError(
                code=WorkerErrorCode.HTTP_5XX,
                message=f"Server Error {status}",
                retryable=True,
            )
        return WorkerError(
            code=WorkerErrorCode.UNKNOWN,
            message=f"HTTP {status}",
            retryable=False,
        )

    async def _setup_blocking(self, page: Page) -> None:
        block_types = {"image", "font", "media", "stylesheet"}

        async def handle(route):
            if route.request.resource_type in block_types:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", handle)
```

---

## Queue Consumer 實作

呼叫 Supabase lease RPC 的具體實作。

```python
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import AsyncClient

from .db_types import CrawlPageType, CrawlQueueRow
from .service_inputs import EnqueueUrlInput
from .types import Json, LeasedJob, WorkerError, WorkerErrorCode

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """取得 UTC 當前時間的 ISO 字串，供 Supabase 使用。"""
    return datetime.now(timezone.utc).isoformat()


def _future_iso(minutes: int) -> str:
    """取得 UTC 當前時間 + N 分鐘的 ISO 字串，供 Supabase 使用。"""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class SupabaseQueueConsumer:
    """實作 QueueConsumer protocol，對接 Supabase。"""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def enqueue(self, input: EnqueueUrlInput) -> CrawlQueueRow:
        result = await self._client.schema("crawler").table("crawl_queue").insert(
            {
                "project_id": input.project_id,
                "source_id": input.source_id,
                "url": input.url,
                "page_type": input.page_type.value,
                "priority": input.priority,
                "payload": input.payload,
            }
        ).execute()
        return result.data[0]

    async def lease_next_job(self, worker_id: str) -> LeasedJob | None:
        result = await self._client.schema("crawler").rpc(
            "lease_next_crawl_job", {"p_worker_id": worker_id}
        ).execute()
        rows = result.data
        if not rows:
            return None
        row = rows[0]
        return LeasedJob(
            job_id=row["id"],
            source_id=row["source_id"],
            url=row["url"],
            page_type=CrawlPageType(row["page_type"]),
            lease_token=row["lease_token"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            payload=row.get("payload", {}),
        )

    async def heartbeat(self, job_id: str, lease_token: str) -> None:
        await self._client.schema("crawler").table("crawl_queue").update(
            {"lease_expires_at": _future_iso(5)}
        ).eq("id", job_id).eq("lease_token", lease_token).execute()

    async def complete_job(
        self, job_id: str, lease_token: str, result: Json | None = None
    ) -> None:
        await self._client.schema("crawler").table("crawl_queue").update(
            {"status": "done", "finished_at": _now_iso()}
        ).eq("id", job_id).eq("lease_token", lease_token).execute()

    async def fail_job(
        self, job_id: str, lease_token: str, error: WorkerError
    ) -> None:
        await self._client.schema("crawler").table("crawl_queue").update(
            {
                "status": "failed",
                "finished_at": _now_iso(),
                "error_code": error.code.value,
                "error_message": error.message,
            }
        ).eq("id", job_id).eq("lease_token", lease_token).execute()

    async def requeue_job(
        self, job_id: str, lease_token: str, retry_at: str, error: WorkerError
    ) -> None:
        # 取得目前的 retry_count
        row = await self._client.schema("crawler").table("crawl_queue").select(
            "retry_count, max_retries"
        ).eq("id", job_id).single().execute()

        new_retry = row.data["retry_count"] + 1
        new_status = "dead" if new_retry >= row.data["max_retries"] else "pending"

        await self._client.schema("crawler").table("crawl_queue").update(
            {
                "status": new_status,
                "scheduled_at": retry_at,
                "retry_count": new_retry,
                "lease_token": None,
                "leased_at": None,
                "lease_expires_at": None,
                "worker_id": None,
                "error_code": error.code.value,
                "error_message": error.message,
            }
        ).eq("id", job_id).eq("lease_token", lease_token).execute()
```

---

## Lease SQL（Supabase RPC）

使用 `FOR UPDATE SKIP LOCKED` 進行原子性 lease 取得：

```sql
create or replace function crawler.lease_next_crawl_job(
  p_worker_id text,
  p_lease_duration interval default interval '5 minutes'
)
returns setof crawler.crawl_queue
language sql
security definer
set search_path = crawler
as $$
  update crawler.crawl_queue
  set
    status = 'leased',
    lease_token = gen_random_uuid()::text,
    leased_at = now(),
    lease_expires_at = now() + p_lease_duration,
    worker_id = p_worker_id
  where id = (
    select id
    from crawler.crawl_queue
    where (status = 'pending' and scheduled_at <= now())
       or (status = 'leased' and lease_expires_at < now())
    order by priority desc, scheduled_at asc
    limit 1
    for update skip locked
  )
  returning *;
$$;
```

---

## 實作階段

### 第一階段：最小可行 Worker

- `crawl_queue` + `lease_next_crawl_job()` RPC
- 單一 `process(job)` 迴圈
- 指數退避重試
- Domain 並行數 = 1
- 遇到 429/403 時對來源進行冷卻

### 第二階段：穩定性

- Heartbeat / lease 續租
- Browser Pool 含重啟策略
- 來源健康狀態機
- 失敗時截圖
- 結構化日誌

### 第三階段：正式環境

- 來源專屬爬取策略
- Circuit Breaker 模式
- 每來源配額限制
- Queue 指標儀表板
- Dead-letter 審查
- 手動重播

---

## 快速參考

| 模組 | 決策 |
| --------------------- | ----------------------------------------------- |
| Queue 後端 | Supabase `crawl_queue` |
| Worker 執行環境 | Cloud Run container（Python + Playwright） |
| Lease 模式 | 必須使用（`FOR UPDATE SKIP LOCKED`） |
| 重試策略 | 指數退避 + jitter |
| 來源保護 | 冷卻 + 健康狀態機 |
| Domain 並行數 | 預設 1 |
| 資源封鎖 | 封鎖圖片／字型／媒體／樣式表 |
| 瀏覽器策略 | 重複使用瀏覽器，短暫建立 context |
| 被封鎖時的回應 | 減速、冷卻、人工審查 |
| 禁止行為 | 不得繞過 CAPTCHA、不得規避挑戰機制 |
