# Ch 04：Intent Router 與 Skills 註冊

> 核心檔案：[`app/router/`](../../app/router/)、[`app/skills/`](../../app/skills/)、[`app/ai/factory.py`](../../app/ai/factory.py)
>
> Variant 適用性：**全部三個** — 任何 variant 進來第一站都是 router

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `RouterResult` schema：router 的輸出長什麼樣 |
| 2 | 讀懂 `IntentRouter`：LLM + heuristic 雙軌設計 |
| 3 | 看 router prompt + confidence gate |
| 4 | 讀懂 `emotion_detector`：純規則為什麼比 LLM 好 |
| 5 | 看 `categories.py`：RAG filter 白名單 |
| 6 | 看 `SkillRegistry`：file vs supabase 兩種來源 |
| 7 | 看 `ai/factory.py`：role-based model 與溫度 |
| 8 | ✏️ 加一個新 skill 跑通 router |
| 9 | ✏️ 把 SkillRegistry 從 file 切到 supabase 熱更新 |

---

## Step 1：`RouterResult` schema — router 的契約

打開 [`app/router/schemas.py`](../../app/router/schemas.py)：

```python
SkillId = Literal[
    "tech_architect", "data_scientist", "business_strategist",
    "philosophical_dialectic", "emotional_calibration", "general_chat",
]

EmotionState = Literal[
    "neutral", "curious", "urgent", "confused", "frustrated", "anxious", "reflective",
]

ResponseMode = Literal[
    "brief", "structured", "step_by_step", "decision_support", "debugging", "reflection",
]


class RouterResult(BaseModel):
    target_skill: SkillId
    is_rag_required: bool
    rag_query: str
    rag_categories: list[str] = Field(default_factory=list)
    emotion_state: EmotionState
    response_mode: ResponseMode
    confidence: float = Field(ge=0.0, le=1.0)
```

