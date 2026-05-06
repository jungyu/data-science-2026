-- ch09 RAG 對齊：在 crawler.articles 補充 category / source_type 兩欄
-- 讓 project-linebot-rag-skills 的 SupabaseArticleIngester 可以直接對應
-- KnowledgeChunkInsert 欄位，不需要額外的 JSONB 解析。

alter table crawler.articles
  add column if not exists category    text,
  add column if not exists source_type text not null default 'web';

-- 補舊資料：從 meta.categories[0] 回填 category
update crawler.articles
  set category = meta -> 'categories' ->> 0
  where category is null
    and meta -> 'categories' is not null;

comment on column crawler.articles.category is
  'RAG 知識分類；對應 KnowledgeChunkInsert.category。空值由 IngestionPipeline 補 ''general''。';

comment on column crawler.articles.source_type is
  'RAG 來源類型；固定為 ''web''，對應 KnowledgeChunkInsert.source_type。';
