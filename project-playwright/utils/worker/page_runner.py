"""
PageRunner — WorkerProcessor Protocol 的實作。

來源文件：docs/supabase/04_crawler/06_worker-consume-loop-python.md

職責：給定一個 LeasedJob，執行完整的「抓頁面 → 擷取 → 存 DB」流程，
回傳 ProcessResult（Done / Retry / Failed / Skipped）。

PageRunner 只依賴 Protocol（BrowserPool、extractors、repos），
不直接建立 Supabase client，方便測試時替換 fake 實作。
"""

from __future__ import annotations

import logging
import time

from playwright.async_api import BrowserContext, Page, Route
from playwright.async_api import TimeoutError as PwTimeout

from utils.config import (
    DISCOVERY_BATCH_LIMIT,
    WORKER_NAV_TIMEOUT_MS,
)
from utils.db_types import CrawlPageType
from utils.time_helpers import now_iso as _now_iso
from utils.worker.consumer import SupabaseQueueConsumer
from utils.worker.extractors.article_extractor import ArticleExtractor
from utils.worker.extractors.list_extractor import ListExtractor
from utils.worker.persistence.article_repo import SupabaseArticleRepo
from utils.worker.persistence.source_page_repo import SupabaseSourcePageRepo
from utils.worker.persistence.source_repo import SupabaseSourceRepo
from utils.worker.policies.retry_policy import decide_retry
from utils.worker.service_inputs import (
    EnqueueUrlInput,
    SaveFetchedPageInput,
    UpsertArticleInput,
)
from utils.worker.types import (
    LeasedJob,
    ProcessResult,
    ProcessResultDone,
    ProcessResultFailed,
    ProcessResultRetry,
    RetryContext,
    WorkerError,
    WorkerErrorCode,
)
from utils.worker.browser_pool import BrowserPool

logger = logging.getLogger(__name__)

# 阻擋的資源類型（加速爬取、降低流量）
_BLOCK_RESOURCE_TYPES: frozenset[str] = frozenset(
    {"image", "font", "media", "stylesheet"}
)


class PageRunner:
    """單一任務處理器。

    呼叫 process(job) 即執行完整 pipeline：
      1. 從 SourceRepo 取得 source 設定
      2. BrowserPool 開啟 context
      3. 導航至 URL，收集回應信號
      4. 依 page_type 擷取內容（list → ListExtractor，article → ArticleExtractor）
      5. 存 source_pages + upsert articles
      6. 回傳 ProcessResult
    """

    def __init__(
        self,
        pool: BrowserPool,
        consumer: SupabaseQueueConsumer,
        source_repo: SupabaseSourceRepo,
        source_page_repo: SupabaseSourcePageRepo,
        article_repo: SupabaseArticleRepo,
    ) -> None:
        self._pool = pool
        self._consumer = consumer
        self._source_repo = source_repo
        self._source_page_repo = source_page_repo
        self._article_repo = article_repo
        self._list_extractor = ListExtractor()
        self._article_extractor = ArticleExtractor()

    async def process(self, job: LeasedJob) -> ProcessResult:
        """執行單一爬取任務，回傳結果型別。"""
        ctx: BrowserContext | None = None
        try:
            # 1. 載入來源設定
            source = await self._source_repo.find_by_id(job.source_id)
            if source is None:
                return ProcessResultFailed(
                    error=WorkerError(
                        code=WorkerErrorCode.UNKNOWN,
                        message=f"Source {job.source_id} not found in DB",
                        retryable=False,
                    )
                )

            project_id = source.project_id

            # 2. 建立 browser context，頁面完成後自動關閉
            ctx = await self._pool.new_context()
            page = await ctx.new_page()
            await self._setup_blocking(page)

            # 3. 導航
            t0 = time.monotonic()
            response = await page.goto(
                job.url,
                wait_until="domcontentloaded",
                timeout=WORKER_NAV_TIMEOUT_MS,
            )
            ttfb_ms = (time.monotonic() - t0) * 1000
            http_status = response.status if response else None

            # 4xx/5xx → 錯誤分類並決定是否重試
            if http_status and http_status >= 400:
                error = self._classify_http_error(http_status)
                return self._make_retry_or_fail(error, job)

            # 4. 儲存原始頁面快照
            html = await page.content()
            title = await page.title()
            page_row = await self._source_page_repo.upsert_page(
                SaveFetchedPageInput(
                    project_id=project_id,
                    source_id=job.source_id,
                    page_type=job.page_type,
                    url=job.url,
                    title=title,
                    raw_html=html,
                    http_status=http_status,
                    fetched_at=_now_iso(),
                )
            )

            # 5. 依頁面類型擷取內容
            discovered_urls: list[str] = []

            if job.page_type == CrawlPageType.LIST:
                result = await self._list_extractor.extract_list(page, source)
                discovered_urls = result.discovered_urls

                # 把發現的文章 URL 加入佇列（partial unique index 防重複）
                for url in discovered_urls[:DISCOVERY_BATCH_LIMIT]:
                    await self._safe_enqueue(
                        EnqueueUrlInput(
                            project_id=project_id,
                            source_id=job.source_id,
                            url=url,
                            page_type=CrawlPageType.ARTICLE,
                            priority=50,
                        )
                    )

                if result.next_page_url:
                    await self._safe_enqueue(
                        EnqueueUrlInput(
                            project_id=project_id,
                            source_id=job.source_id,
                            url=result.next_page_url,
                            page_type=CrawlPageType.LIST,
                            priority=150,
                        )
                    )

            elif job.page_type in (CrawlPageType.ARTICLE, CrawlPageType.DETAIL):
                draft = await self._article_extractor.extract_article(page, source)
                await self._article_repo.upsert_article(
                    UpsertArticleInput(
                        project_id=project_id,
                        source_id=job.source_id,
                        source_url=job.url,
                        source_page_id=page_row["id"] if page_row else None,
                        draft=draft,
                    )
                )

            return ProcessResultDone(
                page_id=page_row["id"] if page_row else None,
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

    # ── 內部工具 ──────────────────────────────────────────────────

    def _make_retry_or_fail(
        self, error: WorkerError, job: LeasedJob
    ) -> ProcessResult:
        """呼叫 decide_retry()，把 RetryDecision 轉換成 ProcessResult。"""
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
        """HTTP 狀態碼 → WorkerError（含 retryable 旗標）。"""
        mapping = {
            403: (WorkerErrorCode.HTTP_403, "Forbidden", True),
            404: (WorkerErrorCode.HTTP_404, "Not Found", False),
            429: (WorkerErrorCode.HTTP_429, "Rate Limited", True),
        }
        if status in mapping:
            code, msg, retryable = mapping[status]
            return WorkerError(code=code, message=msg, retryable=retryable)
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

    async def _safe_enqueue(self, payload: EnqueueUrlInput) -> None:
        """Enqueue URL；URL 已在佇列（unique 衝突）視為正常，其餘錯誤留下警告。"""
        try:
            await self._consumer.enqueue(payload)
        except Exception as exc:
            msg = str(exc).lower()
            # PostgreSQL unique_violation (23505) / PostgREST 對應訊息
            if "23505" in msg or "duplicate key" in msg or "unique" in msg:
                logger.debug("Skip enqueue (already queued): %s", payload.url)
                return
            logger.warning(
                "Enqueue failed for %s: %s", payload.url, exc, exc_info=True
            )

    async def _setup_blocking(self, page: Page) -> None:
        """攔截並拒絕不必要的資源請求，加速爬取。"""
        async def handle(route: Route) -> None:
            if route.request.resource_type in _BLOCK_RESOURCE_TYPES:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", handle)
