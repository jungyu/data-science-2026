# 03 — Build Gate：建置品質驗證

> 所有模式都必須通過此閘門。

## 驗證清單

### 攝取操作
- [ ] 前置條件驗證通過（metadata 完整、文件新鮮、namespace 授權）
- [ ] 原子性攝取成功（使用 atomic_knowledge_update）
- [ ] chunk 數量與預期一致
- [ ] 無空白 chunk（INV-1）
- [ ] 向量 DB 無殘餘 chunk（INV-2）

### 查詢操作
- [ ] Retrieval Gate 正常運作
- [ ] namespace 隔離生效
- [ ] Hallucination Shield 已啟用
- [ ] 答案包含文件來源引用

### 通用
- [ ] Action Log 已記錄
- [ ] Token 使用量在預算內