三個 `Literal` 構成封閉集合（見 [LangGraph ch03 封閉集合](../RAG/LangGraph/ch03-conditional-edges.md#設計原則decision-必須是封閉集合)）。router 永遠只能回這幾個值，graph 後續節點才能用 `match` 分流。

### 1-1 ✏️ 改成你的需求：增加新的 SkillId

假設你要加一個 `legal_advisor`：

```python
# app/router/schemas.py
SkillId = Literal[
    "tech_architect", "data_scientist", "business_strategist",
    "philosophical_dialectic", "emotional_calibration", "general_chat",
    "legal_advisor",   # ← 新增
]
```

**注意**：這只是「告訴型別系統存在這個 skill」。要讓 router LLM 真的選它，還要：

1. 改 router prompt（Step 3）
2. 在 SkillRegistry 註冊（Step 6 / Step 8）
3. 在 heuristic fallback 加 keyword 觸發（Step 2）

---

## Step 2：讀懂 `IntentRouter` — LLM + heuristic 雙軌

打開 [`app/router/intent_router.py`](../../app/router/intent_router.py)，131 行。核心邏輯：

```python
async def route_message(self, user_input: str, recent_history: str) -> RouterResult:
    emotion = detect_emotion(user_input)   # 1. 純規則先算情緒
    if self.llm is None:
        return self._heuristic_route(user_input, emotion)   # 2a. 沒 LLM → heuristic

    try:
        prompt = render_router_prompt(user_input, recent_history)
        raw_output = await self.llm.complete(prompt)
        parsed = self._parse_router_output(raw_output)
        result = RouterResult.model_validate(parsed)
        return self._normalize_result(result, user_input, emotion)
    except Exception:
        return self._heuristic_route(user_input, emotion)   # 2b. LLM 失敗 → heuristic
```

三層防線：

1. **emotion 永遠先算**（純規則，不會失敗）
2. **LLM 路由**為主
3. **heuristic** 為 fallback

### 2-1 為什麼要 heuristic fallback？

LLM 失敗的情境很多：超時、API quota、解析失敗、confidence 太低。完全靠 LLM 等於把整個 graph 卡死。`_heuristic_route` 用關鍵字 + emotion 規則，保證**永遠回得了一個合理結果**。

```python
TECH_KEYWORDS = ("supabase", "fastapi", "rag", "api", "schema", ...)
DATA_KEYWORDS = ("ab test", "metric", "實驗", "資料", ...)
BUSINESS_KEYWORDS = ("商業", "定價", "市場", ...)

def _heuristic_route(self, user_input, emotion):
    lowered = user_input.lower()
    if any(k in lowered for k in TECH_KEYWORDS):
        return RouterResult.fallback(..., target_skill="tech_architect", confidence=0.65)
    if any(k in lowered for k in DATA_KEYWORDS):
        return RouterResult.fallback(..., target_skill="data_scientist", confidence=0.65)
    # ...
    if emotion in {"anxious", "frustrated"}:
        return RouterResult.fallback(..., target_skill="emotional_calibration", confidence=0.7)
    # 最後 fallback
    return RouterResult.fallback(..., target_skill="general_chat", confidence=0.5)
```

### 2-2 ✏️ 改成你的需求：替你的領域加 keyword

假設加 `legal_advisor`：

```python
# app/router/intent_router.py 頂部
LEGAL_KEYWORDS = ("法律", "合約", "勞基法", "訴訟", "權益", "違法")

# _heuristic_route 加一段（放在 emotion 規則之前）
if any(k in lowered for k in LEGAL_KEYWORDS):
    return RouterResult.fallback(
        user_input,
        target_skill="legal_advisor",
        emotion_state=emotion,
        response_mode="structured",
        is_rag_required=True,
        rag_categories=["legal"],   # ← 對應你 KB 的 category
        confidence=0.7,
    )
```

LLM 失敗時，含這些關鍵字的訊息會穩定走到 legal_advisor。

---

## Step 3：router prompt + confidence gate

打開 [`app/router/prompts.py`](../../app/router/prompts.py)：

```python
ROUTER_PROMPT = """你是 LINE Bot 的訊息路由器。你的任務不是回答問題，而是判斷應該交給哪個 skill。

## Available Skills
1. tech_architect - 用於系統架構、資料庫、API、部署、RAG、技術決策。
2. data_scientist - 用於資料分析、模型評估、指標設計、實驗設計。
...

## Input
User message: {user_input}
Recent conversation summary: {recent_history}

## Rules
1. 只輸出 JSON。
2. 不要回答使用者問題。
3. 若問題涉及技術知識、RAG、LangGraph、系統架構... is_rag_required = true。
...
8. rag_categories 只從以下清單選擇（可多選）：rag、engineering、architecture、code、...

## Output JSON
{{
  "target_skill": "...",
  "is_rag_required": true,
  ...
  "confidence": 0.0
}}
"""
```

### 3-1 confidence threshold gate

[`intent_router.py:44-61`](../../app/router/intent_router.py#L44-L61) 的 `_normalize_result`：

```python
def _normalize_result(self, result, user_input, fallback_emotion):
    normalized = result.model_copy(update={
        "rag_query": result.rag_query.strip() or user_input.strip(),
        "emotion_state": result.emotion_state or fallback_emotion,
        "rag_categories": [c for c in result.rag_categories if c in VALID_RAG_CATEGORIES],
    })
    if normalized.confidence < self.confidence_threshold:
        return self._heuristic_route(user_input, fallback_emotion)
    return normalized
```

兩道防線：

- **`rag_categories` 白名單過濾**：LLM 回的 category 不在 `VALID_RAG_CATEGORIES` 直接丟掉（即使 LLM 自己編一個 category）
- **confidence < 0.55** → 降級到 heuristic（即使 LLM 給了結構正確的 JSON）

### 3-2 ✏️ 改成你的需求：調 confidence threshold

```python
# 建立 router 時
router = IntentRouter(llm=llm, confidence_threshold=0.7)  # 更嚴格
```

或從 settings 拉：

```python
# app/config.py
router_confidence_threshold: float = 0.55

# app/dependencies.py
router = IntentRouter(llm=llm, confidence_threshold=settings.router_confidence_threshold)
```

提高 threshold = 更多 query 走 heuristic（更穩定但較笨）。降低 = 更信任 LLM（較聰明但較不穩定）。

### 3-3 ✏️ 改 router prompt 加新 skill

把上面 `ROUTER_PROMPT` 加一條：

```python
ROUTER_PROMPT = """...
## Available Skills
...
6. general_chat - 用於一般對話。
7. legal_advisor - 用於法律相關問題、合約、勞動權益、條文解讀。  ← 新增

## Input
...
"""
```

router LLM 下次看到「我簽合約該注意什麼」就會選 `legal_advisor`。

---

## Step 4：`emotion_detector` — 純規則為什麼比 LLM 好

[`app/router/emotion_detector.py`](../../app/router/emotion_detector.py)，27 行：

```python
ANXIOUS_KEYWORDS = ("焦慮", "擔心", "害怕", "可怕", "恐懼", "沒人用", "緊張", "壓力", "panic")
FRUSTRATED_KEYWORDS = ("卡住", "煩", "崩潰", "受不了", "失敗", "挫折", "怒")
CONFUSED_KEYWORDS = ("不懂", "看不懂", "為什麼", "怎麼會", "confused")
URGENT_KEYWORDS = ("立即", "馬上", "緊急", "urgent", "asap")
REFLECTIVE_KEYWORDS = ("意義", "價值", "我在想", "反思", "存在")


def detect_emotion(text: str) -> EmotionState:
    lowered = text.lower()
    if any(k in text for k in ANXIOUS_KEYWORDS):
        return "anxious"
    if any(k in text for k in FRUSTRATED_KEYWORDS):
        return "frustrated"
    if any(k in text for k in CONFUSED_KEYWORDS) or "?" in text:
        return "confused"
    if any(k in text for k in URGENT_KEYWORDS):
        return "urgent"
    # ...
    return "neutral"
```

純規則的好處：

- **零成本**（不打 LLM）
- **零延遲**
- **完全可預測**
- **永遠不會失敗**

代價：規則寫死，撞不到 keyword 就回 `neutral`。但 emotion 在系統裡只是「答案風格調整」，不是路由決策核心，**這個精度足夠**。

### 4-1 ✏️ 改成你的需求：加你自己的情緒分類

```python
# app/router/emotion_detector.py 加
EXCITED_KEYWORDS = ("興奮", "太棒了", "wow", "讚")

def detect_emotion(text: str) -> EmotionState:
    # ... 既有規則
    if any(k in text for k in EXCITED_KEYWORDS):
        return "excited"
    return "neutral"
```

別忘了 `EmotionState` Literal 也要加 `"excited"`：

```python
# app/router/schemas.py
EmotionState = Literal[..., "excited"]
```

---

## Step 5：`categories.py` — RAG filter 白名單

[`app/router/categories.py`](../../app/router/categories.py)：

```python
VALID_RAG_CATEGORIES: frozenset[str] = frozenset({
    "rag", "engineering", "architecture", "code",
    "analytics", "experiments", "metrics",
    "strategy", "market", "product",
    "philosophy", "notes",
})
```

這個 `frozenset` 是 **router heuristic、router prompt、normalize 過濾三個地方共用的單一真相**。要加新 category 只改這裡。

### 5-1 ✏️ 改成你的需求：加 `legal` category

```python
# app/router/categories.py
VALID_RAG_CATEGORIES = frozenset({
    ..., "legal",   # ← 新增
})
```

確認三處同步：

1. ✅ heuristic 已可用（Step 2-2 已加）
2. ⚠️ Router prompt 也要列（Step 3-3 改 `rag_categories` 規則那行）
3. ✅ `_normalize_result` 過濾會自動接受

---

## Step 6：`SkillRegistry` — file vs supabase 兩種來源

打開 [`app/skills/registry.py`](../../app/skills/registry.py)，145 行。重點是「skill 可以從哪裡讀」。

### 6-1 從目錄讀（file mode，預設）

```python
@classmethod
def from_directory(cls, skills_root: Path) -> "SkillRegistry":
    return cls(load_skills(skills_root))
```

`load_skills` 在 [`loader.py`](../../app/skills/loader.py)，掃 `skills/*/SKILL.md`，每個檔案前面有 YAML frontmatter + system_prompt body：

```markdown
---
skill_id: tech_architect
name: 技術架構師
description: 系統設計與技術決策
category: engineering
default_temperature: 0.4
rag_categories: [engineering, architecture, code]
---

你是一個資深技術架構師...（這段就是 system_prompt）
```

### 6-2 從 Supabase 讀（supabase mode，可熱更新）

```python
@classmethod
async def from_supabase(cls, supabase_client: Any) -> "SkillRegistry":
    skills = await _fetch_skills_from_supabase(supabase_client)
    if not skills:
        raise RuntimeError("ai_skills returned 0 enabled rows; run scripts/seed_skills.py first")
    return cls(skills)
```

這個方法**首次啟動失敗會 raise**——零 skill 比舊版掛掉更危險。

### 6-3 熱更新（reload_from_supabase）

```python
async def reload_from_supabase(self, supabase_client) -> bool:
    try:
        skills = await _fetch_skills_from_supabase(supabase_client)
    except Exception as exc:
        logger.warning("skill reload failed (keeping previous): %s", exc)
        return False
    if not skills:
        logger.warning("skill reload returned 0 rows; keeping previous")
        return False

    # 單次 attribute rebind；Python GIL 下原子
    self._skills = {s.skill_id: s for s in skills}
    return True
```

注意這裡**沒有 lock**——`self._skills = {...}` 在 Python GIL 下是原子操作。reader 看到的要嘛是舊 dict、要嘛是新 dict，不會半新半舊。

### 6-4 背景 reload loop

```python
async def skill_reload_loop(registry, supabase_client, interval_seconds):
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await registry.reload_from_supabase(supabase_client)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("...")
```

FastAPI lifespan 啟動時 `asyncio.create_task(skill_reload_loop(...))`，shutdown 時 cancel。

---

## Step 7：`ai/factory.py` — role-based model 與溫度

[`app/ai/factory.py`](../../app/ai/factory.py)，94 行。所有 LLM 實例都從這裡產出。

### 7-1 三個 role

```python
LLMRole = Literal["router", "generator", "judge"]


def build_llm(settings: Settings, role: LLMRole) -> LLMBackend:
    if role == "router":
        model = settings.router_model
    elif role == "judge":
        model = settings.judge_model or settings.router_model
    else:
        model = settings.generator_model

    temperature = 0.0 if role in ("router", "judge") else None
    # ...
```

**為什麼 router / judge 強制 temperature=0.0？**

- router 要 deterministic——同樣的 input 永遠回同樣的 skill，否則 graph 行為不可重現
- judge 要 deterministic——同樣的草稿永遠給同樣的分數，否則 retry 邏輯會抖

generator `temperature=None`（用 model 預設或 skill 自己的 `default_temperature`）——生成需要創意。

### 7-2 Provider 選擇

```python
provider = settings.ai_provider   # openai / claude / gemini / github_copilot

if provider == "openai":
    from app.ai.providers.openai_provider import OpenAILLM
    return OpenAILLM(settings, model, temperature=temperature)
if provider == "claude":
    from app.ai.providers.anthropic_provider import AnthropicLLM
    return AnthropicLLM(settings.anthropic_api_key, model, temperature=temperature)
# ...
```

provider 切換完全靠 `.env`，不用改 code。

### 7-3 四個 provider 實作各自的細節

四個 provider 在 [`app/ai/providers/`](../../app/ai/providers/) 各自一檔，介面都實作 `LLMBackend` Protocol（`async complete(prompt) -> str`），但內部差異不小：

#### OpenAILLM（`openai_provider.py:9-58`）

```python
class OpenAILLM:
    """OpenAI Responses API — for openai.com endpoints."""

    async def complete(self, prompt: str) -> str:
        t0 = time.time()
        kwargs: dict = {"model": self._model, "input": prompt}
        if self._temperature is not None:
            kwargs["temperature"] = temperature
        response = await self._client.responses.create(**kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_llm_call_if_traced(
                model=self._model, provider="openai",
                input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                cached_tokens=getattr(usage, "input_tokens_cached", 0) or 0,
                duration_ms=int((time.time() - t0) * 1000),
            )
        return response.output_text
```

關鍵：
- **用 Responses API**（非 Chat Completions），原生支援 reasoning / structured output
- 跑完自動 `record_llm_call_if_traced`——tracer 取得 token、cost、cached_tokens
- 也實作 `stream_complete` 給 [Ch 07 §8 streaming](ch07-sufficiency-generation.md#step-8-加-streaming-輸出openai-provider) 用

#### OpenAIChatLLM（`openai_provider.py:60-108`）

```python
class OpenAIChatLLM:
    """OpenAI Chat Completions API — for OpenAI-compatible endpoints (GitHub Copilot, etc.)."""
```

走老 Chat Completions API，**GitHub Copilot API、本機 Ollama、LM Studio** 等 OpenAI-compatible endpoint 都用這個。差別：

| 比較 | OpenAILLM | OpenAIChatLLM |
|------|-----------|---------------|
| API | Responses（新） | Chat Completions（舊但通用） |
| Endpoint | openai.com | 任意 compatible |
| 適用 | OpenAI 官方 | Copilot / Ollama / LM Studio |

#### AnthropicLLM（`anthropic_provider.py`）

```python
async def complete(self, prompt: str) -> str:
    response = await self._client.messages.create(
        model=self._model, max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        **({"temperature": self._temperature} if self._temperature is not None else {}),
    )
    # Extract the first text block; content may include tool_use or other block types.
    for block in response.content:
        if block.type == "text":
            return block.text
    raise RuntimeError(
        f"Anthropic returned no text block (stop_reason={response.stop_reason}, ...)"
    )
```

特別注意：

- **`max_tokens=4096` 寫死**——Claude 沒預設值，不傳會錯
- **response.content 是 block list**——可能含 tool_use 區塊，要找第一個 `type=="text"`
- 還沒實作 streaming（如果你需要 [Ch 07 §8](ch07-sufficiency-generation.md#step-8) 串流，要自己補）

#### GeminiLLM（`gemini_provider.py:4-27`）

```python
async def complete(self, prompt: str) -> str:
    kwargs = {"model": self._model, "contents": prompt}
    if self._temperature is not None:
        from google.genai import types
        kwargs["config"] = types.GenerateContentConfig(temperature=self._temperature)
    response = await self._client.aio.models.generate_content(**kwargs)
    if not response.text:
        raise RuntimeError(
            f"Gemini returned no text (finish_reason="
            f"{response.candidates[0].finish_reason if response.candidates else 'unknown'})"
        )
    return response.text
```

關鍵：

- **`response.text is None`** 代表被 safety filter 擋下——必須明確報錯，否則上層拿到 `None` 會崩
- 溫度透過 `GenerateContentConfig` 包進去（不是 top-level kwarg）

#### HuggingFaceEmbedder（`huggingface_provider.py`）

```python
class HuggingFaceEmbedder:
    """Local HuggingFace sentence-transformers embedder (spec-29)."""

    def __init__(self, settings: object) -> None:
        from sentence_transformers import SentenceTransformer
        model_name = getattr(settings, "embedding_model", "BAAI/bge-small-zh-v1.5")
        self._model = SentenceTransformer(model_name)

    async def embed_query(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        vec = await loop.run_in_executor(None, self._model.encode, text)
        return vec.tolist()
```

- **本機 embedder**，零 API 成本
- `SentenceTransformer.encode` 是同步的，用 `run_in_executor` 丟 thread pool 不阻塞 event loop
- 預設 `BAAI/bge-small-zh-v1.5` 給中文場景；換 `text-embedding-3-small` 維度可能不同——記得也改 `private_knowledge.embedding vector(N)`（見 [Ch 01 §3-2](ch01-supabase-schema.md#3-2-改成你的需求一換-embedding-模型維度)）

### 7-4 ✏️ 改成你的需求：加新 LLM provider

假設你想接 DeepSeek（OpenAI-compatible API）：

```python
# app/ai/providers/deepseek_provider.py
from app.ai.providers.openai_provider import OpenAIChatLLM

class DeepSeekLLM(OpenAIChatLLM):
    """DeepSeek 走 OpenAI-compatible Chat API。"""
    pass   # 直接繼承，差別只在 base_url


# app/ai/factory.py 加 provider 分支
def build_llm(settings, role):
    # ... 既有
    if provider == "deepseek":
        from app.ai.providers.deepseek_provider import DeepSeekLLM
        return DeepSeekLLM(
            settings.deepseek_api_key,
            settings.deepseek_base_url,    # "https://api.deepseek.com/v1"
            model, temperature=temperature,
        )
```

別忘了：

1. 加 `deepseek_api_key` / `deepseek_base_url` 到 [`app/config.py`](../../app/config.py)
2. 加 model 定價到 [`app/observability/pricing.py`](../../app/observability/pricing.py)（[Ch 09 §5-2](ch09-observability-security.md#5-2-改成你的需求加新模型)）

### 7-5 ✏️ 改成你的需求：不同 role 用不同 provider

預設邏輯所有 role 用同一個 provider。如果你想 router 用便宜的 gpt-4o-mini、generator 用強的 claude-sonnet：

```python
# app/ai/factory.py:33
def build_llm(settings, role):
    if role == "router":
        provider = settings.router_provider or settings.ai_provider
        model = settings.router_model
    elif role == "judge":
        provider = settings.judge_provider or settings.ai_provider
        model = settings.judge_model or settings.router_model
    else:
        provider = settings.generator_provider or settings.ai_provider
        model = settings.generator_model

    # 後面 provider 分支照舊
```

`.env`：

```bash
AI_PROVIDER=openai            # 預設
ROUTER_PROVIDER=openai
GENERATOR_PROVIDER=claude     # generator 用 claude
JUDGE_PROVIDER=openai
```

### 7-6 ✏️ 改 router 模型

```bash
# .env
ROUTER_MODEL=gpt-4o-mini       # 預設常見便宜選擇
GENERATOR_MODEL=gpt-4o
JUDGE_MODEL=gpt-4o-mini
```

router / judge 不需要強模型——decision 很簡單，便宜模型夠用。把成本省在 generator 上。

---

## Step 8：✏️ 加一個新 skill 跑通 router

完整流程整合 Step 1-7，加一個 `legal_advisor`：

### 8-1 在 schema.sql 加 SkillId

```python
# app/router/schemas.py
SkillId = Literal[..., "legal_advisor"]
```

### 8-2 加 heuristic keyword（Step 2-2 已示範）

```python
# app/router/intent_router.py
LEGAL_KEYWORDS = ("法律", "合約", "勞基法", "訴訟", "權益", "違法")

# _heuristic_route 內加分支
```

### 8-3 加 router prompt 條目

```python
# app/router/prompts.py
ROUTER_PROMPT = """...
6. general_chat - 用於一般對話。
7. legal_advisor - 用於法律相關問題、合約、勞動權益、條文解讀。
...
"""
```

### 8-4 加 RAG category

```python
# app/router/categories.py
VALID_RAG_CATEGORIES = frozenset({..., "legal"})
```

### 8-5 註冊 skill（兩種方式擇一）

**方式 A：file mode**——新增 `skills/legal_advisor/SKILL.md`：

```markdown
---
skill_id: legal_advisor
name: 法律顧問
description: 法規諮詢、合約分析、勞動權益
category: legal
default_temperature: 0.3
rag_categories: [legal]
---

你是一個資深法律顧問。回答時必須：
1. 明確引用法條（標出條號）
2. 說明適用情境與例外
3. 提醒使用者「本回答僅供參考，建議諮詢律師」
4. 不確定時誠實說不知道
```

跑：

```bash
# 把 SKILL.md 同步到 Supabase
poetry run python scripts/seed_skills.py
```

**方式 B：直接 INSERT supabase**

```sql
insert into ai_skills (
  skill_id, name, description, category, system_prompt, version, enabled,
  default_temperature, output_style
) values (
  'legal_advisor',
  '法律顧問',
  '法規諮詢、合約分析、勞動權益',
  'legal',
  '你是一個資深法律顧問...',
  '0.1.0',
  true,
  0.3,
  '{}'::jsonb
) on conflict (skill_id) do update
set name = excluded.name, description = excluded.description,
    system_prompt = excluded.system_prompt, default_temperature = excluded.default_temperature,
    enabled = excluded.enabled;
```

### 8-6 跑 stub channel 驗證

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    result = await services.router.route_message(
        "我的勞動契約裡有競業條款，這個會無效嗎？",
        recent_history=""
    )
    print(result.model_dump_json(indent=2))

asyncio.run(main())
'
```

預期：`target_skill = "legal_advisor"`、`rag_categories` 含 `"legal"`、`is_rag_required = true`。

---

## Step 9：✏️ 把 SkillRegistry 從 file 切到 supabase 熱更新

### 9-1 同步既有 SKILL.md 到 Supabase

```bash
poetry run python scripts/seed_skills.py
```

跑完去 [Supabase Studio](https://app.supabase.com/) Table Editor 確認 `ai_skills` 有對應筆數。

### 9-2 開啟 supabase mode

```bash
# .env
SKILLS_SOURCE=supabase
SKILLS_RELOAD_INTERVAL_SECONDS=60   # 每 60 秒重新拉一次
```

[`app/dependencies.py`](../../app/dependencies.py) 會依 `SKILLS_SOURCE` 在啟動時用 `from_supabase` 而非 `from_directory`，並啟動 `skill_reload_loop`。

### 9-3 測試熱更新

```bash
# Terminal 1：啟動服務
poetry run uvicorn app.main:app --reload

# Terminal 2：直接改 Supabase
psql "$SUPABASE_DB_URL" -c "
  update ai_skills
  set system_prompt = '你是極度簡潔的法律顧問，每次回應不超過 100 字。'
  where skill_id = 'legal_advisor';
"
```

等最多 60 秒，下次跟 bot 互動會看到新 prompt 生效——**完全沒重啟服務**。

### 9-4 ✏️ 想立即生效不等 60 秒

加一個 admin endpoint：

```python
# app/admin/router.py
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import RuntimeServices, get_runtime_services

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/reload-skills")
async def reload_skills(services: RuntimeServices = Depends(get_runtime_services)):
    ok = await services.skill_registry.reload_from_supabase(services.supabase_client)
    if not ok:
        raise HTTPException(500, "reload failed")
    return {"ok": True, "count": len(services.skill_registry.list())}
```

```bash
curl -X POST http://localhost:8000/admin/reload-skills
```

> ⚠️ Production 記得加 auth（API key / IP allowlist）。

---

## 🎯 本章驗收

### Step 1：router 純 heuristic 模式

```bash
poetry run python -c '
import asyncio
from app.router.intent_router import IntentRouter
from app.router.schemas import RouterResult

async def main():
    router = IntentRouter(llm=None)   # 故意不給 LLM
    cases = [
        "supabase 怎麼設 RLS？",
        "我覺得最近壓力好大",
        "勞基法第 84 條之 1 是什麼？",
        "今天天氣不錯",
    ]
    for c in cases:
        r = await router.route_message(c, recent_history="")
        print(f"{c[:20]:<22} → {r.target_skill} (conf={r.confidence}, emotion={r.emotion_state})")

asyncio.run(main())
'
```

預期：技術問題走 `tech_architect`、情緒問題走 `emotional_calibration`、其他走 `general_chat`。

### Step 2：router LLM 模式 + confidence gate

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.ai.factory import build_llm
from app.router.intent_router import IntentRouter

async def main():
    llm = build_llm(Settings(), role="router")
    router = IntentRouter(llm=llm, confidence_threshold=0.5)

    r = await router.route_message(
        "幫我設計 LINE bot 怎麼接 webhook，需要 ngrok 嗎？",
        recent_history=""
    )
    print(r.model_dump_json(indent=2))

asyncio.run(main())
'
```

預期：`target_skill = "tech_architect"`、`is_rag_required = true`、`confidence > 0.5`。

### Step 3：SkillRegistry 兩種來源

```bash
# file mode
SKILLS_SOURCE=file poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    print("skills from file:", [s.skill_id for s in services.skill_registry.list()])

asyncio.run(main())
'

# supabase mode
SKILLS_SOURCE=supabase poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    print("skills from supabase:", [s.skill_id for s in services.skill_registry.list()])

asyncio.run(main())
'
```

預期兩個列表一致（前提是已跑過 `seed_skills.py`）。

### Step 4：emotion_detector 規則

```bash
poetry run python -c '
from app.router.emotion_detector import detect_emotion
for t in ["我快崩潰了", "請問 RAG 是什麼?", "馬上幫我處理", "今天好開心"]:
    print(f"{t:<20} → {detect_emotion(t)}")
'
```

預期看到 `frustrated / confused / urgent / neutral`。

---

## 下一章

[Ch 05：Query 理解 — Feature Extraction + Query Transform](ch05-query-understanding.md) — router 完成後，graph 開始拆解 query 結構，產出多個 seed 給後面 multi-seed retrieval 用。
