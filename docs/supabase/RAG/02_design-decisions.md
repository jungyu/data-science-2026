# RAG Schema 設計決策（v3.0）

> 記錄 Supabase RAG Schema 的關鍵設計取捨與架構審查修正。

---

## 修正總覽

| # | 風險等級 | 問題 | 修正版本 | 修正方式 |
|---|---------|------|---------|---------|
| ❶ | 致命 | embedding 維度與 model 矛盾 | v2.0 | CHECK 強制 1536 only |
| ❷ | 安全 | chunks.collection_id 可不一致 | v2.0 | trigger 強制同步 |
| ❸ | 效能 | hybrid search 無 FTS index | v2.0 | GIN index 加入 |
| ❹ | 設計 | query_logs 用 array 存結果 | v2.0 | 正規化 query_log_results |
| ❺ | 效能 | RLS subquery N+1 | v2.0 | owner_id 傳播 + 直接比對 |
| ❻ | 設計 | process_status 太粗糙 | v2.0 | 7 狀態 ingestion pipeline |
| ❼ | 效能 | metadata jsonb 無 index | v2.0 | 高頻欄位抽 column + index |
| ❽ | 效能 | RLS 使用 EXISTS/JOIN | v2.1 | 改用 helper function |
| C1 | 規範 | PK 使用 bigserial 而非 ULID | v3.0 | TEXT + generate_ulid() |
| C2 | 規範 | FK 使用 bigint 而非 TEXT | v3.0 | 全面改為 TEXT |
| C3 | 規範 | owner_id 直接引用 auth.users | v3.0 | TEXT 型別 + helper function |
| C4 | 規範 | 無 GRANT 語句 | v3.0 | 每張表加 GRANT |
| C5 | 規範 | 無 service_role policy | v3.0 | ETL pipeline 需要 |
| C6 | 規範 | auth.uid() 未包裝 | v3.0 | (SELECT auth.uid()) |
| H1 | 規範 | 部分表缺 updated_at trigger | v3.0 | 全面補上 |
| H2 | 規範 | DDL 非冪等 | v3.0 | IF NOT EXISTS |
| H3 | 規範 | 缺 created_by 欄位 | v3.0 | documents, query_logs |

---

## 1. 為什麼用 pgvector 而非 Qdrant？

| 面向 | pgvector (Supabase) | Qdrant |
|------|---------------------|--------|
| 部署 | Supabase 內建，零額外基礎設施 | 需獨立 Docker 容器 |
| 關聯式查詢 | 原生 JOIN、WHERE 過濾 | 需在應用層組合 |
| 交易一致性 | PostgreSQL ACID | 最終一致性 |
| RLS 多租戶 | Supabase RLS 原生支援 | 需自行實作 |
| 大規模性能 | <1M 向量表現優秀，>10M 需調校 | 專為大規模設計 |
| 混合搜尋 | `tsvector` + `vector` 原生整合 | 需額外設定 payload index |

**結論**：教學場景 + 中小規模知識庫，pgvector 的一站式體驗優於 Qdrant。

---

## 2. ❶ 向量維度策略：為什麼強制 1536？

整個系統只用 1536 維。`embedding_models` 加 `CHECK (dimensions = 1536)`。

| 方案 | 優點 | 缺點 |
|------|------|------|
| `vector(1536)` 固定 | HNSW 索引有效、查詢快 | 不支援 3072 |
| `vector` 動態 | 靈活 | 無法建 HNSW 索引、查詢慢 |

若需多維度支援（未來 v4.0）：
1. 按維度建獨立 chunks 表：`chunks_1536`、`chunks_3072`
2. 搜尋函數自動路由到正確的表

---

## 3. ❷ chunks.collection_id：保留但加上安全護欄

### v1.0 的問題（安全級 bug）

```sql
-- 手動插入可以設定不一致的 collection_id
INSERT INTO chunks (document_id, collection_id, ...)
VALUES (doc_in_collection_1, collection_2, ...);  -- ← 💣 cross-tenant leak
```

### v2.0 修正：trigger 強制一致性

```sql
-- trigger 在 INSERT/UPDATE 時自動覆蓋 collection_id
new.collection_id := (SELECT collection_id FROM documents WHERE id = new.document_id);
```

**為什麼不直接刪掉 collection_id？**

語意搜尋的核心查詢是：
```sql
WHERE collection_id = ? AND embedding <=> query_embedding
```

如果刪掉 collection_id，每次搜尋都要 JOIN documents → 對於高頻、低延遲的 RAG 查詢來說不可接受。

