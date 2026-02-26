# 攝取操作檢查清單

## 攝取前

- [ ] 文件 metadata 完整（source, owner, last_updated, status）
- [ ] 文件 status = "approved"
- [ ] 文件在有效期內（<= 180 天；HR/Legal <= 90 天）
- [ ] Namespace 已授權且在 Task Pack 允許範圍內
- [ ] Token 預算已確認（根據複雜度 tier）
- [ ] 如為版本更新，舊版本已識別

## 攝取中

- [ ] 使用 atomic_knowledge_update 確保原子性
- [ ] Chunking 使用 ADR-002 策略
- [ ] 每個 chunk 帶有完整 metadata（doc_id, namespace, source）
- [ ] 嵌入使用 ADR-001 指定的模型

## 攝取後

- [ ] chunk_count >= 1
- [ ] 向量 DB 中的 chunk 數量與預期一致（INV-2）
- [ ] 無空白 chunk（INV-1）
- [ ] Hit@5 測試通過（Standard/Full 模式）
- [ ] Namespace 隔離測試通過（Standard/Full 模式）
- [ ] 舊版本已標記為 deprecated（若為版本更新）
- [ ] Action Log 已記錄
