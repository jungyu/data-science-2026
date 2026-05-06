"""AnswerContractBuilder 純單元測試。對應 spec-16 / task-16 step 9。

builder 是純程式（不呼叫 LLM），所有測試 sync 執行。
"""

from __future__ import annotations

from app.generator.contract import AnswerContractBuilder, Citation, KeyFinding
from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult


def _features(intent: str = "concept") -> ExtractedFeatures:
    return ExtractedFeatures(
        primary_topic="RAG",
        qualifiers=[],
        intent=intent,
        entities=[],
        raw_query="什麼是 RAG？",
    )


def _router(response_mode: str = "brief") -> RouterResult:
    return RouterResult(
        target_skill="general_chat",
        is_rag_required=True,
        rag_query="RAG",
        rag_categories=[],
        emotion_state="neutral",
        response_mode=response_mode,
        confidence=0.9,
    )


def _chunk(
    id: str, content: str = "RAG is retrieval augmented generation.",
    score: float = 0.7, **meta
) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=id,
        title=f"Title {id}",
        content=content,
        category="general",
        vector_score=score,
        keyword_score=score,
        combined_score=score,
        metadata=meta or {},
    )


def test_summary_uses_primary_topic_and_intent():
    builder = AnswerContractBuilder()
    contract = builder.build(
        features=_features("concept"),
        chunks=[_chunk("c1")],
        router_result=_router(),
    )
    assert "RAG" in contract.summary
    assert "是什麼" in contract.summary  # concept → "是什麼"


def test_key_findings_take_first_sentence_with_citation():
    builder = AnswerContractBuilder()
    chunks = [
        _chunk("c1", content="RAG 是檢索增強生成。它把外部知識帶進 LLM。"),
        _chunk("c2", content="向量檢索是基礎。"),
    ]
    contract = builder.build(
        features=_features(), chunks=chunks, router_result=_router()
    )
    assert len(contract.key_findings) == 2
    assert contract.key_findings[0].point == "RAG 是檢索增強生成。"
    assert contract.key_findings[0].citations == ["c1"]
    assert contract.key_findings[1].citations == ["c2"]


def test_citations_prefer_source_url():
    builder = AnswerContractBuilder()
    chunks = [
        _chunk("c1", source_url="https://example.com/doc1"),
        _chunk("c2"),  # no source_url → fallback to title
    ]
    contract = builder.build(
        features=_features(), chunks=chunks, router_result=_router()
    )
    by_id = {cit.chunk_id: cit for cit in contract.citations}
    assert by_id["c1"].source == "https://example.com/doc1"
    assert by_id["c2"].source == "Title c2"


def test_caveat_when_top_score_low():
    builder = AnswerContractBuilder(low_score_threshold=0.5)
    contract = builder.build(
        features=_features(),
        chunks=[_chunk("c1", score=0.3)],
        router_result=_router(),
    )
    assert any("0.30" in cv for cv in contract.caveats)


def test_caveat_includes_sufficiency_reasons():
    builder = AnswerContractBuilder()
    contract = builder.build(
        features=_features(),
        chunks=[_chunk("c1", score=0.8)],
        router_result=_router(),
        sufficiency_reasons=["chunks=1 < min_chunks=2"],
    )
    assert any("檢索條件" in cv for cv in contract.caveats)


def test_caveat_default_when_clean():
    builder = AnswerContractBuilder()
    contract = builder.build(
        features=_features(),
        chunks=[_chunk("c1", score=0.8)],
        router_result=_router(),
    )
    # 無低分、無 sufficiency 異常 → 預設 caveat 仍存在
    assert len(contract.caveats) == 1
    assert "知識庫整理" in contract.caveats[0]


def test_next_steps_by_response_mode():
    builder = AnswerContractBuilder()
    for mode, expected_substr in [
        ("step_by_step", "執行上述步驟"),
        ("decision_support", "確認選擇"),
        ("debugging", "驗證最高機率"),
    ]:
        contract = builder.build(
            features=_features(),
            chunks=[_chunk("c1")],
            router_result=_router(response_mode=mode),
        )
        assert any(expected_substr in step for step in contract.next_steps), (
            f"{mode} should produce next_step containing {expected_substr!r}"
        )


def test_next_steps_empty_for_brief_mode():
    builder = AnswerContractBuilder()
    contract = builder.build(
        features=_features(),
        chunks=[_chunk("c1")],
        router_result=_router(response_mode="brief"),
    )
    assert contract.next_steps == []


def test_handles_empty_chunks():
    builder = AnswerContractBuilder()
    contract = builder.build(
        features=_features(), chunks=[], router_result=_router()
    )
    assert contract.key_findings == []
    assert contract.citations == []
    # caveats 仍應有預設
    assert len(contract.caveats) >= 1


def test_pure_program_no_llm_dependency():
    """builder 是純程式，不需要任何 async / LLM。"""
    builder = AnswerContractBuilder()
    # 純 sync 呼叫即可成功——這是契約硬要求
    contract = builder.build(
        features=_features(),
        chunks=[_chunk("c1")],
        router_result=_router(),
    )
    # 序列化 OK（給 P4 judge 用）
    json_str = contract.model_dump_json()
    assert '"summary"' in json_str
    assert '"citations"' in json_str
