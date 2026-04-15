# Spec-010: API 契約

- Status: Draft
- Owner: Platform Engineer
- Last Updated: 2026-04-15

## 1. 目的

定義對外暴露的介面：MCP Tools（Claude Desktop / Agent）與 REST 端點（Dashboard / curl）。

實作：[mcp-server/server.py](../../mcp-server/server.py)。

## 2. 共用原則

* 單一 FastAPI 應用，port 預設 3000
* 同一工具同時可用 SSE 與 REST 呼叫
* 所有錯誤以標準 HTTP code + JSON `{detail: "..."}` 回傳
* 任何成功回應的頂層結構為 `{content: ...}`（REST）或 MCP TextContent（SSE）

## 3. MCP Tools

### 3.1 `diagnose_tcm`

| 項目 | 值 |
| --- | --- |
| Input | `query: string, top_k?: int=5, synthesize_markdown?: bool=true` |
| Output | Answer Contract JSON（見 [Spec-007 §7](./spec-007-generation-orchestrator.md)） |
| 使用時機 | 使用者描述舌脈出汗潮熱等症狀 |

### 3.2 `search_knowledge_atoms`

| 項目 | 值 |
| --- | --- |
| Input | `query: string, atom_types?: string[], top_k?: int=10` |
| Output | 原子陣列：`{atom_id, atom_type, canonical_name, summary_text, domain, category, score}[]` |
| 使用時機 | 查詢術語、列相關概念清單 |

### 3.3 `explain_pattern`

| 項目 | 值 |
| --- | --- |
| Input | `canonical_name: string` |
| Output | 單一證型完整說明與支持 / 衝突邊 |
| 使用時機 | 明確詢問某證型定義 |

## 4. REST 端點

| Method | Path | 說明 |
| ------ | ---- | ---- |
| GET | `/health` | DB / embedding / synthesis 子系統狀態 |
| POST | `/tools/{name}` | 同 §3 工具，body 為 JSON arguments |

### 4.1 `/health` 回應

```json
{
  "status": "ok",
  "database": true,
  "openai_embeddings": true,
  "anthropic_synthesis": true,
  "tools": ["diagnose_tcm", "search_knowledge_atoms", "explain_pattern"]
}
```

## 5. MCP SSE 端點

| Method | Path | 說明 |
| ------ | ---- | ---- |
| GET | `/sse` | 保持長連線 |
| POST | `/messages/` | SSE 配合端點 |

Claude Desktop 設定：

```json
{
  "mcpServers": {
    "tcm-diagnostic-rag": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

## 6. 驗證契約

### 6.1 工具名稱與 schema 一致性

MCP `list_tools()` 的 schema 必須與 REST `/tools/{name}` 接受的參數一致。
實作上由單一 `TOOL_SCHEMAS` 列表驅動。

### 6.2 錯誤對應

| 情境 | HTTP | MCP text |
| --- | --- | --- |
| 未知工具 | 404 | `Unknown tool: {name}` |
| 參數型別錯 | 400 | 內嵌於 `Tool error: {msg}` |
| DB 失敗 | 500 | `Tool error: {msg}` |

## 7. 非功能要求

* `/tools/diagnose_tcm` 在關閉 Stage 2 時 < 1s；開啟時 < 8s（LLM 延遲）
* 併發上限由 uvicorn workers 控制；單 connection per request（不用 pool 的話必須設 `max_workers=1`）

## 8. 未來擴充

* `/tools/case_lookup`（Phase 3 醫案檢索）
* `/tools/multi_turn_refine`（接多輪補問）
* Bearer token 驗證（目前為內網使用）

## 9. 驗收要求

* `curl /health` 在啟動後 5 秒內回 200
* 每個工具均有 curl 範例於 [mcp-server/README.md](../../mcp-server/README.md) 可重現
* Claude Desktop 連線後，在對話中輸入描述症狀可自動觸發 `diagnose_tcm`

## 10. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §5（兩階段生成由 API 控制 synthesize 開關）
