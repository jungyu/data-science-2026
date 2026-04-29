# ADR-006：MVP 階段不建 MCP Server

## 狀態

已採納

## 背景

MCP（Model Context Protocol）Server 的價值在於讓多個 agent 客戶端（Claude Desktop、Web Dashboard、其他 agent runtime）共用同一套工具與知識存取介面。但此專案目前只有一個客戶端：LINE Bot。

額外建立 MCP Server 會增加以下成本：
- 需定義並維護 tool schema（JSON Schema）
- 需處理 MCP 協議的連線管理
- 本地開發環境需同時啟動兩個服務

## 決策

MVP 階段不建 MCP Server。公開介面維持：

- **LINE Webhook**：`POST /api/line/webhook`（唯一對外入口）
- **Health Check**：`GET /health`
- **內部 Python 模組**：router、retriever、generator 作為純函式庫呼叫

待以下任一情況發生時再評估：

- 需從 Claude Desktop 或其他 AI 工具存取同一套知識庫
- 需建立 Web Dashboard 讓非 LINE 使用者查詢
- 需將 router/retriever 作為工具暴露給其他 agent

## 後果

### 正面

- 服務介面最小，只需維護一個 FastAPI app
- 不需學習 MCP 協議即可讓系統運作
- 更快到達可用的 bot 狀態

### 負面

- 目前無法從 Claude Desktop 或其他 agent 直接呼叫知識庫
- 未來若需 MCP 整合，需額外開發一層轉接
