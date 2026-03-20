# DS Dashboard — Next.js + DaisyUI 起始模板

資料科學期末專題的前端起始點。儀表板（Chart.js / Mermaid）+ AI 側欄（串接 MCP Server）。

## 快速開始（開發模式）

```bash
cp .env.example .env.local
# 填入 OPENAI_API_KEY 和 MCP_SERVER_URL

npm install
npm run dev          # → http://localhost:4000
```

> MCP Server 需另外啟動（`_project-fullstack/` 的 docker-compose），
> 或直接設 `MCP_SERVER_URL=` 空白，AI 仍可回答，只是沒有外部知識庫。

---

## 學生需要修改的地方

### 1. 替換圖表資料（`app/page.tsx`）

```tsx
// 把這兩個換成你的資料
const SAMPLE_TREND_DATA = { ... }
const SAMPLE_DIST_DATA  = { ... }
```

資料可以來自：
- Supabase 查詢（用 `fetch('/api/data')` 在 server component 取得）
- CSV 直接 import
- MCP Server 查詢結果

### 2. 修改預設問題（`lib/preset-questions.ts`）

```ts
export const PRESET_QUESTIONS = [
  '你的問題 1',
  '你的問題 2',
  ...
]
```

問題要能對應到儀表板上的圖表，讓 AI 的回答有所根據。

### 3. 修改系統 Prompt（`app/api/chat/route.ts`）

```ts
const systemPrompt = `你是一個 [你的專題領域] 助理。...`
```

---

## 目錄結構

```
_project-nextjs/
├── app/
│   ├── layout.tsx          # DaisyUI 主題設定
│   ├── page.tsx            # Dashboard 主頁（修改圖表資料）
│   ├── globals.css
│   └── api/
│       └── chat/route.ts   # SSE 串流 → OpenAI + MCP Server
├── components/
│   ├── Sidebar.tsx         # AI 聊天側欄（預設問題 + 串流）
│   ├── ChartCard.tsx       # Chart.js 圖表容器
│   └── MermaidBlock.tsx    # Mermaid 渲染元件
├── lib/
│   ├── mcp-client.ts       # 呼叫 MCP Server 的 helper
│   └── preset-questions.ts # 預設問題（學生修改）
├── Dockerfile              # 整合進 _project-fullstack 用
└── .env.example
```

---

## 整合進 _project-fullstack（交作品時）

1. 複製整個資料夾到 `_project-fullstack/frontend/`
2. 取消 `docker-compose.yml` 中 `frontend` service 的註解
3. 取消 `nginx/default.conf` 中 proxy 設定的註解
4. `docker compose up -d --build`

詳見 `_project-fullstack/README.md`。

---

## Port 一覽

| 服務 | Port | 說明 |
|------|------|------|
| Next.js（本機開發） | 4000 | `npm run dev` |
| MCP Server | 3000 | docker-compose |
| Qdrant | 6333 | 向量資料庫 |
| nginx | 8080 | 整合後的對外入口 |
