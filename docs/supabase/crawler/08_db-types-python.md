# Playwright Crawler — Python 資料庫列型別

所有資料庫列/插入/更新型別皆以 Python `dataclass` 定義，與 `003_crawler_schema.sql` 對齊。

> 從 `12_typescript-types.md` 轉換而來。此為權威性的 Python 版本。
> 已對齊 `003_crawler_schema.sql` v3.0（ULID text PK + project_id 多租戶）。

---

## 共用

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Json = str | int | float | bool | None | dict[str, Any] | list[Any]
```

---

## 1. 來源（Sources）

### 設定型別

```python
from dataclasses import dataclass, field


@dataclass
class SourceCookieConfig:
    name: str = ""
    value: str = ""
    domain: str | None = None
    path: str | None = None


@dataclass
class SourceConfig:
    user_agent: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: list[SourceCookieConfig] = field(default_factory=list)
    wait_until: str | None = None  # "load" | "domcontentloaded" | "networkidle"
    timeout_ms: int | None = None
    use_proxy: bool = False
    proxy_key: str | None = None
    block_resources: list[str] = field(default_factory=list)
    login_required: bool = False


@dataclass
class ListExtractorSchema:
    item_selector: str | None = None
    link_selector: str | None = None
    title_selector: str | None = None
    next_page_selector: str | None = None


@dataclass
class ArticleExtractorSchema:
    title_selector: str | None = None
    author_selector: str | None = None
    published_at_selector: str | None = None
    content_selector: str | None = None
    remove_selectors: list[str] = field(default_factory=list)
    tag_selector: str | None = None
    category_selector: str | None = None
    asset_selector: str | None = None


@dataclass
class ExtractorSchema:
    list: ListExtractorSchema | None = None
    article: ArticleExtractorSchema | None = None


@dataclass
class FieldMapping:
    title: str | None = None
    author_name: str | None = None
    published_at: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    tags: str | None = None
    categories: str | None = None
```

### 列型別

```python
@dataclass
class SourceRow:
    id: str
    project_id: str
    code: str
    name: str
    description: str | None
    base_url: str | None
    domain: str | None
    crawler_url: str | None
    config: SourceConfig
    extractor_schema: ExtractorSchema
    field_mapping: FieldMapping
    is_enabled: bool
    schedule_cron: str | None
    last_run_at: str | None
    created_by: str | None
    created_at: str
    updated_at: str


@dataclass
class SourceInsert:
    project_id: str
    code: str
    name: str
    config: SourceConfig = field(default_factory=SourceConfig)
    extractor_schema: ExtractorSchema = field(default_factory=ExtractorSchema)
    field_mapping: FieldMapping = field(default_factory=FieldMapping)
    is_enabled: bool = True
    description: str | None = None
    base_url: str | None = None
    domain: str | None = None
    crawler_url: str | None = None
    schedule_cron: str | None = None
    last_run_at: str | None = None
    created_by: str | None = None


@dataclass
class SourceUpdate:
    """所有欄位皆為可選，用於部分更新。"""
    code: str | None = None
    name: str | None = None
    description: str | None = None
    base_url: str | None = None
    domain: str | None = None
    crawler_url: str | None = None
    config: SourceConfig | None = None
    extractor_schema: ExtractorSchema | None = None
    field_mapping: FieldMapping | None = None
    is_enabled: bool | None = None
    schedule_cron: str | None = None
```

---

## 2. 爬取佇列（Crawl Queue）

```python
import enum


class CrawlPageType(str, enum.Enum):
    LIST = "list"
    ARTICLE = "article"
    DETAIL = "detail"
    UNKNOWN = "unknown"


class CrawlQueueStatus(str, enum.Enum):
    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEAD = "dead"


