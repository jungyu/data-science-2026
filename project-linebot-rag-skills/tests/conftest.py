"""Shared test fixtures: stub RuntimeServices for graph tests.

提供三個 fixture 變體：
- stub_services：正常路徑（responder 回 "假回覆"）
- stub_services_failing_responder：generate 階段拋錯，驗證 fallback
- stub_services_no_rag：router 回 is_rag_required=False，驗證跳過 retrieve
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.loader import SkillDefinition


@dataclass
class _StubSettings:
    knowledge_top_k: int = 8
    final_context_k: int = 4
    line_max_message_chars: int = 4500
    fusion_strategy: str = "max"
    max_seeds: int = 5
    sufficiency_min_chunks: int = 2
    sufficiency_min_top_score: float = 0.4
    sufficiency_min_feature_overlap: int = 1
    judge_enabled: bool = True
    judge_model: str = ""
    judge_min_axis: int = 6
    judge_min_mean: float = 7.0
    max_reflection_retries: int = 1
    graph_variant: str = "reflection"
    hitl_enabled: bool = False
    hitl_always_review_skills: list[str] = field(default_factory=list)
    checkpoint_backend: str = "none"
    checkpoint_sqlite_path: str = ".checkpoints/test.db"


@dataclass
class _StubLineClient:
    pushed: list[tuple[str, list[str] | str]] = field(default_factory=list)

    async def push_text(self, user_id: str, messages: list[str] | str) -> None:
        self.pushed.append((user_id, messages))


@dataclass
class _StubMessagesRepo:
    saved: list[dict] = field(default_factory=list)

    async def save_message(self, **kwargs) -> None:
        self.saved.append(kwargs)

    async def build_recent_history(self, line_user_id: str, limit: int = 5) -> str:
        return ""


class _StubSkillRegistry:
    """Stub：根據 router 要的 skill_id 動態產出對應 SkillDefinition。

    測「judge 跳過」的個案請覆寫 self._skill 為固定值（例如
    general_chat / emotional_calibration），其餘情況依 router 動態回傳。
    """

    def __init__(self) -> None:
        # 為相容既有測試保留可覆寫的 attribute；非 None 時 lookup 一律回此實例。
        self._skill: SkillDefinition | None = None

    def _build(self, skill_id: str) -> SkillDefinition:
        return SkillDefinition(
            skill_id=skill_id,
            name=skill_id,
            description="desc",
            category="general",
            system_prompt="prompt",
        )

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skill or self._build(skill_id)

    def require(self, skill_id: str) -> SkillDefinition:
        return self._skill or self._build(skill_id)


class _StubRouter:
    """預設 target_skill=tech_architect，避免落入 SKIP_JUDGE_SKILLS
    （general_chat / emotional_calibration）讓 judge 流程的測試失效。

    需要測「judge 跳過」的個案請傳 target_skill="general_chat"。
    """

    def __init__(
        self,
        *,
        is_rag_required: bool = True,
        target_skill: str = "tech_architect",
    ) -> None:
        self._is_rag_required = is_rag_required
        self._target_skill = target_skill

    async def route_message(self, user_input: str, recent_history: str) -> RouterResult:
        return RouterResult(
            target_skill=self._target_skill,
            is_rag_required=self._is_rag_required,
            rag_query=user_input,
            rag_categories=[],
            emotion_state="neutral",
            response_mode="brief",
            confidence=0.9,
        )


def _default_stub_chunks() -> list[KnowledgeChunk]:
    """Default stub chunks pass P3 sufficiency:
    - count ≥ 2 → satisfies min_chunks=2
    - top combined_score ≥ 0.4 → satisfies min_top_score
    - content contains "topic" → overlaps with stub feature extractor's primary_topic="topic"
    """
    return [
        KnowledgeChunk(
            id="chunk-1",
            title="Stub 1",
            content="topic content alpha",
            category="general",
            vector_score=0.85,
            keyword_score=0.6,
            combined_score=0.75,
        ),
        KnowledgeChunk(
            id="chunk-2",
            title="Stub 2",
            content="topic content beta",
            category="general",
            vector_score=0.7,
            keyword_score=0.5,
            combined_score=0.6,
        ),
    ]


class _StubRetriever:
    def __init__(self, *, chunks: list[KnowledgeChunk] | None = None) -> None:
        self._chunks = chunks if chunks is not None else _default_stub_chunks()

    async def retrieve(self, *args, **kwargs) -> list[KnowledgeChunk]:
        return self._chunks

    async def retrieve_for_seed(self, *args, **kwargs) -> list[KnowledgeChunk]:
        return self._chunks

    async def log_fused_retrieval(self, **kwargs) -> None:
        pass

    def build_context(self, chunks: list[KnowledgeChunk]) -> str:
        if not chunks:
            return "No retrieved context."
        return "\n".join(c.content for c in chunks)


class _StubResponder:
    """保留作 RuntimeServices.responder 欄位佔位（graph 不再呼叫）。"""

    async def generate_response(self, **kwargs) -> list[str]:
        return ["假回覆"]


class _FailingResponder:
    """同樣保留為佔位；graph 走 narrative_renderer 不會觸發。"""

    async def generate_response(self, **kwargs) -> list[str]:
        raise RuntimeError("simulated responder failure")


class _StubNarrativeRenderer:
    """常數回覆，方便既有測試維持「responses == ['假回覆']」契約。

    不走真 NarrativeRenderer 的模板降級——那條路徑由 test_narrative_renderer.py 直接驗。
    """

    async def render(self, **kwargs) -> list[str]:
        return ["假回覆"]


class _FailingNarrativeRenderer:
    """模擬 P3 兩階段 generator 在 render 階段失敗 → render_narrative_node 回 fallback。"""

    async def render(self, **kwargs):
        raise RuntimeError("simulated renderer failure")


class _LineForwardingChannel:
    """Conftest 用：channels["line"] 寫進 line_client.pushed，保留既有 test assert。"""

    name = "line"

    def __init__(self, line_client) -> None:
        self._client = line_client

    def build_thread_id(self, inp) -> str:
        return f"line-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> str:
        return ""

    def format(self, markdown: str) -> list[str]:
        return [markdown]

    async def push(self, *, recipient_id, messages) -> None:
        await self._client.push_text(recipient_id, messages)


class _StubFeatureExtractor:
    """常數 primary_topic="topic"，與 _default_stub_chunks 內容對齊使 sufficiency overlap=1。"""

    async def extract(self, *, user_input, recent_history=None) -> ExtractedFeatures:
        return ExtractedFeatures(
            primary_topic="topic",
            qualifiers=[],
            intent="other",
            entities=[],
            raw_query=user_input,
        )


def _make_services(
    *,
    router: Any,
    retriever: Any,
    responder: Any,
) -> Any:
    """組一份 duck-typed RuntimeServices；不引 dataclass 是為了避免 import cycle 與 frozen 限制。"""
    from app.graph.rag_graph import build_rag_graph

    class _Services:
        pass

    services = _Services()
    from app.generator.contract import AnswerContractBuilder
    from app.generator.narrative import NarrativeRenderer
    from app.graph.clarifier import LLMClarifier
    from app.graph.seed_expander import DefaultSeedExpander
    from app.graph.sufficiency import SufficiencyChecker, SufficiencyConfig
    from app.judge.scorer import GroundednessJudge

    from app.channels.stub import StubChannel

    services.line_client = _StubLineClient()
    services.messages_repo = _StubMessagesRepo()
    services.skill_registry = _StubSkillRegistry()
    services.router = router
    services.retriever = retriever
    services.responder = responder
    services.feature_extractor = _StubFeatureExtractor()
    services.seed_expander = DefaultSeedExpander()
    services.settings = _StubSettings()
    # 「line」channel forward 到 line_client，讓既有測試 assert line_client.pushed 仍有效
    services.channels = {
        "line": _LineForwardingChannel(services.line_client),
        "stub": StubChannel(),
    }
    services.checkpointer = None  # 預設不啟用 checkpointer；HITL fixture 自行覆蓋
    services.sufficiency_checker = SufficiencyChecker(
        SufficiencyConfig(
            min_chunks=services.settings.sufficiency_min_chunks,
            min_top_score=services.settings.sufficiency_min_top_score,
            min_feature_overlap=services.settings.sufficiency_min_feature_overlap,
        )
    )
    # Clarifier 預設用 LLM=None 走 fallback 預設追問
    services.clarifier = LLMClarifier(llm=None)
    services.contract_builder = AnswerContractBuilder()
    # NarrativeRenderer 用常數 stub 維持既有測試「responses==['假回覆']」契約；
    # 真實 fallback 行為由 test_narrative_renderer.py 直接驗。
    services.narrative_renderer = _StubNarrativeRenderer()
    # Judge 預設 LLM=None → 永遠回 None → 視為 pass，不阻塞 stub 路徑既有測試
    services.judge = GroundednessJudge(llm=None)
    services.rag_graph = build_rag_graph(services)
    return services


@pytest.fixture
def stub_services():
    return _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )


@pytest.fixture
def stub_services_failing_responder():
    """歷史 fixture：graph 不再呼叫 responder。保留供 webhook 直測 / 兼容舊 test。"""
    return _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_FailingResponder(),
    )


class _ScriptedJudge:
    """模擬一序列 judge 結果：每次呼叫吐出列表中的下一個 score / None。"""

    def __init__(self, scripted_scores) -> None:
        self._scripted = list(scripted_scores)
        self._calls = 0

    async def judge(self, **kwargs):
        if self._calls >= len(self._scripted):
            value = self._scripted[-1] if self._scripted else None
        else:
            value = self._scripted[self._calls]
        self._calls += 1
        return value


def _make_score(*, all_axes: int, issues=None):
    from app.judge.scorer import JudgeScore

    return JudgeScore(
        groundedness=all_axes,
        citation_fidelity=all_axes,
        format_completeness=all_axes,
        uncertainty_honesty=all_axes,
        issues=list(issues or []),
    )


@pytest.fixture
def stub_services_judge_pass():
    """Judge 高分 pass → 不重 render。"""
    services = _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )
    services.judge = _ScriptedJudge([_make_score(all_axes=9)])
    return services


@pytest.fixture
def stub_services_judge_fail_then_pass():
    """Judge 第一次低分（觸發 retry），第二次 pass。"""
    services = _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )
    services.judge = _ScriptedJudge(
        [
            _make_score(all_axes=4, issues=["citation 沒對齊"]),
            _make_score(all_axes=9),
        ]
    )
    return services


@pytest.fixture
def stub_services_judge_always_fail():
    """Judge 永遠 fail → retry 達上限後 force_push 加品質警告。"""
    services = _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )
    services.judge = _ScriptedJudge(
        [_make_score(all_axes=2, issues=["都不對"])]
    )
    return services


@pytest.fixture
def stub_services_hitl_always_fail():
    """HITL 啟用 + judge 永遠 fail → graph 在 human_review 前 interrupt。"""
    from langgraph.checkpoint.memory import InMemorySaver

    services = _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )
    services.settings.hitl_enabled = True
    services.checkpointer = InMemorySaver()
    services.judge = _ScriptedJudge([_make_score(all_axes=2, issues=["everything wrong"])])
    # rebuild graph with checkpointer + interrupt_before
    from app.graph.variants.reflection import build_reflection_graph
    services.rag_graph = build_reflection_graph(services)
    return services


@pytest.fixture
def stub_services_failing_renderer():
    """模擬 narrative renderer 失敗 → render_narrative_node 回 fallback 訊息。"""
    services = _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(),
        responder=_StubResponder(),
    )
    services.narrative_renderer = _FailingNarrativeRenderer()
    # graph 已 build（含原 renderer 的 partial 綁定）；node 透過 services.narrative_renderer
    # 動態查找，所以替換 attribute 即生效，不需 rebuild graph
    return services


@pytest.fixture
def stub_services_no_rag():
    return _make_services(
        router=_StubRouter(is_rag_required=False),
        retriever=_StubRetriever(chunks=[]),
        responder=_StubResponder(),
    )


@pytest.fixture
def stub_services_insufficient():
    """RAG 路徑但 retrieve 回空——觸發 sufficiency=insufficient 進 clarify。"""
    return _make_services(
        router=_StubRouter(is_rag_required=True),
        retriever=_StubRetriever(chunks=[]),
        responder=_StubResponder(),
    )
