# _project-fullstack — 完整專案基礎設施模板

資料科學期末專題的 Docker 基礎設施模板。
包含爬蟲、向量資料庫、MCP Server、反向代理、前端儀表板，依課程進度分四個 Stage 解鎖。

## 目錄結構

```
_project-fullstack/
├── docker-compose.yml   # 主設定檔，服務依 Stage 逐步解鎖
├── .env.example         # 環境變數範本（複製為 .env 後填入）
├── nginx/
│   └── default.conf     # 反向代理路由規則
├── crawler/             # Playwright 爬蟲（Stage 1，需自行建立）
├── mcp-server/          # MCP Server 骨架（Stage 3）
│   ├── server.py        # 工具定義（學生修改這裡）
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/            # Next.js Dashboard（Stage 4，從 _project-nextjs/ 複製）
    └── dist/            # 靜態檔輸出（Stage 1–3 使用）
```

## Stage 解鎖順序

| Stage | 新增服務 | 解鎖方式 | 說明 |
|-------|---------|---------|------|
| 1 | nginx + crawler | 預設啟用 | 爬蟲收集資料、nginx 提供靜態頁面 |
| 2 | + qdrant | 已預設啟用 | 向量資料庫，儲存 RAG embedding |
| 3 | + mcp-server | 已預設啟用 | RAG 工具伺服器，供 Claude Desktop 連線 |
| 4 | + frontend | 取消 `frontend` service 註解 | Next.js 儀表板，取代靜態頁面 |

## 快速開始

```bash
# 1. 複製環境變數範本
cp .env.example .env
# 填入 OPENAI_API_KEY、SUPABASE_URL、SUPABASE_ANON_KEY

# 2. 啟動（Stage 1–3）
docker compose up -d

# 3. 確認狀態
docker compose ps

# 4. 驗收 MCP Server
curl http://localhost:3000/health
```

## Port 一覽

| 服務 | Port | 說明 |
|------|------|------|
| nginx | 8080 | 統一對外入口 |
| crawler | 3001 | Playwright 爬蟲 API |
| qdrant | 6333 | 向量庫 REST API + Web UI |
| qdrant gRPC | 6334 | gRPC 連線 |
| mcp-server SSE | 3000 | Claude Desktop 連線 |
| mcp-server REST | 3000 | Next.js Dashboard 呼叫 `/tools/<name>` |
| frontend (Stage 4) | 4000 | Next.js（容器內，對外由 nginx proxy） |
| supabase | 54321–54323 | 由 `supabase start` 獨立管理 |

## 與 Supabase 的關係

PostgreSQL 由 `supabase start` 獨立管理，不在此 docker-compose 中：

```bash
# 終端機 1
supabase start        # 啟動 DB + Auth + Studio（port 54321~54323）

# 終端機 2
docker compose up -d  # 啟動本模板的服務
```

MCP Server 透過 `extra_hosts: host.docker.internal` 連回宿主機的 Supabase。

## Stage 4：整合 Next.js Dashboard

```bash
# 1. 將前端模板複製進來
cp -r ../_project-nextjs/ ./frontend/

# 2. 取消 docker-compose.yml 中 frontend service 的註解

# 3. 切換 nginx 路由（nginx/default.conf 中有說明）

# 4. 重新建置並啟動
docker compose up -d --build

# 訪問 http://localhost:8080
```

詳細步驟見 [docs/RAG/module-b-dashboard.md](../docs/RAG/module-b-dashboard.md) B5 節。

## Claude Desktop 連線設定

MCP Server 啟動後，在 Claude Desktop 的 `claude_desktop_config.json` 加入：

```json
{
  "mcpServers": {
    "ds-mcp": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

詳細設定見 [docs/RAG/module-a-mcp-server.md](../docs/RAG/module-a-mcp-server.md) A5 節。
