# RAG 操作規格 — Lite 模式

## 操作摘要
- **操作類型**：{ingest | query | evaluate}
- **目標文件**：{file_path}
- **Namespace**：{namespace}
- **複雜度分數**：{score} / 10

## 前置條件
- [ ] 文件已審核（status = approved）
- [ ] 文件在有效期內（< 180 天）
- [ ] Namespace 已授權

## 預期結果
- Chunk 數量預估：{N}
- Token 預算：simple tier（< 10K tokens）

## 完成標準
- [ ] 攝取成功，無殘餘 chunk
- [ ] Action Log 已記錄
