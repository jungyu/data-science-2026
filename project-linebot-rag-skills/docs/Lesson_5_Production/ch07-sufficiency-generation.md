# Ch 07：Sufficiency + Clarifier + 兩階段生成

> 核心檔案：[`app/graph/sufficiency.py`](../../app/graph/sufficiency.py)、[`app/graph/clarifier.py`](../../app/graph/clarifier.py)、[`app/generator/contract.py`](../../app/generator/contract.py)、[`app/generator/narrative.py`](../../app/generator/narrative.py)、[`app/generator/formatter.py`](../../app/generator/formatter.py)、[`app/generator/prompts.py`](../../app/generator/prompts.py)
>
> Variant 適用性：**selfrag / reflection 必要** — basic variant 走單階段生成

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `SufficiencyChecker`：三條規則純判斷夠不夠 |
| 2 | 看 `LLMClarifier`：不夠時生成具體追問 |
| 3 | 為什麼要拆兩階段（contract + narrative） |
| 4 | 讀懂 Stage 1：`AnswerContractBuilder`（純程式組） |
| 5 | 讀懂 Stage 2：`NarrativeRenderer`（受限 LLM + 模板降級） |
| 6 | 看 `formatter.py` / `prompts.py` 細節 |
| 7 | ✏️ 調 sufficiency 門檻 |
| 8 | ✏️ 加 streaming 輸出（OpenAI provider） |
| 9 | ✏️ 改 contract builder 的 `_summary` 加自己領域用語 |

---

## Step 1：`SufficiencyChecker` — 純規則判斷夠不夠

打開 [`app/graph/sufficiency.py`](../../app/graph/sufficiency.py)，72 行：

```python
@dataclass
class SufficiencyConfig:
    min_chunks: int = 2
    min_top_score: float = 0.4
    min_feature_overlap: int = 1


class SufficiencyChecker:
    def __init__(self, config: SufficiencyConfig) -> None:
        self._cfg = config

    def check(self, *, chunks, features) -> SufficiencyResult:
        reasons: list[str] = []

        # 規則 1：chunks 數量
        if len(chunks) < self._cfg.min_chunks:
            reasons.append(f"chunks={len(chunks)} < min_chunks={self._cfg.min_chunks}")

        # 規則 2：top chunk 的 vector_score
        top_score = chunks[0].vector_score if chunks else 0.0
        if top_score < self._cfg.min_top_score:
            reasons.append(f"top_score={top_score:.2f} < min_top_score={self._cfg.min_top_score}")

        # 規則 3：feature 詞彙 lexical overlap
        terms: set[str] = set()
        if features.primary_topic:
            terms.add(features.primary_topic.lower())
        for q in features.qualifiers:
            if q:
                terms.add(q.lower())
        chunk_text = " ".join(c.content.lower() for c in chunks)
        hit = sum(1 for t in terms if t and t in chunk_text)
        if hit < self._cfg.min_feature_overlap:
            reasons.append(f"feature_overlap={hit} < min={self._cfg.min_feature_overlap}")

        return ("insufficient" if reasons else "sufficient", reasons)
```

### 1-1 三條規則的意義

| 規則 | 抓什麼問題 |
|------|----------|
| `min_chunks=2` | 只撈到 1 篇文件 → 證據單薄 |
| `min_top_score=0.4` | 最高分都 < 0.4 → 整批都不相關 |
| `min_feature_overlap=1` | feature 詞一個都沒在 chunks 出現 → 撈錯方向 |

任何一條不過 → `insufficient` + reasons 列表（用來給 LLM 追問參考）。

### 1-2 為什麼用 `vector_score` 不用 `combined_score`？

註解寫清楚：

> 早期版本比的是 combined_score，但 spec-27 改為 RRF 後 combined_score 上限 ≈ 0.033，原 0.4 門檻永遠到不了 → 改比 vector_score（與門檻 0.4 同尺度）。

**教訓**：fusion 演算法演進時，原本用的門檻可能失效。改 fusion 時要回頭檢查所有用 score 的判斷邏輯。

### 1-3 為什麼不用 LLM 判斷？

註解：

> 故意全用程式規則：學生看得懂、改得動。後續可換成 LLM-based 判定，但教學版優先用 rule-based。

