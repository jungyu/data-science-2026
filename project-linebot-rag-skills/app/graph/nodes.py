from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Send

from app.graph.clarifier import format_clarification
from app.graph.state import RAGState
from app.observability.tracer import traced
from app.rag.fusion import get_fuser

logger = logging.getLogger(__name__)


@traced("extract_features")
async def extract_features_node(state: RAGState, services: Any) -> dict[str, Any]:
    features = await services.feature_extractor.extract(
        user_input=state["user_input"],
        recent_history=state.get("recent_history"),
    )
    return {"features": features}


@traced("route")
async def route_node(state: RAGState, services: Any) -> dict[str, Any]:
    result = await services.router.route_message(
        state["user_input"],
        state.get("recent_history", "No recent conversation."),
    )
    skill = services.skill_registry.get(result.target_skill) or services.skill_registry.require(
        "general_chat"
    )
    return {"router_result": result, "skill": skill}


@traced("retrieve")
async def retrieve_basic_node(state: RAGState, services: Any) -> dict[str, Any]:
    """P1 原版單 seed retrieve（給 basic variant 用，spec-19）。

    與 expand_seeds + retrieve_one + fuse_scores 的 multi-seed 路徑互斥；
    basic variant 只用本 node 一次性 embed → match → rerank → log。
    """
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"rag_chunks": [], "rag_context": "No retrieved context."}

    chunks = await services.retriever.retrieve(
        router_result.rag_query or state["user_input"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
        external_user_id=state["external_user_id"],
        skill_id=router_result.target_skill,
    )
    context = services.retriever.build_context(chunks)
    return {"rag_chunks": chunks, "rag_context": context}


@traced("generate")
async def generate_basic_node(state: RAGState, services: Any) -> dict[str, Any]:
    """P1 原版單階段 generator（給 basic variant 用，spec-19）。

    呼叫 services.responder.generate_response（既有 ResponseGenerator），
    含失敗 fallback。selfrag/reflection 用 build_answer_contract + render_narrative 取代。
    """
    try:
        responses = await services.responder.generate_response(
            user_input=state["user_input"],
            router_result=state["router_result"],
            skill=state["skill"],
            rag_chunks=state.get("rag_chunks", []),
            rag_context=state.get("rag_context", "No retrieved context."),
            recent_history=state.get("recent_history", "No recent conversation."),
        )
    except Exception:
        logger.exception("generate_response failed")
        responses = ["系統暫時無法完成此請求，請稍後再試。"]
    return {"responses": responses}


@traced("expand_seeds")
async def expand_seeds_node(state: RAGState, services: Any) -> dict[str, Any]:
    """把 features 展開為 seeds。若不需 RAG 直接回空 list 短路後續 fan-out。"""
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"seeds": [], "hits_per_seed": []}

    seeds = services.seed_expander.expand(
        state["features"],
        max_seeds=services.settings.max_seeds,
    )
    # 若 expander 一條 seed 都產不出（極端 fallback），保底用 router_result.rag_query
    if not seeds:
        seeds = [router_result.rag_query or state["user_input"]]
    return {"seeds": seeds, "hits_per_seed": []}


def fan_out_to_retrieve(state: RAGState):
    """Conditional edge：若有 seeds 則 fan-out；否則跳過 retrieve 直奔 fuse_scores。"""
    seeds = state.get("seeds") or []
    if not seeds:
        return ["fuse_scores"]
    return [
        Send(
            "retrieve_one",
            {
                "user_input": state["user_input"],
                "external_user_id": state["external_user_id"],
                "channel": state.get("channel", ""),
                "router_result": state["router_result"],
                "seed": s,
                "seed_index": i,
            },
        )
        for i, s in enumerate(seeds)
    ]


