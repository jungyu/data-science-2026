"""
Worker 服務輸入型別與核心介面（Protocol）。

來源文件：docs/supabase/04_crawler/10_worker-interfaces-python.md

包含：
    - 服務輸入型別（EnqueueUrlInput、SaveFetchedPageInput 等）
    - 佇列消費者（QueueConsumer）
    - Worker 處理器（WorkerProcessor）
    - 頁面擷取器（PageExtractor）
    - 爬取策略引擎（CrawlPolicyEngine）
    - 網域速率限制器（DomainRateLimiter）
    - Repository 介面（Source / CrawlRun / SourcePage / Article / Asset / Tag）
    - 聚合型別（ArticleAggregate）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from utils.db_types import (
    ArticleAssetInsert,
    ArticleAssetRow,
    ArticleInsert,
    ArticleRow,
    CrawlPageType,
    CrawlQueueRow,
    CrawlRunLog,
    CrawlRunRow,
    SourcePageRow,
    SourcePageSnapshot,
    SourceRow,
    TagInsert,
    TagRow,
    TaxonomyType,
)
from utils.worker.types import (
    ExtractedArticleDraft,
    Json,
    LeasedJob,
    ListExtractionResult,
    PolicyDecision,
    ProcessResult,
    ResponseSignal,
    RetryContext,
    RetryDecision,
    WorkerError,
)


# ============================================================
# 服務輸入型別
# ============================================================

@dataclass
class EnqueueUrlInput:
    project_id: str
    source_id: str
    url: str
    page_type: CrawlPageType = CrawlPageType.ARTICLE
    priority: int = 100
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StartCrawlRunInput:
    project_id: str
    source_id: str


@dataclass
class SaveFetchedPageInput:
    project_id: str
    source_id: str
    page_type: CrawlPageType
    url: str
    crawl_run_id: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    raw_html: str | None = None
    snapshot_json: SourcePageSnapshot | None = None
    http_status: int | None = None
    fetched_at: str | None = None


@dataclass
class UpsertArticleInput:
    project_id: str
    source_id: str
    source_url: str
    draft: ExtractedArticleDraft
    source_page_id: str | None = None
    content_hash: str | None = None


# ============================================================
# 聚合型別（與 ArticleRepository 並列定義）
# ============================================================

@dataclass
class ArticleAggregate:
    """文章及其關聯資產、標籤、發布狀態的聚合檢視。"""
    article: ArticleRow
    assets: list[ArticleAssetRow] = field(default_factory=list)
    tags: list[TagRow] = field(default_factory=list)
    # publications: list[ArticlePublicationRow]  # Phase 3（publish_targets 表）


# ============================================================
# 佇列消費者（Protocol）
# ============================================================

class QueueConsumer(Protocol):
    """Lease-based 佇列介面，唯一的並行控制邊界。"""

    async def enqueue(self, input: EnqueueUrlInput) -> CrawlQueueRow:
        """將新的網址加入爬取佇列。"""
        ...

    async def lease_next_job(self, worker_id: str) -> LeasedJob | None:
        """原子性地租約下一個待處理的工作。佇列為空時回傳 None。"""
        ...

    async def heartbeat(self, job_id: str, lease_token: str) -> None:
        """延長長時間執行工作的租約到期時間。"""
        ...

    async def complete_job(
        self, job_id: str, lease_token: str, result: Json | None = None
    ) -> None:
        """將工作標記為完成。"""
        ...

    async def fail_job(
        self, job_id: str, lease_token: str, error: WorkerError
    ) -> None:
        """將工作標記為永久失敗。"""
        ...

    async def requeue_job(
        self, job_id: str, lease_token: str, retry_at: str, error: WorkerError
    ) -> None:
        """將工作退回待處理狀態，並設定排程重試時間。"""
        ...


# ============================================================
# Worker 處理器（Protocol）
# ============================================================

class WorkerProcessor(Protocol):
    async def process(self, job: LeasedJob) -> ProcessResult:
        """執行單一爬取工作並回傳結果。"""
        ...


# ============================================================
# 頁面擷取器（Protocol）
# ============================================================

class PageExtractor(Protocol):
    async def extract_list(
        self, page: Any, source: SourceRow
    ) -> ListExtractionResult:
        """從列表頁面擷取連結與分頁資訊。"""
        ...

    async def extract_article(
        self, page: Any, source: SourceRow
    ) -> ExtractedArticleDraft:
        """從文章頁面擷取正規化的文章內容。"""
        ...


# ============================================================
# 爬取策略引擎（Protocol）
# ============================================================

class CrawlPolicyEngine(Protocol):
    async def before_request(
        self, source: SourceRow, url: str
    ) -> PolicyDecision:
        """檢查請求是否被允許。可能回傳延遲或拒絕。"""
        ...

    async def after_response(
        self, source: SourceRow, result: ResponseSignal
    ) -> None:
        """根據回應訊號更新來源健康狀態。"""
        ...

    def decide_retry(
        self, error: WorkerError, ctx: RetryContext
    ) -> RetryDecision:
        """根據錯誤與上下文，決定重試／失敗／停用／跳過。"""
        ...


# ============================================================
# 網域速率限制器（Protocol）
# ============================================================

class DomainRateLimiter(Protocol):
    async def acquire(self, domain: str) -> None:
        """等待直到該網域有可用的請求名額。"""
        ...

    def release(self, domain: str) -> None:
        """完成後釋放請求名額。"""
        ...

    async def mark_penalty(self, domain: str, reason: str) -> None:
        """對網域施加冷卻懲罰。"""
        ...


# ============================================================
# Repository 介面（Protocols）
# ============================================================

class SourceRepository(Protocol):
    async def find_by_id(self, source_id: str) -> SourceRow | None: ...
    async def find_by_code(self, code: str) -> SourceRow | None: ...
    async def list_enabled(self) -> list[SourceRow]: ...


class CrawlRunRepository(Protocol):
    async def create(self, input: StartCrawlRunInput) -> CrawlRunRow: ...
    async def finish(self, run_id: str, patch: dict) -> None: ...
    async def append_log(self, run_id: str, log: CrawlRunLog) -> None: ...


class SourcePageRepository(Protocol):
    async def upsert_page(self, input: SaveFetchedPageInput) -> SourcePageRow: ...


class ArticleRepository(Protocol):
    async def upsert_article(self, input: UpsertArticleInput) -> ArticleRow: ...
    async def get_aggregate_by_id(
        self, article_id: str
    ) -> ArticleAggregate | None: ...


class ArticleAssetRepository(Protocol):
    async def replace_assets(
        self, article_id: str, assets: list[ArticleAssetInsert]
    ) -> None: ...


class TagRepository(Protocol):
    async def ensure_tags(
        self, taxonomy: TaxonomyType, names: list[str]
    ) -> list[TagRow]: ...

    async def attach_tags(
        self, article_id: str, tag_ids: list[str]
    ) -> None: ...