純規則的好處：

- **零成本**（不打 LLM）
- **完全可重現**（相同 chunks + features → 相同結果）
- **可單元測試**
- **判斷理由明確可解釋**（直接看 reasons list）

### 1-4 ✏️ 改成你的需求：依領域調門檻

醫療 / 法律高風險領域要更嚴格：

```python
# app/dependencies.py 改 SufficiencyConfig
sufficiency_config = SufficiencyConfig(
    min_chunks=settings.sufficiency_min_chunks,           # 預設 2
    min_top_score=settings.sufficiency_min_top_score,     # 預設 0.4
    min_feature_overlap=settings.sufficiency_min_overlap, # 預設 1
)
```

```bash
# .env
SUFFICIENCY_MIN_CHUNKS=4            # 醫療：至少 4 篇佐證
SUFFICIENCY_MIN_TOP_SCORE=0.6       # 提高相似度門檻
SUFFICIENCY_MIN_OVERLAP=2           # 至少 2 個 feature 詞要命中
```

對普通閒聊 bot：

```bash
SUFFICIENCY_MIN_CHUNKS=1            # 放寬
SUFFICIENCY_MIN_TOP_SCORE=0.3
SUFFICIENCY_MIN_OVERLAP=0
```

---

## Step 2：`LLMClarifier` — 不夠時生成具體追問

打開 [`app/graph/clarifier.py`](../../app/graph/clarifier.py)，97 行：

### 2-1 prompt 強調「具體」

```python
_PROMPT = """使用者問了：{user_input}

我們找到的相關資料不足以給出可信回覆。已知 features：{features}

找到的（不足）資料摘要：
{chunks_summary}

請生成 2~3 個「具體、可一句話回答」的追問，幫助補齊資訊。要求：
- 每個追問 ≤ 30 字
- 不問空泛的「能再多說明嗎」
- 針對 features 中未明確的點

只輸出 JSON：{{"questions": ["q1", "q2", ...]}}，不要 markdown fence、不要解釋。"""
```

關鍵：「**不問空泛的能再多說明嗎**」——明確告訴 LLM 不要產出沒幫助的客套追問。

### 2-2 fallback 永遠有

```python
_FALLBACK_QUESTIONS = [
    "方便提供更多細節嗎？例如使用的版本或場景。",
    "你期望的結果或下一步是什麼？",
]
```

LLM 失敗、`self._llm is None`、回傳格式錯誤——任何情況下都用 fallback，使用者至少看到 2 條合理追問。

### 2-3 `format_clarification`：回覆組合純程式

```python
def format_clarification(questions: list[str]) -> str:
    """程式組（不交給 LLM）。"""
    if not questions:
        questions = list(_FALLBACK_QUESTIONS)
    body = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    return f"我需要再確認幾件事：\n{body}\n\n回覆後我再幫你分析。"
```

LLM 只負責「**生問題**」，問題之外的固定文案（「我需要再確認幾件事」、編號、「回覆後我再幫你分析」）全部 hard-code。

**為什麼**：交給 LLM 組會冒出非預期回覆（例如它自己嘗試回答某個追問）。把固定文案從 LLM 拿掉，行為更可預測。

### 2-4 ✏️ 改成你的需求：改追問文案語氣

```python
# app/graph/clarifier.py
def format_clarification(questions: list[str]) -> str:
    if not questions:
        questions = list(_FALLBACK_QUESTIONS)
    body = "\n".join(f"❓ {q}" for q in questions)   # ← 加 emoji
    return f"請補充以下資訊：\n{body}"                 # ← 改開頭/收尾
```

或從 settings 拉模板：

```bash
# .env
CLARIFIER_HEADER="幫我了解更多："
CLARIFIER_FOOTER="補完後我再回覆 ✨"
```

---

## Step 3：為什麼要拆兩階段（contract + narrative）

傳統一階段生成：

```
[Chunks + Prompt] → LLM → [Final Answer]
```

問題：

- 不知道答案的「結構」是怎麼來的——全在 LLM 一次推理裡
- 改格式（加 citation、加 caveat）只能改 prompt 後祈禱
- 沒辦法獨立 audit「事實面」與「敘事面」