**結論**：反正規化 + trigger 護欄 = 效能 + 安全的最佳平衡。

---

## 4. HNSW vs IVFFlat 索引選擇

| 面向 | HNSW | IVFFlat |
|------|------|---------|
| 查詢精度 | 更高（recall ~99%） | 較低（recall ~95%，取決於 nprobe） |
| 建立時間 | 較長 | 較短 |
| 記憶體 | 較多 | 較少 |
| 動態插入 | 支援良好 | 需定期重建 |
| 適用規模 | <5M 向量 | <10M 向量 |

**選擇 HNSW**：RAG 場景對精度要求高（漏掉相關文件影響答案品質），且知識庫通常不超過百萬級。

---

## 5. Chunking 策略儲存在哪？

```
collection.chunking_strategy     ← 集合預設
document.chunking_override       ← 文件層級覆蓋（null = 用預設）
chunks.chunking_method           ← 實際使用的方法（紀錄用）
```

**理由**：
- 同一知識庫通常用同一策略，避免每份文件重複設定
- 特殊文件（如程式碼 vs 散文）可覆蓋預設
- chunk 上記錄實際使用的方法，用於回溯和評估

---

## 6. 與 Crawler Schema 的整合策略

不直接用外鍵（FK）連結 `articles` 和 `documents`，而是用軟連結：

```sql
documents.source_ref_type = 'article'
documents.source_ref_id   = articles.id
```

**理由**：
- 兩個 schema 可獨立部署，不強制耦合
- RAG 知識庫可能包含非爬蟲來源的文件
- 未來可擴展到其他來源（如 Notion、Google Docs）

---

## 7. query_logs 為什麼要存 embedding？

`query_logs.query_embedding` 看似冗餘（可以重新生成），但它：

- **免重複 API 呼叫**：分析查詢模式時不需重新 embed
- **版本一致性**：模型更新後，原始 embedding 仍可比對
- **聚類分析**：可對查詢 embedding 做 k-means 分析使用模式

---

## 8. ❸ 全文搜尋配置

混合搜尋使用 `plainto_tsquery('simple', ...)` 而非語言特定配置：

- `'simple'` 對中文友善（不做詞幹處理）
- 中文全文搜尋效果有限，主要靠語意搜尋
- 全文搜尋作為**補充**，用 `p_semantic_weight` 控制比重

**v2.0 新增**：`idx_chunks_fts` GIN 索引，hybrid search 不再 full scan。

如需更好的中文搜尋，可考慮安裝 `pg_jieba` 或 `zhparser` 擴充。

---

## 9. ❹ 為什麼把檢索結果從 array 改成正規化表？

### v1.0 的問題

```sql
-- 無法 JOIN、無法 index、無法分析
retrieved_chunk_ids bigint[]
retrieved_scores    float8[]
```

想知道「哪個 chunk 被命中最多次」→ **做不到**（需要 `unnest` + aggregate）。

### v2.0 修正

```sql
query_log_results (
  query_id    → query_logs.id
  chunk_id    → chunks.id
  rank        -- 排名
  score       -- 分數
)
```

現在可以直接：
```sql
-- 哪些 chunk 最常被命中？
SELECT chunk_id, count(*) FROM query_log_results GROUP BY chunk_id ORDER BY count DESC;

-- 某個 chunk 的平均相似度分數？
SELECT avg(score) FROM query_log_results WHERE chunk_id = ?;
```

---

## 10. ❺ + ❽ RLS 優化：避免 subquery N+1 + 禁止 EXISTS/JOIN

### v1.0 的問題

```sql
-- 每一筆 chunk row 都跑 subquery hit collections
EXISTS (SELECT 1 FROM collections WHERE id = chunks.collection_id AND ...)
```

100K chunks → 100K 次 subquery → CPU 爆炸。

### v2.0 修正

1. `owner_id` 從 collections → documents → chunks 逐層傳播（trigger 自動）
2. RLS policy 對 owner 的檢查直接比對 `owner_id = auth.uid()`（O(1)）

### v2.1 修正（performance-linter compliance）

v2.0 仍在部分 RLS policy 中使用 `EXISTS`（公開集合檢查），違反 performance-linter Rule Group 2。

改為 3 個 helper function：

```sql
-- 直接查詢，PG 可快取結果
public.is_collection_owner(p_collection_id)   -- owner 檢查
public.is_collection_active(p_collection_id)  -- 公開檢查
public.can_read_collection(p_collection_id)   -- owner 或公開
```

RLS policy 現在全部使用 function call：

