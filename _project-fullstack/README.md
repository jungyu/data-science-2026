# Project Fullstack Template

資料科學專案的完整基礎設施模板。涵蓋爬蟲、向量資料庫、MCP Server、反向代理。

## 目錄結構

```
project-fullstack-template/
├── docker-compose.yml   # 主設定檔，服務依課程進度逐步解鎖
├── .env.example         # 環境變數範本
├── nginx/
│   └── default.conf     # 反向代理路由規則
├── crawler/             # Playwright 爬蟲（Stage 1）
├── mcp-server/          # RAG + MCP Server（Stage 3）
└── frontend/
    └── dist/            # 前端靜態檔建置輸出
```

## 服務解鎖順序

| Stage | 服務 | 指令 |
|-------|------|------|
| 1 | nginx + crawler | `docker compose up -d` |
| 2 | + qdrant | 取消 qdrant 區塊註解 → `docker compose up -d` |
| 3 | + mcp-server | 取消 mcp-server 區塊註解 → `docker compose up -d` |

## 快速開始

```bash
cp .env.example .env
# 編輯 .env 填入金鑰

docker compose up -d
docker compose ps
```

## 與 Supabase 的關係

PostgreSQL 由 `supabase start` 獨立管理：

```bash
# 終端機 1
supabase start        # 啟動 DB + Auth + Studio（port 54321~54323）

# 終端機 2
docker compose up -d  # 啟動 crawler + nginx（之後加 qdrant + mcp-server）
```