兩階段：

```
Stage 1（純程式）：[Chunks + Features + Router] → AnswerContract（JSON）
Stage 2（受限 LLM）：[AnswerContract + Skill prompt] → Markdown 答案
```

優點：

| 維度 | 一階段 | 兩階段 |
|------|--------|--------|
| 結構是誰組的 | LLM 自由 | Python 程式 |
| 可單元測試 | 困難 | Stage 1 完全可測 |
| Citation 一致性 | 依賴 prompt 自律 | Schema 強制每個 finding 帶 citations |
| 可審計 | 只能看最終文字 | Contract JSON 可單獨 dump |
| LLM 失敗時 | 整段崩 | Stage 2 降級為模板，Contract 內容全保留 |

---

## Step 4：Stage 1 — `AnswerContractBuilder`（純程式組）

打開 [`app/generator/contract.py`](../../app/generator/contract.py)。

### 4-1 三個 schema

```python
class Citation(BaseModel):
    chunk_id: str
    source: str
    snippet: str = Field(..., description="原文片段，給 P4 judge 對照 fidelity 用")


class KeyFinding(BaseModel):
    point: str
    citations: list[str] = Field(default_factory=list, description="chunk_id 列表")


class AnswerContract(BaseModel):
    summary: str
    key_findings: list[KeyFinding]
    caveats: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    citations: list[Citation]
```

### 4-2 `build` 的五個欄位各自怎麼來

```python
def build(self, *, features, chunks, router_result, sufficiency_reasons=None):
    return AnswerContract(
        summary=self._summary(features),
        key_findings=self._key_findings(chunks),
        caveats=self._caveats(chunks, sufficiency_reasons or []),
        next_steps=self._next_steps(router_result),
        citations=self._citations(chunks),
    )
```

**`_summary`**：依 intent 套模板：

```python
_INTENT_PHRASES = {
    "how_to": "怎麼做",
    "debug": "如何排查",
    "concept": "是什麼",
    "compare": "如何比較",
    "decide": "如何決定",
}

def _summary(self, f: ExtractedFeatures) -> str:
    intent_phrase = _INTENT_PHRASES.get(f.intent, "相關說明")
    topic = f.primary_topic or f.raw_query or "（未知主題）"
    return f"關於「{topic}」的{intent_phrase}。"
```

完全可預測，零 LLM。

**`_key_findings`**：每個 chunk 取首句：

```python
def _key_findings(self, chunks):
    out = []
    for c in chunks:
        point = _first_sentence(c.content)
        if not point:
            continue
        out.append(KeyFinding(point=point, citations=[c.id]))
    return out
```

`_first_sentence` 切首句（句號/驚嘆/問號）：

```python
def _first_sentence(text: str, max_chars: int = 120) -> str:
    cleaned = text.strip()
    for sep in ("。", "！", "？", "\n"):
        idx = cleaned.find(sep)
        if 0 < idx < max_chars:
            return cleaned[: idx + 1].strip()
    return cleaned[:max_chars].strip()
```

**`_caveats`**：兩個觸發條件：

```python
def _caveats(self, chunks, sufficiency_reasons):
    caveats = []
    if chunks and chunks[0].combined_score < self.low_score_threshold:
        caveats.append(f"Top 相關性僅 {chunks[0].combined_score:.2f}，回覆可能不完全切題")
    if sufficiency_reasons:
        caveats.append("檢索條件未全部達標：" + "; ".join(sufficiency_reasons))
    if not caveats:
        caveats.append("以下內容依當前知識庫整理，未涵蓋的最新更新請另行查證")
    return caveats
```

至少有一條 caveat——「未涵蓋最新更新」是預設保險。

**`_next_steps`**：依 response_mode 套：

```python
_RESPONSE_MODE_NEXT_STEPS = {
    "step_by_step": ["執行上述步驟後回報結果"],
    "decision_support": ["確認選擇並告知，我再幫你接下一步"],
    "debugging": ["先驗證最高機率的原因，再回報結果"],
}
```

非這三個 mode 就回空 list（不強塞 next_steps）。

**`_citations`**：每個 chunk 一個 citation：

