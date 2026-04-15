#!/usr/bin/env python3
"""
End-to-end TCM diagnostic RAG query demo.

Pipeline:
  1. Load feature dictionary from knowledge_atoms
  2. Dictionary-based feature extraction from user query
  3. Optional embedding of user query
  4. Run rank_patterns.sql to get top candidates
  5. Apply diagnostic_rules (boost / flag / suggest)
  6. Assemble answer contract (Answer §A~G per spec)
  7. Persist into query_logs / retrieval_logs

Usage:
  python scripts/answer_query.py "午後潮熱，夜間盜汗，口乾，舌紅少苔"

Environment variables (see embed_atoms.py for embedding-related):
  DATABASE_URL               - required
  OPENAI_API_KEY             - optional (embeds query when present)
  OPENAI_EMBEDDING_MODEL     - optional (default: text-embedding-3-small)
  ANSWER_TOP_K               - optional (default: 5)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import ulid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import psycopg

from apply_rules import (
    FeatureHit,
    PatternCandidate,
    apply_rules,
    load_active_rules,
)
from synthesize_answer import synthesize


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("answer_query")

RANK_PATTERNS_SQL = Path(__file__).resolve().parent.parent / "sql" / "rank_patterns.sql"


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str | None
    embedding_model: str
    top_k: int


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")

    return Settings(
        database_url=database_url,
        openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip() or None,
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        top_k=int(os.getenv("ANSWER_TOP_K", "5")),
    )


# ---------------------------------------------------------
# Feature extraction (Python port of extract_features.ts)
# ---------------------------------------------------------

TIME_LEXICON = [
    "午後", "下午", "午前", "上午", "清晨", "晨起",
    "夜間", "夜裡", "睡中", "入睡後", "醒後",
    "飯後", "空腹", "經期", "經前", "經後",
]

LOCATION_LEXICON = [
    "頭", "胸", "脅", "脘", "腹", "腰", "膝",
    "四肢", "手足心", "咽", "口", "眼", "耳",
]

FEATURE_ATOM_TYPES = ("symptom", "sign", "tongue_feature", "pulse_feature")


@dataclass
class DictEntry:
    atom_id: str
    atom_type: str
    canonical_name: str
    aliases: list[str]


def load_feature_dictionary(conn: psycopg.Connection) -> list[DictEntry]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, atom_type, canonical_name, aliases
            FROM public.knowledge_atoms
            WHERE is_active = true
              AND atom_type = ANY(%s)
            """,
            (list(FEATURE_ATOM_TYPES),),
        )
        rows = cur.fetchall()

    entries = []
    for row in rows:
        aliases = row[3] if isinstance(row[3], list) else (row[3] or [])
        entries.append(
            DictEntry(
                atom_id=row[0],
                atom_type=row[1],
                canonical_name=row[2],
                aliases=list(aliases),
            )
        )
    return entries


def normalize_query(query: str) -> str:
    return "".join(
        ch for ch in query
        if ch not in "，。！？、；：,.!?;: \t\n"
    )


def extract_features(query: str, dictionary: list[DictEntry]) -> list[FeatureHit]:
    normalized = normalize_query(query)

    # surface → entry, prefer canonical over alias on collision
    surface_map: dict[str, DictEntry] = {}
    for entry in dictionary:
        surface_map[entry.canonical_name] = entry
        for alias in entry.aliases:
            surface_map.setdefault(alias, entry)

    # longest match first to avoid "自汗" being shadowed by "汗"
    surfaces = sorted(surface_map.keys(), key=len, reverse=True)

    hits: list[FeatureHit] = []
    seen: set[str] = set()
    for surface in surfaces:
        if surface in normalized and surface_map[surface].atom_id not in seen:
            entry = surface_map[surface]
            seen.add(entry.atom_id)
            hits.append(
                FeatureHit(
                    atom_id=entry.atom_id,
                    atom_type=entry.atom_type,
                    canonical_name=entry.canonical_name,
                )
            )
    return hits


def detect_missing(features: list[FeatureHit], query: str) -> list[str]:
    types_present = {f.atom_type for f in features}
    missing: list[str] = []
    if "tongue_feature" not in types_present:
        missing.append("tongue_feature")
    if "pulse_feature" not in types_present:
        missing.append("pulse_feature")
    if not any(token in query for token in TIME_LEXICON):
        missing.append("time_feature")
    return missing


# ---------------------------------------------------------
# Ranking
# ---------------------------------------------------------

