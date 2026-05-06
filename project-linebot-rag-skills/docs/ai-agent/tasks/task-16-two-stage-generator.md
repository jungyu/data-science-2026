# task-16：Two-stage Generator（Answer Contract）

> 規格詳見 [spec-16](../specs/spec-16-two-stage-generator.md)

---

把現行 `ResponseGenerator` 拆成兩階段：**Stage 1** 用 Python 組 Answer Contract（純程式、可單元測試）→ **Stage 2** 用受限 LLM prompt 把 contract 寫成 markdown。Stage 2 的 prompt 嚴格限制只能引用 contract 列出的事實。

## 前置

- task-15 完成（sufficient 分支才會走到 generator）

## 步驟 1：定義 Answer Contract schema

新增 `app/generator/contract.py`：

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str
    source: str
    snippet: str = Field(..., description="原文片段，用於 P4 judge citation_fidelity")


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

## 步驟 2：實作 AnswerContractBuilder（純程式、無 LLM）

同檔加入：

```python
from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult


class AnswerContractBuilder:
    def __init__(self, low_score_threshold: float = 0.5) -> None:
        self._low = low_score_threshold

    def build(
        self,
        *,
        features: ExtractedFeatures,
        chunks: list[KnowledgeChunk],
        router_result: RouterResult,
        sufficiency_reasons: list[str],
    ) -> AnswerContract:
        summary = self._summary(features)
        key_findings = self._key_findings(chunks)
        caveats = self._caveats(chunks, sufficiency_reasons)
        next_steps = self._next_steps(router_result)
        citations = self._citations(chunks)
        return AnswerContract(
            summary=summary,
            key_findings=key_findings,
            caveats=caveats,
            next_steps=next_steps,
            citations=citations,
        )

    def _summary(self, f: ExtractedFeatures) -> str:
        intent_phrase = {
            "how_to": "怎麼做",
            "debug": "如何排查",
            "concept": "是什麼",
            "compare": "如何比較",
            "decide": "如何決定",
        }.get(f.intent, "相關說明")
        return f"關於「{f.primary_topic}」的{intent_phrase}。"

    def _key_findings(self, chunks: list[KnowledgeChunk]) -> list[KeyFinding]:
        out: list[KeyFinding] = []
        for c in chunks:
            point = c.content.split("。")[0][:120].strip()  # 取首句
            if not point:
                continue
            out.append(KeyFinding(point=point, citations=[c.id]))
        return out

    def _caveats(
        self, chunks: list[KnowledgeChunk], sufficiency_reasons: list[str]
    ) -> list[str]:
        caveats = []
        if chunks and chunks[0].score < self._low:
            caveats.append(
                f"Top 相關性僅 {chunks[0].score:.2f}，回覆可能不完全切題"
            )
        if sufficiency_reasons:
            caveats.append("檢索條件未全部達標：" + "; ".join(sufficiency_reasons))
        if not caveats:
            caveats.append("以下內容依當前知識庫整理，未涵蓋的最新更新請另行查證")
        return caveats

    def _next_steps(self, r: RouterResult) -> list[str]:
        # response_mode 對應的下一步建議模板
        mode = getattr(r, "response_mode", None)
        if mode == "step_by_step":
            return ["執行上述步驟後回報結果"]
        if mode == "decision_support":
            return ["確認選擇並告知，我再幫你接下一步"]
        return []

    def _citations(self, chunks: list[KnowledgeChunk]) -> list[Citation]:
        return [
            Citation(
                chunk_id=c.id,
                source=getattr(c, "source", "knowledge_base"),
                snippet=c.content[:200],
            )
            for c in chunks
        ]
```

> 屬性名稱（`c.id`、`c.content`、`c.score`、`c.source`）對齊 `KnowledgeChunk` 實際 schema。

## 步驟 3：實作 NarrativeRenderer（受限 LLM）

新增 `app/generator/narrative.py`：

