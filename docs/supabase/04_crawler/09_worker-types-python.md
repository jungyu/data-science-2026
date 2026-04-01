# Playwright Worker — Python 型別參考（Layer 2）

> **這份文件的定位**：三層型別架構的中間層，專屬於 Worker pipeline，不綁定資料庫 schema。

## 這層型別在 pipeline 的哪裡？

```
crawl_queue (DB)
    ↓ lease_next_crawl_job()
  LeasedJob          ← Worker 搶到任務後，拿到的是這個，不是 CrawlQueueRow
    ↓ PageRunner.process()
  ProcessResult      ← 任務的結果：Done / Retry / Failed / Skipped（四選一）
    ↓ 依結果型別
  RetryDecision      ← 如果是 Retry，decide_retry() 決定何時重試
```

**為什麼不直接用 `CrawlQueueRow`？**
`CrawlQueueRow` 含有所有 DB 欄位（30 個），但 Worker 在處理任務時只需要其中幾個（url、page_type、lease_token、retry_count）。
`LeasedJob` 只保留 Worker 真正需要的欄位，讓程式碼不必依賴完整的 DB 結構。

**為什麼 `ProcessResult` 是 union type？**
一個任務的結果只有四種可能，且每種後續處理方式完全不同：
- `Done` → 呼叫 `complete_job()`
- `Retry` → 呼叫 `requeue_job()`，帶 `retry_at`
- `Failed` → 呼叫 `fail_job()`，永久失敗
- `Skipped` → 呼叫 `complete_job()`，但不計入成功統計

用 union type 配合 `isinstance()` 判斷，比用 `status` 字串欄位更安全（型別檢查器會提醒你沒處理到某種情況）。

> 已對齊 `003_crawler_schema.sql` v3.0（ULID text PK）。所有 ID 欄位皆為 `str`。

---

---

## 共用

```python
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Literal

# 通用 JSON 別名
Json = str | int | float | bool | None | dict[str, Any] | list[Any]
```

---

## 從 db-types 重新匯出

以下 enum 定義於 `db_types`，在此重新匯出以方便使用：

```python
from utils.db_types import (
    CrawlPageType,
    CrawlQueueStatus,
    CrawlRunLog,
    CrawlRunStatus,
    SourcePageSnapshot,
    TaxonomyType,
)
```

---

## 已租賃任務（由 `lease_next_job` 回傳）

```python
@dataclass
class LeasedJob:
    job_id: str
    source_id: str
    url: str
    page_type: CrawlPageType
    lease_token: str
    retry_count: int
    max_retries: int
    payload: dict[str, Any] = field(default_factory=dict)
```

---

## 錯誤型別

```python
class WorkerErrorCode(str, enum.Enum):
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    HTTP_403 = "HTTP_403"
    HTTP_404 = "HTTP_404"
    HTTP_429 = "HTTP_429"
    HTTP_5XX = "HTTP_5XX"
    ROBOTS_DENIED = "ROBOTS_DENIED"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    SELECTOR_MISSING = "SELECTOR_MISSING"
    BROWSER_CRASH = "BROWSER_CRASH"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class WorkerError:
    code: WorkerErrorCode
    message: str
    retryable: bool
    details: dict[str, Any] | None = None
```

---

## 處理結果

```python
@dataclass
class ProcessResultDone:
    status: Literal["done"] = "done"
    page_id: str | None = None
    article_id: str | None = None
    discovered_urls: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProcessResultRetry:
    status: Literal["retry"] = "retry"
    retry_at: str = ""
    error: WorkerError | None = None


@dataclass
class ProcessResultFailed:
    status: Literal["failed"] = "failed"
    error: WorkerError | None = None


@dataclass
class ProcessResultSkipped:
    status: Literal["skipped"] = "skipped"
    reason: str = ""


ProcessResult = ProcessResultDone | ProcessResultRetry | ProcessResultFailed | ProcessResultSkipped
```

---

## Retry 型別

```python
@dataclass
class RetryDecisionRetry:
    action: Literal["retry"] = "retry"
    retry_at: str = ""
    reason: str = ""


@dataclass
class RetryDecisionFail:
    action: Literal["fail"] = "fail"
    reason: str = ""


@dataclass
class RetryDecisionDead:
    action: Literal["dead"] = "dead"
    reason: str = ""


@dataclass
class RetryDecisionSkip:
    action: Literal["skip"] = "skip"
    reason: str = ""


RetryDecision = RetryDecisionRetry | RetryDecisionFail | RetryDecisionDead | RetryDecisionSkip


@dataclass
class RetryContext:
    retry_count: int
    max_retries: int
    source_id: str
    url: str
    page_type: CrawlPageType
    last_error: WorkerError | None = None
```

---

## 來源健康狀態

```python
class SourceHealthState(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"


@dataclass
class SourceHealth:
    source_id: str
    state: SourceHealthState = SourceHealthState.HEALTHY
    active_requests: int = 0
    last_request_at: str | None = None
    penalty_until: str | None = None
    consecutive_failures: int = 0
    consecutive_429s: int = 0
    consecutive_403s: int = 0
```

---

## 來源爬取政策

```python
@dataclass
class SourceCrawlPolicy:
    max_concurrency_per_domain: int = 1
    min_interval_ms: int = 2000
    max_retries: int = 5
    timeout_ms: int = 30000
    cooldown_on_429_ms: int = 60000
    cooldown_on_403_ms: int = 300000
    block_resource_types: list[str] = field(default_factory=lambda: ["image", "font", "media", "stylesheet"])
    respect_robots: bool = True
```

---

## 政策決策

```python
@dataclass
class PolicyDecisionAllow:
    action: Literal["allow"] = "allow"


@dataclass
class PolicyDecisionDelay:
    action: Literal["delay"] = "delay"
    delay_ms: int = 0
    reason: str = ""


@dataclass
class PolicyDecisionDeny:
    action: Literal["deny"] = "deny"
    reason: str = ""


PolicyDecision = PolicyDecisionAllow | PolicyDecisionDelay | PolicyDecisionDeny
```

---

## 頁面擷取型別

### 來源頁面快照

```python
from utils.db_types import SourcePageSnapshot  # 重用資料庫型別
```

### 列表擷取結果

```python
@dataclass
class ListExtractionResult:
    title: str | None = None
    discovered_urls: list[str] = field(default_factory=list)
    next_page_url: str | None = None
    snapshot: SourcePageSnapshot | None = None
```

### 草稿附件（必須在 ExtractedArticleDraft 之前定義）

```python
@dataclass
class DraftAsset:
    original_url: str = ""
    asset_type: str | None = None
    alt_text: str | None = None
    caption: str | None = None
```

### 擷取的文章草稿

```python
@dataclass
class ExtractedArticleDraft:
    title: str = ""
    author_name: str | None = None
    published_at: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    canonical_url: str | None = None
    lang: str | None = None
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    assets: list[DraftAsset] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    extraction_data: dict[str, Any] = field(default_factory=dict)
```

---

## 回應信號（供政策引擎使用）

```python
@dataclass
class ResponseSignal:
    url: str = ""
    http_status: int | None = None
    content_length: int | None = None
    ttfb_ms: float | None = None
    has_captcha: bool = False
    has_challenge: bool = False
    is_redirect_loop: bool = False
    is_empty_body: bool = False
    error: WorkerError | None = None
```
