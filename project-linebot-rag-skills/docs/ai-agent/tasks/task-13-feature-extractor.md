# task-13：Feature Extractor Node

> 規格詳見 [spec-13](../specs/spec-13-feature-extractor.md)

---

在 P1 完成的 graph 上，於 `route` 與 `retrieve` 之間插入 `extract_features` node。預設提供 LLM-based 實作；介面留 Protocol，學生轉題目時可換 rule-based。

## 前置

- task-12 已完成、graph 可跑
- LLM client（router 用的那顆即可）已注入 services

## 步驟 1：定義 schema 與 protocol

新增 `app/graph/feature_extractor.py`：

```python
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class ExtractedFeatures(BaseModel):
    primary_topic: str = Field(..., description="問題核心主題")
    qualifiers: list[str] = Field(default_factory=list, description="限定條件，最多 5")
    intent: Literal["how_to", "debug", "concept", "compare", "decide", "other"] = "other"
    entities: list[str] = Field(default_factory=list, description="命名實體，最多 8")
    raw_query: str


class FeatureExtractor(Protocol):
    async def extract(
        self, *, user_input: str, recent_history: str | None = None
    ) -> ExtractedFeatures: ...
```

## 步驟 2：實作 LLM-based extractor

同檔加入：

```python
import json
import logging

logger = logging.getLogger(__name__)


_PROMPT = """你是查詢結構化抽取器。讀取使用者問題，輸出 JSON。

欄位定義：
- primary_topic: 問題的核心主題（一個短語）
- qualifiers: 限定條件（版本、場景、限制等），最多 5 條
- intent: 從 [how_to, debug, concept, compare, decide, other] 擇一
- entities: 明確命名的實體（套件、產品、人名...），最多 8 條

使用者輸入：{user_input}
最近對話（可選）：{recent_history}

只輸出 JSON，不要解釋。"""


class LLMFeatureExtractor:
    def __init__(self, llm, model: str) -> None:
        self._llm = llm
        self._model = model

    async def extract(
        self, *, user_input: str, recent_history: str | None = None
    ) -> ExtractedFeatures:
        try:
            text = await self._llm.complete_json(
                model=self._model,
                prompt=_PROMPT.format(
                    user_input=user_input,
                    recent_history=recent_history or "（無）",
                ),
                max_output_tokens=400,
            )
            data = json.loads(text)
            return ExtractedFeatures(**data, raw_query=user_input)
        except Exception:
            logger.warning("feature extraction failed, falling back to raw query")
            return ExtractedFeatures(
                primary_topic=user_input,
                qualifiers=[],
                intent="other",
                entities=[],
                raw_query=user_input,
            )
```

> `complete_json` 的實際介面對齊 `app/ai/providers/*.py` 既有抽象。若還沒有 JSON-mode 包裝，先用 `complete_text` 然後手動 `json.loads`，並在 prompt 末尾加「不要 markdown fence」。

## 步驟 3：擴充 RAGState

修改 `app/graph/state.py`：

```python
from app.graph.feature_extractor import ExtractedFeatures

class RAGState(TypedDict, total=False):
    # ...既有欄位
    features: ExtractedFeatures
```

## 步驟 4：新增 node

修改 `app/graph/nodes.py`：

```python
async def extract_features_node(state: RAGState, services: RuntimeServices) -> dict:
    features = await services.feature_extractor.extract(
        user_input=state["user_input"],
        recent_history=state.get("recent_history"),
    )
    return {"features": features}
```

## 步驟 5：注入 dependency

修改 `app/dependencies.py`：

```python
from app.graph.feature_extractor import LLMFeatureExtractor

@dataclass(frozen=True)
class RuntimeServices:
    # ...既有欄位
    feature_extractor: Any = None  # 將在 get_runtime_services 注入

@lru_cache(maxsize=1)
def get_feature_extractor():
    settings = get_settings()
    llm = build_llm(settings, "router") if has_llm_configured(settings) else None
    return LLMFeatureExtractor(llm=llm, model=settings.router_model)
```

`get_runtime_services` 加入 `feature_extractor=get_feature_extractor()`。

## 步驟 6：插入 graph edge

修改 `app/graph/rag_graph.py`：

```python
g.add_node("extract_features", partial(extract_features_node, services=services))

g.add_edge(START, "route")
g.add_edge("route", "extract_features")
g.add_edge("extract_features", "retrieve")  # 取代原 route → retrieve
```

## 步驟 7：測試

新增 `tests/test_feature_extractor.py`：

```python
import pytest
from app.graph.feature_extractor import ExtractedFeatures, LLMFeatureExtractor


@pytest.mark.asyncio
async def test_llm_extractor_parses_valid_json(stub_llm_returning_valid_json):
    extractor = LLMFeatureExtractor(llm=stub_llm_returning_valid_json, model="x")
    f = await extractor.extract(user_input="Next.js 14 SSR hydration error")
    assert f.primary_topic
    assert f.intent in ["how_to", "debug", "concept", "compare", "decide", "other"]


@pytest.mark.asyncio
async def test_llm_extractor_falls_back_on_failure(stub_llm_raising):
    extractor = LLMFeatureExtractor(llm=stub_llm_raising, model="x")
    f = await extractor.extract(user_input="壞掉的問題")
    assert f.primary_topic == "壞掉的問題"
    assert f.intent == "other"


@pytest.mark.asyncio
async def test_graph_with_feature_extractor(stub_services):
    """整合測試：graph 跑完後 state 應含 features。"""
    from app.graph.rag_graph import build_rag_graph
    graph = build_rag_graph(stub_services)
    final = await graph.ainvoke({
        "user_input": "Next.js SSR error",
        "line_user_id": "U_test",
        "recent_history": "",
    })
    assert final["features"].primary_topic
```

## 請輸出

1. `app/graph/feature_extractor.py`（schema + protocol + LLMFeatureExtractor）
2. 修改後的 `app/graph/state.py`、`nodes.py`、`rag_graph.py`、`dependencies.py`
3. `tests/test_feature_extractor.py`
4. `docs/ai-agent/examples/feature-extractor-medical.md`（範例：把 extractor 換成醫療領域，示範可換性）

## 驗收指令

```bash
pytest tests/test_feature_extractor.py -v
pytest

# 手動驗證
./scripts/run_local.sh
# LINE 傳「我用 Next.js 14 做 SSR，hydration mismatch 怎麼處理？」
# log 應出現 features={primary_topic="hydration mismatch", qualifiers=["Next.js 14","SSR"], intent="debug", entities=["Next.js"]}
```
