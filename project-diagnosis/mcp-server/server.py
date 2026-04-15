#!/usr/bin/env python3
"""
MCP Server for the TCM Diagnostic RAG system.

Exposes three tools over both MCP/SSE (for Claude Desktop) and REST
(for Next.js dashboards or shell curl), matching the course Module A
pattern.

Tools:
  - diagnose_tcm              end-to-end辨證輔助 (runs answer_query pipeline)
  - search_knowledge_atoms    full-text + vector search over atoms
  - explain_pattern           fetch one pattern + its related symptoms

Ports and endpoints:
  GET  /health                health check
  POST /tools/{name}          REST invocation
  GET  /sse                   MCP Server-Sent Events transport
  POST /messages/             MCP SSE companion endpoint

Environment variables:
  DATABASE_URL              required
  OPENAI_API_KEY            optional (enables vector route + query embedding)
  ANTHROPIC_API_KEY         optional (enables natural-language synthesis)
  MCP_SERVER_PORT           default 3000
  MCP_SERVER_HOST           default 0.0.0.0

Run:
  python server.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Make ../scripts importable so we can reuse the pipeline
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from answer_query import (  # noqa: E402
    detect_missing,
    embed_query,
    extract_features,
    load_feature_dictionary,
    rank_patterns,
    resolve_atom_names,
    assemble_answer,
)
from apply_rules import apply_rules, load_active_rules  # noqa: E402
from synthesize_answer import synthesize  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("mcp_server")


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip() or None
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "3000"))
SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")


# ---------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------

def _open_conn() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL)


def diagnose_tcm(query: str, top_k: int = 5, synthesize_markdown: bool = True) -> dict[str, Any]:
    """執行完整的中醫辨證輔助流程。

    Args:
        query: 使用者的症狀敘述（自然語言，中文）
        top_k: 返回前幾名候選證型
        synthesize_markdown: 是否呼叫 LLM 產生 Markdown 敘事答案
    """
    with _open_conn() as conn:
        dictionary = load_feature_dictionary(conn)
        features = extract_features(query, dictionary)
        missing = detect_missing(features, query)

        query_embedding = None
        if OPENAI_API_KEY:
            try:
                query_embedding = embed_query(OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, query)
            except Exception as exc:
                logger.warning("Query embedding failed: %s", exc)

        candidates = rank_patterns(
            conn=conn,
            feature_atom_ids=[f.atom_id for f in features],
            query_embedding=query_embedding,
            query_fts=query,
            top_k=top_k,
        )

        rules = load_active_rules(conn)
        rule_result = apply_rules(
            rules=rules,
            features=features,
            candidates=candidates,
            missing_categories=missing,
        )

        all_feature_ids = {
            fid
            for c in rule_result.adjusted_candidates
            for fid in (c.supporting_feature_ids + c.conflicting_feature_ids)
        }
        name_lookup = resolve_atom_names(conn, list(all_feature_ids))

        answer = assemble_answer(
            raw_query=query,
            features=features,
            missing=missing,
            candidates=rule_result.adjusted_candidates,
            name_lookup=name_lookup,
            suggested_questions=rule_result.suggested_questions,
            ambiguity_flags=rule_result.ambiguity_flags,
        )

    if synthesize_markdown:
        markdown = synthesize(answer)
        if markdown:
            answer["H_synthesized_markdown"] = markdown

    return answer


def search_knowledge_atoms(
    query: str,
    atom_types: list[str] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """以 FTS + 向量混合檢索 knowledge_atoms，回傳最相關的原子。

    Args:
        query: 查詢字串
        atom_types: 限定類型，如 ["symptom", "pattern"]；None 表示全類型
        top_k: 返回前幾筆
    """
    atom_types = atom_types or [
        "symptom", "sign", "tongue_feature", "pulse_feature",
        "pattern", "treatment_principle", "formula",
    ]

    query_embedding_literal = None
    if OPENAI_API_KEY:
        try:
            vec = embed_query(OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, query)
            query_embedding_literal = json.dumps(vec, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Embedding failed for search: %s", exc)

    sql = """
        with fts as (
          select id, ts_rank_cd(search_vector, plainto_tsquery('simple', %(q)s)) as score
          from public.knowledge_atoms
          where is_active = true
            and atom_type = any(%(types)s)
            and search_vector @@ plainto_tsquery('simple', %(q)s)
          order by score desc
          limit %(k)s
        ),
        vec as (
          select id,
                 case when %(vec)s::text is null or embedding is null then 0.0
                      else 1.0 - (embedding <=> %(vec)s::vector) end as score
          from public.knowledge_atoms
          where is_active = true
            and atom_type = any(%(types)s)
            and embedding is not null
          order by score desc
          limit %(k)s
        ),
        merged as (
          select id, max(score) as score from (
            select id, score from fts
            union all
            select id, score from vec
          ) u
          group by id
        )
        select ka.id, ka.atom_type, ka.canonical_name, ka.summary_text,
               ka.domain, ka.category, m.score
        from merged m
        join public.knowledge_atoms ka on ka.id = m.id
        order by m.score desc
        limit %(k)s
    """

    with _open_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, {
            "q": query,
            "types": list(atom_types),
            "vec": query_embedding_literal,
            "k": top_k,
        })
        rows = cur.fetchall()

    return [
        {
            "atom_id": r[0],
            "atom_type": r[1],
            "canonical_name": r[2],
            "summary_text": r[3],
            "domain": r[4],
            "category": r[5],
            "score": float(r[6]) if r[6] is not None else 0.0,
        }
        for r in rows
    ]


def explain_pattern(canonical_name: str) -> dict[str, Any]:
    """取得指定證型的完整說明、相關症狀與舌脈支持訊號。

    Args:
        canonical_name: 證型名稱（如「陰虛內熱」「衛氣不固」）
    """
    with _open_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, title, canonical_name, body_markdown, summary_text,
                       metadata, authority_level
                from public.knowledge_atoms
                where atom_type = 'pattern'
                  and is_active = true
                  and canonical_name = %s
                limit 1
                """,
                (canonical_name,),
            )
            row = cur.fetchone()

        if not row:
            return {"found": False, "canonical_name": canonical_name}

        pattern_id = row[0]

        with conn.cursor() as cur:
            cur.execute(
                """
                select ka.atom_type, ka.canonical_name, r.relation_type, r.weight
                from public.atom_relations r
                join public.knowledge_atoms ka on ka.id = r.from_atom_id
                where r.to_atom_id = %s
                  and r.relation_type in ('suggests', 'strengthens', 'strongly_strengthens', 'conflicts_with')
                order by r.weight desc
                """,
                (pattern_id,),
            )
            edges = cur.fetchall()

    return {
        "found": True,
        "pattern_id": row[0],
        "title": row[1],
        "canonical_name": row[2],
        "body_markdown": row[3],
        "summary": row[4],
        "metadata": row[5],
        "authority_level": row[6],
        "supporting": [
            {"atom_type": e[0], "name": e[1], "relation": e[2], "weight": float(e[3])}
            for e in edges if e[2] != "conflicts_with"
        ],
        "conflicting": [
            {"atom_type": e[0], "name": e[1], "relation": e[2], "weight": float(e[3])}
            for e in edges if e[2] == "conflicts_with"
        ],
    }


