"""
MCP Server — 資料科學專題工具伺服器

架構：單一 FastAPI app，port 3000
  /sse         → SSE transport（給 Claude Desktop 連線）
  /messages    → SSE 訊息端點（配合 /sse）
  /tools/{name}→ REST adapter（給 Next.js Dashboard 呼叫）
  /health      → 健康檢查

Claude Desktop 設定（claude_desktop_config.json）：
  {
    "mcpServers": {
      "ds-mcp": {
        "url": "http://localhost:3000/sse"
      }
    }
  }

Next.js Dashboard（.env.local）：
  MCP_SERVER_URL=http://localhost:3000
  → 呼叫 POST http://localhost:3000/tools/search_knowledge_base
"""

import os
import json
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from openai import OpenAI
from qdrant_client import QdrantClient
from supabase import create_client

load_dotenv()

# ── 環境變數 ─────────────────────────────────────────────────
QDRANT_URL        = os.getenv("QDRANT_URL",        "http://localhost:6333")
SUPABASE_URL      = os.getenv("SUPABASE_URL",       "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY",  "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY",     "")

# ── 用戶端初始化 ─────────────────────────────────────────────
openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)
supabase_client = (
    create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if SUPABASE_URL and SUPABASE_ANON_KEY else None
)


# ════════════════════════════════════════════════════════════
#  工具實作（純函式，MCP handler 和 REST endpoint 共用）
# ════════════════════════════════════════════════════════════

def search_knowledge_base(
    query: str,
    collection: str = "knowledge",
    top_k: int = 5,
) -> str:
    """搜尋向量知識庫，回傳最相關的文件片段。"""
    # 把問題嵌入成向量
    embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    ).data[0].embedding

    # 向量相似度搜尋
    try:
        hits = qdrant_client.search(
            collection_name=collection,
            query_vector=embedding,
            limit=top_k,
            with_payload=True,
        )
    except Exception as e:
        return f"[Qdrant 搜尋失敗：{e}]"

    if not hits:
        return "（知識庫中找不到相關內容）"

    segments = []
    for i, hit in enumerate(hits, 1):
        payload = hit.payload or {}
        source  = payload.get("source", "未知來源")
        text    = payload.get("text", "")
        score   = round(hit.score, 3)
        segments.append(f"[{i}] 來源：{source}（相似度 {score}）\n{text}")

    return "\n---\n".join(segments)


def query_supabase(
    table: str,
    filters: str = "{}",
    limit: int = 20,
    select: str = "*",
) -> str:
    """查詢 Supabase 資料表，回傳 JSON 格式結果。"""
    if not supabase_client:
        return "[Supabase 未設定，請檢查 SUPABASE_URL 和 SUPABASE_ANON_KEY]"

    try:
        q = supabase_client.table(table).select(select).limit(limit)
        for col, val in json.loads(filters).items():
            q = q.eq(col, val)
        rows = q.execute().data
        return json.dumps(rows, ensure_ascii=False, indent=2) if rows else f"（{table} 查無資料）"
    except json.JSONDecodeError:
        return '[filters 格式錯誤，例如：{"status": "active"}]'
    except Exception as e:
        return f"[Supabase 查詢失敗：{e}]"


# 工具清單（新增工具時在此登記）
TOOLS: dict[str, Any] = {
    "search_knowledge_base": search_knowledge_base,
    "query_supabase":        query_supabase,
}

TOOL_SCHEMAS: list[Tool] = [
    Tool(
        name="search_knowledge_base",
        description="搜尋向量知識庫，回傳最相關的文件片段",
        inputSchema={
            "type": "object",
            "properties": {
                "query":      {"type": "string",  "description": "搜尋關鍵字或問題"},
                "collection": {"type": "string",  "description": "Qdrant 集合名稱", "default": "knowledge"},
                "top_k":      {"type": "integer", "description": "回傳筆數", "default": 5},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="query_supabase",
        description="查詢 Supabase 資料表，回傳 JSON 結果",
        inputSchema={
            "type": "object",
            "properties": {
                "table":   {"type": "string", "description": "資料表名稱"},
                "filters": {"type": "string", "description": 'JSON 篩選條件，例如 {"status":"active"}', "default": "{}"},
                "limit":   {"type": "integer", "description": "回傳筆數上限", "default": 20},
                "select":  {"type": "string", "description": "欄位（逗號分隔）", "default": "*"},
            },
            "required": ["table"],
        },
    ),
]


# ════════════════════════════════════════════════════════════
#  MCP Server（SSE transport，給 Claude Desktop 用）
# ════════════════════════════════════════════════════════════
mcp_server = Server("ds-mcp-server")

@mcp_server.list_tools()
async def list_tools():
    return TOOL_SCHEMAS

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name not in TOOLS:
        return [TextContent(type="text", text=f"[工具 {name} 不存在]")]
    result = TOOLS[name](**arguments)
    return [TextContent(type="text", text=result)]


# ════════════════════════════════════════════════════════════
#  FastAPI app（統一 port 3000）
# ════════════════════════════════════════════════════════════
app  = FastAPI(title="DS MCP Server")
sse  = SseServerTransport("/messages")


# ── SSE endpoints（Claude Desktop）────────────────────────
@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1],
            mcp_server.create_initialization_options(),
        )

@app.post("/messages")
async def messages_endpoint(request: Request):
    await sse.handle_post_message(
        request.scope, request.receive, request._send
    )


# ── REST adapter（Next.js Dashboard）──────────────────────
@app.post("/tools/{tool_name}")
async def rest_tool(tool_name: str, request: Request):
    if tool_name not in TOOLS:
        return JSONResponse({"error": f"工具 [{tool_name}] 不存在"}, status_code=404)
    try:
        body   = await request.json()
        result = TOOLS[tool_name](**body)
        return JSONResponse({"content": result})
    except TypeError as e:
        return JSONResponse({"error": f"參數錯誤：{e}"}, status_code=422)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── 健康檢查 ───────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":   "ok",
        "qdrant":   QDRANT_URL,
        "supabase": bool(supabase_client),
        "tools":    list(TOOLS.keys()),
    }


# ── 啟動 ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("DS MCP Server 啟動中（port 3000）")
    print("  /sse          → Claude Desktop SSE transport")
    print("  /tools/<name> → Next.js REST API")
    print("  /health       → 健康檢查")
    uvicorn.run(app, host="0.0.0.0", port=3000)