```python
def _citations(self, chunks):
    return [
        Citation(
            chunk_id=c.id,
            source=_source_from_chunk(c),   # 詳見 _source_from_chunk
            snippet=c.content[:200],
        )
        for c in chunks
    ]
```

### 4-3 `_source_from_chunk` 怎麼推 source 字串

```python
def _source_from_chunk(c: KnowledgeChunk) -> str:
    """Citation.source 推導順序：metadata.source_url → title → category，
    PDF / Notion 來源附加 (p.42, 第 3.2 節) 後綴。"""
    meta = c.metadata if isinstance(c.metadata, dict) else {}
    base: str
    url = meta.get("source_url")
    if url:
        base = str(url)
    elif c.title:
        base = c.title
    else:
        base = c.category or "knowledge_base"

    suffix_parts = []
    page = meta.get("page_number")
    if page is not None:
        suffix_parts.append(f"p.{page}")
    section_path = meta.get("section_path")
    if section_path:
        if isinstance(section_path, list):
            suffix_parts.append(" > ".join(str(s) for s in section_path))
        else:
            suffix_parts.append(str(section_path))
    if suffix_parts:
        return f"{base} ({', '.join(suffix_parts)})"
    return base
```

優先序：**URL > title > category**，PDF 則附 `(p.42, 第 3.2 節)`。學生可以在 ingest 時把 `source_url` / `page_number` / `section_path` 塞進 metadata，這裡會自動帶出來。

### 4-4 ✏️ 改成你的需求：加自己的 intent → 用語對照

假設你的 bot 是醫療諮詢，要加 `"diagnose"` intent。**改三個地方才完整**：

**Step A：擴充 feature_extractor 的 Literal**

```python
# app/graph/feature_extractor.py:24
intent: Literal["how_to", "debug", "concept", "compare", "decide", "other", "diagnose"] = "other"
```

不改這裡的話，contract builder 看到 `intent="diagnose"` 會直接 pydantic ValidationError。

**Step B：在 prompt 加新 intent 描述**

```python
# app/graph/feature_extractor.py 的 _PROMPT
- intent: 從 [how_to, debug, concept, compare, decide, other, diagnose] 擇一
```

否則 LLM 不知道何時該回 `diagnose`。

**Step C：contract.py 對應用語**

```python
# app/generator/contract.py
_INTENT_PHRASES = {
    "how_to": "建議的處理方式",
    "debug": "症狀的可能成因",
    "concept": "醫學定義",
    "compare": "比較與差異",
    "decide": "決策建議",
    "diagnose": "鑑別診斷",   # ← 新 intent 對應的中文用語
}
```

> ⚠️ 加新 intent 至少改 feature_extractor 的 Literal、prompt、contract 三處。漏一處系統就會掉到 default fallback。

### 4-5 ✏️ 改 caveat 強度（高風險領域）

醫療法律必須附醫師/律師建議：

```python
def _caveats(self, chunks, sufficiency_reasons):
    caveats = ["⚠️ 本回答僅供參考，不可取代專業醫師診斷"]   # ← 永遠先放
    if chunks and chunks[0].combined_score < self.low_score_threshold:
        caveats.append(...)
    if sufficiency_reasons:
        caveats.append(...)
    return caveats
```

---

## Step 5：Stage 2 — `NarrativeRenderer`（受限 LLM）

打開 [`app/generator/narrative.py`](../../app/generator/narrative.py)，210 行。

### 5-1 受限 prompt

```python
_PROMPT = """你是 {skill_name} 的回覆撰寫者。依照以下 Answer Contract 寫成自然語言回覆。

嚴格規則（違反任一條視為品質不合格）：
1. 只能使用 Answer Contract 中列出的事實
2. 不得引入 Contract 外的資訊
3. 每個論點若 Contract 中有 citations，必須在敘述後標註「[來源 N]」（N 從 1 起）
4. caveats 必須完整呈現，不可省略

## Mode Instruction（spec-01，response_mode={response_mode}）
{mode_instruction}

## Emotion Instruction（spec-02，emotion_state={emotion_state}）
{emotion_instruction}

Skill system prompt（語氣依據）：
{skill_system_prompt}

Answer Contract（JSON）：
{contract_json}

{feedback_section}輸出純 markdown，不要解釋你的決策。"""
```

