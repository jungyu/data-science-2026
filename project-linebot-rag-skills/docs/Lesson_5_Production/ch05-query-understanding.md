# Ch 05：Query 理解 — Feature Extraction + Query Transform

> 核心檔案：[`app/graph/feature_extractor.py`](../../app/graph/feature_extractor.py)、[`app/graph/query_transform.py`](../../app/graph/query_transform.py)
>
> Variant 適用性：**selfrag / reflection 必要** — basic variant 略過這層

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `ExtractedFeatures` schema：把 user_input 拆成 4 個結構化欄位 |
| 2 | 讀懂 `LLMFeatureExtractor`：LLM 抽 features + fallback 機制 |
| 3 | 看 query transform 三策略：hyde / step_back / decompose |
| 4 | 看 `query_transform_node` 怎麼塞進 graph + 失敗降級 |
| 5 | ✏️ 加自己的 transform 策略（multi-language 範例） |
| 6 | ✏️ 切換 transform 策略看檢索差異 |

---

## Step 1：`ExtractedFeatures` schema

打開 [`app/graph/feature_extractor.py:21-27`](../../app/graph/feature_extractor.py#L21-L27)：

```python
class ExtractedFeatures(BaseModel):
    primary_topic: str = Field(..., description="問題核心主題")
    qualifiers: list[str] = Field(default_factory=list, description="限定條件，最多 5")
    intent: Literal["how_to", "debug", "concept", "compare", "decide", "other"] = "other"
    entities: list[str] = Field(default_factory=list, description="命名實體，最多 8")
    raw_query: str
```

四個欄位各自的角色：

| 欄位 | 範例輸入 | 抽取結果 |
|------|---------|---------|
| `primary_topic` | 「Supabase HNSW 怎麼選 lists 參數」 | `"HNSW lists 參數"` |
| `qualifiers` | 「在 Supabase 上 ...」 | `["supabase"]` |
| `intent` | 「**為什麼**...」/「**怎麼**...」/「**A 跟 B 哪個好**」 | `"concept"` / `"how_to"` / `"compare"` |
| `entities` | 「Supabase HNSW」 | `["supabase", "hnsw"]` |

`raw_query` 保留原句，給後面節點當 fallback 或 audit 用。

### 1-1 為什麼是這 4 個欄位？

下一章 ([Ch 06](ch06-multi-seed-retrieval.md)) 的 `seed_expander` 會把這 4 個欄位**展開成多個檢索 seed**：

- `primary_topic` → 一條主 seed
- 每個 `entity` → 一條 seed（補語意連結）
- `primary_topic + qualifier` 組合 → 一條精細 seed
- `intent` 用來決定 prompt 風格

把抽取與展開分開（`feature_extractor` 不知道後面要做幾條 seed），讓兩者各自演進。

### 1-2 ✏️ 改成你的需求：加 difficulty 欄位

假設你的 KB 內容有「入門 / 進階」標記，想讓 router 偏好查相應 difficulty：

```python
# app/graph/feature_extractor.py
class ExtractedFeatures(BaseModel):
    primary_topic: str
    qualifiers: list[str] = Field(default_factory=list)
    intent: Literal["how_to", "debug", "concept", "compare", "decide", "other"] = "other"
    entities: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced", "unknown"] = "unknown"  # ← 新增
    raw_query: str
```

prompt 也要加：

```python
_PROMPT = """你是查詢結構化抽取器。讀取使用者問題，輸出 JSON。

欄位定義：
- primary_topic: 問題的核心主題（一個短語）
- qualifiers: 限定條件（版本、場景、限制等），最多 5 條
- intent: 從 [how_to, debug, concept, compare, decide, other] 擇一
- entities: 明確命名的實體（套件、產品、人名...），最多 8 條
- difficulty: 推測使用者程度，[beginner, intermediate, advanced, unknown]   ← 新增

...
"""
```

再改 fallback 補預設值：

```python
def _fallback(user_input: str) -> ExtractedFeatures:
    return ExtractedFeatures(
        primary_topic=user_input[:120],
        qualifiers=[],
        intent="other",
        entities=[],
        difficulty="unknown",   # ← 新增
        raw_query=user_input,
    )
```

之後 retriever filter 可以多帶一個 difficulty 條件。

---

## Step 2：讀懂 `LLMFeatureExtractor`

完整實作 [`feature_extractor.py:69-99`](../../app/graph/feature_extractor.py#L69-L99)：

```python
class LLMFeatureExtractor:
    def __init__(self, llm, *, name: str = "llm-feature-extractor") -> None:
        self._llm = llm

    async def extract(self, *, user_input, recent_history=None) -> ExtractedFeatures:
        if self._llm is None:
            return _fallback(user_input)

        prompt = _PROMPT.format(
            user_input=user_input,
            recent_history=recent_history or "（無）",
        )
        try:
            raw = await self._llm.complete(prompt)
            data = json.loads(_strip_fence(raw))
            data.setdefault("raw_query", user_input)
            # 限制長度避免 prompt 注入
            if isinstance(data.get("qualifiers"), list):
                data["qualifiers"] = data["qualifiers"][:5]
            if isinstance(data.get("entities"), list):
                data["entities"] = data["entities"][:8]
            return ExtractedFeatures(**data)
        except Exception:
            logger.warning("feature extraction failed, falling back to raw query", exc_info=True)
            return _fallback(user_input)
```

### 2-1 三道防線

1. **`self._llm is None` → fallback**：完全沒配 LLM 也能跑
2. **try/except 包整段**：JSON parse 失敗、validation 失敗、LLM 超時都不拋
3. **長度截斷**：`qualifiers[:5]` / `entities[:8]`——LLM 可能瞎掰一堆，截斷防 prompt 注入下游

### 2-2 `_strip_fence`：處理 markdown fence

```python
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

def _strip_fence(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()
```

很多 LLM 即使叫它「不要 markdown fence」還是會加。這個 regex 把開頭結尾的 fence 砍掉，讓 `json.loads` 能正確 parse。

### 2-3 `_fallback`：最低保證

```python
def _fallback(user_input: str) -> ExtractedFeatures:
    return ExtractedFeatures(
        primary_topic=user_input[:120],
        qualifiers=[],
        intent="other",
        entities=[],
        raw_query=user_input,
    )
```

把原句當 `primary_topic`（截 120 字防爆）、其他全空。**保證後面節點永遠拿得到合法 `ExtractedFeatures`**，graph 不會卡住。

### 2-4 ✏️ 改成你的需求：寫 rule-based extractor

如果你的領域是高度結構化（例如醫療術語、法條編號），rule-based 反而比 LLM 穩定且零成本：

```python
# app/graph/feature_extractor.py
import re

class RuleBasedFeatureExtractor:
    """純規則 extractor，零 LLM 成本。"""

    LAW_PATTERN = re.compile(r"第\s*(\d+)\s*條(?:之\s*(\d+))?")
    SYMPTOM_KEYWORDS = ("頭痛", "腹痛", "失眠", "焦慮", ...)

    async def extract(self, *, user_input, recent_history=None) -> ExtractedFeatures:
        entities = []

        # 抓法條
        for m in self.LAW_PATTERN.finditer(user_input):
            entities.append(f"第{m.group(1)}條" + (f"之{m.group(2)}" if m.group(2) else ""))

        # 抓症狀
        entities.extend(k for k in self.SYMPTOM_KEYWORDS if k in user_input)

        return ExtractedFeatures(
            primary_topic=user_input[:80],
            qualifiers=[],
            intent=self._guess_intent(user_input),
            entities=entities[:8],
            raw_query=user_input,
        )

    def _guess_intent(self, text: str) -> str:
        if "為什麼" in text or "怎麼會" in text:
            return "debug"
        if "怎麼" in text or "如何" in text:
            return "how_to"
        if "比較" in text or "差別" in text:
            return "compare"
        if "是什麼" in text or "定義" in text:
            return "concept"
        return "other"
```

註冊：

```python
# app/dependencies.py 內 build_runtime_services
from app.graph.feature_extractor import RuleBasedFeatureExtractor

feature_extractor = RuleBasedFeatureExtractor()   # 不用傳 LLM
```

graph 完全不知道你換了——`extract_features_node` 只依賴 Protocol。

---

## Step 3：query transform 三策略

打開 [`app/graph/query_transform.py`](../../app/graph/query_transform.py)。三個獨立函式對應三種策略：

### 3-1 HyDE（Hypothetical Document Embedding）

```python
async def _hyde_transform(user_input: str, settings: Any) -> tuple[str, str]:
    """產生假設性解答，拿它去 embed（而非 query 本身）。"""
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "你是一位專家。請以完整解答的形式回覆（不要重述問題本身）。"},
            {"role": "user", "content": user_input},
        ],
        max_tokens=settings.hyde_max_tokens,
        temperature=0.3,
    )
    hyde_doc = resp.choices[0].message.content.strip()
    return hyde_doc, hyde_doc   # (顯示用, embed 用) 都一樣
```

**為什麼**：embedding 是「文件 vs 文件」相似度比「問題 vs 文件」準。HyDE 用 LLM 先寫一個「假裝是答案」的段落，拿它去 embed，更容易撈到真正相關的文件。

**代價**：每次多打一次 LLM。

### 3-2 Step-back（抽象化）

```python
async def _step_back_transform(user_input: str, settings: Any) -> list[str]:
    """把具體問題抽象成 background 問題，兩者一起檢索。"""
    resp = await client.chat.completions.create(
        ...
        messages=[
            {"role": "system",
             "content": "將以下具體問題轉換成更廣泛的背景問題（一句話，不超過 30 字）。"
                        "只輸出問題，不加說明。"},
            {"role": "user", "content": user_input},
        ],
        max_tokens=60,
        temperature=0.2,
    )
    abstract_q = resp.choices[0].message.content.strip()
    return [abstract_q, user_input]   # 兩條 seed
```

**為什麼**：「Python 3.12 的 GIL 怎麼讓 free-threaded build 可選？」這種具體問題可能 KB 沒直接答案，但「Python GIL 是什麼」可能有完整背景文件。同時撈兩條，組合答案。

### 3-3 Decompose（分解多面向）

```python
async def _decompose_transform(user_input: str, settings: Any) -> list[str]:
    """把問題分解成多個子問題並行檢索。"""
    resp = await client.chat.completions.create(
        ...
        messages=[
            {"role": "system",
             "content": f"將問題分解成最多 {max_q} 個獨立的子問題。"
                        "輸出純 JSON 物件，格式：{{\"questions\": [\"...\", \"...\"]}}。"
                        "若問題本身簡單不需分解，回傳只含原問題的陣列。"},
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},   # 強制 JSON mode
        max_tokens=200,
        temperature=0.2,
    )
    data = json.loads(resp.choices[0].message.content)
    subqueries = data.get("questions") or data.get("subqueries") or [user_input]
    return subqueries[:max_q]
```

**為什麼**：「比較 React、Vue、Svelte 的狀態管理」這種複合問題拆成三個 sub-query 並行檢索，比一次撈全部準。

注意這裡用了 `response_format={"type": "json_object"}`——OpenAI 的 JSON mode，**保證**輸出是合法 JSON。

### 3-4 三策略對照

| 策略 | 適合什麼問題 | 多少條 seed | 多少次 LLM call |
|------|------------|------------|----------------|
| `none` | 已經很明確的 query | 1 | 0 |
| `hyde` | 抽象 / 短問題 | 2（hyde_doc + 原句） | 1 |
| `step_back` | 太具體、KB 沒直接答案 | 2（抽象 + 原句） | 1 |
| `decompose` | 多面向複合問題 | 1-N（依拆解結果） | 1 |

---

## Step 4：`query_transform_node` 怎麼塞進 graph + 失敗降級

[`query_transform.py:99-151`](../../app/graph/query_transform.py#L99-L151)：

```python
async def query_transform_node(state: RAGState, services: Any) -> dict:
    settings = services.settings
    strategy: str = getattr(settings, "query_transform_strategy", "none")
    user_input: str = state["user_input"]

    if strategy == "none":
        return {
            "transformed_queries": [user_input],
            "hyde_doc": None,
            "transform_strategy": "none",
        }

    try:
        if strategy == "hyde":
            hyde_doc, embed_text = await _hyde_transform(user_input, settings)
            return {
                "transformed_queries": [embed_text, user_input],
                "hyde_doc": hyde_doc,
                "transform_strategy": "hyde",
            }
        if strategy == "step_back":
            queries = await _step_back_transform(user_input, settings)
            return {...}
        if strategy == "decompose":
            subqueries = await _decompose_transform(user_input, settings)
            return {...}
    except Exception:
        logger.exception("query_transform failed (strategy=%s), falling back to none", strategy)

    # 任何失敗（或 strategy 不認識）→ fallback to single query
    return {
        "transformed_queries": [user_input],
        "hyde_doc": None,
        "transform_strategy": "none",
    }
```

### 4-1 三個關鍵設計

**設計 1：strategy 從 settings 拉**

```python
strategy: str = getattr(settings, "query_transform_strategy", "none")
```

`.env` 一行切換策略，不用改 code：

```bash
QUERY_TRANSFORM_STRATEGY=hyde   # none | hyde | step_back | decompose
```

**設計 2：失敗永遠 fallback 到 `[user_input]`**

```python
except Exception:
    logger.exception(...)
return {"transformed_queries": [user_input], ...}
```

LLM 失敗、API 超時、JSON 解析錯誤——任何狀況都不阻斷 graph。最差就是「沒做 transform」，retrieval 拿原 query 跑。

**設計 3：每個策略都更新 `transform_strategy` 欄位**

```python
return {"transformed_queries": [...], "hyde_doc": ..., "transform_strategy": "hyde"}
```

state 記下用了哪個策略，方便 trace 與 debug。「為什麼這條 query 撈到的結果跟上次不一樣？」一看 trace 就知道是策略切換。

### 4-2 在 graph 上的位置

```
[query_transform_node]  ← 你在這裡
       ↓
[extract_features_node]
       ↓
[expand_seeds_node]   ← 把 transformed_queries 與 features 合併成 seeds
       ↓
[retrieve_one_node × N]  ← Ch 06 詳述
```

---

## Step 5：✏️ 加自己的 transform 策略（multi-language）

假設你的 KB 是英文文件，但使用者用中文發問。可以加一個 `translate` 策略：

### 5-1 寫 transform 函式

```python
# app/graph/query_transform.py 加
async def _translate_transform(user_input: str, settings: Any) -> list[str]:
    """中文 → 英文翻譯，兩條 seed 同時用。"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    resp = await client.chat.completions.create(
        model=settings.router_model,
        messages=[
            {"role": "system",
             "content": "Translate the user's question into English. Output only the translation."},
            {"role": "user", "content": user_input},
        ],
        max_tokens=200,
        temperature=0,
    )
    en_query = resp.choices[0].message.content.strip()
    return [en_query, user_input]
```

### 5-2 加到 `query_transform_node` 分支

```python
if strategy == "translate":
    queries = await _translate_transform(user_input, settings)
    logger.info("query_transform: translate → %d queries", len(queries))
    return {
        "transformed_queries": queries,
        "hyde_doc": None,
        "transform_strategy": "translate",
    }
```

### 5-3 啟用

```bash
# .env
QUERY_TRANSFORM_STRATEGY=translate
```

跑一個中文 query 看 trace 確認兩條 seed（中英各一）都送進 retriever。

---

## Step 6：✏️ 切換策略看檢索差異

最直接的驗收——同一個 query，跑 4 種策略，看撈到的 chunk 差多少。

### 6-1 寫驗證 script

```python
# scripts/compare_transform.py
import asyncio, os
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def run_with_strategy(strategy: str, query: str):
    os.environ["QUERY_TRANSFORM_STRATEGY"] = strategy
    services = await build_runtime_services(Settings())

    stub = services.channels["stub"]
    stub.pushed.clear()

    inp = ChannelInput(
        channel="stub",
        external_user_id=f"U_eval_compare_{strategy}",
        external_message_id=f"msg_{strategy}",
        raw_text=query,
    )

    final_state = None
    # 直接 invoke graph 取 state，不走 process_channel_input
    # （process_channel_input 沒回傳 final_state，要直接打 graph）
    config = {"configurable": {"thread_id": f"compare-{strategy}"}}
    final_state = await services.rag_graph.ainvoke(
        {"user_input": query, "channel": "stub",
         "external_user_id": f"U_eval_{strategy}",
         "external_message_id": "x", "recent_history": "",
         "dry_run": True},
        config=config,
    )

    chunks = final_state.get("rag_chunks", [])
    print(f"\n[{strategy}] {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"  {c.get('title', '<no title>')[:60]} (score={c.get('combined_score', 0):.3f})")


async def main():
    query = "為什麼 Supabase 的 HNSW 比 IVFFlat 更適合小型 KB？"
    for strategy in ["none", "hyde", "step_back", "decompose"]:
        await run_with_strategy(strategy, query)

asyncio.run(main())
```

### 6-2 跑

```bash
poetry run python scripts/compare_transform.py
```

預期看到不同策略撈到的 top chunks 有重疊但不完全相同。決定哪個策略適合你的 KB 跟使用者問題分佈。

---

## 🎯 本章驗收

### Step 1：feature extractor 純 fallback 模式

```bash
poetry run python -c '
import asyncio
from app.graph.feature_extractor import LLMFeatureExtractor

async def main():
    fe = LLMFeatureExtractor(llm=None)   # 不給 LLM
    result = await fe.extract(user_input="Supabase HNSW 怎麼選 lists？")
    print(result.model_dump_json(indent=2))

asyncio.run(main())
'
```

預期：拿到合法 `ExtractedFeatures`（`primary_topic` = 原句、其他空）。**不會拋例外**。

### Step 2：feature extractor LLM 模式

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.ai.factory import build_llm
from app.graph.feature_extractor import LLMFeatureExtractor

async def main():
    llm = build_llm(Settings(), role="router")
    fe = LLMFeatureExtractor(llm=llm)
    result = await fe.extract(
        user_input="比較 React、Vue、Svelte 的狀態管理機制有何不同？",
        recent_history="使用者剛問過 React Context API",
    )
    print(result.model_dump_json(indent=2))

asyncio.run(main())
'
```

預期：`intent = "compare"`、`entities` 含 react / vue / svelte。

### Step 3：四種 transform 策略

```bash
for s in none hyde step_back decompose; do
  echo "=== strategy=$s ==="
  QUERY_TRANSFORM_STRATEGY=$s poetry run python -c "
import asyncio, os
from app.config import Settings
from app.graph.query_transform import query_transform_node
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    state = {'user_input': '比較 React、Vue、Svelte 的狀態管理'}
    result = await query_transform_node(state, services)
    print(f'strategy={result[\"transform_strategy\"]}, queries={result[\"transformed_queries\"]}')

asyncio.run(main())
"
done
```

預期：
- `none` → 1 query
- `hyde` → 2 queries（hyde doc + 原句）
- `step_back` → 2 queries（抽象 + 原句）
- `decompose` → 3 queries（react / vue / svelte 各一）

### Step 4：transform 失敗降級

把 OpenAI key 故意設錯：

```bash
OPENAI_API_KEY=sk-invalid QUERY_TRANSFORM_STRATEGY=hyde poetry run python -c '
import asyncio
from app.config import Settings
from app.graph.query_transform import query_transform_node
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    result = await query_transform_node({"user_input": "test"}, services)
    print(result)

asyncio.run(main())
'
```

預期：拿到 `{"transformed_queries": ["test"], "hyde_doc": None, "transform_strategy": "none"}`——LLM 失敗，graceful degrade 回 single query。

---

## 下一章

[Ch 06：Multi-seed Retrieval + Fusion + Rerank](ch06-multi-seed-retrieval.md) — 拿到 features + transformed_queries 後，怎麼展開成多 seed 並行檢索，再用 RRF 合併、cross-encoder 重排。