def rank_patterns(
    conn: psycopg.Connection,
    feature_atom_ids: list[str],
    query_embedding: list[float] | None,
    query_fts: str | None,
    top_k: int,
) -> list[PatternCandidate]:
    sql = RANK_PATTERNS_SQL.read_text(encoding="utf-8")

    embedding_literal = (
        json.dumps(query_embedding, ensure_ascii=False) if query_embedding else None
    )

    # Replace named parameters with %(...)s format understood by psycopg
    # rank_patterns.sql uses :name notation for readability; adapt to psycopg here
    sql = (
        sql.replace(":feature_atom_ids", "%(feature_atom_ids)s")
           .replace(":query_embedding", "%(query_embedding)s::vector")
           .replace(":query_fts", "%(query_fts)s")
           .replace(":top_k", "%(top_k)s")
    )

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "feature_atom_ids": feature_atom_ids or [""],
                "query_embedding": embedding_literal,
                "query_fts": query_fts,
                "top_k": top_k,
            },
        )
        rows = cur.fetchall()

    candidates: list[PatternCandidate] = []
    for row in rows:
        candidates.append(
            PatternCandidate(
                pattern_id=row[0],
                pattern_name=row[1],
                pattern_family=row[2],
                final_score=float(row[9]) if row[9] is not None else 0.0,
                supporting_feature_ids=list(row[10] or []),
                conflicting_feature_ids=list(row[11] or []),
            )
        )
    return candidates


# ---------------------------------------------------------
# Embedding (optional)
# ---------------------------------------------------------

def embed_query(api_key: str, model: str, query: str) -> list[float]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(model=model, input=[query])
    return resp.data[0].embedding


# ---------------------------------------------------------
# Atom name resolution
# ---------------------------------------------------------

