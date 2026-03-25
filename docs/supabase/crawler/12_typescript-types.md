# Playwright Crawler - TypeScript 型別參考

> **已取代**：Python 版本請見 `08_db-types-python.md` + `09_worker-types-python.md`。本檔案僅保留作為 TypeScript 參考。

所有型別皆對齊 `03_playwright_crawler_schema.sql`。

---

## 通用型別

```ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json }
  | Json[];
```

---

## 1. 來源（Sources）

### 設定型別

```ts
export type SourceConfig = {
  userAgent?: string;
  headers?: Record<string, string>;
  cookies?: Array<{
    name: string;
    value: string;
    domain?: string;
    path?: string;
  }>;
  waitUntil?: "load" | "domcontentloaded" | "networkidle";
  timeoutMs?: number;
  useProxy?: boolean;
  proxyKey?: string;
  blockResources?: string[];
  loginRequired?: boolean;
};

export type ExtractorSchema = {
  list?: {
    itemSelector?: string;
    linkSelector?: string;
    titleSelector?: string;
    nextPageSelector?: string;
  };
  article?: {
    titleSelector?: string;
    authorSelector?: string;
    publishedAtSelector?: string;
    contentSelector?: string;
    removeSelectors?: string[];
    tagSelector?: string;
    categorySelector?: string;
    assetSelector?: string;
  };
};

export type FieldMapping = {
  title?: string;
  author_name?: string;
  published_at?: string;
  content_html?: string;
  content_text?: string;
  tags?: string;
  categories?: string;
};
```

### 列型別

```ts
export type SourceRow = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  base_url: string | null;
  domain: string | null;
  crawler_url: string | null;
  config: SourceConfig;
  extractor_schema: ExtractorSchema;
  field_mapping: FieldMapping;
  is_enabled: boolean;
  schedule_cron: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceInsert = Omit<
  SourceRow,
  "id" | "created_at" | "updated_at" | "last_run_at"
> & {
  last_run_at?: string | null;
};

export type SourceUpdate = Partial<SourceInsert>;
```

> `sources` 是「網站規則設定」，不是執行紀錄。

---

## 2. 爬取佇列（Crawl Queue）

```ts
export type CrawlPageType = "list" | "article" | "detail" | "unknown";
export type CrawlQueueStatus = "pending" | "running" | "done" | "failed" | "skipped";

export type CrawlQueuePayload = {
  referrerUrl?: string;
  topic?: string;
  depth?: number;
  discoveredFrom?: "seed" | "list" | "manual" | "retry";
  meta?: Record<string, Json>;
};

export type CrawlQueueRow = {
  id: number;
  source_id: number;
  url: string;
  page_type: CrawlPageType;
  priority: number;
  status: CrawlQueueStatus;
  retry_count: number;
  scheduled_at: string;
  locked_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  payload: CrawlQueuePayload;
  created_at: string;
};

export type CrawlQueueInsert = Omit<CrawlQueueRow, "id" | "created_at">;
export type CrawlQueueUpdate = Partial<CrawlQueueInsert>;
```

> `crawl_queue` 是 Playwright 管線的進入點。不要將佇列邏輯合併到 `source_pages` 中。

---

## 3. 爬取執行紀錄（Crawl Runs）

```ts
export type CrawlRunStatus = "pending" | "running" | "success" | "partial" | "failed";

export type CrawlRunLog = {
  ts: string;
  level: "debug" | "info" | "warn" | "error";
  message: string;
  context?: Record<string, Json>;
};

export type CrawlRunRow = {
  id: number;
  source_id: number;
  run_status: CrawlRunStatus;
  started_at: string | null;
  finished_at: string | null;
  pages_found: number;
  pages_fetched: number;
  articles_extracted: number;
  error_count: number;
  logs: CrawlRunLog[];
  created_at: string;
};

export type CrawlRunInsert = Omit<CrawlRunRow, "id" | "created_at">;
export type CrawlRunUpdate = Partial<CrawlRunInsert>;
```

> 回答以下問題：爬取了多少頁面？擷取了多少文章？哪些失敗了？

---

## 4. 來源頁面（Source Pages）

```ts
export type SourcePageSnapshot = {
  finalUrl?: string;
  title?: string;
  meta?: Record<string, string>;
  links?: string[];
  screenshots?: string[];
  extractedSelectors?: Record<string, string>;
};

export type SourcePageRow = {
  id: number;
  source_id: number;
  crawl_run_id: number | null;
  page_type: CrawlPageType;
  topic: string | null;
  url: string;
  canonical_url: string | null;
  title: string | null;
  raw_html: string | null;
  snapshot_json: SourcePageSnapshot | null;
  http_status: number | null;
  fetched_at: string | null;
  last_seen_at: string | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
};

export type SourcePageInsert = Omit<
  SourcePageRow,
  "id" | "created_at" | "updated_at"
>;

export type SourcePageUpdate = Partial<SourcePageInsert>;
```

