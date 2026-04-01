"""
Crawler DB 型別定義。

對應 003_crawler_schema.sql v3.0 的所有資料表，
以 Python dataclass 表示 Row / Insert 兩種形態。

來源文件：docs/supabase/04_crawler/08_db-types-python.md

型別架構：
    - *Row     — 從 DB 讀回的完整列（含 id / created_at / updated_at）
    - *Insert  — 寫入 DB 時使用（省略自動產生的欄位）
    - *Status  — CHECK constraint 對應的 Enum

序列化工具：
    to_insert_dict(obj)  — 將 Insert dataclass 轉成可直接傳給 Supabase 的 dict
                           自動跳過 None 值、展開巢狀 dataclass、轉換 Enum 為字串
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from typing import Any


Json = str | int | float | bool | None | dict[str, Any] | list[Any]


# ============================================================
# 序列化工具
# ============================================================

def to_insert_dict(obj: Any, *, exclude_none: bool = True) -> dict[str, Any]:
    """將 Insert dataclass 轉成 Supabase 可接受的 dict。

    - None 值預設排除（Supabase 用 DB default）
    - Enum → 其 .value（字串）
    - 巢狀 dataclass → 遞迴轉換為 dict（用於 jsonb 欄位）
    - list → 每個元素遞迴處理

    Args:
        obj: 任意 Insert dataclass 實例
        exclude_none: 是否排除 None 欄位（預設 True）

    Returns:
        可直接傳入 .insert() / .upsert() 的 dict
    """
    if not dataclasses.is_dataclass(obj):
        raise TypeError(f"to_insert_dict 只接受 dataclass，收到 {type(obj)}")

    result: dict[str, Any] = {}
    for f in dataclasses.fields(obj):
        val = getattr(obj, f.name)
        if val is None:
            if not exclude_none:
                result[f.name] = None
            continue
        result[f.name] = _serialize(val)
    return result


def _serialize(val: Any) -> Any:
    if isinstance(val, enum.Enum):
        return val.value
    if dataclasses.is_dataclass(val):
        return {
            f.name: _serialize(getattr(val, f.name))
            for f in dataclasses.fields(val)
            if getattr(val, f.name) is not None
        }
    if isinstance(val, list):
        return [_serialize(v) for v in val]
    return val


# ============================================================
# 1. Sources（crawler.sources）
# ============================================================

@dataclass
class SourceCookieConfig:
    name: str = ""
    value: str = ""
    domain: str | None = None
    path: str | None = None


@dataclass
class SourceConfig:
    """對應 crawler.sources.config jsonb。"""
    user_agent: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: list[SourceCookieConfig] = field(default_factory=list)
    wait_until: str | None = None       # "load" | "domcontentloaded" | "networkidle"
    timeout_ms: int | None = None
    use_proxy: bool = False
    proxy_key: str | None = None
    block_resources: list[str] = field(default_factory=list)
    login_required: bool = False


@dataclass
class ListExtractorSchema:
    """列表頁的擷取規則。"""
    item_selector: str | None = None
    link_selector: str | None = None
    title_selector: str | None = None
    next_page_selector: str | None = None


@dataclass
class ArticleExtractorSchema:
    """文章頁的擷取規則。"""
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
    """對應 crawler.sources.extractor_schema jsonb。"""
    list: ListExtractorSchema | None = None
    article: ArticleExtractorSchema | None = None


@dataclass
class FieldMapping:
    """對應 crawler.sources.field_mapping jsonb。"""
    title: str | None = None
    author_name: str | None = None
    published_at: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    tags: str | None = None
    categories: str | None = None


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
    config: dict[str, Any]            # jsonb，從 DB 讀回為 dict
    extractor_schema: dict[str, Any]  # jsonb
    field_mapping: dict[str, Any]     # jsonb
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
    """所有欄位皆為可選，用於部分更新（PATCH 語意）。"""
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


# ============================================================
# 2. Crawl Runs（crawler.crawl_runs）
# ============================================================

class CrawlRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class CrawlRunLog:
    """單筆執行日誌。"""
    ts: str                              # ISO 8601
    level: str                           # "debug" | "info" | "warn" | "error"
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


# ============================================================
# 3. Crawl Queue（crawler.crawl_queue）
# ============================================================

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
    """任務附帶的額外資訊（存於 payload jsonb）。"""
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
    lease_token: str | None
    leased_at: str | None
    lease_expires_at: str | None
    worker_id: str | None
    locked_at: str | None
    finished_at: str | None
    error_code: str | None
    error_message: str | None
    payload: CrawlQueuePayload
    created_at: str


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


# ============================================================
# 4. Source Pages（crawler.source_pages）
# ============================================================

@dataclass
class SourcePageSnapshot:
    """存於 snapshot_json jsonb 的頁面快照。"""
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
    snapshot_json: dict[str, Any] | None
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


# ============================================================
# 5. Articles（crawler.articles）
# ============================================================

@dataclass
class ArticleMeta:
    """存於 articles.meta jsonb。"""
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
    """存於 articles.extraction_data jsonb，記錄擷取過程資訊。"""
    extractor_version: str | None = None
    raw_published_at: str | None = None
    raw_author: str | None = None
    selector_matches: dict[str, str] = field(default_factory=dict)
    extraction_warnings: list[str] = field(default_factory=list)
    language_confidence: float | None = None
    ai_normalized: bool = False


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
    meta: dict[str, Any]
    extraction_data: dict[str, Any]
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


# ============================================================
# 6. Article Assets（crawler.article_assets）
# ============================================================

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


# ============================================================
# 7. Tags（crawler.tags / crawler.article_tags）
# ============================================================

class TaxonomyType(str, enum.Enum):
    TAG = "tag"
    CATEGORY = "category"
    TOPIC = "topic"
    SERIES = "series"


@dataclass
class TagRow:
    id: str
    project_id: str
    taxonomy: TaxonomyType
    name: str
    slug: str | None
    description: str | None
    parent_id: str | None
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


@dataclass
class ArticleTagInsert:
    article_id: str
    tag_id: str
