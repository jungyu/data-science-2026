# ADR-005：無狀態角色切換 + 短期對話記憶

## 狀態

已採納

## 背景

使用者在相鄰幾則訊息間可能快速切換情境：技術問題 → 情緒抒發 → 商業策略。若用有狀態的 session 鎖定角色，切換時容易殘留前一個角色的回覆風格，產生觀點漂移。

## 決策

每則訊息都重新執行路由（Router），同時傳入最近幾輪對話的摘要（`recent_history`）作為上下文輔助。Router 根據當前訊息內容重新選 skill，不繼承前一輪的 `target_skill`。

### 實作細節

- `recent_history` 從 `line_messages` 資料表取最近 N 筆，拼成摘要字串傳入 Router prompt
- Router 輸出的 `emotion_state` 只影響當次回覆的語氣，不持久存入 session
- 若 Router LLM 失敗，heuristic fallback 同樣每次獨立執行，不依賴前一輪結果

### 失敗模式觀察

若 Router prompt 設計不當（例如 `rag_categories` 列舉不完整，或規則描述模糊），即使使用者的問題明顯屬於某 skill，LLM 仍可能選出信心不足的結果並降回 heuristic，導致回覆風格不一致。

解法是在 Router prompt 中明確列出所有合法 category 值與 skill 判斷規則，減少 LLM 的自由解釋空間。

## 後果

### 正面

- 不需維護複雜的 session state machine
- 角色切換自然，使用者無需下達切換指令
- 每輪路由決策獨立，邏輯清晰易除錯

### 負面

- 多輪對話的連貫性依賴 `recent_history` 摘要品質
- 摘要若失真，後續輪次的路由可能偏移
- 每則訊息都呼叫 Router LLM，有額外的 token 成本與延遲