> 原始證據資料。不是用於產品邏輯的最終文章資料表。

---

## 5. 文章（Articles）

### 中繼資料型別

```ts
export type ArticleMeta = {
  categories?: string[];
  tags?: string[];
  og_image?: string;
  section?: string;
  keywords?: string[];
  byline_raw?: string;
  source_labels?: string[];
  extra?: Record<string, Json>;
};

export type ArticleExtractionData = {
  extractorVersion?: string;
  rawPublishedAt?: string;
  rawAuthor?: string;
  selectorMatches?: Record<string, string>;
  extractionWarnings?: string[];
  languageConfidence?: number;
  aiNormalized?: boolean;
};
```

### 列型別

```ts
export type ArticleRow = {
  id: number;
  source_id: number;
  source_page_id: number | null;
  external_id: string | null;
  title: string;
  slug: string | null;
  author_name: string | null;
  author_url: string | null;
  abstract: string | null;
  content_html: string | null;
  content_text: string | null;
  published_at: string | null;
  source_modified_at: string | null;
  source_url: string;
  canonical_url: string | null;
  lang: string | null;
  meta: ArticleMeta;
  extraction_data: ArticleExtractionData;
  is_published: boolean;
  is_available: boolean;
  content_hash: string | null;
  created_at: string;
  updated_at: string;
};

export type ArticleInsert = Omit<
  ArticleRow,
  "id" | "created_at" | "updated_at"
>;

export type ArticleUpdate = Partial<ArticleInsert>;
```

> `articles` 是用於 UI 顯示、搜尋、分析、發佈與 AI 改寫的主要資料表。

---

## 6. 文章素材（Article Assets）

```ts
export type AssetType = "image" | "video" | "file" | "audio";

export type ArticleAssetRow = {
  id: number;
  article_id: number;
  source_page_id: number | null;
  asset_type: AssetType;
  original_url: string | null;
  storage_bucket: string | null;
  storage_path: string | null;
  mime_type: string | null;
  alt_text: string | null;
  caption: string | null;
  width: number | null;
  height: number | null;
  checksum: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type ArticleAssetInsert = Omit<
  ArticleAssetRow,
  "id" | "created_at" | "updated_at"
>;

export type ArticleAssetUpdate = Partial<ArticleAssetInsert>;
```

> 僅索引與中繼資料。二進位檔案儲存於 Supabase Storage。

---

## 7. 標籤／文章標籤（Tags / Article Tags）

```ts
export type TaxonomyType = "tag" | "category" | "topic" | "series";

export type TagMeta = {
  color?: string;
  icon?: string;
  aliases?: string[];
};

export type TagRow = {
  id: number;
  taxonomy: TaxonomyType;
  name: string;
  slug: string | null;
  description: string | null;
  parent_id: number | null;
  meta: TagMeta;
  created_at: string;
};

export type TagInsert = Omit<TagRow, "id" | "created_at">;
export type TagUpdate = Partial<TagInsert>;

export type ArticleTagRow = {
  article_id: number;
  tag_id: number;
};
```

---

## 8. 發佈目標／文章發佈紀錄（Publish Targets / Article Publications）

```ts
export type PublishTargetType =
  | "wordpress"
  | "notion"
  | "ghost"
  | "custom_api"
  | "internal";

export type PublishStatus = "pending" | "published" | "failed" | "deleted";

export type PublishTargetConfig = {
  endpoint?: string;
  siteUrl?: string;
  databaseId?: string;
  authType?: "token" | "oauth" | "basic";
  meta?: Record<string, Json>;
};

export type PublishTargetRow = {
  id: number;
  code: string;
  name: string;
  target_type: PublishTargetType;
  config: PublishTargetConfig;
  is_enabled: boolean;
  created_at: string;
};

export type PublishTargetInsert = Omit<PublishTargetRow, "id" | "created_at">;
export type PublishTargetUpdate = Partial<PublishTargetInsert>;

export type ArticlePublicationRow = {
  id: number;
  article_id: number;
  target_id: number;
  remote_id: string | null;
  remote_url: string | null;
  publish_status: PublishStatus;
  last_published_at: string | null;
  payload: Record<string, Json>;
  result: Record<string, Json>;
};

export type ArticlePublicationInsert = Omit<ArticlePublicationRow, "id">;
export type ArticlePublicationUpdate = Partial<ArticlePublicationInsert>;
```