@traced("retrieve_one")
async def retrieve_one_node(state: RAGState, services: Any) -> dict[str, Any]:
    """Per-seed retrieval（並行執行的 sub-task）。

    透過 Send 收到的 state 只含必要欄位；回傳的 hits_per_seed 透過 reducer
    append 到主 state。
    """
    router_result = state["router_result"]
    chunks = await services.retriever.retrieve_for_seed(
        state["seed"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
    )
    logger.info(
        "retrieve_one seed=%r idx=%d → %d chunks",
        state["seed"],
        state.get("seed_index", -1),
        len(chunks),
    )
    return {"hits_per_seed": [chunks]}


@traced("fuse_scores")
async def fuse_scores_node(state: RAGState, services: Any) -> dict[str, Any]:
    """合併所有 seed 的命中、依 fusion strategy 排序、取 top final_context_k。"""
    hits_per_seed = state.get("hits_per_seed") or []
    router_result = state["router_result"]

    if not hits_per_seed or not any(hits_per_seed):
        return {"rag_chunks": [], "rag_context": "No retrieved context."}

    strategy = services.settings.fusion_strategy
    fuser = get_fuser(strategy)
    fused = fuser(hits_per_seed)
    final = fused[: services.settings.final_context_k]

    logger.info(
        "fuse strategy=%s seeds=%d total_unique=%d top=%d",
        strategy,
        len(hits_per_seed),
        len(fused),
        len(final),
    )

    # 統一 log（取代原 retrieve_node 內每次 retrieve 的 log）
    await services.retriever.log_fused_retrieval(
        query=state["user_input"],
        chunks=final,
        categories=router_result.rag_categories,
        external_user_id=state["external_user_id"],
        skill_id=router_result.target_skill,
    )

    context = services.retriever.build_context(final)
    return {"rag_chunks": final, "rag_context": context}


@traced("check_sufficiency")
async def check_sufficiency_node(state: RAGState, services: Any) -> dict[str, Any]:
    """判斷 retrieval 是否足以生成可信回覆。不需 RAG 的 skill 直接視為 sufficient。"""
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"sufficiency": "sufficient", "sufficiency_reasons": []}

    decision, reasons = services.sufficiency_checker.check(
        chunks=state.get("rag_chunks", []),
        features=state["features"],
    )
    logger.info("sufficiency=%s reasons=%s", decision, reasons)
    return {"sufficiency": decision, "sufficiency_reasons": reasons}


def route_by_sufficiency(state: RAGState) -> str:
    return state.get("sufficiency", "sufficient")


@traced("clarify")
async def clarify_node(state: RAGState, services: Any) -> dict[str, Any]:
    """資料不足時生成具體追問，組成 responses 直接 push。"""
    questions = await services.clarifier.generate_questions(
        user_input=state["user_input"],
        features=state["features"],
        chunks=state.get("rag_chunks", []),
    )
    return {
        "clarification_questions": questions,
        "responses": [format_clarification(questions)],
    }


@traced("build_answer_contract")
async def build_answer_contract_node(state: RAGState, services: Any) -> dict[str, Any]:
    """Stage 1：純程式組 Answer Contract（無 LLM）。"""
    contract = services.contract_builder.build(
        features=state["features"],
        chunks=state.get("rag_chunks", []),
        router_result=state["router_result"],
        sufficiency_reasons=state.get("sufficiency_reasons", []),
    )
    logger.info(
        "answer_contract: findings=%d caveats=%d citations=%d",
        len(contract.key_findings),
        len(contract.caveats),
        len(contract.citations),
    )
    return {"answer_contract": contract}


@traced("render_narrative")
async def render_narrative_node(state: RAGState, services: Any) -> dict[str, Any]:
    """Stage 2：受限 LLM 把 contract 寫成 markdown，依 LINE 上限切段。"""
    response_mode = getattr(state["router_result"], "response_mode", "default")
    try:
        responses = await services.narrative_renderer.render(
            contract=state["answer_contract"],
            skill=state["skill"],
            response_mode=response_mode,
            feedback=state.get("judge_feedback"),
        )
    except Exception:
        logger.exception("render_narrative failed")
        responses = ["系統暫時無法完成此請求，請稍後再試。"]
    return {"responses": responses}


SKIP_JUDGE_SKILLS: set[str] = {"small_talk", "emotional_calibration"}


