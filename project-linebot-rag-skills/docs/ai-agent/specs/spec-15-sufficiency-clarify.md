# Spec-15：Sufficiency Check + Clarification 分支（P3）

## 背景

P2 完成後 retrieval 品質提升，但仍會遇到「資料不足」的情況——可能是知識庫沒涵蓋、可能是使用者問題太模糊。目前 generator 在這種情況會強行生成（加前綴「目前知識庫沒有足夠資料」），對使用者價值低。

更好的做法是**先判斷資訊是否足夠生成可信回覆，不夠就走 Clarification 分支，產生具體可回答的追問**。這也是 LangGraph 條件 edge 的最佳教學場景。

借鑑：project-diagnosis spec-005（rule engine 的 ambiguity_flags / suggested_questions）、spec-007（generation orchestrator 的 missing 處理）。

## 設計

### Graph 位置

```
fuse_scores → check_sufficiency
                ├─ "sufficient"   → build_answer_contract（spec-16）
                └─ "insufficient" → clarify → push
```

### Sufficiency 判定（預設規則）

回傳 `"sufficient"` 必須**同時**滿足：

1. `len(rag_chunks) >= MIN_CHUNKS`（預設 2）
2. `rag_chunks[0].score >= MIN_TOP_SCORE`（預設 0.4）
3. 至少 N 個 features 在 chunks 文字中出現（lexical overlap，預設 N=1）

任一條不滿足 → `"insufficient"`。

> 規則簡單刻意。學生看得懂、改得動。後續可換成 LLM-based 判定，但教學版優先用 rule-based。

> ⚠️ **跨語言查詢的已知限制**（[W1 e2e 驗收](../examples/w1-e2e-verification.md) §「摩擦 2」發現）：
> 
> Lexical overlap 用 case-insensitive 子字串比對。若 features 是中文（如 `primary_topic="決定方式"`）但 chunks 是英文（`"When to use Server Components..."`），overlap 永遠 = 0 → 全部 query 被誤判為 insufficient。
>
> **解法**（學生依需求選一）：
> - **A. 預設關閉**：`SUFFICIENCY_MIN_FEATURE_OVERLAP=0`（最快，但失去這條規則的把關價值）
> - **B. 同語言查詢**：限制使用者 / extractor 的語言與 chunks 一致
> - **C. 升級為 token-level / multilingual 比對**：用 spaCy multilingual model 或 embedding-based 相似度替換 substring 比對（學生延伸題；不在 P3 教學主線範圍）
>
> 預設值的取捨：保留 `min=1` 對單語場景有把關意義；學生轉到跨語言領域時應主動調 0 並用其他規則（min_chunks / min_top_score）補強。

### Clarification Node

LLM prompt 結構：

```
使用者問了：{user_input}
我們找到的相關資料不足以給出可信回覆。已知的 features：{features}
找到的（不足）資料摘要：{chunks_summary}

請生成 2~3 個「具體、可一句話回答」的追問，幫助補齊資訊。要求：
- 每個追問 ≤ 30 字
- 不問空泛的「能再多說明嗎」
- 針對 features 中未明確的點

輸出 JSON：{"questions": [...]}
```

Clarification 回覆組合（程式組，**不交給 LLM**）：

```
我需要再確認幾件事：
1. {q1}
2. {q2}
3. {q3}

回覆後我再幫你分析。
```

### State 新增欄位

```python
class RAGState(TypedDict, total=False):
    ...
    sufficiency: Literal["sufficient", "insufficient"]
    sufficiency_reasons: list[str]            # debug 用，列出未通過的判定條件
    clarification_questions: list[str]        # clarify node 產出
```

### 失敗降級

- `clarify` LLM 失敗 → 回傳預設追問「方便提供更多細節嗎？例如使用的版本、發生情境、預期結果。」
- `sufficiency` 判定永不失敗（純程式）

### 不啟用 sufficiency 的情境

- `router_result.skill_name == "small_talk"` 等不需 RAG 的 skill → 直接走 generate 分支（在 sufficiency node 前用 short-circuit edge 略過）

## 介面契約

**新增**：`app/graph/sufficiency.py`

```python
@dataclass
class SufficiencyConfig:
    min_chunks: int = 2
    min_top_score: float = 0.4
    min_feature_overlap: int = 1

class SufficiencyChecker:
    def __init__(self, config: SufficiencyConfig) -> None: ...
    def check(
        self, *, chunks: list[KnowledgeChunk], features: ExtractedFeatures
    ) -> tuple[Literal["sufficient", "insufficient"], list[str]]: ...
```

**新增**：`app/graph/clarifier.py`

```python
class Clarifier(Protocol):
    async def generate_questions(
        self, *, user_input: str, features: ExtractedFeatures, chunks: list[KnowledgeChunk]
    ) -> list[str]: ...
```

**新增 nodes**：`check_sufficiency_node`、`clarify_node`

**修改**：`app/graph/rag_graph.py` 加入 `add_conditional_edges("check_sufficiency", route_by_sufficiency, {"sufficient": "build_answer_contract", "insufficient": "clarify"})`

## 驗收標準

- 問一個知識庫沒涵蓋的問題 → log 顯示 `sufficiency=insufficient`，回覆是具體追問而非「沒有資料」
- 問一個知識庫有的問題 → log 顯示 `sufficiency=sufficient`，走 generate 分支
- `small_talk` skill 不觸發 sufficiency 判定（看 log 略過）
- `SufficiencyConfig` 三個門檻可由環境變數覆寫
- clarify LLM 失敗時，使用預設追問模板，不 crash