```sql
-- documents/chunks: owner_id 直接比對 + helper function
USING (owner_id = auth.uid() OR public.is_collection_active(collection_id))

-- query_logs: helper function
USING (public.can_read_collection(collection_id))
```

**完全消除 RLS 中的 EXISTS/JOIN**，符合 performance-linter 規範。

---

## 11. ❻ Ingestion Pipeline 狀態機

### v1.0
```
pending → processing → completed / failed / stale
```
→ 「processing 中哪一步出錯了？」→ 不知道。

### v2.0
```
uploaded → parsed → chunked → embedded → ready
    ↓         ↓        ↓          ↓
  failed    failed   failed     failed
    ↑         ↑        ↑          ↑
  stale     stale    stale      stale
```

每個階段有明確語義：
| 狀態 | 意義 | 下一步 |
|------|------|--------|
| `uploaded` | 檔案已上傳 | Extract：解析文字 |
| `parsed` | 文字已萃取 | Transform：切分 chunks |
| `chunked` | 切分完成 | Load：生成 embedding |
| `embedded` | embedding 完成 | 驗證索引 |
| `ready` | 全部完成 | 可供查詢 |
| `failed` | 處理失敗 | 查看 `process_error` |
| `stale` | 來源已更新 | 重新處理 |

---

## 12. v3.0 PK/FK 遷移：bigserial → TEXT + ULID

### 為什麼改？

`pk-convention.md` 明確規定：

> 所有業務表 **必須** 使用 `id TEXT PRIMARY KEY DEFAULT generate_ulid()`
> 使用 SERIAL / BIGINT → ❌ 不可違反

ULID 相比 BIGINT 的優勢：
- **可排序**：前 10 字元 = 時間戳，B-Tree 友善
- **分散式安全**：不需要 sequence，可在應用層預生成
- **FK 型別一致**：全部 TEXT，不會出現 bigint ↔ uuid 混用

### schema 影響

所有表的 PK 從 `bigserial` 改為 `TEXT DEFAULT generate_ulid()`。
所有 FK 從 `bigint` 改為 `TEXT`。
搜尋函數的參數型別從 `bigint` 改為 `TEXT`。

### generate_ulid() 函式

v3.0 在 schema 開頭定義了 PL/pgSQL 版本的 ULID 生成器：
- 6 bytes timestamp（毫秒精度）
- 10 bytes random entropy
- 輸出 26 字元 Crockford Base32

---

## 13. v3.0 GRANT + service_role

### 為什麼加？

`migration-guidelines.md` 規定每張表必須有：
1. GRANT SELECT/INSERT/UPDATE/DELETE TO authenticated
2. GRANT ALL TO service_role
3. service_role policy（ETL pipeline 需要繞過 RLS）

### RAG 場景的 service_role 使用場景

| 操作 | 角色 | 為什麼需要 service_role |
|------|------|----------------------|
| Embedding 批次生成 | Background Worker | 無使用者 session |
| Crawler → Document 匯入 | ETL Pipeline | 無使用者 session |
| Chunk 批次寫入 | ETL Pipeline | 大量寫入需繞過 RLS |
| 定期評估（Ragas） | Cron Job | 系統級操作 |

---

## 14. v3.0 auth.uid() 優化

### 問題

```sql
-- ❌ 每列重算
USING (owner_id = auth.uid()::TEXT)

-- ✅ initPlan，只算一次
USING (owner_id = (SELECT auth.uid())::TEXT)
```

### 修正

所有 helper function 內部的 `auth.uid()` 統一包裝為 `(SELECT auth.uid())`。
`get_current_owner_id()` 也使用此模式。

---

## 15. 未來擴展方向

| 功能 | 實作方式 | Phase |
|------|---------|-------|
| 多維度 embedding | 按維度建獨立 chunks 表 + 搜尋路由 | v3.0 |
| 多模態 RAG（圖片） | 新增 `image_embeddings` 表，使用 CLIP 模型 | v3.0 |
| 對話記憶 | 擴展 `query_logs.session_id` 為獨立 `sessions` 表 | v2.1 |
| 自動重新 chunking | PostgreSQL trigger 在 `documents.content_text` 更新時觸發 | v2.1 |
| A/B 測試檢索策略 | `query_logs.metadata` 記錄策略版本 | v2.1 |
| 向量壓縮 | pgvector 的 `halfvec` 類型（float16，節省 50% 空間） | v3.0 |
| OLTP/Analytics 分離 | query_logs 移至獨立 analytics DB | v3.0 |
| Document versioning | `document_versions` + `chunk_versions` 表 | v3.0 |

---

*最後更新：2026-03*