# ---------------------------------------------------------
# Tool registry
# ---------------------------------------------------------

TOOLS = {
    "diagnose_tcm": diagnose_tcm,
    "search_knowledge_atoms": search_knowledge_atoms,
    "explain_pattern": explain_pattern,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "diagnose_tcm",
        "description": (
            "根據使用者的中醫症狀敘述，執行完整辨證輔助流程，"
            "回傳結構化 Answer Contract（症狀摘要、前 3 候選證型、支持證據、"
            "鑑別重點、尚缺資訊、治法方向、引用），含可選的 Markdown 敘事答案。"
            "適用情境：使用者描述舌脈、出汗、潮熱、疲倦等中醫症狀時。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "使用者的中醫症狀自然語言敘述",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回前幾名候選證型（預設 5）",
                    "default": 5,
                },
                "synthesize_markdown": {
                    "type": "boolean",
                    "description": "是否呼叫 LLM 產生 Markdown 敘事答案（預設 true）",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_knowledge_atoms",
        "description": (
            "以全文檢索 + 向量混合方式搜尋中醫知識原子（症狀 / 證型 / 舌脈 / 治法 / 方劑）。"
            "適用情境：使用者想查詢某個術語定義、或需要列出相關概念清單時。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜尋關鍵字或短語"},
                "atom_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "限定原子類型（symptom / pattern / tongue_feature / ...）",
                },
                "top_k": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "explain_pattern",
        "description": (
            "取得指定證型的詳細說明、病機、相關症狀與舌脈支持訊號，以及衝突訊號。"
            "適用情境：使用者明確詢問某一證型（如「什麼是陰虛內熱？」）。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "canonical_name": {
                    "type": "string",
                    "description": "證型的正規名稱（如「陰虛內熱」「衛氣不固」）",
                },
            },
            "required": ["canonical_name"],
        },
    },
]