@traced("judge")
async def judge_node(state: RAGState, services: Any) -> dict[str, Any]:
    """P4 LLM-as-Judge：4 軸結構化評分。失敗 / 跳過情境 → judge_score=None 視為 pass。"""
    settings = services.settings
    if not getattr(settings, "judge_enabled", True):
        return {"judge_score": None, "judge_feedback": []}

    skill = state.get("skill")
    if skill is not None and skill.skill_id in SKIP_JUDGE_SKILLS:
        logger.info("judge skipped: skill=%s in SKIP_JUDGE_SKILLS", skill.skill_id)
        return {"judge_score": None, "judge_feedback": []}

    router_result = state["router_result"]
    if not router_result.is_rag_required:
        # 不需 RAG 的回覆通常無 chunks 可審；pass through
        return {"judge_score": None, "judge_feedback": []}

    response_mode = getattr(router_result, "response_mode", "default")
    narrative = "\n\n".join(state.get("responses") or [])

    score = await services.judge.judge(
        narrative=narrative,
        contract=state["answer_contract"],
        response_mode=response_mode,
    )
    if score is None:
        return {"judge_score": None, "judge_feedback": []}

    passed = score.passes(
        min_axis=settings.judge_min_axis, min_mean=settings.judge_min_mean
    )
    feedback = [] if passed else list(score.issues)
    logger.info(
        "judge mean=%.1f pass=%s issues=%d",
        score.mean,
        passed,
        len(score.issues),
    )
    return {"judge_score": score, "judge_feedback": feedback}


def make_route_after_judge(max_retries: int, *, hitl_enabled: bool = False):
    """Closure：注入 max_retries 作為 retry → force_push / human_review 的門檻。

    硬上限保險：min(settings.max_reflection_retries, 2)——避免設定過高導致無限迴圈。
    `hitl_enabled=True` 時，retry 用盡走 human_review；否則走 force_push（既有行為）。
    """
    HARD_MAX = 2
    effective_max = min(max(max_retries, 0), HARD_MAX)

    def route_after_judge(state: RAGState) -> str:
        score = state.get("judge_score")
        feedback = state.get("judge_feedback") or []
        if score is None or not feedback:
            return "pass"
        retry = state.get("reflection_retry", 0)
        if retry >= effective_max:
            return "human_review" if hitl_enabled else "force_push"
        return "retry"

    return route_after_judge


@traced("human_review")
async def human_review_node(state: RAGState, services: Any) -> dict[str, Any]:
    """HITL 中繼 node。實際 interrupt 由 graph compile 時的 interrupt_before 完成。

    Resume 後本 node 不做事；push_node 會讀 reviewer_decision 決定推什麼。
    """
    logger.info(
        "human_review entered: thread=%s reviewer_decision=%s",
        state.get("external_message_id"),
        state.get("reviewer_decision"),
    )
    return {}


@traced("increment_retry")
async def increment_retry_node(state: RAGState, services: Any) -> dict[str, Any]:
    """retry 路徑：累加 reflection_retry 計數，下一輪 render_narrative 會帶 feedback。"""
    current = state.get("reflection_retry", 0)
    next_count = current + 1
    logger.info("reflection retry → %d (max=%d)", next_count, services.settings.max_reflection_retries)
    return {"reflection_retry": next_count}


@traced("mark_warning")
async def mark_warning_node(state: RAGState, services: Any) -> dict[str, Any]:
    """force_push 前在訊息開頭加品質警告。"""
    responses = list(state.get("responses") or [])
    if responses:
        responses[0] = "⚠️ 品質警告：本次回覆未通過自審\n\n" + responses[0]
    return {"responses": responses, "judge_warning_prefix": True}


@traced("push")
async def push_node(state: RAGState, services: Any) -> dict[str, Any]:
    user_id = state.get("external_user_id", "")
    if state.get("dry_run", False):
        logger.info("(dry_run) skip push: user=%s msgs=%d", user_id, len(state.get("responses") or []))
        return {}

    # task-21 HITL：reviewer_decision 在 human_review 路徑後可能存在
    decision = state.get("reviewer_decision")
    if decision == "drop":
        logger.info("hitl drop: skipping push for user=%s", user_id)
        return {}

    # graph 不感知 channel 種類；統一委派給 services.channels[channel_name]。
    # state 未指定 channel 時 default "line"（多數教學情境的入口）。
    channel_name = state.get("channel") or "line"
    channel = services.channels.get(channel_name)
    if channel is None:
        logger.error("push_node: unknown channel %r — cannot push to user=%s", channel_name, user_id)
        return {}
    if decision == "revise" and state.get("reviewer_revised_text"):
        text = state["reviewer_revised_text"]
    else:
        text = "\n\n".join(state.get("responses") or [])
    await channel.push(recipient_id=user_id, messages=channel.format(text))
    return {}