@dataclass
class CrawlQueuePayload:
    referrer_url: str | None = None
    topic: str | None = None
    depth: int | None = None
    discovered_from: str | None = None  # "seed" | "list" | "manual" | "retry"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlQueueRow:
    id: str
    project_id: str
    source_id: str
    url: str
    page_type: CrawlPageType
    priority: int
    status: CrawlQueueStatus
    retry_count: int
    max_retries: int
    scheduled_at: str
    lease_token: str | None = None
    leased_at: str | None = None
    lease_expires_at: str | None = None
    worker_id: str | None = None
    locked_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    payload: CrawlQueuePayload = field(default_factory=CrawlQueuePayload)
    created_at: str = ""


@dataclass
class CrawlQueueInsert:
    project_id: str
    source_id: str
    url: str
    page_type: CrawlPageType = CrawlPageType.ARTICLE
    priority: int = 100
    status: CrawlQueueStatus = CrawlQueueStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5
    scheduled_at: str | None = None
    payload: CrawlQueuePayload = field(default_factory=CrawlQueuePayload)
```

---

## 3. 爬取執行記錄（Crawl Runs）

```python
class CrawlRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class CrawlRunLog:
    ts: str
    level: str  # "debug" | "info" | "warn" | "error"
    message: str
    context: dict[str, Any] | None = None


@dataclass
class CrawlRunRow:
    id: str
    project_id: str
    source_id: str
    run_status: CrawlRunStatus
    started_at: str | None
    finished_at: str | None
    pages_found: int
    pages_fetched: int
    articles_extracted: int
    error_count: int
    logs: list[CrawlRunLog]
    created_at: str
    updated_at: str


@dataclass
class CrawlRunInsert:
    project_id: str
    source_id: str
    run_status: CrawlRunStatus = CrawlRunStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    pages_found: int = 0
    pages_fetched: int = 0
    articles_extracted: int = 0
    error_count: int = 0
    logs: list[CrawlRunLog] = field(default_factory=list)
```

---

## 4. 來源頁面（Source Pages）

```python
@dataclass
class SourcePageSnapshot:
    final_url: str | None = None
    title: str | None = None
    meta: dict[str, str] | None = None
    links: list[str] | None = None
    screenshots: list[str] | None = None
    extracted_selectors: dict[str, str] | None = None


@dataclass
class SourcePageRow:
    id: str
    project_id: str
    source_id: str
    crawl_run_id: str | None
    page_type: CrawlPageType
    topic: str | None
    url: str
    canonical_url: str | None
    title: str | None
    raw_html: str | None
    snapshot_json: SourcePageSnapshot | None
    http_status: int | None
    fetched_at: str | None
    last_seen_at: str | None
    is_available: bool
    created_at: str
    updated_at: str


@dataclass
class SourcePageInsert:
    project_id: str
    source_id: str
    url: str
    page_type: CrawlPageType = CrawlPageType.ARTICLE
    crawl_run_id: str | None = None
    topic: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    raw_html: str | None = None
    snapshot_json: SourcePageSnapshot | None = None
    http_status: int | None = None
    fetched_at: str | None = None
    last_seen_at: str | None = None
    is_available: bool = True
```

---

## 5. 文章（Articles）

### 中繼資料型別

```python
@dataclass
class ArticleMeta:
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    og_image: str | None = None
    section: str | None = None
    keywords: list[str] = field(default_factory=list)
    byline_raw: str | None = None
    source_labels: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArticleExtractionData:
    extractor_version: str | None = None
    raw_published_at: str | None = None
    raw_author: str | None = None
    selector_matches: dict[str, str] = field(default_factory=dict)
    extraction_warnings: list[str] = field(default_factory=list)
    language_confidence: float | None = None
    ai_normalized: bool = False
```

### 列型別

```python
@dataclass
class ArticleRow:
    id: str
    project_id: str
    source_id: str
    source_page_id: str | None
    external_id: str | None
    title: str
    slug: str | None
    author_name: str | None
    author_url: str | None
    abstract: str | None
    content_html: str | None
    content_text: str | None
    published_at: str | None
    source_modified_at: str | None
    source_url: str
    canonical_url: str | None
    lang: str | None
    meta: ArticleMeta
    extraction_data: ArticleExtractionData
    is_published: bool
    is_available: bool
    content_hash: str | None
    created_at: str
    updated_at: str