四條規則用「**違反任一條視為品質不合格**」強調。即使 LLM 偶爾違規，[Ch 08](ch08-judge-hitl.md) 的 judge 會檢查並觸發 retry。

### 5-2 `feedback_section`：retry 時帶上次 judge 的意見

```python
def _build_prompt(self, *, contract, skill, response_mode, emotion_state, feedback):
    feedback_section = ""
    if feedback:
        feedback_section = (
            "（前一次的問題，請改善）\n"
            + "\n".join(f"- {f}" for f in feedback)
            + "\n\n"
        )
    return _PROMPT.format(..., feedback_section=feedback_section)
```

retry 時 judge 的 issue 會塞進這段，提示 LLM 別重犯。是「Reflection 跨輪學習」的工程實現（[Ch 08](ch08-judge-hitl.md) 詳述）。

### 5-3 `_fallback_render`：LLM 失敗時的模板輸出

```python
def _fallback_render(contract: AnswerContract) -> str:
    """LLM 失敗或未配置時的模板降級輸出。
    保留所有 contract 內容，明確標註「（降級輸出）」讓使用者知道。"""
    parts = [f"**摘要**：{contract.summary}", ""]
    if contract.key_findings:
        parts.append("**重點**：")
        for i, kf in enumerate(contract.key_findings, 1):
            cites = (" [" + ", ".join(f"來源 {ci+1}" for ci, _ in enumerate(kf.citations)) + "]"
                     if kf.citations else "")
            parts.append(f"{i}. {kf.point}{cites}")
        parts.append("")
    if contract.caveats:
        parts.append("**注意事項**：")
        parts.extend(f"- {c}" for c in contract.caveats)
        parts.append("")
    # ... next_steps、citations 同理
    parts.append("（降級輸出）")
    return "\n".join(parts).strip()
```

關鍵：**所有 contract 內容都還在**——caveats、citations、key_findings 全部以模板形式顯示。使用者看到「（降級輸出）」會知道答案品質可能不如預期，但不會缺資訊。

### 5-4 `render` vs `stream_render`

```python
async def render(self, *, contract, skill, response_mode, emotion_state="neutral", feedback=None):
    text = await self._render_text(...)
    return split_for_line(text, max_chars=self.line_max_message_chars)

async def stream_render(self, *, contract, skill, response_mode, ...):
    """spec-31：以 async generator 形式 yield 文字 chunk。"""
    stream_method = getattr(self.llm, "stream_complete", None)
    if stream_method is None:
        # Provider 未實作串流：退化成一次性回覆
        text = await self.llm.complete(prompt)
        yield text
        return
    try:
        async for delta in stream_method(prompt):
            if delta:
                yield delta
    except Exception:
        yield _fallback_render(contract)
```

`render` 一次回完整 list；`stream_render` 是 async generator，逐 token yield 給 channel 串流推送（LINE quick reply / Telegram editMessage / web SSE）。

---

## Step 6：`formatter.py` / `prompts.py`

### 6-1 `formatter.py` — LINE 5000 字切段

[`app/generator/formatter.py`](../../app/generator/formatter.py)：

```python
def split_for_line(text: str, *, max_chars: int = 4500) -> list[str]:
    """LINE 訊息上限 5000 字，預留 buffer 為 4500。優先在段落邊界切。"""
    if len(text) <= max_chars:
        return [text]

    parts = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = (current + "\n\n" + paragraph).strip() if current else paragraph
        else:
            if current:
                parts.append(current)
            current = paragraph
    if current:
        parts.append(current)
    return parts
```

切點優先在段落（`\n\n`），不破壞 markdown 結構。

### 6-2 `prompts.py` — Mode / Emotion instruction

[`app/generator/prompts.py`](../../app/generator/prompts.py) 定義兩個輔助函式：

