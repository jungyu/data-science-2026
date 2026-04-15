"""Retrieval Orchestrator — 呼叫 bazi.match_knowledge_atoms()。

對應 Spec-006 (retrieval pipeline) 與 migrations/001_initial_schema.sql 中的 SQL function。

此模組支援兩種模式：
- 單 seed（舊 API，保留相容）：`retrieve()` 以單一 query_text 呼叫 SQL function
- 多 seed（新，Phase 1 audit 改進）：`retrieve_multi_seed()` 將 Rule Engine 產出的
  retrieval_query_seeds 逐一向量化並並行呼叫 function，再以 score fusion 合併。
  背景：audit 指出把多個 seed 用 " / ".join 合成單一字串 embed 會稀釋各條件的語意強度；
  多條件命理查詢（甲木 + 申月 + 正官格 + 調候）用分路檢索後 max-fusion 命中率較佳。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import psycopg

    from destiny.embeddings import EmbeddingClient

FusionStrategy = Literal["max", "mean", "rrf"]


@dataclass
class RetrievalQuery:
    query_text: str
    day_master_tags: list[str] = field(default_factory=list)
    month_branch_tags: list[str] = field(default_factory=list)
    pattern_tags: list[str] = field(default_factory=list)
    seasonal_tags: list[str] = field(default_factory=list)
    top_k: int = 12
    candidate_limit: int = 50


@dataclass
class RetrievalHit:
    atom_id: int
    atom_code: str
    source_book: str
    source_priority: int
    title: str | None
    original_text: str
    modern_interpretation: str | None
    vector_score: float
    source_priority_score: float
    symbolic_match_score: float
    metadata_overlap_score: float
    final_score: float
    # 多 seed 檢索時記錄此 atom 被幾條 seed 召回、最高 seed
    hit_seed_count: int = 1
    top_seed: str | None = None


def _run_sql(
    conn: "psycopg.Connection",
    embedding: list[float],
    q: RetrievalQuery,
) -> list[dict]:
    from psycopg.rows import dict_row  # lazy import; allow tests without driver

    sql = """
        SELECT
          atom_id, atom_code, source_book, source_priority, title,
          original_text, modern_interpretation,
          vector_score, source_priority_score,
          symbolic_match_score, metadata_overlap_score, final_score
        FROM bazi.match_knowledge_atoms(
          query_embedding     := %s::vector,
          p_day_master_tags   := %s::text[],
          p_month_branch_tags := %s::text[],
          p_pattern_tags      := %s::text[],
          p_seasonal_tags     := %s::text[],
          p_top_k             := %s,
          p_candidate_limit   := %s
        );
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            sql,
            (
                embedding,
                q.day_master_tags, q.month_branch_tags,
                q.pattern_tags, q.seasonal_tags,
                q.top_k, q.candidate_limit,
            ),
        )
        return cur.fetchall()


def retrieve(
    conn: "psycopg.Connection",
    embedder: "EmbeddingClient",
    query: RetrievalQuery,
) -> list[RetrievalHit]:
    """單 seed 檢索（相容舊呼叫點）。"""
    embedding = embedder.embed(query.query_text)
    rows = _run_sql(conn, embedding, query)
    return [RetrievalHit(**row) for row in rows]


def retrieve_multi_seed(
    conn: "psycopg.Connection",
    embedder: "EmbeddingClient",
    seeds: list[str],
    *,
    day_master_tags: list[str] | None = None,
    month_branch_tags: list[str] | None = None,
    pattern_tags: list[str] | None = None,
    seasonal_tags: list[str] | None = None,
    top_k: int = 12,
    per_seed_limit: int = 20,
    fusion: FusionStrategy = "max",
    rrf_k: int = 60,
) -> list[RetrievalHit]:
    """多 seed 並行檢索 + score fusion。

    Args:
        seeds: 來自 Rule Engine 的 retrieval_query_seeds
        fusion:
            - "max":  取該 atom 在所有 seed 檢索中的最高 final_score
            - "mean": 平均 final_score（對未被某 seed 召回者計 0）
            - "rrf":  Reciprocal Rank Fusion，score = sum(1/(rrf_k + rank_i))
        rrf_k: RRF 常數，通常 60

    Returns:
        Top-K atoms，排序後；hit_seed_count 與 top_seed 可用於除錯觀察。
    """
    if not seeds:
        return []

    base_query = RetrievalQuery(
        query_text="",  # 不使用
        day_master_tags=day_master_tags or [],
        month_branch_tags=month_branch_tags or [],
        pattern_tags=pattern_tags or [],
        seasonal_tags=seasonal_tags or [],
        top_k=per_seed_limit,
        candidate_limit=max(50, per_seed_limit * 2),
    )

    # 批次一次算完所有 seed 的 embedding，省 API 往返
    embeddings = embedder.embed_many(seeds)

    # atom_code -> (best_row, accumulated_score, hit_count, top_seed)
    accum: dict[str, dict] = {}

    for seed, emb in zip(seeds, embeddings, strict=True):
        rows = _run_sql(conn, emb, base_query)
        for rank, row in enumerate(rows, 1):
            code = row["atom_code"]
            score = float(row["final_score"])
            entry = accum.get(code)
            if entry is None:
                accum[code] = {
                    "row": row,
                    "scores": [score],
                    "best_score": score,
                    "top_seed": seed,
                    "ranks": [rank],
                    "best_row_score": score,
                }
            else:
                entry["scores"].append(score)
                entry["ranks"].append(rank)
                if score > entry["best_score"]:
                    entry["best_score"] = score
                    entry["top_seed"] = seed
                    entry["row"] = row  # 使用最高分那次的 per-component 分數
                    entry["best_row_score"] = score

    # 融合
    fused: list[RetrievalHit] = []
    for code, entry in accum.items():
        row = entry["row"]
        scores: list[float] = entry["scores"]
        ranks: list[int] = entry["ranks"]
        n_hits = len(scores)

        if fusion == "max":
            fused_score = max(scores)
        elif fusion == "mean":
            fused_score = sum(scores) / len(seeds)  # 未命中者計 0
        elif fusion == "rrf":
            fused_score = sum(1.0 / (rrf_k + r) for r in ranks)
        else:
            raise ValueError(f"unknown fusion: {fusion}")

        fused.append(RetrievalHit(
            atom_id=row["atom_id"],
            atom_code=code,
            source_book=row["source_book"],
            source_priority=row["source_priority"],
            title=row["title"],
            original_text=row["original_text"],
            modern_interpretation=row["modern_interpretation"],
            vector_score=row["vector_score"],
            source_priority_score=row["source_priority_score"],
            symbolic_match_score=row["symbolic_match_score"],
            metadata_overlap_score=row["metadata_overlap_score"],
            final_score=fused_score,
            hit_seed_count=n_hits,
            top_seed=entry["top_seed"],
        ))

    fused.sort(key=lambda h: h.final_score, reverse=True)
    return fused[:top_k]
