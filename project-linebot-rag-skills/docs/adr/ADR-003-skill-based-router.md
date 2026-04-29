# ADR-003：以 Skill 路由取代單一巨型 Prompt

## 狀態

已採納

## 背景

使用者不希望每次輸入都要手動指定「現在要問技術問題」或「現在要聊心情」。系統需要自動判斷意圖並選擇適合的回覆框架，同時讓分類邏輯與回覆生成邏輯保持獨立、可維護。

## 決策

將 skill 定義寫在 `skills/*/SKILL.md`，透過 `seed_skills.py` 寫入 `ai_skills` 資料表。Router 負責選出目標 skill 與檢索設定；Generator 只負責依據 skill 的 system prompt 生成最終回覆。

### Router 架構

Router 使用 OpenAI **Responses API**（`/v1/responses`），而非 Chat Completions API：

```python
response = await self._client.responses.create(
    model=self._settings.router_model,  # gpt-5.4-mini
    input=prompt,
)
```

若 LLM 呼叫失敗或 `confidence < 0.55`，自動降回啟發式（heuristic）路由，依關鍵字規則選 skill。

Router 輸出的 JSON 欄位：

| 欄位 | 說明 |
|------|------|
| `target_skill` | 目標 skill ID |
| `is_rag_required` | 是否需要 RAG 檢索 |
| `rag_query` | 改寫後的檢索 query |
| `rag_categories` | 要過濾的知識庫 category |
| `emotion_state` | 情緒狀態，影響回覆風格 |
| `confidence` | 路由信心分數 |

### Skill 設計注意事項

**system prompt 不要產生結構化輸出前綴**

Skill 的 system prompt 若包含「先判斷問題屬於哪一層」之類的指令，模型會把分類結果（如「層級：application」）直接輸出到回覆中，污染使用者看到的訊息。System prompt 應只描述**回覆的方式與風格**，不應要求模型輸出中間推理步驟。

**`rag_categories` 必須與 ingest 的 `--category` 對應**

Router 的 `rag_categories` 是 retriever 的 category filter，若不包含實際 ingest 時使用的 category 值，即使知識庫有資料也找不到。例如：

```bash
# ingest 時用 --category rag
python scripts/ingest_markdown.py docs/RAG/*.md --category rag

# skill 的 rag_categories 與啟發式路由都必須包含 "rag"
rag_categories: [engineering, architecture, code, rag]
```

Router prompt 也需明確列出可用的 category 值，避免 LLM 自行發明不存在的 category。

## 後果

### 正面

- Skill 可獨立版本控制與調整，不需改動核心邏輯
- 路由失敗時有啟發式保底，不會完全無法回覆
- emotion_state 讓同一 skill 能依情緒調整語氣

### 負面

- 路由錯誤時，回覆觀點會漂移（如技術問題被導向情緒校準）
- `rag_categories` 與 ingest `--category` 不一致時，RAG 靜默失敗，難以察覺
- Skill 清單與 Router prompt 需同步維護，否則 LLM 可能選出不存在的 skill