```python
def _mode_instruction(response_mode: str) -> str:
    """依 response_mode 給 generator 不同指令。"""
    return {
        "brief": "用 1-2 句話直接回答。",
        "structured": "用 3-5 點列出關鍵內容，加標題分組。",
        "step_by_step": "用編號列出每一步驟，每步驟一行。",
        "decision_support": "提供 2-3 個選項，附 trade-off。",
        "debugging": "依機率排序可能原因，附驗證步驟。",
        "reflection": "用問題引導，最後給一個觀點。",
    }.get(response_mode, "用清楚易讀的格式回應。")


def _emotion_instruction(emotion_state: str) -> str:
    """依使用者情緒調整語氣，**優先於 mode 的長度設定**。"""
    return {
        "anxious": "語氣要安撫，先承認感受再給建議，回應不超過 200 字。",
        "frustrated": "語氣要直接，不要客套，給可立即執行的下一步。",
        "confused": "用簡單詞彙，避免術語，必要時打比方。",
        "urgent": "去掉客套，直接給結論，後面才補細節。",
        "neutral": "（無特別調整）",
    }.get(emotion_state, "")
```

emotion 優先於 mode——`anxious` 即使 mode 是 `structured` 也要 ≤ 200 字。

---

## Step 7：✏️ 調 sufficiency 門檻

