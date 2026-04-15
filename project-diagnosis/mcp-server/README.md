# TCM Diagnostic RAG — MCP Server

把 `project-diagnosis` 的 RAG pipeline 包裝成 **MCP Tools**，讓 Claude Desktop、
Next.js Dashboard 或任何 HTTP client 都能呼叫。

對齊課程 [Module A](../../docs/RAG/module-a-mcp-server.md) 的 FastAPI + SSE + REST 雙接口模式。

---

## 提供的工具

| Tool name                 | 用途                                                   |
| ------------------------- | ------------------------------------------------------ |
| `diagnose_tcm`            | 端到端辨證輔助：症狀敘述 → Answer Contract + Markdown  |
| `search_knowledge_atoms`  | FTS + 向量混合搜尋，限定 atom_type 可用                |
| `explain_pattern`         | 單一證型完整說明、相關症狀與衝突訊號                   |

---

## 端點

| 方法 | 路徑               | 用途                                    |
| ---- | ------------------ | --------------------------------------- |
| GET  | `/health`          | 健康檢查（含 DB / embedding / LLM 狀態）|
| POST | `/tools/{name}`    | REST 呼叫（Next.js / curl）             |
| GET  | `/sse`             | MCP SSE 通道（Claude Desktop）          |
| POST | `/messages/`       | MCP SSE 配合端點                        |

---

## 啟動

```bash
# 依賴（主專案 + MCP server）
pip install -r ../requirements.txt
pip install -r requirements.txt

# 環境變數
export DATABASE_URL=postgresql://...
export OPENAI_API_KEY=sk-...          # 選配：啟用查詢 embedding
export ANTHROPIC_API_KEY=sk-ant-...   # 選配：啟用 Markdown 敘事

# 啟動
python server.py
```

預設 `0.0.0.0:3000`。可用 `MCP_SERVER_PORT` 覆寫。

---

## 快速驗證

```bash
# 健康檢查
curl http://localhost:3000/health

# 端到端辨證
curl -X POST http://localhost:3000/tools/diagnose_tcm \
  -H "Content-Type: application/json" \
  -d '{"query": "最近下午容易潮熱，晚上盜汗，口乾，舌紅少苔"}'

# 搜尋原子
curl -X POST http://localhost:3000/tools/search_knowledge_atoms \
  -H "Content-Type: application/json" \
  -d '{"query": "盜汗", "atom_types": ["symptom", "pattern"], "top_k": 5}'

# 查詢單一證型
curl -X POST http://localhost:3000/tools/explain_pattern \
  -H "Content-Type: application/json" \
  -d '{"canonical_name": "陰虛內熱"}'
```

---

## Claude Desktop 設定

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 加入：

```json
{
  "mcpServers": {
    "tcm-diagnostic-rag": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

重啟 Claude Desktop，對話中輸入「幫我分析這個症狀：午後潮熱、盜汗、口乾」，
Claude 應會自動呼叫 `diagnose_tcm`。

---

## 設計備註

- **MCP SDK 選配**：沒裝 `mcp` package 時仍可跑 REST-only 模式，SSE 路徑不掛載
- **共用 pipeline**：直接 import `scripts/answer_query.py` 的函數，沒重寫
- **LLM synthesis 可關**：`diagnose_tcm` 接受 `synthesize_markdown: false` 省 token
- **工具 description 寫具體情境**：課程強調這是 Claude 決定呼叫時機的唯一依據
