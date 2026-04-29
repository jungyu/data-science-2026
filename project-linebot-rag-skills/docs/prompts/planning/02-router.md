# 02 · Router 設計（Planning Prompt）

> **使用時機**：新增 skill、修改路由邏輯、調整 emotion 偵測時使用。

---

你是資深 Python 工程師。`app/router/` 是這個 LINE Bot 的意圖路由模組，已完整實作並可正常運作。

## 現行實作（已完成）

**架構：**

```
app/router/
├── intent_router.py   # IntentRouter dataclass + OpenAIRouterLLM
├── emotion_detector.py
├── prompts.py         # render_router_prompt()
└── schemas.py         # RouterResult, SkillId, EmotionState, ResponseMode
```

**RouterResult schema：**

```python
class RouterResult(BaseModel):
    target_skill: SkillId        # 6 個合法值
    is_rag_required: bool
    rag_query: str               # LLM 改寫後的檢索 query
    rag_categories: list[str]    # retriever 的 category filter
    emotion_state: EmotionState  # 7 個合法值
    response_mode: ResponseMode  # 6 個合法值
    confidence: float            # 0.0 ~ 1.0
```

**關鍵實作細節（已確認）：**

1. **Responses API**：一律使用 `client.responses.create(model=..., input=prompt)`，不是 `chat.completions.create()`
2. **Fallback 條件**：LLM 呼叫失敗 OR `confidence < 0.55` → heuristic fallback（依關鍵字規則）
3. **rag_categories 必須對應 ingest 的 --category 值**：若 LLM 輸出不存在的 category，retriever 靜默找不到資料。Router prompt 的 Rule 8 列出所有合法 category 值
4. **heuristic fallback 的 rag_categories** 必須包含實際 ingest 使用的 category（例如 `"rag"` 若知識庫是以 `--category rag` 匯入的）

**現行合法 SkillId：**

`tech_architect`, `data_scientist`, `business_strategist`, `philosophical_dialectic`, `emotional_calibration`, `general_chat`

**現行合法 rag_categories：**

`rag`, `engineering`, `architecture`, `code`, `analytics`, `experiments`, `metrics`, `strategy`, `market`, `product`, `philosophy`, `notes`

## 請評估以下 Router 變更：

{在此填入你要修改的目標，例如：「新增 life_coach skill」或「改善技術問題的 rag_query 改寫品質」}

請輸出：
1. 需要修改的檔案與具體改動
2. 若新增 skill，給出完整的 SKILL.md frontmatter 與 system prompt
3. 若修改 Router prompt，給出完整替換版本
4. heuristic fallback 對應修改
5. 測試案例（至少覆蓋：LLM 正常分類、confidence 低觸發 fallback、LLM 呼叫失敗）

**禁止事項：**
- Skill system prompt 不能要求模型輸出分類前綴（如「層級：xxx」），這會污染用戶看到的回覆
- 不要新增現有合法 rag_categories 之外的值，除非同步更新 ingest 腳本和所有 skill 的設定
