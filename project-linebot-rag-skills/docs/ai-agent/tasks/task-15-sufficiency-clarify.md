# task-15：Sufficiency Check + Clarification 分支

> 規格詳見 [spec-15](../specs/spec-15-sufficiency-clarify.md)

---

在 `fuse_scores` 後插入條件 node：資料夠 → 走 generate；不夠 → 走 clarify 產生具體追問。本 task 是 LangGraph 條件 edge 的核心教學案例。

## 前置

- task-14 完成（`rag_chunks` 已經是 fusion 後結果）

## 步驟 1：實作 SufficiencyChecker

新增 `app/graph/sufficiency.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk


@dataclass
class SufficiencyConfig:
    min_chunks: int = 2
    min_top_score: float = 0.4
    min_feature_overlap: int = 1


SufficiencyResult = tuple[Literal["sufficient", "insufficient"], list[str]]


class SufficiencyChecker:
    def __init__(self, config: SufficiencyConfig) -> None:
        self._cfg = config

    def check(
        self,
        *,
        chunks: list[KnowledgeChunk],
        features: ExtractedFeatures,
    ) -> SufficiencyResult:
        reasons: list[str] = []

        if len(chunks) < self._cfg.min_chunks:
            reasons.append(
                f"chunks={len(chunks)} < min_chunks={self._cfg.min_chunks}"
            )

        if not chunks or chunks[0].score < self._cfg.min_top_score:
            top = chunks[0].score if chunks else 0.0
            reasons.append(
                f"top_score={top:.2f} < min_top_score={self._cfg.min_top_score}"
            )

        # lexical overlap：feature 詞是否在任一 chunk 的文字中出現
        feature_terms = {features.primary_topic.lower(), *(q.lower() for q in features.qualifiers)}
        chunk_text = " ".join(c.content.lower() for c in chunks)
        hit = sum(1 for t in feature_terms if t and t in chunk_text)
        if hit < self._cfg.min_feature_overlap:
            reasons.append(
                f"feature_overlap={hit} < min={self._cfg.min_feature_overlap}"
            )

        return ("insufficient" if reasons else "sufficient", reasons)
```

> ⚠️ `chunks[0].content` 與 `score` 的實際 attribute 對齊 `KnowledgeChunk` schema。

## 步驟 2：實作 Clarifier

新增 `app/graph/clarifier.py`：

```python
from __future__ import annotations

import json
import logging
from typing import Protocol

from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk

logger = logging.getLogger(__name__)


_PROMPT = """使用者問了：{user_input}

我們找到的相關資料不足。已知 features：{features}

找到的（不足）資料摘要：
{chunks_summary}

請生成 2~3 個「具體、可一句話回答」的追問，幫助補齊資訊。要求：
- 每個追問 ≤ 30 字
- 不問空泛的「能再多說明嗎」
- 針對 features 中未明確的點

只輸出 JSON：{{"questions": ["q1", "q2", ...]}}"""


_FALLBACK_QUESTIONS = [
    "方便提供更多細節嗎？例如使用的版本或場景。",
    "你期望的結果或下一步是什麼？",
]


class Clarifier(Protocol):
    async def generate_questions(
        self, *, user_input: str, features: ExtractedFeatures, chunks: list[KnowledgeChunk]
    ) -> list[str]: ...


class LLMClarifier:
    def __init__(self, llm, model: str) -> None:
        self._llm = llm
        self._model = model

    async def generate_questions(
        self, *, user_input: str, features: ExtractedFeatures, chunks: list[KnowledgeChunk]
    ) -> list[str]:
        try:
            chunks_summary = "\n".join(
                f"- {c.content[:80]}..." for c in chunks[:3]
            ) or "（無）"
            text = await self._llm.complete_json(
                model=self._model,
                prompt=_PROMPT.format(
                    user_input=user_input,
                    features=features.model_dump_json(),
                    chunks_summary=chunks_summary,
                ),
                max_output_tokens=300,
            )
            questions = json.loads(text).get("questions", [])
            return questions or _FALLBACK_QUESTIONS
        except Exception:
            logger.warning("clarifier failed, using fallback questions")
            return _FALLBACK_QUESTIONS


def format_clarification(questions: list[str]) -> str:
    """程式組（不交給 LLM）。"""
    body = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    return f"我需要再確認幾件事：\n{body}\n\n回覆後我再幫你分析。"
```

## 步驟 3：擴充 RAGState

修改 `app/graph/state.py`：

```python
class RAGState(TypedDict, total=False):
    # ...
    sufficiency: Literal["sufficient", "insufficient"]
    sufficiency_reasons: list[str]
    clarification_questions: list[str]
```

## 步驟 4：新增 nodes 與條件 edge

修改 `app/graph/nodes.py`：

