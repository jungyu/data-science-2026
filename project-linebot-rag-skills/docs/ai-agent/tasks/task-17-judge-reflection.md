# task-17：LLM-as-Judge + Reflection 迴圈

> 規格詳見 [spec-17](../specs/spec-17-judge-reflection.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-17 頂部「實作狀態」段。
---

在 `render_narrative` 後加入 `judge` node，4 軸結構化評分。不通過時帶 feedback 回到 `render_narrative` 重生成（最多 1 次，硬上限 2）。

> 此 task **取代** task-11（reflection 單分數版）。task-10 的 Self-RAG 重試需求已被 P2/P3 覆蓋，不再對應實作。

## 前置

- task-16 完成（`render_narrative` 已能讀 `judge_feedback`）

## 步驟 1：實作 Judge

新增 `app/judge/__init__.py`（空）與 `app/judge/scorer.py`：

```python
from __future__ import annotations

import json
import logging
from typing import Protocol

from pydantic import BaseModel, Field

from app.generator.contract import AnswerContract

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    groundedness: int = Field(..., ge=0, le=10)
    citation_fidelity: int = Field(..., ge=0, le=10)
    format_completeness: int = Field(..., ge=0, le=10)
    uncertainty_honesty: int = Field(..., ge=0, le=10)
    issues: list[str] = Field(default_factory=list)

    @property
    def mean(self) -> float:
        return (
            self.groundedness
            + self.citation_fidelity
            + self.format_completeness
            + self.uncertainty_honesty
        ) / 4

    def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool:
        return (
            min(
                self.groundedness,
                self.citation_fidelity,
                self.format_completeness,
                self.uncertainty_honesty,
            )
            >= min_axis
            and self.mean >= min_mean
        )


_SYSTEM = """你是嚴格的 RAG 輸出審查員。
你會收到：(a) 助理產出的回覆 markdown；(b) 該次的 Answer Contract（含 citations）。

依以下 4 軸打分（0~10）：
- groundedness: 結論是否都有 contract 中的依據
- citation_fidelity: 引用文字是否與 contract.citations[].snippet 逐字相符
- format_completeness: 是否符合 response_mode={mode} 的格式要求
- uncertainty_honesty: caveats 是否完整呈現

輸出嚴格 JSON（無 markdown fence、無前後文）：
{{
  "groundedness": 0,
  "citation_fidelity": 0,
  "format_completeness": 0,
  "uncertainty_honesty": 0,
  "issues": ["最多 5 條具體問題"]
}}"""


class JudgeLLM(Protocol):
    async def complete_json(
        self, *, model: str, system: str, prompt: str, max_output_tokens: int
    ) -> str: ...


class GroundednessJudge:
    def __init__(self, llm: JudgeLLM, model: str) -> None:
        self._llm = llm
        self._model = model

    async def judge(
        self, *, narrative: str, contract: AnswerContract, response_mode: str
    ) -> JudgeScore | None:
        try:
            text = await self._llm.complete_json(
                model=self._model,
                system=_SYSTEM.format(mode=response_mode),
                prompt=(
                    f"回覆 markdown：\n{narrative}\n\n"
                    f"Answer Contract：\n{contract.model_dump_json(indent=2)}"
                ),
                max_output_tokens=500,
            )
            return JudgeScore(**json.loads(text))
        except Exception:
            logger.warning("judge call failed, treating as pass (degrade gracefully)")
            return None
```

## 步驟 2：擴充 RAGState

修改 `app/graph/state.py`：

```python
class RAGState(TypedDict, total=False):
    # ...
    judge_score: JudgeScore | None
    judge_feedback: list[str]            # 已在 task-16 預留
    reflection_retry: int                # 0 / 1 / 2
    judge_warning_prefix: bool
```

## 步驟 3：新增 judge node 與 conditional edge

修改 `app/graph/nodes.py`：

```python
SKIP_JUDGE_SKILLS = {"small_talk", "emotional_calibration"}


async def judge_node(state: RAGState, services: RuntimeServices):
    # 跳過情境：閒聊 / 情緒回應
    skill_name = state["skill"].name
    if skill_name in SKIP_JUDGE_SKILLS:
        return {"judge_score": None, "judge_feedback": []}

    response_mode = getattr(state["router_result"], "response_mode", "default")
    narrative = "\n\n".join(state.get("responses", []))

    score = await services.judge.judge(
        narrative=narrative,
        contract=state["answer_contract"],
        response_mode=response_mode,
    )
    if score is None:
        return {"judge_score": None, "judge_feedback": []}

    feedback = score.issues if not score.passes(
        min_axis=services.settings.judge_min_axis,
        min_mean=services.settings.judge_min_mean,
    ) else []

    return {"judge_score": score, "judge_feedback": feedback}


def route_after_judge(state: RAGState) -> str:
    """三向：pass / retry / force_push"""
    score: JudgeScore | None = state.get("judge_score")
    if score is None or not state.get("judge_feedback"):
        return "pass"

    retry = state.get("reflection_retry", 0)
    if retry >= 1:  # 已重試過一次
        return "force_push"
    return "retry"


async def increment_retry_node(state: RAGState, services: RuntimeServices):
    """retry 路徑前累加 counter，避免 render_narrative 自己改。"""
    return {"reflection_retry": state.get("reflection_retry", 0) + 1}


async def mark_warning_node(state: RAGState, services: RuntimeServices):
    """force_push 路徑：在訊息開頭加品質警告。"""
    warned = ["⚠️ 品質警告：本次回覆未通過自審\n\n" + r for r in state.get("responses", [])]
    return {"responses": warned, "judge_warning_prefix": True}
```

## 步驟 4：改寫 graph

修改 `app/graph/rag_graph.py`：

```python
g.add_node("judge", partial(judge_node, services=services))
g.add_node("increment_retry", partial(increment_retry_node, services=services))
g.add_node("mark_warning", partial(mark_warning_node, services=services))

g.add_edge("render_narrative", "judge")
g.add_conditional_edges(
    "judge",
    route_after_judge,
    {
        "pass": "push",
        "retry": "increment_retry",
        "force_push": "mark_warning",
    },
)
g.add_edge("increment_retry", "render_narrative")  # 迴圈
g.add_edge("mark_warning", "push")
```

> LangGraph 會在 `render_narrative` 第二次執行時讀到 `judge_feedback` 並把它加入 prompt（task-16 已實作）。

## 步驟 5：DI + config

修改 `app/dependencies.py`：

```python
from app.judge.scorer import GroundednessJudge

@lru_cache(maxsize=1)
def get_judge() -> GroundednessJudge:
    s = get_settings()
    if not s.judge_enabled:
        return _NoOpJudge()  # always None
    # 建議用獨立 provider；若同一 provider，至少換更小模型 + temp=0
    llm = build_llm(s, "judge") if has_llm_configured(s) else None
    return GroundednessJudge(llm=llm, model=s.judge_model)
```

`Settings` 加：

```python
judge_enabled: bool = True
judge_model: str = "gpt-4.1-mini"  # 預設 default 同 router；可獨立指定
judge_provider: str | None = None  # None=沿用 ai_provider
judge_min_axis: int = 6
judge_min_mean: float = 7.0
max_reflection_retries: int = 1  # 硬上限 2
```

> `build_llm(s, "judge")` 需要 `app/ai/factory.py` 支援第三個 role；若還沒，先用 `build_llm(s, "router")` 並注意 prompt 是否與 judge 任務匹配。

`RuntimeServices` 加 `judge` 欄位。

## 步驟 6：測試

`tests/test_judge_scorer.py`：

```python
def test_passes_when_all_high():
    score = JudgeScore(groundedness=8, citation_fidelity=8, format_completeness=8, uncertainty_honesty=8, issues=[])
    assert score.passes()


def test_fails_when_one_axis_low():
    score = JudgeScore(groundedness=5, citation_fidelity=8, format_completeness=8, uncertainty_honesty=8, issues=["..."])
    assert not score.passes()


@pytest.mark.asyncio
async def test_judge_returns_none_on_llm_failure(stub_llm_raising):
    j = GroundednessJudge(llm=stub_llm_raising, model="x")
    result = await j.judge(narrative="...", contract=..., response_mode="brief")
    assert result is None
```

`tests/test_reflection_loop.py`（整合）：

```python
@pytest.mark.asyncio
async def test_judge_pass_skips_retry(stub_services_judge_pass):
    final = await graph.ainvoke({...})
    assert final.get("reflection_retry", 0) == 0


@pytest.mark.asyncio
async def test_judge_fail_triggers_one_retry(stub_services_judge_fail_then_pass):
    final = await graph.ainvoke({...})
    assert final["reflection_retry"] == 1
    assert not final.get("judge_warning_prefix")


@pytest.mark.asyncio
async def test_retry_limit_forces_push_with_warning(stub_services_judge_always_fail):
    final = await graph.ainvoke({...})
    assert final["reflection_retry"] == 1  # 達上限不再加
    assert final["judge_warning_prefix"] is True
    assert final["responses"][0].startswith("⚠️")


@pytest.mark.asyncio
async def test_small_talk_skips_judge(stub_services_small_talk):
    final = await graph.ainvoke({...})
    assert final.get("judge_score") is None
```

## 步驟 7：刪除已過時的 spec/task

- 把 `docs/ai-agent/specs/spec-10-selfrag.md` 開頭加 deprecation 標頭：
  ```markdown
  > ⚠️ Deprecated（2026-05-05）：本 spec 的 query 改寫重試需求已被 [spec-14 multi-seed](./spec-14-multi-seed-retrieval.md) + [spec-15 sufficiency](./spec-15-sufficiency-clarify.md) 覆蓋。保留作為歷史紀錄，不再實作。
  ```
- 同樣處理 `spec-11-reflection.md`：指向 spec-17。
- `tasks/task-10-selfrag.md`、`task-11-reflection.md` 加同樣 deprecation 標頭。

> 不直接刪除檔案，避免破壞 PR 連結 / 學生 fork 的歷史。

## 步驟 8：教學配套

新增 `docs/ai-agent/examples/judge-cases.md`：

收錄 9 個案例，每個案例附 contract + narrative + judge JSON：

| 類別 | 案例數 |
|------|------|
| Pass（高分通過）| 3 |
| Fail → retry → pass | 3 |
| Fail → retry → still fail（force push）| 3 |

讓學生看到「不同類型的 narrative 為什麼分數高 / 低」。

## 請輸出

1. `app/judge/__init__.py`、`app/judge/scorer.py`
2. 修改後的 `app/graph/state.py`、`nodes.py`、`rag_graph.py`、`dependencies.py`、`config.py`
3. `app/ai/factory.py` 支援 `role="judge"`（若尚未支援）
4. `tests/test_judge_scorer.py`、`tests/test_reflection_loop.py`
5. `docs/ai-agent/examples/judge-cases.md`
6. `spec-10` / `spec-11` / `task-10` / `task-11` 加 deprecation 標頭
7. README 加「為什麼要 4 軸 judge」與「retry 上限的成本考量」

## 驗收指令

```bash
pytest tests/test_judge_scorer.py tests/test_reflection_loop.py -v
pytest

./scripts/run_local.sh
# 1. 正常問題（高品質）
#    log: judge_score={ground:9, cite:9, format:8, uncert:8} → pass
#    無 retry
#
# 2. 故意餵不足 chunks（觸發低分）
#    log: judge_score=... → retry
#    第二次 render 後 log: judge_score=... → pass
#
# 3. 設 JUDGE_MIN_MEAN=99 強制永遠 fail
#    log: retry 1 → force_push → 訊息開頭「⚠️ 品質警告」
#
# 4. JUDGE_ENABLED=false
#    log: judge skipped
#    無任何 judge 呼叫
```

驗收通過條件：

- pass / retry / force_push 三條 edge 都能在 graph 視覺化看到
- judge LLM 失敗 → fallback 視為 pass（不阻塞輸出）
- retry 永不超過 1 次（硬編碼安全網）
- `small_talk` 不觸發 judge
- judge 與 generator 可用不同 model / provider，無設定衝突