# ---------------------------------------------------------
# REST API
# ---------------------------------------------------------

app = FastAPI(title="TCM Diagnostic RAG — MCP Server", version="0.1.0")


class ToolRequest(BaseModel):
    model_config = {"extra": "allow"}


@app.get("/health")
def health() -> dict[str, Any]:
    db_ok = False
    try:
        with _open_conn() as conn, conn.cursor() as cur:
            cur.execute("select 1")
            db_ok = True
    except Exception as exc:
        logger.warning("Health check DB error: %s", exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "openai_embeddings": bool(OPENAI_API_KEY),
        "anthropic_synthesis": bool((os.getenv("ANTHROPIC_API_KEY") or "").strip()),
        "tools": list(TOOLS.keys()),
    }


@app.post("/tools/{name}")
def invoke_tool(name: str, payload: ToolRequest) -> JSONResponse:
    if name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

    kwargs = payload.model_dump()
    try:
        result = TOOLS[name](**kwargs)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid arguments: {exc}")
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse({"content": result})


# ---------------------------------------------------------
# MCP SSE transport (optional — requires `mcp` package)
# ---------------------------------------------------------

def _mount_mcp_sse() -> None:
    """Attach MCP SSE endpoints if the `mcp` SDK is available.

    Done lazily so the server still runs (REST-only) without the SDK.
    """
    try:
        from mcp.server import Server
        from mcp.server.sse import SseServerTransport
        from mcp.types import TextContent, Tool
    except ImportError:
        logger.info("`mcp` package not installed; SSE transport disabled.")
        return

    mcp_server = Server("tcm-diagnostic-rag")

    @mcp_server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [Tool(**schema) for schema in TOOL_SCHEMAS]

    @mcp_server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name not in TOOLS:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = TOOLS[name](**(arguments or {}))
        except Exception as exc:
            return [TextContent(type="text", text=f"Tool error: {exc}")]
        text = json.dumps(result, ensure_ascii=False, indent=2) if not isinstance(result, str) else result
        return [TextContent(type="text", text=text)]

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):  # type: ignore[no-untyped-def]
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )

    from starlette.routing import Mount, Route

    app.router.routes.append(Route("/sse", endpoint=handle_sse))
    app.router.routes.append(Mount("/messages/", app=sse.handle_post_message))
    logger.info("MCP SSE transport mounted at /sse and /messages/")


_mount_mcp_sse()


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

def main() -> None:
    logger.info("TCM Diagnostic RAG — MCP Server starting on %s:%s", SERVER_HOST, SERVER_PORT)
    logger.info("Registered tools: %s", list(TOOLS.keys()))
    if not DATABASE_URL:
        logger.warning("DATABASE_URL is not set — tool calls will fail.")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")


if __name__ == "__main__":
    main()
