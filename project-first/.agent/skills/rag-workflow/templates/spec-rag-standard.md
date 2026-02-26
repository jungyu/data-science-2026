# RAG 操作規格 — Standard 模式

## 操作摘要
- **操作類型**：{ingest | query | evaluate | batch}
- **目標文件**：{file_paths}
- **Namespace**：{namespace}
- **複雜度分數**：{score} / 10
- **影響用戶數**：{user_count}

## 前置條件
- [ ] 所有文件已審核（status = approved）
- [ ] 所有文件在有效期內
- [ ] Namespace 已授權
- [ ] Token 預算已確認（moderate tier）
- [ ] 回滾計畫已準備

## BDD 場景

### Happy Path
```gherkin
Given {前置狀態}
When {觸發操作}
Then {預期結果}
```

### Error Path
```gherkin
Given {前置狀態}
When {失敗條件}
Then {預期錯誤處理}
```

## 預期結果
- Chunk 數量預估：{N}
- Hit@5 預期：>= 2/3
- Token 預算：moderate tier（< 40K tokens）

## 評測計畫
- 測試問題：{questions}
- 預期命中的文件：{doc_ids}

## 完成標準
- [ ] 攝取成功，無殘餘 chunk
- [ ] Hit@5 >= 2/3
- [ ] Namespace 隔離驗證通過
- [ ] 舊版本已 deprecated（若有）
- [ ] Action Log 已記錄