見 [Step 1-4](#1-4-改成你的需求依領域調門檻)。

---

## Step 8：✏️ 加 streaming 輸出（OpenAI provider）

OpenAI provider 已實作 `stream_complete`（[`app/ai/providers/openai_provider.py`](../../app/ai/providers/openai_provider.py)）。要啟用：

### 8-1 切 settings

```bash
# .env
STREAMING_ENABLED=true
STREAMING_PLACEHOLDER="⏳ 思考中，請稍候..."   # webhook.py 先推這條，再等 stream
```

### 8-2 channel 層接收串流

目前 LINE channel 不支援 editMessage，所以本專案 streaming 只支援 `http` channel（透過 SSE 推給前端）。

如果你想接 Telegram editMessage，要在 `TelegramChannel.push` 加 stream 版本：

```python
async def push_stream(self, *, recipient_id, stream):
    """先送一條 placeholder，邊收 stream 邊 editMessage。"""
    placeholder = await self._send_message(recipient_id, "⏳ 思考中...")
    msg_id = placeholder["message_id"]

    buf = ""
    async for delta in stream:
        buf += delta
        # 節流：每 500ms 或 50 字才 update 一次（避免 API rate limit）
        if len(buf) % 50 == 0:
            await self._edit_message(recipient_id, msg_id, buf)

    # 最後完整 edit
    await self._edit_message(recipient_id, msg_id, buf)
```

完整 spec-31 設計見 `docs/specs/spec-31-streaming.md`。

---

## Step 9：✏️ 改 contract builder `_summary` 加自己領域用語

預設摘要：「關於「{topic}」的{intent_phrase}。」太工整不像人話。改成：

```python
# app/generator/contract.py
def _summary(self, f: ExtractedFeatures) -> str:
    topic = f.primary_topic or f.raw_query or "你的問題"

    # 依領域客製
    if f.intent == "how_to":
        return f"OK，我來分享「{topic}」的做法。"
    if f.intent == "debug":
        return f"看起來「{topic}」遇到狀況，我們一起拆解。"
    if f.intent == "compare":
        return f"我來幫你對照「{topic}」的差異。"
    if f.intent == "concept":
        return f"關於「{topic}」的核心概念是這樣的。"

    return f"以下是我對「{topic}」整理的內容。"
```

---

## 🎯 本章驗收

### Step 1：sufficiency 三條規則

```bash
poetry run python -c '
from app.graph.sufficiency import SufficiencyChecker, SufficiencyConfig
from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk

features = ExtractedFeatures(
    primary_topic="hnsw", qualifiers=["supabase"],
    intent="how_to", entities=[], raw_query="test",
)

# Case A：完全空
checker = SufficiencyChecker(SufficiencyConfig())
print("empty:", checker.check(chunks=[], features=features))

# Case B：1 個低分 chunk
chunk1 = KnowledgeChunk(id="1", title="x", content="random content",
                        category="x", vector_score=0.2,
                        keyword_score=0, combined_score=0.2)
print("low:", checker.check(chunks=[chunk1], features=features))

# Case C：兩個高分 chunk + overlap
chunk2 = KnowledgeChunk(id="2", title="hnsw guide",
                        content="hnsw on supabase setup",
                        category="x", vector_score=0.8,
                        keyword_score=0, combined_score=0.8)
chunk3 = KnowledgeChunk(id="3", title="more", content="supabase hnsw",
                        category="x", vector_score=0.7,
                        keyword_score=0, combined_score=0.7)
print("ok:", checker.check(chunks=[chunk2, chunk3], features=features))
'
```

預期：A 三條都不過、B 兩條不過、C 過。

### Step 2：clarifier fallback

```bash
poetry run python -c '
import asyncio
from app.graph.clarifier import LLMClarifier, format_clarification
from app.graph.feature_extractor import ExtractedFeatures

async def main():
    c = LLMClarifier(llm=None)
    qs = await c.generate_questions(
        user_input="HNSW 怎麼用",
        features=ExtractedFeatures(primary_topic="HNSW", qualifiers=[], intent="how_to", entities=[], raw_query="HNSW 怎麼用"),
        chunks=[],
    )
    print("questions:", qs)
    print(format_clarification(qs))

asyncio.run(main())
'
```

預期：看到 2 條 fallback questions + 完整 format。

### Step 3：contract builder

```bash
poetry run python -c '
from app.generator.contract import AnswerContractBuilder
from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult

features = ExtractedFeatures(
    primary_topic="HNSW lists", qualifiers=["supabase"],
    intent="how_to", entities=["HNSW"], raw_query="HNSW lists 怎麼設？",
)
chunks = [
    KnowledgeChunk(id="c1", title="HNSW", content="HNSW 是基於圖的近似最近鄰索引。Supabase 預設使用 m=16。",
                   category="eng", vector_score=0.85,
                   keyword_score=0.3, combined_score=0.7,
                   metadata={"source_url": "https://docs.example.com/hnsw"}),
]
router = RouterResult(
    target_skill="tech_architect", is_rag_required=True,
    rag_query="HNSW lists", rag_categories=["engineering"],
    emotion_state="neutral", response_mode="step_by_step", confidence=0.8,
)
contract = AnswerContractBuilder().build(features=features, chunks=chunks, router_result=router)
print(contract.model_dump_json(indent=2))
'
```

預期：拿到完整 JSON 含 summary / key_findings（1 個）/ caveats / next_steps（["執行上述步驟後回報結果"]）/ citations（1 個，含 source URL）。

### Step 4：narrative fallback

```bash
poetry run python -c '
import asyncio
from app.generator.narrative import NarrativeRenderer
from app.skills.loader import SkillDefinition
# 假設你的 contract 已建好
from app.generator.contract import AnswerContract, KeyFinding, Citation

contract = AnswerContract(
    summary="關於 HNSW 的怎麼做",
    key_findings=[KeyFinding(point="HNSW 是基於圖的近似最近鄰索引", citations=["c1"])],
    caveats=["以下內容依當前知識庫整理"],
    next_steps=["執行上述步驟後回報結果"],
    citations=[Citation(chunk_id="c1", source="HNSW docs", snippet="HNSW 是...")],
)

skill = SkillDefinition(
    skill_id="tech_architect", name="技術架構師", description="...",
    category="eng", system_prompt="你是架構師...",
)

async def main():
    r = NarrativeRenderer(llm=None)   # 強制 fallback
    out = await r.render(contract=contract, skill=skill, response_mode="step_by_step")
    print(out[0])

asyncio.run(main())
'
```

預期：看到模板輸出，結尾有「（降級輸出）」。

### Step 5：整條 generation 跑通

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    inp = ChannelInput(channel="stub", external_user_id="U_demo_gen",
                       external_message_id="msg_1",
                       raw_text="HNSW lists 參數要怎麼設？")
    await process_channel_input(inp, services)
    for r, ms in services.channels["stub"].pushed:
        for m in ms:
            print(m)
            print("---")

asyncio.run(main())
'
```

預期：看到結構化回答含 citations。

---

## 下一章

[Ch 08：Judge + Reflection 迴圈 + HITL](ch08-judge-hitl.md) — 拿到 narrative 後，怎麼自審品質？不過怎麼 retry？真的不行怎麼交給人？
