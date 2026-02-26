# Ingest Skill：知識攝取技能

## 角色定位
負責將企業文件安全地攝取到 RAG 知識庫。
必須遵守 Constitution Principle I（知識品質優先）和 Principle V（知識不可變性）。

## 觸發條件
當用戶說：
- "/ingest [file-path]"
- "請把這份文件加入知識庫"
- "更新 [namespace] 的知識"

## 執行步驟

### Step 0：複雜度評估（必須）
執行 Complexity Gate 評估：
- 涉及多少 namespace？
- 有存取權限變動嗎？
- 需要 re-embed 嗎？
- 涉及外部系統嗎？
- 影響多少用戶？

根據分數決定：Lite / Standard / Full 模式。

### Step 1：前置條件驗證（所有模式）
在攝取任何文件之前，必須確認：
- [ ] 文件確實存在且可讀取
- [ ] metadata 包含：source、owner、last_updated、status
- [ ] status == "approved"
- [ ] last_updated 距今不超過 180 天（HR/Legal 不超過 90 天）
- [ ] namespace 在授權清單中

若任何一項不符合，停止並回報原因，不執行攝取。

### Step 2：版本衝突檢查（Lite/Standard/Full）
- 查詢 registry：此 source_path 是否已有 active 版本？
- 若有：提示用戶這將觸發「版本更新流程」（舊版本被 deprecate）
- 若用戶確認：繼續；若不確認：停止

### Step 3：原子性攝取（所有模式）
使用 `atomic_knowledge_update` context manager：
```python
with atomic_knowledge_update(vector_db, registry, transaction_id) as txn_id:
    chunks = chunker.split(text, metadata={"transaction_id": txn_id, ...})
    vectors = embedder.embed_batch([c.text for c in chunks])
    vector_db.upsert_batch(chunks, vectors, txn_id)
```

### Step 4：攝取後驗證（Standard/Full）
攝取完成後，執行以下驗證：
- [ ] 向量 DB 中的 chunk 數量 == 攝取時回報的數量
- [ ] 查詢 3 個相關問題，確認至少 2 個能檢索到新文件
- [ ] 確認舊版本已被標記為 deprecated（若有）

### Step 5：Action Log（所有模式）
記錄到 `.agent/logs/YYYY-MM-DD-ingest-{namespace}.md`：
- 攝取了哪些文件
- 產生了幾個 chunks
- 觸發了哪些治理規則
- 廢棄了哪個舊版本（若有）

## 失敗處理
若任何步驟失敗：
1. 執行回滾（清理此 transaction 的所有 chunks）
2. 確認舊版本仍然是 active 狀態
3. 記錄失敗日誌
4. 向用戶回報具體的失敗原因