@dataclass
class ArticleInsert:
    project_id: str
    source_id: str
    title: str
    source_url: str
    source_page_id: str | None = None
    external_id: str | None = None
    slug: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    abstract: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    published_at: str | None = None
    source_modified_at: str | None = None
    canonical_url: str | None = None
    lang: str | None = None
    meta: ArticleMeta = field(default_factory=ArticleMeta)
    extraction_data: ArticleExtractionData = field(default_factory=ArticleExtractionData)
    is_published: bool = True
    is_available: bool = True
    content_hash: str | None = None
```

---

## 6. 文章附件（Article Assets）

```python
class AssetType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    AUDIO = "audio"


@dataclass
class ArticleAssetRow:
    id: str
    project_id: str
    article_id: str
    source_page_id: str | None
    asset_type: AssetType
    original_url: str | None
    storage_bucket: str | None
    storage_path: str | None
    mime_type: str | None
    alt_text: str | None
    caption: str | None
    width: int | None
    height: int | None
    checksum: str | None
    sort_order: int
    created_at: str
    updated_at: str


@dataclass
class ArticleAssetInsert:
    project_id: str
    article_id: str
    asset_type: AssetType = AssetType.IMAGE
    source_page_id: str | None = None
    original_url: str | None = None
    storage_bucket: str | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    alt_text: str | None = None
    caption: str | None = None
    width: int | None = None
    height: int | None = None
    checksum: str | None = None
    sort_order: int = 0
```

---

## 7. 標籤 / 文章標籤（Tags / Article Tags）

```python
class TaxonomyType(str, enum.Enum):
    TAG = "tag"
    CATEGORY = "category"
    TOPIC = "topic"
    SERIES = "series"


@dataclass
class TagMeta:
    color: str | None = None
    icon: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class TagRow:
    id: str
    project_id: str
    taxonomy: TaxonomyType
    name: str
    slug: str | None
    description: str | None
    parent_id: str | None
    meta: TagMeta
    created_at: str
    updated_at: str


@dataclass
class TagInsert:
    project_id: str
    taxonomy: TaxonomyType
    name: str
    slug: str | None = None
    description: str | None = None
    parent_id: str | None = None
    meta: TagMeta = field(default_factory=TagMeta)


@dataclass
class ArticleTagRow:
    article_id: str
    tag_id: str
    created_at: str
```

---

## 8. 發佈目標 / 文章發佈記錄（Publish Targets / Article Publications）

```python
class PublishTargetType(str, enum.Enum):
    WORDPRESS = "wordpress"
    NOTION = "notion"
    GHOST = "ghost"
    CUSTOM_API = "custom_api"
    INTERNAL = "internal"


class PublishStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class PublishTargetConfig:
    endpoint: str | None = None
    site_url: str | None = None
    database_id: str | None = None
    auth_type: str | None = None  # "token" | "oauth" | "basic"
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishTargetRow:
    id: str
    project_id: str
    code: str
    name: str
    target_type: PublishTargetType
    config: PublishTargetConfig
    is_enabled: bool
    created_by: str | None
    created_at: str
    updated_at: str


@dataclass
class PublishTargetInsert:
    project_id: str
    code: str
    name: str
    target_type: PublishTargetType
    config: PublishTargetConfig = field(default_factory=PublishTargetConfig)
    is_enabled: bool = True
    created_by: str | None = None


@dataclass
class ArticlePublicationRow:
    id: str
    project_id: str
    article_id: str
    target_id: str
    remote_id: str | None
    remote_url: str | None
    publish_status: PublishStatus
    last_published_at: str | None
    payload: dict[str, Any]
    result: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class ArticlePublicationInsert:
    project_id: str
    article_id: str
    target_id: str
    publish_status: PublishStatus = PublishStatus.PENDING
    remote_id: str | None = None
    remote_url: str | None = None
    last_published_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
```
