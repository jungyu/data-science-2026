# Supabase RAG 資料庫 Schema 設計（v3.0）

> 以 Supabase（PostgreSQL + pgvector）實現 RAG Pipeline 資料層。
> 完整符合 `agent-init/skills/supabase/*.md` 規範。

---

## 設計目標

將 [RAG 完全實戰課程](../../RAG/README.md) 的知識庫管線遷移到 Supabase：

- **pgvector** — 向量儲存與語意搜尋（取代 Qdrant / FAISS）
- **TEXT + ULID** — 所有 PK/FK 統一為 TEXT 型別 + ULID 生成
- **RLS + Helper Functions** — 多租戶隔離，無 EXISTS/JOIN in policy
- **GRANT + service_role** — 每張表完整權限設定
- **Ingestion Pipeline** — 5 階段狀態機 + trigger 一致性護欄

---

## Schema 總覽

```
                    ┌──────────────┐
                    │  collections │  知識庫（tenant scope, owner_id）
                    └──────┬───────┘
                           │ 1:N
                    ┌──────┴───────┐
                    │  documents   │  原始文件（pipeline 狀態機）
                    └──────┬───────┘  owner_id ← trigger 同步
                           │ 1:N
                    ┌──────┴───────┐
                    │   chunks     │  切片 + embedding vector(1536)
                    └──────┬───────┘  collection_id, owner_id ← trigger 同步
                           │ N:M
                    ┌──────┴───────┐
                    │  chunk_tags  │  分類標籤
                    └──────────────┘

   ┌──────────────┐    ┌────────────────────┐    ┌──────────────────┐
   │ query_logs   │───→│ query_log_results  │    │ embedding_models │
   │ 查詢 + 評估  │    │ 檢索結果明細       │    │ 模型（1536 only）│
   └──────────────┘    └────────────────────┘    └──────────────────┘
```

所有 PK = `TEXT DEFAULT generate_ulid()` · 所有 FK = `TEXT`

---

## Skill 規範合規對照

| Skill 文件 | 合規項目 | 狀態 |
|-----------|---------|------|
| pk-convention | ULID PK, TEXT FK, 無 BIGINT/UUID 混用 | ✅ |
| schema-design | 分層架構, 必備欄位, JSONB 使用 | ✅ |
| rls-patterns | Helper function, (SELECT auth.uid()), GRANT | ✅ |
| performance-linter | 無 EXISTS in RLS, FTS index, 無 OFFSET | ✅ |
| anti-patterns | 全部 checklist 通過 | ✅ |
| migration-guidelines | 冪等 DDL, 完整元素, service_role policy | ✅ |
| query-patterns | 有 scope + limit, 無全表掃描 | ✅ |
| scaling-guidelines | Helper function RLS, auth.uid() 優化 | ✅ |

詳見 [03_audit-report.md](03_audit-report.md)。

---

## 架構改進歷程

| 版本 | 重點修正 |
|------|---------|
| v1.0 | 初始設計（collection → document → chunk） |
| v2.0 | 架構審查：維度鎖定、trigger 一致性、FTS index、query_logs 正規化 |
| v2.1 | RLS 改用 helper function（消除 EXISTS/JOIN） |
| v3.0 | **Skill 規範全面合規**：ULID PK、GRANT、service_role、auth.uid() 優化 |

---

## 檔案清單

| 檔案 | 說明 |
|------|------|
| [01_guide-supabase-rag.md](01_guide-supabase-rag.md) | **教學指南**（Head First 風格，先讀這個） |
| [04_lab-rag-pipeline.md](04_lab-rag-pipeline.md) | Stage-by-stage 實操 Lab（7 階段 + 3 挑戰題） |
| [05_05_rag_supabase_schema.sql](05_05_rag_supabase_schema.sql) | 完整 SQL Schema v3.0 |
| [02_design-decisions.md](02_design-decisions.md) | 設計決策與取捨說明 |
| [03_audit-report.md](03_audit-report.md) | Skill 規範審查報告 |

---

## 快速開始

```sql
-- 1. 執行 schema
-- （複製 05_rag_supabase_schema.sql 貼到 Supabase SQL Editor 執行）

-- 2. 建立知識庫
INSERT INTO collections (name, code, embedding_model_id, owner_id)
SELECT 'my-kb', 'my-kb', id, 'owner-001'
FROM embedding_models WHERE name = 'text-embedding-3-small';

-- 3. 新增文件（owner_id 由 trigger 自動填入）
INSERT INTO documents (collection_id, title, source_type, content_text)
SELECT id, '我的文件', 'text', '內容...'
FROM collections WHERE code = 'my-kb';

-- 4. 新增切片（collection_id 由 trigger 自動填入）
INSERT INTO chunks (document_id, content, chunk_index, embedding)
SELECT id, '切片...', 0, '[0.1,0.2,...]'::vector(1536)
FROM documents WHERE title = '我的文件';

-- 5. 語意搜尋
SELECT * FROM match_chunks(
  '[0.1,0.2,...]'::vector(1536),
  (SELECT id FROM collections WHERE code = 'my-kb'),
  5, 0.7
);
```

詳細步驟請看 [04_lab-rag-pipeline.md](04_lab-rag-pipeline.md)。

---

*最後更新：2026-03*
