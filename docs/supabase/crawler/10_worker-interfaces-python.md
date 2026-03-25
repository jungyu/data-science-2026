# Playwright Worker - Python 介面（Protocol）

所有核心介面皆使用 `typing.Protocol` 實現結構化子型別。

> 資料庫列型別從 `db_types` 模組匯入（參見 `08_db-types-python.md`）。
> Worker 型別從 `types` 模組匯入（參見 `09_worker-types-python.md`）。
>
> **⚠️ ULID 遷移注意**：Protocol 方法中的 `int` 型別 ID 參數，遷移後應改為 `str`。詳見 `08_db-types-python.md` 說明。

---

## 佇列消費者（標準佇列介面）

**唯一**的佇列介面。使用租約（lease）為基礎的並行控制。
包含 `enqueue` 方法，供 PageRunner 新增探索到的網址。

```python
from __future__ import annotations

from typing import Protocol

from .db_types import CrawlQueueRow
from .service_inputs import EnqueueUrlInput
from .types import (
    Json,
    LeasedJob,
    WorkerError,
)


class QueueConsumer(Protocol):
    async def enqueue(self, input: EnqueueUrlInput) -> CrawlQueueRow:
        """將新的網址加入爬取佇列。"""
        ...

    async def lease_next_job(self, worker_id: str) -> LeasedJob | None:
        """原子性地租約下一個待處理的工作。佇列為空時回傳 None。"""
        ...

    async def heartbeat(self, job_id: int, lease_token: str) -> None:
        """延長長時間執行工作的租約到期時間。"""
        ...

    async def complete_job(
        self, job_id: int, lease_token: str, result: Json | None = None
    ) -> None:
        """將工作標記為完成。"""
        ...

    async def fail_job(
        self, job_id: int, lease_token: str, error: WorkerError
    ) -> None:
        """將工作標記為永久失敗。"""
        ...

    async def requeue_job(
        self, job_id: int, lease_token: str, retry_at: str, error: WorkerError
    ) -> None:
        """將工作退回待處理狀態，並設定排程重試時間。"""
        ...
```

---

## Worker 處理器

```python
from .types import LeasedJob, ProcessResult


class WorkerProcessor(Protocol):
    async def process(self, job: LeasedJob) -> ProcessResult:
        """執行單一爬取工作並回傳結果。"""
        ...
```

---

## 頁面擷取器

```python
from playwright.async_api import Page

from .db_types import SourceRow
from .types import (
    ExtractedArticleDraft,
    ListExtractionResult,
)


class PageExtractor(Protocol):
    async def extract_list(
        self, page: Page, source: SourceRow
    ) -> ListExtractionResult:
        """從列表頁面擷取連結與分頁資訊。"""
        ...

    async def extract_article(
        self, page: Page, source: SourceRow
    ) -> ExtractedArticleDraft:
        """從文章頁面擷取正規化的文章內容。"""
        ...
```

---

## 爬取策略引擎

```python
from .db_types import SourceRow
from .types import (
    PolicyDecision,
    ResponseSignal,
    RetryContext,
    RetryDecision,
    WorkerError,
)


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
```

---

## 網域速率限制器

```python
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
```

---

## Repository 介面

### Source Repository

```python
from .db_types import SourceRow


class SourceRepository(Protocol):
    async def find_by_id(self, source_id: int) -> SourceRow | None: ...
    async def find_by_code(self, code: str) -> SourceRow | None: ...
    async def list_enabled(self) -> list[SourceRow]: ...
```

### Crawl Run Repository

```python
from .db_types import CrawlRunLog, CrawlRunRow
from .service_inputs import StartCrawlRunInput


class CrawlRunRepository(Protocol):
    async def create(self, input: StartCrawlRunInput) -> CrawlRunRow: ...
    async def finish(self, run_id: int, patch: dict) -> None: ...
    async def append_log(self, run_id: int, log: CrawlRunLog) -> None: ...
```

### Source Page Repository

```python
from .db_types import SourcePageRow
from .service_inputs import SaveFetchedPageInput


class SourcePageRepository(Protocol):
    async def upsert_page(self, input: SaveFetchedPageInput) -> SourcePageRow: ...
```

### Article Repository

```python
from .db_types import ArticleAssetRow, ArticlePublicationRow, ArticleRow, TagRow
from .service_inputs import UpsertArticleInput


class ArticleRepository(Protocol):
    async def upsert_article(self, input: UpsertArticleInput) -> ArticleRow: ...
    async def get_aggregate_by_id(self, article_id: int) -> ArticleAggregate | None: ...


@dataclass
class ArticleAggregate:
    """定義於此處，與回傳它的 ArticleRepository 並列。"""
    article: ArticleRow
    assets: list[ArticleAssetRow]
    tags: list[TagRow]
    publications: list[ArticlePublicationRow]
```

### Article Asset Repository

```python
from .db_types import ArticleAssetInsert


class ArticleAssetRepository(Protocol):
    async def replace_assets(
        self, article_id: int, assets: list[ArticleAssetInsert]
    ) -> None: ...
```

### Tag Repository

```python
from .db_types import TagRow, TaxonomyType


class TagRepository(Protocol):
    async def ensure_tags(
        self, taxonomy: TaxonomyType, names: list[str]
    ) -> list[TagRow]: ...

    async def attach_tags(
        self, article_id: int, tag_ids: list[int]
    ) -> None: ...
```

---

## 服務輸入型別

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .db_types import CrawlPageType, SourcePageSnapshot
from .types import ExtractedArticleDraft


@dataclass
class EnqueueUrlInput:
    source_id: int
    url: str
    page_type: CrawlPageType = CrawlPageType.ARTICLE
    priority: int = 100
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StartCrawlRunInput:
    source_id: int


@dataclass
class SaveFetchedPageInput:
    source_id: int
    page_type: CrawlPageType
    url: str
    crawl_run_id: int | None = None
    canonical_url: str | None = None
    title: str | None = None
    raw_html: str | None = None
    snapshot_json: SourcePageSnapshot | None = None
    http_status: int | None = None
    fetched_at: str | None = None


@dataclass
class UpsertArticleInput:
    source_id: int
    source_url: str
    draft: ExtractedArticleDraft
    source_page_id: int | None = None
    content_hash: str | None = None
```

---

## 聚合型別

`ArticleAggregate` 定義於上方的 Article Repository 區段中，與回傳它的 Repository 並列。可供外部使用時重新匯出：

```python
from .repositories import ArticleAggregate  # 或 ArticleRepository 所在的模組
```
