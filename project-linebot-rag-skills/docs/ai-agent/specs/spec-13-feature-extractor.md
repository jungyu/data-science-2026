# Spec-13：Feature Extractor Node（P2）

## 背景

目前 retrieval 直接拿 `router_result.rag_query`（往往是使用者原句經輕度改寫）去做 embedding。這對單一條件問題還行，對「多條件並置」（例：「React 18 + Next.js SSR + hydration error」）會稀釋語意——多個訊號混在同一個 embedding，反而拉低高度相關但只命中單條件的 chunk。

解法是**先把使用者輸入結構化抽取為一組「特徵」**，再由 spec-14 的 multi-seed expander 把特徵展開為多條檢索 seed。此 node 是 graph 上 retrieval 之前的橋樑。

借鑑：project-diagnosis spec-002（feature extractor 模式）。

## 設計

### Graph 位置

```
route → extract_features → expand_seeds（spec-14）→ retrieve × N → ...
```

### 特徵抽取的兩種模式

| 模式 | 說明 | 何時用 |
|------|------|--------|
| **rule-based** | 用 regex / keyword list / heuristic 抽特徵 | 領域有清楚詞彙表（程式語言、症狀名、產品 SKU 等）|
| **llm-based** | 給 LLM 一個 schema，請它回填 JSON | 領域語意鬆散、表達多變 |

**預設提供 llm-based 實作**（通用性高）；rule-based 留 protocol 介面，學生轉題目可自行實作。

### Feature Schema（通用版）

```python
class ExtractedFeatures(BaseModel):
    primary_topic: str            # 主軸（必填）
    qualifiers: list[str]         # 限定條件（版本、場景、角色...）
    intent: Literal["how_to", "debug", "concept", "compare", "decide", "other"]
    entities: list[str]           # 命名實體（套件名、人名、產品名...）
    raw_query: str                # 原句保留，供 fallback
```

**領域可擴充**：學生可子類化加欄位（例如醫療版加 `symptoms`、`duration`）。骨架 4 個欄位不可改名，因為 spec-14 會讀。

### LLM Prompt 結構（預設版）

```
你是查詢結構化抽取器。讀取使用者問題，輸出 JSON，欄位定義如下：
- primary_topic：問題的核心主題（一個短語）
- qualifiers：限定條件（版本、場景、限制等），最多 5 條
- intent：意圖分類，從 [how_to, debug, concept, compare, decide, other] 擇一
- entities：明確命名的實體，最多 8 條

使用者輸入：{user_input}
（最近對話脈絡，可選）：{recent_history}

只輸出 JSON，不要解釋。
```

### State 新增欄位

```python
class RAGState(TypedDict, total=False):
    ...
    features: ExtractedFeatures
```

### 失敗降級

- LLM 呼叫失敗 → 回傳 `ExtractedFeatures(primary_topic=user_input, qualifiers=[], intent="other", entities=[], raw_query=user_input)`，graph 繼續跑
- 不因抽取失敗中斷流程

## 介面契約

**新增**：`app/graph/feature_extractor.py`

```python
class FeatureExtractor(Protocol):
    async def extract(
        self,
        *,
        user_input: str,
        recent_history: str | None = None,
    ) -> ExtractedFeatures: ...

class LLMFeatureExtractor:
    def __init__(self, llm: RouterLLM, model: str) -> None: ...
    async def extract(...) -> ExtractedFeatures: ...
```

**新增 node**：`app/graph/nodes.py::extract_features_node()`

**修改**：`app/graph/state.py` 加入 `features` 欄位；`app/graph/rag_graph.py` 在 `route` 與 `retrieve` 之間插入 `extract_features` node。

**注意**：不修改 `IntentRouter`。Feature 抽取是獨立關注點（router 管 skill 路由，extractor 管 query 結構化）。

## 驗收標準

- 給「我用 Next.js 14 做 SSR，hydration mismatch 怎麼處理？」→ 輸出 `primary_topic="hydration mismatch"`、`qualifiers=["Next.js 14", "SSR"]`、`intent="debug"`、`entities=["Next.js"]`
- LLM 失敗時，graph 仍能跑完並回覆（fallback 用原句）
- 介面 `FeatureExtractor` 是 Protocol，可被 rule-based 實作替換無需動 graph
- 學生範例：在 `docs/ai-agent/examples/` 加一份「換成醫療領域 feature extractor」的對照範例