```python
from __future__ import annotations

import logging
from typing import Protocol

from app.generator.contract import AnswerContract
from app.skills.registry import Skill

logger = logging.getLogger(__name__)


_PROMPT = """你是 {skill_name} 的回覆撰寫者。依照以下 Answer Contract 寫成自然語言回覆。

嚴格規則（違反任一條視為品質不合格）：
1. 只能使用 Answer Contract 中列出的事實
2. 不得引入 Contract 外的資訊
3. 每個論點若 Contract 中有 citations，必須在敘述後標註「[來源 N]」（N 從 1 起）
4. caveats 必須完整呈現，不可省略
5. 語氣依 response_mode：{response_mode}

Answer Contract：
{contract_json}

{feedback_section}
輸出純 markdown，不要解釋你的決策。"""


class GeneratorLLM(Protocol):
    async def complete_text(self, *, model: str, prompt: str, max_output_tokens: int) -> str: ...


class NarrativeRenderer:
    def __init__(self, llm: GeneratorLLM, model: str) -> None:
        self._llm = llm
        self._model = model

    async def render(
        self,
        *,
        contract: AnswerContract,
        skill: Skill,
        response_mode: str,
        feedback: list[str] | None = None,
    ) -> str:
        feedback_section = ""
        if feedback:
            feedback_section = (
                "（前一次的問題，請改善）\n"
                + "\n".join(f"- {f}" for f in feedback)
                + "\n\n"
            )

        try:
            return await self._llm.complete_text(
                model=self._model,
                prompt=_PROMPT.format(
                    skill_name=skill.name,
                    response_mode=response_mode,
                    contract_json=contract.model_dump_json(indent=2),
                    feedback_section=feedback_section,
                ),
                max_output_tokens=1500,
            )
        except Exception:
            logger.exception("narrative render failed, falling back to template")
            return _fallback_render(contract)


def _fallback_render(contract: AnswerContract) -> str:
    """LLM 失敗時的模板降級輸出。"""
    parts = [f"**摘要**：{contract.summary}", "", "**重點**："]
    for i, kf in enumerate(contract.key_findings, 1):
        parts.append(f"{i}. {kf.point}")
    if contract.caveats:
        parts.append("\n**注意事項**：")
        parts.extend(f"- {c}" for c in contract.caveats)
    parts.append("\n（降級輸出）")
    return "\n".join(parts)
```

## 步驟 4：擴充 RAGState

修改 `app/graph/state.py`：

```python
from app.generator.contract import AnswerContract

class RAGState(TypedDict, total=False):
    # ...
    answer_contract: AnswerContract
    judge_feedback: list[str]  # 預留給 P4，本 phase 不寫入
```

## 步驟 5：拆 generate_node

修改 `app/graph/nodes.py`：

```python
async def build_answer_contract_node(state: RAGState, services: RuntimeServices):
    contract = services.contract_builder.build(
        features=state["features"],
        chunks=state.get("rag_chunks", []),
        router_result=state["router_result"],
        sufficiency_reasons=state.get("sufficiency_reasons", []),
    )
    return {"answer_contract": contract}


async def render_narrative_node(state: RAGState, services: RuntimeServices):
    response_mode = getattr(state["router_result"], "response_mode", "default")
    text = await services.narrative_renderer.render(
        contract=state["answer_contract"],
        skill=state["skill"],
        response_mode=response_mode,
        feedback=state.get("judge_feedback"),
    )
    # 切分 LINE 訊息上限（沿用既有 formatter）
    responses = services.responder.format_for_line(text)
    return {"responses": responses}
```

刪除舊的 `generate_node`。

> `responder.format_for_line` 是把舊 `ResponseGenerator` 的「LINE 訊息切段」邏輯抽出來作為 utility。若不想動 `ResponseGenerator`，可在 `narrative.py` 內 inline 切段邏輯。

## 步驟 6：改寫 graph

修改 `app/graph/rag_graph.py`：

```python
g.add_node("build_answer_contract", partial(build_answer_contract_node, services=services))
g.add_node("render_narrative", partial(render_narrative_node, services=services))

# 移除舊 generate node
g.add_conditional_edges(
    "check_sufficiency",
    route_by_sufficiency,
    {"sufficient": "build_answer_contract", "insufficient": "clarify"},
)
g.add_edge("build_answer_contract", "render_narrative")
g.add_edge("render_narrative", "push")
```

## 步驟 7：DI 注入

修改 `app/dependencies.py`：

