"""
MCP Server：企業知識庫（只讀存取）。
執行方式：python server.py --namespace hr-* --readonly

來源：第九章 — MCP Server 的工具定義
"""

import argparse
import json
import sys

from mcp.server import Server
import mcp.types as types

app = Server("knowledge-mcp")

# 由啟動參數設定
SERVER_NAMESPACE = "hr-*"
READ_ONLY = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Knowledge MCP Server (scaffold)")
    parser.add_argument(
        "--namespace",
        default=SERVER_NAMESPACE,
        help="Allowed namespace pattern (default: hr-*)",
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        default=True,
        help="Keep server in read-only mode (default: true)",
    )
    return parser.parse_args()


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """定義 MCP Server 暴露給 AI Agent 的工具清單"""
    return [
        types.Tool(
            name="search_knowledge",
            description=(
                "在企業知識庫中語意搜尋相關文件。"
                "只能搜尋授權的 namespace，不能跨部門存取。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋問題或關鍵詞",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回結果數量（1-10，預設 5）",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_document_info",
            description="查詢文件的版本資訊和 metadata（不返回全文）",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                },
                "required": ["doc_id"],
            },
        ),
        types.Tool(
            name="list_namespace_stats",
            description="列出授權 namespace 的統計資訊（文件數、新鮮度等）",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # 注意：沒有 write 工具（MCP-2：MCP Server 只讀）
        # 寫入操作必須透過 ingest-skill，有完整的治理流程
    ]


@app.call_tool()
async def call_tool(
    name: str,
    arguments: dict,
) -> list[types.TextContent]:

    if name == "search_knowledge":
        return await _search_knowledge(arguments)
    elif name == "get_document_info":
        return await _get_document_info(arguments)
    elif name == "list_namespace_stats":
        return await _list_namespace_stats()
    else:
        raise ValueError(f"未知工具：{name}")


async def _search_knowledge(args: dict) -> list[types.TextContent]:
    """
    執行語意搜尋，包含：
    1. 嵌入查詢
    2. 向量搜尋（受 namespace 限制）
    3. Retrieval Gate 過濾
    4. 格式化結果
    5. 記錄稽核日誌
    """
    query = str(args["query"]).strip()
    top_k = int(args.get("top_k", 5))

    if not query:
        raise ValueError("query 不可為空")
    if top_k < 1 or top_k > 10:
        raise ValueError("top_k 必須介於 1 到 10")

    # TODO: 接入真實的 RAGQueryPipeline
    result = {
        "status": "no_relevant_knowledge",
        "reason": "MCP Server 尚未接入向量資料庫",
        "chunks": [],
        "suggestion": "請先執行 ingest-skill 攝取文件到知識庫",
        "server_mode": "scaffold",
        "namespace_pattern": SERVER_NAMESPACE,
    }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _get_document_info(args: dict) -> list[types.TextContent]:
    """查詢文件的版本資訊和 metadata。"""
    doc_id = args["doc_id"]

    # TODO: 接入真實的 document registry
    result = {
        "status": "not_found",
        "doc_id": doc_id,
        "message": "Document registry 尚未初始化",
        "server_mode": "scaffold",
    }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _list_namespace_stats() -> list[types.TextContent]:
    """列出授權 namespace 的統計資訊。"""

    # TODO: 接入真實的向量資料庫
    result = {
        "namespace_pattern": SERVER_NAMESPACE,
        "namespaces": [],
        "message": "向量資料庫尚未連接",
        "readonly": READ_ONLY,
        "server_mode": "scaffold",
    }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


if __name__ == "__main__":
    args = parse_args()
    SERVER_NAMESPACE = args.namespace
    READ_ONLY = bool(args.readonly)
    print(
        json.dumps(
            {
                "server": "knowledge-mcp",
                "status": "configured",
                "namespace_pattern": SERVER_NAMESPACE,
                "readonly": READ_ONLY,
                "note": "Scaffold mode: MCP transport bootstrap not wired in this sample.",
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
