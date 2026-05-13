"""
SupabaseQueueConsumer — QueueConsumer Protocol 的 Supabase 實作。

來源文件：docs/supabase/04_crawler/06_worker-consume-loop-python.md

職責：封裝所有 crawl_queue 的資料庫操作（lease / complete / fail / requeue）。
PageRunner 只依賴 QueueConsumer Protocol，不直接操作 Supabase。
"""

from __future__ import annotations

import logging

from supabase import AsyncClient

from utils.config import LEASE_DURATION_MINUTES
from utils.db_types import CrawlPageType, CrawlQueueRow
from utils.time_helpers import future_iso as _future_iso
from utils.time_helpers import now_iso as _now_iso
from utils.worker.service_inputs import EnqueueUrlInput
from utils.worker.types import Json, LeasedJob, WorkerError

logger = logging.getLogger(__name__)


# ── 佇列消費者 ────────────────────────────────────────────────────

class SupabaseQueueConsumer:
    """實作 QueueConsumer protocol，對接 Supabase crawl_queue。

    所有狀態變更都用 lease_token 做樂觀鎖：
    lease 過期後的 update 因 token 不符而靜默失效，不會覆蓋其他 Worker 的工作。
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _table(self):
        return self._client.schema("crawler").table("crawl_queue")

    async def enqueue(self, input: EnqueueUrlInput) -> CrawlQueueRow:
        """將新 URL 加入佇列。ignore_duplicates 讓 partial unique index 靜默跳過。"""
        result = await self._table().insert(
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
        """原子性地租用下一筆待處理任務。佇列空時回傳 None。

        RPC 內部以 FOR UPDATE SKIP LOCKED 確保多 Worker 不搶同一筆。
        """
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
            payload=row.get("payload") or {},
        )

    async def heartbeat(self, job_id: str, lease_token: str) -> None:
        """延長 lease 5 分鐘，供長時間任務避免到期被其他 Worker 接手。"""
        await self._table().update(
            {"lease_expires_at": _future_iso(LEASE_DURATION_MINUTES)}
        ).eq("id", job_id).eq("lease_token", lease_token).execute()

    async def complete_job(
        self, job_id: str, lease_token: str, result: Json | None = None
    ) -> None:
        """任務成功完成，標記為 done。"""
        await self._table().update(
            {"status": "done", "finished_at": _now_iso()}
        ).eq("id", job_id).eq("lease_token", lease_token).execute()

    async def fail_job(
        self, job_id: str, lease_token: str, error: WorkerError
    ) -> None:
        """任務永久失敗（不重試），標記為 failed。"""
        await self._table().update(
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
        """退回佇列並安排重試。超過 max_retries 則標記為 dead。

        requeue 需要讀目前的 retry_count，再決定是 pending 還是 dead。
        """
        row_result = await self._table().select(
            "retry_count, max_retries"
        ).eq("id", job_id).single().execute()

        current = row_result.data
        new_retry = current["retry_count"] + 1
        new_status = "dead" if new_retry >= current["max_retries"] else "pending"

        await self._table().update(
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
        logger.info(
            "Job %s requeued → %s (retry %d/%d, at %s)",
            job_id, new_status, new_retry, current["max_retries"], retry_at,
        )
