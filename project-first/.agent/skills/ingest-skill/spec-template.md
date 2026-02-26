# 攝取規格模板

## 文件資訊

- **文件路徑**：{file_path}
- **Namespace**：{namespace}
- **Owner**：{owner}
- **Status**：{status}
- **Last Updated**：{last_updated}

## 前置條件確認

- [ ] `status == "approved"`
- [ ] `last_updated` 距今 <= 180 天
- [ ] Namespace 已授權
- [ ] `source`、`owner`、`last_updated` 欄位完整

## Chunking 預估

- **策略**：ADR-002 遞迴分塊（target_size=600, overlap=100）
- **預估 chunk 數**：{estimated_chunks}
- **Token 預算 tier**：{tier}

## 攝取方式

- [ ] 單檔攝取（`KnowledgeIngestor`）
- [ ] 版本更新（`VersionedKnowledgeIngestor`）
- [ ] 批次攝取（`atomic_knowledge_update`）

## 驗證計畫

- 測試問題：{test_questions}
- 預期 Hit@5：{expected_hit_rate}
