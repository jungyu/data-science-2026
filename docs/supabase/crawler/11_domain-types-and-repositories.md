# Playwright Crawler - 領域型別與 Repository 介面

> **已取代**：Python 版本請見 `10_worker-interfaces-python.md`。本檔案僅保留作為 TypeScript 參考。

型別依照**管線職責**組織，而非僅對應資料表。

---

## 領域型別

### 文章聚合

包含所有關聯的完整文章。

```ts
export type ArticleAggregate = {
  article: ArticleRow;
  assets: ArticleAssetRow[];
  tags: TagRow[];
  publications: ArticlePublicationRow[];
};
```

### 擷取文章草稿

在 Playwright 擷取與資料庫寫入之間的記憶體中間型別。這是管線中最重要的領域型別。

```ts
export type ExtractedArticleDraft = {
  title: string;
  author_name?: string;
  published_at?: string;
  content_html?: string;
  content_text?: string;
  canonical_url?: string;
  lang?: string;
  tags?: string[];
  categories?: string[];
  assets?: Array<{
    original_url: string;
    asset_type?: AssetType;
    alt_text?: string;
    caption?: string;
  }>;
  meta?: ArticleMeta;
  extraction_data?: ArticleExtractionData;
};
```

---

## 服務輸入型別

### EnqueueUrlInput

```ts
export type EnqueueUrlInput = {
  sourceId: number;
  url: string;
  pageType?: CrawlPageType;
  priority?: number;
  payload?: CrawlQueuePayload;
};
```

### StartCrawlRunInput

```ts
export type StartCrawlRunInput = {
  sourceId: number;
};
```

### SaveFetchedPageInput

```ts
export type SaveFetchedPageInput = {
  sourceId: number;
  crawlRunId?: number;
  pageType: CrawlPageType;
  url: string;
  canonicalUrl?: string;
  title?: string;
  rawHtml?: string;
  snapshotJson?: SourcePageSnapshot;
  httpStatus?: number;
  fetchedAt?: string;
};
```

### UpsertArticleInput

```ts
export type UpsertArticleInput = {
  sourceId: number;
  sourcePageId?: number;
  sourceUrl: string;
  draft: ExtractedArticleDraft;
  contentHash?: string;
};
```

---

## Repository 介面

以下是 Playwright Worker 與服務所依賴的介面。

### SourceRepository

```ts
export interface SourceRepository {
  findByCode(code: string): Promise<SourceRow | null>;
  listEnabled(): Promise<SourceRow[]>;
}
```

### CrawlQueueRepository

```ts
export interface CrawlQueueRepository {
  enqueue(input: EnqueueUrlInput): Promise<CrawlQueueRow>;
  lockNext(sourceId?: number): Promise<CrawlQueueRow | null>;
  markDone(id: number): Promise<void>;
  markFailed(id: number, errorMessage: string): Promise<void>;
}
```

### CrawlRunRepository

```ts
export interface CrawlRunRepository {
  create(input: StartCrawlRunInput): Promise<CrawlRunRow>;
  finish(id: number, patch: Partial<CrawlRunRow>): Promise<void>;
  appendLog(id: number, log: CrawlRunLog): Promise<void>;
}
```

### SourcePageRepository

```ts
export interface SourcePageRepository {
  upsertPage(input: SaveFetchedPageInput): Promise<SourcePageRow>;
}
```

### ArticleRepository

```ts
export interface ArticleRepository {
  upsertArticle(input: UpsertArticleInput): Promise<ArticleRow>;
  getAggregateById(id: number): Promise<ArticleAggregate | null>;
}
```

### ArticleAssetRepository

```ts
export interface ArticleAssetRepository {
  replaceAssets(articleId: number, assets: ArticleAssetInsert[]): Promise<void>;
}
```

### TagRepository

```ts
export interface TagRepository {
  ensureTags(taxonomy: TaxonomyType, names: string[]): Promise<TagRow[]>;
  attachTags(articleId: number, tagIds: number[]): Promise<void>;
}
```

---

## Supabase Codegen 整合策略

### Repository 層 - 使用 Supabase 產生的型別

```ts
type ArticleRowDb = Database["public"]["Tables"]["articles"]["Row"];
type ArticleInsertDb = Database["public"]["Tables"]["articles"]["Insert"];
type ArticleUpdateDb = Database["public"]["Tables"]["articles"]["Update"];
```

### 領域／服務層 - 使用手寫型別

```ts
export type ExtractedArticleDraft = { ... };
export type ArticleAggregate = { ... };
export type UpsertArticleInput = { ... };
```

**優點**：
- 資料庫 Schema 變更只影響 Repository 層
- 商業邏輯與 Supabase 型別保持解耦
- 領域層對 Playwright Worker、AI 擷取和匯出器保持簡潔