def resolve_atom_names(
    conn: psycopg.Connection,
    atom_ids: list[str],
) -> dict[str, str]:
    if not atom_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, canonical_name
            FROM public.knowledge_atoms
            WHERE id = ANY(%s)
            """,
            (atom_ids,),
        )
        rows = cur.fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------
# Answer assembly
# ---------------------------------------------------------

def assemble_answer(
    raw_query: str,
    features: list[FeatureHit],
    missing: list[str],
    candidates: list[PatternCandidate],
    name_lookup: dict[str, str],
    suggested_questions: list[str],
    ambiguity_flags: list[str],
) -> dict[str, Any]:
    top = candidates[:3]

    supporting_sections = []
    for cand in top:
        supporting_sections.append(
            {
                "pattern": cand.pattern_name,
                "final_score": round(cand.final_score, 4),
                "supporting_features": [
                    name_lookup.get(fid, fid) for fid in cand.supporting_feature_ids
                ],
                "conflicting_features": [
                    name_lookup.get(fid, fid) for fid in cand.conflicting_feature_ids
                ],
            }
        )

    differential = None
    if len(top) >= 2:
        differential = {
            "first": top[0].pattern_name,
            "second": top[1].pattern_name,
            "score_gap": round(top[0].final_score - top[1].final_score, 4),
        }

    return {
        "A_symptom_summary": {
            "raw_query": raw_query,
            "extracted": {
                "symptoms": [f.canonical_name for f in features if f.atom_type == "symptom"],
                "signs": [f.canonical_name for f in features if f.atom_type == "sign"],
                "tongue": [f.canonical_name for f in features if f.atom_type == "tongue_feature"],
                "pulse": [f.canonical_name for f in features if f.atom_type == "pulse_feature"],
            },
        },
        "B_candidate_patterns": [
            {"rank": i + 1, "pattern": c.pattern_name, "score": round(c.final_score, 4)}
            for i, c in enumerate(top)
        ],
        "C_supporting_evidence": supporting_sections,
        "D_differential": differential,
        "E_missing": missing,
        "F_treatment_direction": (
            "本系統僅提供候選方向，具體治法需臨床四診合參後再議。"
        ),
        "G_citations": [
            "中醫症狀鑒別診斷學（醫砭）",
            "中醫診斷學（教材）",
        ],
        "rule_flags": ambiguity_flags,
        "suggested_questions": suggested_questions,
        "safety_note": (
            "本回答為知識檢索輔助，不構成臨床診斷或處方建議。"
        ),
    }


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

def persist_query_log(
    conn: psycopg.Connection,
    user_query: str,
    features: list[FeatureHit],
    missing: list[str],
    candidates: list[PatternCandidate],
    answer: dict[str, Any],
    latency_ms: int,
    model_name: str | None,
) -> str:
    query_log_id = f"qlog_{ulid.new()}"
    normalized = {
        "symptoms": [f.canonical_name for f in features if f.atom_type == "symptom"],
        "signs": [f.canonical_name for f in features if f.atom_type == "sign"],
        "tongue": [f.canonical_name for f in features if f.atom_type == "tongue_feature"],
        "pulse": [f.canonical_name for f in features if f.atom_type == "pulse_feature"],
        "missing": missing,
    }
    extracted = {"features": [asdict(f) for f in features]}
    top_candidates = [
        {"pattern_id": c.pattern_id, "pattern_name": c.pattern_name, "score": c.final_score}
        for c in candidates[:5]
    ]

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.query_logs (
              id, user_query, normalized_query, extracted_features,
              top_candidate_patterns, answer_contract, latency_ms, model_name
            ) VALUES (
              %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s
            )
            """,
            (
                query_log_id,
                user_query,
                json.dumps(normalized, ensure_ascii=False),
                json.dumps(extracted, ensure_ascii=False),
                json.dumps(top_candidates, ensure_ascii=False),
                json.dumps(answer, ensure_ascii=False),
                latency_ms,
                model_name,
            ),
        )
    return query_log_id


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def run(query_text: str) -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        logger.error("Failed to load settings: %s", exc)
        return 1

    start_ts = time.time()

    try:
        with psycopg.connect(settings.database_url) as conn:
            conn.autocommit = False

            dictionary = load_feature_dictionary(conn)
            logger.info("Loaded dictionary with %s entries.", len(dictionary))

            features = extract_features(query_text, dictionary)
            missing = detect_missing(features, query_text)
            logger.info(
                "Extracted features: %s | missing: %s",
                [f.canonical_name for f in features],
                missing,
            )

            query_embedding: list[float] | None = None
            if settings.openai_api_key:
                try:
                    query_embedding = embed_query(
                        settings.openai_api_key,
                        settings.embedding_model,
                        query_text,
                    )
                except Exception as exc:
                    logger.warning("Embedding failed, continuing without vector route: %s", exc)

            candidates = rank_patterns(
                conn=conn,
                feature_atom_ids=[f.atom_id for f in features],
                query_embedding=query_embedding,
                query_fts=query_text,
                top_k=settings.top_k,
            )
            logger.info("Ranked %s candidate patterns.", len(candidates))

            rules = load_active_rules(conn)
            rule_result = apply_rules(
                rules=rules,
                features=features,
                candidates=candidates,
                missing_categories=missing,
            )
            logger.info(
                "Applied %s rules, %s matched.",
                len(rules),
                sum(1 for o in rule_result.outcomes if o.matched),
            )

            all_feature_ids = {
                fid
                for c in rule_result.adjusted_candidates
                for fid in (c.supporting_feature_ids + c.conflicting_feature_ids)
            }
            name_lookup = resolve_atom_names(conn, list(all_feature_ids))

            answer = assemble_answer(
                raw_query=query_text,
                features=features,
                missing=missing,
                candidates=rule_result.adjusted_candidates,
                name_lookup=name_lookup,
                suggested_questions=rule_result.suggested_questions,
                ambiguity_flags=rule_result.ambiguity_flags,
            )

            synthesized_markdown = synthesize(answer)
            if synthesized_markdown:
                answer["H_synthesized_markdown"] = synthesized_markdown
                logger.info("Synthesized natural-language answer (%s chars).", len(synthesized_markdown))

            latency_ms = int((time.time() - start_ts) * 1000)

            query_log_id = persist_query_log(
                conn=conn,
                user_query=query_text,
                features=features,
                missing=missing,
                candidates=rule_result.adjusted_candidates,
                answer=answer,
                latency_ms=latency_ms,
                model_name=settings.embedding_model if query_embedding else None,
            )
            conn.commit()

            print(json.dumps(
                {"query_log_id": query_log_id, "answer": answer},
                ensure_ascii=False,
                indent=2,
            ))
            if synthesized_markdown:
                print("\n" + "=" * 60)
                print(synthesized_markdown)

    except psycopg.OperationalError as exc:
        logger.error("Database connection error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: answer_query.py <natural-language query>", file=sys.stderr)
        sys.exit(2)
    query = " ".join(sys.argv[1:])
    sys.exit(run(query))