```python
from app.generator.contract import AnswerContractBuilder
from app.generator.narrative import NarrativeRenderer

@lru_cache(maxsize=1)
def get_contract_builder() -> AnswerContractBuilder:
    return AnswerContractBuilder()

@lru_cache(maxsize=1)
def get_narrative_renderer() -> NarrativeRenderer:
    s = get_settings()
    llm = build_llm(s, "generator") if has_llm_configured(s) else None
    return NarrativeRenderer(llm=llm, model=s.generator_model)
```

`RuntimeServices` 加 `contract_builder` 與 `narrative_renderer` 欄位。

## 步驟 8：debug 工具

新增 `scripts/dump_contract.py`：

```python
"""讀最新的 outbound query log，dump 出 answer_contract JSON 方便檢視。

用法：python scripts/dump_contract.py [--last 5]
"""
import asyncio
import json
import sys

from app.dependencies import get_runtime_services


async def main(n: int):
    services = get_runtime_services()
    rows = await services.messages_repo.recent_outbound(limit=n)
    for r in rows:
        contract = (r.get("router_result") or {}).get("answer_contract")
        if contract:
            print(json.dumps(contract, ensure_ascii=False, indent=2))
            print("---")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--last") + 1]) if "--last" in sys.argv else 5
    asyncio.run(main(n))
```

> 也可改成從 logs_repo 讀。實際資料寫入位置依 P3 結束時的 schema。若還沒把 contract 寫進 log，這個工具留為下一輪實作（task-17 一起補也可）。

## 步驟 9：測試

`tests/test_answer_contract_builder.py`（純單元測試）：

```python
def test_build_contract_with_chunks():
    builder = AnswerContractBuilder()
    chunks = [_chunk("c1", "RAG 是檢索增強生成。", 0.85)]
    contract = builder.build(
        features=_features("RAG"),
        chunks=chunks,
        router_result=_router(),
        sufficiency_reasons=[],
    )
    assert contract.key_findings[0].citations == ["c1"]
    assert contract.citations[0].chunk_id == "c1"


def test_caveat_when_top_score_low():
    builder = AnswerContractBuilder()
    chunks = [_chunk("c1", "...", 0.3)]
    contract = builder.build(...)
    assert any("0.30" in cv for cv in contract.caveats)
```

`tests/test_narrative_renderer.py`（mock LLM）：

```python
@pytest.mark.asyncio
async def test_renderer_uses_llm(stub_llm_returning_markdown):
    r = NarrativeRenderer(llm=stub_llm_returning_markdown, model="x")
    text = await r.render(contract=..., skill=..., response_mode="brief")
    assert "**" in text or "[來源" in text


@pytest.mark.asyncio
async def test_renderer_falls_back_on_failure(stub_llm_raising):
    r = NarrativeRenderer(llm=stub_llm_raising, model="x")
    text = await r.render(contract=..., skill=..., response_mode="brief")
    assert "（降級輸出）" in text
```

## 請輸出

1. `app/generator/contract.py`、`app/generator/narrative.py`
2. 修改後的 `app/graph/state.py`、`nodes.py`、`rag_graph.py`、`dependencies.py`
3. `app/generator/responder.py` 抽出 `format_for_line` utility（或在 narrative.py 內 inline）
4. `scripts/dump_contract.py`
5. `tests/test_answer_contract_builder.py`、`tests/test_narrative_renderer.py`
6. README 加「為什麼兩階段生成」段（強調可審查性、可測試性）

## 驗收指令

```bash
pytest tests/test_answer_contract_builder.py tests/test_narrative_renderer.py -v
pytest

./scripts/run_local.sh
# 傳一個有資料的問題
# log 應顯示：
#   answer_contract={"summary":"...", "key_findings":[...], "citations":[...]}
# 輸出 markdown 應含「[來源 1]」這類引用標記

# 強制 LLM 失敗（暫時把 generator_model 設為錯誤值）
# 輸出應為「（降級輸出）」模板，不 crash
```

驗收通過條件：

- AnswerContractBuilder 完全純程式，可獨立 unit test 通過（不需 mock LLM）
- 受限 prompt 的輸出**人工抽檢 5 個案例不引入 contract 外事實**
- caveats 永遠出現
- LLM 失敗 → 降級輸出可讀且明確標註