```python
from app.graph.clarifier import format_clarification


async def check_sufficiency_node(state: RAGState, services: RuntimeServices):
    # 不需 RAG 的 skill 直接視為 sufficient
    if not state["router_result"].is_rag_required:
        return {"sufficiency": "sufficient", "sufficiency_reasons": []}

    decision, reasons = services.sufficiency_checker.check(
        chunks=state.get("rag_chunks", []),
        features=state["features"],
    )
    return {"sufficiency": decision, "sufficiency_reasons": reasons}


def route_by_sufficiency(state: RAGState) -> str:
    return state["sufficiency"]  # "sufficient" | "insufficient"


async def clarify_node(state: RAGState, services: RuntimeServices):
    questions = await services.clarifier.generate_questions(
        user_input=state["user_input"],
        features=state["features"],
        chunks=state.get("rag_chunks", []),
    )
    return {
        "clarification_questions": questions,
        "responses": [format_clarification(questions)],
    }
```

## 步驟 5：改寫 graph

修改 `app/graph/rag_graph.py`：

```python
g.add_node("check_sufficiency", partial(check_sufficiency_node, services=services))
g.add_node("clarify", partial(clarify_node, services=services))

g.add_edge("fuse_scores", "check_sufficiency")
g.add_conditional_edges(
    "check_sufficiency",
    route_by_sufficiency,
    {"sufficient": "generate", "insufficient": "clarify"},
)
g.add_edge("clarify", "push")  # clarify 直接到 push
```

## 步驟 6：DI + config

修改 `app/dependencies.py`：

```python
from app.graph.sufficiency import SufficiencyChecker, SufficiencyConfig
from app.graph.clarifier import LLMClarifier

@lru_cache(maxsize=1)
def get_sufficiency_checker():
    s = get_settings()
    return SufficiencyChecker(SufficiencyConfig(
        min_chunks=s.sufficiency_min_chunks,
        min_top_score=s.sufficiency_min_top_score,
        min_feature_overlap=s.sufficiency_min_feature_overlap,
    ))

@lru_cache(maxsize=1)
def get_clarifier():
    s = get_settings()
    llm = build_llm(s, "router") if has_llm_configured(s) else None
    return LLMClarifier(llm=llm, model=s.router_model)
```

`Settings` 加：

```python
sufficiency_min_chunks: int = 2
sufficiency_min_top_score: float = 0.4
sufficiency_min_feature_overlap: int = 1
```

> ⚠️ **跨語言場景請設 `SUFFICIENCY_MIN_FEATURE_OVERLAP=0`**：lexical overlap 用 substring
> 比對；中文 features + 英文 chunks 永遠 overlap=0 → 所有 query 誤判 insufficient。
> 詳情見 [spec-15 §「跨語言查詢的已知限制」](../specs/spec-15-sufficiency-clarify.md#sufficiency-判定預設規則)
> 與 [W1 e2e 驗收](../examples/w1-e2e-verification.md) §「摩擦 2」。

## 步驟 7：測試

新增 `tests/test_sufficiency.py`：

```python
def test_sufficient_when_all_pass():
    # 構造 chunks（top score=0.8，內容含 primary_topic）
    ...

def test_insufficient_when_score_low():
    ...

def test_insufficient_when_no_overlap():
    ...
```

新增 `tests/test_clarifier.py`：

```python
@pytest.mark.asyncio
async def test_clarifier_falls_back(stub_llm_raising):
    c = LLMClarifier(llm=stub_llm_raising, model="x")
    qs = await c.generate_questions(user_input="...", features=..., chunks=[])
    assert qs == _FALLBACK_QUESTIONS
```

整合測試：在 `test_rag_graph_equivalence.py` 補一個 case，驗證 sufficient/insufficient 兩條分支都能跑完不 crash。

## 請輸出

1. `app/graph/sufficiency.py`、`app/graph/clarifier.py`
2. 修改後的 `app/graph/state.py`、`nodes.py`、`rag_graph.py`、`dependencies.py`、`config.py`
3. `tests/test_sufficiency.py`、`tests/test_clarifier.py`、整合測試補充
4. README 加「為什麼要 Sufficiency Check」段（強調誠實追問 > 強行生成）

## 驗收指令

```bash
pytest tests/test_sufficiency.py tests/test_clarifier.py -v
pytest

./scripts/run_local.sh
# 1. 傳一個知識庫沒涵蓋的問題（例：「LangGraph 怎麼接 Kubernetes Operator？」）
#    log 應顯示：sufficiency=insufficient | reasons=[chunks=0 < ...]
#    回覆：「我需要再確認幾件事：1. ... 2. ...」（具體追問，非空泛）
#
# 2. 傳一個知識庫有的問題
#    log 應顯示：sufficiency=sufficient
#    回覆：正常的 RAG 回覆
#
# 3. 傳閒聊（is_rag_required=false）
#    log 應顯示：sufficiency=sufficient（短路通過）
```

驗收通過條件：

- sufficient/insufficient 兩條 edge 都能從 graph 視覺化看到（用 `graph.get_graph().draw_mermaid()`）
- clarify LLM 失敗 → fallback 預設追問，不 crash
- 三個 sufficiency 門檻可由環境變數覆寫
