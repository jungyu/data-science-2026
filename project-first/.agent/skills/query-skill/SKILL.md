# Query Skill：知識查詢技能

## 角色定位
接收用戶的自然語言問題，執行 RAG 查詢，回傳有根據的答案。
必須嚴格遵守 Constitution Principle II（幻覺零容忍）和 Principle III（最小知識原則）。

## 執行步驟

### Step 1：意圖識別
判斷問題的知識域：
- 「年假有幾天？」→ namespace: hr-leaves
- 「如何申請差旅費？」→ namespace: hr-expenses
- 「公司的法律條款？」→ namespace: legal-*

若無法判斷：詢問用戶，或使用 `list_namespace_stats` 工具查看可用知識域。

### Step 2：呼叫 MCP Server
```
使用 search_knowledge 工具：
- query: [用戶的問題]
- top_k: 5（預設）
```

### Step 3：評估 Retrieval Gate 結果
- 若 status == "no_relevant_knowledge"：
  - 誠實告知用戶「根據現有文件無法回答」
  - 可以建議：「您可以聯繫 [owner] 確認是否有相關文件」
  - **絕對不可以**：猜測或用 LLM 的訓練記憶作答

- 若 status == "success"：
  - 繼續 Step 4

### Step 4：呼叫 LLM 生成答案
使用 Constitution 規定的設定：
- model: gpt-4o（不得使用 FORBIDDEN_MODELS）
- temperature: 0.1（不得超過 0.3）
- system prompt: 必須包含「若文件中無相關資訊，請回答根據現有文件無法回答」

### Step 5：幻覺防護驗證
呼叫 HallucinationShield.validate_answer()
- 若 reliability_score < 0.7：在答案前加上警告標記
- 若有 warnings：列出在答案後

### Step 6：格式化輸出
回傳格式：
```
[答案內容]

---
📚 資料來源：
- {doc_id_1}（{source_path_1}，更新於 {last_updated_1}）
- {doc_id_2}（{source_path_2}，更新於 {last_updated_2}）

⚠️ 可信度評分：{reliability_score}（0.7+ = 高 | 0.5-0.7 = 中等 | <0.5 = 請人工驗證）
```
