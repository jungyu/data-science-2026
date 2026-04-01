"""
Worker 主消費迴圈（async）。

來源文件：docs/supabase/04_crawler/06_worker-consume-loop-python.md

與 ch08-supabase/04_single_job_worker.py 的關係：
  04_single_job_worker.py → 同步單次版，教學用，一次消費一筆
  utils/worker/main.py    → 非同步持續版，生產用，持續輪詢直到閒置逾時

執行方式：
    cd project-playwright
    python -m utils.worker.main

環境變數：
    SUPABASE_URL        Supabase 專案 URL
    SUPABASE_SERVICE_KEY Service role key（繞過 RLS）
    PROJECT_ID          多租戶 project id
    SOURCE_CODE         （可選）只消費特定 source（預設：消費全部）
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from supabase import AsyncClient, acreate_client

from utils.worker.browser_pool import BrowserPool
from utils.worker.consumer import SupabaseQueueConsumer
from utils.worker.page_runner import PageRunner
from utils.worker.persistence.article_repo import SupabaseArticleRepo
from utils.worker.persistence.source_page_repo import SupabaseSourcePageRepo
from utils.worker.persistence.source_repo import SupabaseSourceRepo
from utils.worker.policies.rate_limit_policy import DomainLimiter, SourceHealthTracker
from utils.worker.types import (
    ProcessResultDone,
    ProcessResultFailed,
    ProcessResultRetry,
    ProcessResultSkipped,
    WorkerError,
    WorkerErrorCode,
)

logger = logging.getLogger(__name__)

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
POLL_INTERVAL_SEC = 5       # 佇列空時輪詢間隔（秒）
MAX_EMPTY_POLLS = 60        # 連續空佇列次數上限（60 × 5s = 5 分鐘後停止）


async def main(client: AsyncClient) -> None:
    """持續消費 crawl_queue，直到 MAX_EMPTY_POLLS 次連續空佇列。

    架構：
        consumer  → lease / complete / fail / requeue
        runner    → fetch + extract + persist（BrowserPool + extractors + repos）
        health    → 來源健康狀態（429/403 → cooldown）
        limiter   → 每 domain 並行數上限（預設 1）
    """
    consumer = SupabaseQueueConsumer(client)
    health_tracker = SourceHealthTracker()
    domain_limiter = DomainLimiter(default_max=1)

    source_repo = SupabaseSourceRepo(client)
    source_page_repo = SupabaseSourcePageRepo(client)
    article_repo = SupabaseArticleRepo(client)

    async with async_playwright() as pw:
        pool = BrowserPool(pw)
        await pool.start()

        runner = PageRunner(
            pool=pool,
            consumer=consumer,
            source_repo=source_repo,
            source_page_repo=source_page_repo,
            article_repo=article_repo,
        )

        empty_polls = 0

        try:
            while empty_polls < MAX_EMPTY_POLLS:
                # 1. 租用下一筆任務
                job = await consumer.lease_next_job(WORKER_ID)

                if job is None:
                    empty_polls += 1
                    logger.debug(
                        "Queue empty (%d/%d), waiting %ds...",
                        empty_polls, MAX_EMPTY_POLLS, POLL_INTERVAL_SEC,
                    )
                    await asyncio.sleep(POLL_INTERVAL_SEC)
                    continue

                empty_polls = 0
                domain = urlparse(job.url).netloc

                # 2. 檢查來源健康狀態
                if not health_tracker.is_available(job.source_id):
                    logger.info(
                        "Source %s in cooldown → requeue job %s",
                        job.source_id, job.job_id,
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

                    # 5. 依結果型別更新佇列狀態
                    if isinstance(result, ProcessResultDone):
                        await consumer.complete_job(job.job_id, job.lease_token)
                        health_tracker.record_success(job.source_id)
                        logger.info(
                            "Done: job=%s url=%s discovered=%d",
                            job.job_id, job.url, len(result.discovered_urls),
                        )

                    elif isinstance(result, ProcessResultRetry):
                        error = result.error or WorkerError(
                            code=WorkerErrorCode.UNKNOWN,
                            message="Retry without error context",
                            retryable=True,
                        )
                        health_tracker.record_failure(job.source_id, error)
                        await consumer.requeue_job(
                            job.job_id, job.lease_token,
                            retry_at=result.retry_at, error=error,
                        )
                        logger.warning(
                            "Retry: job=%s code=%s msg=%s",
                            job.job_id, error.code.value, error.message,
                        )

                    elif isinstance(result, ProcessResultFailed):
                        error = result.error or WorkerError(
                            code=WorkerErrorCode.UNKNOWN,
                            message="Failed without error context",
                            retryable=False,
                        )
                        health_tracker.record_failure(job.source_id, error)
                        await consumer.fail_job(job.job_id, job.lease_token, error)
                        logger.error(
                            "Failed: job=%s code=%s msg=%s",
                            job.job_id, error.code.value, error.message,
                        )

                    elif isinstance(result, ProcessResultSkipped):
                        await consumer.complete_job(job.job_id, job.lease_token)
                        logger.info(
                            "Skipped: job=%s reason=%s", job.job_id, result.reason
                        )

                except Exception:
                    logger.exception("Unexpected error processing job %s", job.job_id)
                    await consumer.fail_job(
                        job.job_id,
                        job.lease_token,
                        WorkerError(
                            code=WorkerErrorCode.UNKNOWN,
                            message="Unexpected exception in main loop",
                            retryable=False,
                        ),
                    )
                finally:
                    domain_limiter.release(domain)

        finally:
            await pool.stop()

    logger.info(
        "Worker %s shutting down after %d empty polls (idle timeout).",
        WORKER_ID, MAX_EMPTY_POLLS,
    )


def _minutes_from_now(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    async def _run():
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        client = await acreate_client(url, key)
        await main(client)

    asyncio.run(_run())
