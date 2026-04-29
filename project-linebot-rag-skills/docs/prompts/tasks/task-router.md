# task-router · Intent Router 實作

> **使用時機**：新增 skill、修改路由規則，或從零實作 router 模組時使用。

---

請在 `app/router/` 目錄下實作完整的意圖路由模組。

## 目標目錄結構

```
app/router/
├── intent_router.py    # IntentRouter + OpenAIRouterLLM
├── emotion_detector.py # heuristic 情緒偵測
├── prompts.py          # render_router_prompt()
└── schemas.py          # RouterResult, SkillId, EmotionState, ResponseMode
```

## schemas.py 規格

```python
SkillId = Literal[
    "tech_architect", "data_scientist", "business_strategist",
    "philosophical_dialectic", "emotional_calibration", "general_chat"
]
EmotionState = Literal[
    "neutral","curious","urgent","confused","frustrated","anxious","reflective"
]
ResponseMode = Literal[
    "brief","structured","step_by_step","decision_support","debugging","reflection"
]

class RouterResult(BaseModel):
    target_skill: SkillId
    is_rag_required: bool
    rag_query: str
    rag_categories: list[str]
    emotion_state: EmotionState
    response_mode: ResponseMode
    confidence: float = Field(ge=0.0, le=1.0)

    @classmethod
    def fallback(cls, user_input, *, target_skill, ...) -> "RouterResult": ...
```

## intent_router.py 規格

**LLM 呼叫（使用 Responses API，不是 Chat Completions）：**

```python
response = await self._client.responses.create(
    model=self._settings.router_model,
    input=prompt,           # 字串
)
return response.output_text
```

**Fallback 條件：**

- LLM 呼叫拋出任何例外 → heuristic fallback
- `result.confidence < self.confidence_threshold`（預設 0.55）→ heuristic fallback
- JSON parse 失敗 → 嘗試從 `{}` 抽取，仍失敗則 heuristic fallback

**Heuristic fallback（關鍵字比對）：**

```python
TECH_KEYWORDS = ("supabase","fastapi","rag","api","schema","webhook","deploy","pgvector")
DATA_KEYWORDS = ("ab test","metric","實驗","資料","模型","預測","特徵")
BUSINESS_KEYWORDS = ("商業","定價","市場","產品定位","營收","growth","gtm")
PHILOSOPHY_KEYWORDS = ("價值","存在","自由意志","倫理","辯證","意義")
KNOWLEDGE_KEYWORDS = ("筆記","adr","spec","規格","知識庫","project","專案脈絡")
```

tech 關鍵字 → `tech_architect`，`rag_categories=["engineering","architecture","code","rag"]`

## prompts.py 規格

Router prompt 必須包含：

1. Available Skills 列表（與 SkillId 對應）
2. Rules：
   - 只輸出 JSON
   - is_rag_required = true 的觸發條件（技術問題、RAG、知識庫查詢）
   - `rag_categories` 必須從明確列出的合法值選取：`rag、engineering、architecture、code、analytics、experiments、metrics、strategy、market、product、philosophy、notes`
   - rag_query 要改寫，不原封不動複製用戶訊息
3. Output JSON schema 範本

## 請輸出

1. `schemas.py` 完整程式碼
2. `intent_router.py` 完整程式碼
3. `emotion_detector.py` 完整程式碼
4. `prompts.py` 完整程式碼（含 render_router_prompt 函式）
5. `tests/test_router.py` 測試案例，覆蓋：
   - LLM 正常分類 → RouterResult 正確
   - LLM 回傳 confidence < 0.55 → heuristic fallback
   - LLM 拋出例外 → heuristic fallback
   - JSON parse 失敗但有 `{...}` 可抽取

## 驗收指令

```bash
pytest tests/test_router.py -v
```
