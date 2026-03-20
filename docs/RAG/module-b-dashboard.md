# Module B｜Dashboard + AI 側欄

> **前置條件**：已完成 ch01–ch06（RAG Pipeline）和 Module A（MCP Server）
>
> **學習成果**：交出一個可展示的資料科學儀表板，含 AI 問答側欄

---

## 你將建立什麼？

```
┌─────────────────────────────┬──────────────────┐
│  固定圖表區（左 / 主體）      │  AI 側欄（右）    │
│                              │                  │
│  ┌──────────┐ ┌──────────┐  │  你好！請問有什麼  │
│  │ 趨勢折線圖│ │ 類別長條圖│  │  可以幫助你？      │
│  └──────────┘ └──────────┘  │                  │
│                              │  ● 解釋這張圖     │
│  ┌──────────────────────┐   │  ● 找異常點       │
│  │ Mermaid 架構圖        │   │  ● 預測趨勢       │
│  └──────────────────────┘   │                  │
│                              │  [輸入框]  [送出] │
└─────────────────────────────┴──────────────────┘
```

**必要功能（評分）**：
- ≥ 2 張 Chart.js 圖表，資料來自你的專題
- 1 個 Mermaid 架構圖（可以是你的系統架構或資料流程）
- AI 側欄，≥ 3 個預設問題，問題能對應到圖表
- 預設問題點擊後有 AI 串流回應

---

## B1｜模板導覽（30 分鐘）

### 取得模板

```bash
# 複製模板到你的工作目錄
cp -r _project-nextjs/ ~/my-project/frontend-dev
cd ~/my-project/frontend-dev

cp .env.example .env.local
# 填入你的 API Key
```

### 目錄結構快速導覽

```
frontend-dev/
├── app/
│   ├── page.tsx            ← 你的主要工作區（替換圖表資料）
│   └── api/chat/route.ts   ← AI 回答邏輯（修改 system prompt）
├── components/
│   ├── Sidebar.tsx         ← AI 側欄（通常不需修改）
│   ├── ChartCard.tsx       ← 圖表容器（傳資料進去就好）
│   └── MermaidBlock.tsx    ← Mermaid 渲染（傳字串就好）
└── lib/
    └── preset-questions.ts ← 你的預設問題（必改）
```

> **原則**：你主要只需要修改 3 個地方：
> `page.tsx`（圖表資料）、`preset-questions.ts`（問題）、`route.ts`（prompt）

### 啟動開發伺服器

```bash
npm install
npm run dev
# 開啟 http://localhost:4000
```

你應該會看到範例儀表板。接下來把範例資料換成你的。

---

## B2｜Chart.js：把資料變成圖表

### ChartCard 使用方式

模板已準備好 `<ChartCard>` 元件，你只需要傳入資料：

```tsx
// app/page.tsx

// ① 定義你的資料（Chart.js 格式）
const MY_DATA = {
  labels: ['第一週', '第二週', '第三週', '第四週'],
  datasets: [
    {
      label: '你的指標名稱',
      data: [120, 135, 98, 160],
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
    },
  ],
}

// ② 在 JSX 中使用
<ChartCard
  title="你的圖表標題"
  type="line"          // 'line' | 'bar' | 'pie' | 'doughnut'
  data={MY_DATA}
  height={260}
  description="可選：圖表說明文字"
/>
```

### 從 Supabase 取得真實資料

如果你的資料存在 Supabase，可以在 Server Component 中取得：

```tsx
// app/page.tsx（Server Component，不需 'use client'）
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export default async function DashboardPage() {
  // 從 Supabase 取得資料
  const { data: rows } = await supabase
    .from('your_table')
    .select('date, value')
    .order('date')

  // 轉換成 Chart.js 格式
  const chartData = {
    labels: rows?.map((r) => r.date) ?? [],
    datasets: [{
      label: '指標',
      data: rows?.map((r) => r.value) ?? [],
      borderColor: 'rgb(59, 130, 246)',
      fill: false,
    }],
  }

  return (
    <div>
      <ChartCard title="真實資料趨勢" type="line" data={chartData} />
    </div>
  )
}
```

> ⚠️ 注意：如果頁面需要 `'use client'`（因為用了 Sidebar 等互動元件），
> 就改用 API Route 取得資料：建立 `app/api/data/route.ts`，前端用 `useEffect` + `fetch` 呼叫。

### 腦力激盪

> **思考一下**：你的專題資料適合哪種圖表？
> - 時間序列 → `line`
> - 分類比較 → `bar`
> - 佔比 → `pie` 或 `doughnut`
> - 如果有兩個以上的指標，考慮用 `bar` 搭配多個 datasets

---

## B3｜Mermaid：讓 AI 畫給你看

### 靜態 Mermaid 圖（儀表板固定顯示）

```tsx
// app/page.tsx

const MY_ARCHITECTURE = `
graph LR
  A[使用者] --> B[Dashboard]
  B --> C[MCP Server]
  C --> D[你的 RAG]
  D --> E[Qdrant]
  D --> F[Supabase]
`

// 在 JSX 中
<div className="card bg-base-100 shadow">
  <div className="card-body">
    <h2 className="card-title text-base">系統架構</h2>
    <MermaidBlock chart={MY_ARCHITECTURE} />
  </div>
</div>
```

### 讓 AI 動態產生 Mermaid

當 AI 側欄需要解釋流程時，你可以在 system prompt 中要求 AI 用 Mermaid 回答：

```typescript
// app/api/chat/route.ts

const systemPrompt = `你是一個資料科學助理。
...
如果使用者問到流程、架構或步驟，請用以下格式回答：

\`\`\`mermaid
graph LR
  ... 你的圖 ...
\`\`\`

Sidebar 會自動渲染它。`
```

AI 回傳的 ` ```mermaid ` 區塊，Sidebar 會自動偵測並渲染，不需要額外處理。

### Mermaid 常用語法速查

```
# 流程圖（從左到右）
graph LR
  A[方塊] --> B[方塊]
  A --> C((圓形))
  B --> D{菱形判斷}

# 時序圖
sequenceDiagram
  使用者->>AI: 提問
  AI->>MCP: 搜尋知識庫
  MCP-->>AI: 回傳結果
  AI-->>使用者: 回答

# 甘特圖（專題時程）
gantt
  title 專題時程
  section 第一階段
  資料收集: 2025-03-01, 7d
  RAG 建立: 7d
```

---

## B4｜AI 側欄：設計你的預設問題

這是本模組的核心作業。**預設問題的品質決定了作品的品質。**

### 什麼是好的預設問題？

| 好的問題 | 壞的問題 |
|---------|---------|
| 「趨勢圖中，哪個月份出現最大跌幅？原因可能是什麼？」 | 「分析資料」（太廣泛） |
| 「A 類和 B 類的差距，對我們的策略有什麼影響？」 | 「告訴我所有事情」（無法收斂） |
| 「根據目前趨勢，下個月的預測值大約是多少？」 | 「預測未來」（沒有時間範圍） |
| 「用流程圖說明資料從收集到呈現的完整流程」 | 「畫圖」（不知道畫什麼） |

**設計原則**：
1. 每個問題都能在儀表板的圖表上找到對應
2. 問題要有明確的回答方向（不要開放到無邊際）
3. 至少一個問題會讓 AI 回傳 Mermaid 圖表

### 修改預設問題

```typescript
// lib/preset-questions.ts

export const PRESET_QUESTIONS = [
  // 對應「趨勢折線圖」
  '請解釋最近三個月的趨勢變化，並找出可能的原因',

  // 對應「類別長條圖」
  '哪個類別表現最好？哪個需要關注？',

  // 觸發 Mermaid 回應
  '請用流程圖說明這份資料的處理流程',

  // 預測性問題
  '根據目前趨勢，下個月的預測為何？',

  // 異常偵測
  '資料中有沒有值得注意的異常點？',
]
```

### 修改 System Prompt

```typescript
// app/api/chat/route.ts

const systemPrompt = `你是一個專門分析「[你的資料主題]」的 AI 助理。

儀表板目前顯示：
- 折線圖：[說明這張圖在看什麼指標]
- 長條圖：[說明這張圖在看什麼分類]
- 架構圖：[說明這個 Mermaid 圖的用途]

請根據以下知識庫內容回答問題，如果問到流程，用 \`\`\`mermaid 格式回答。

知識庫內容：
${context}

語氣：專業但平易近人，用繁體中文。`
```

---

## B5｜部署：整合進 _project-fullstack

當你的儀表板在本機測試完畢，可以整合進完整的 docker 環境。

### 步驟一：複製前端到 _project-fullstack

```bash
cp -r ~/my-project/frontend-dev/ _project-fullstack/frontend/
```

### 步驟二：解鎖 docker-compose.yml 的 frontend service

```yaml
# _project-fullstack/docker-compose.yml
# 取消 frontend service 的註解：

frontend:
  build: ./frontend
  container_name: ds-frontend
  restart: unless-stopped
  environment:
    MCP_SERVER_URL: http://mcp-server:3000
    OPENAI_API_KEY: ${OPENAI_API_KEY}
  depends_on:
    - mcp-server
```

### 步驟三：切換 nginx 路由

```nginx
# _project-fullstack/nginx/default.conf
# 將 location / 的靜態檔設定，替換為 Next.js proxy：

location / {
    proxy_pass http://frontend:4000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

### 步驟四：啟動

```bash
cd _project-fullstack
docker compose up -d --build

# 確認所有服務都起來了
docker compose ps
```

訪問 `http://localhost:8080` 就能看到你的儀表板。

---

## 重點回顧

```
╔══════════════════════════════════════════════╗
║  Module B 核心概念                            ║
╠══════════════════════════════════════════════╣
║  • ChartCard：傳 data 物件 → 自動渲染圖表      ║
║  • MermaidBlock：傳字串 → 自動渲染流程圖        ║
║  • Sidebar：SSE 串流 + 自動偵測 mermaid 區塊   ║
║  • 預設問題 → 收斂使用者行為，提升展示品質      ║
║  • 整合：frontend service + nginx proxy       ║
╚══════════════════════════════════════════════╝
```

---

## 課後練習

**⭐ 基本（必要）**
1. 把 `page.tsx` 中的範例資料換成你的專題資料
2. 修改 `preset-questions.ts`，設計 5 個能對應你的圖表的問題
3. 修改 `route.ts` 的 system prompt，符合你的專題主題

**⭐⭐ 進階**
4. 讓 Chart.js 圖表的資料來自 Supabase 查詢（而不是寫死在 `page.tsx`）
5. 讓 AI 能根據問題動態回傳 Mermaid 流程圖

**⭐⭐⭐ 挑戰**
6. 新增第三張圖表（例如：散點圖 scatter，需要自己查 Chart.js 文件整合）
7. 完成 docker-compose 整合，讓整個作品在 `http://localhost:8080` 可存取

---

## 常見問題

**Q：`npm install` 完但 `npm run dev` 報錯怎麼辦？**
A：確認 Node.js 版本 ≥ 20（`node -v`），並確認 `.env.local` 存在且有正確的 `OPENAI_API_KEY`。

**Q：AI 側欄沒有回應？**
A：打開瀏覽器 DevTools → Network，看 `/api/chat` 的請求是否成功。
常見原因：`OPENAI_API_KEY` 未填或格式錯誤。

**Q：MCP Server 沒有連上，AI 還能回答嗎？**
A：可以。`mcp-client.ts` 連線失敗時會 silent fail，AI 仍會用自己的知識回答，只是沒有你的知識庫內容。

**Q：Mermaid 圖表沒有渲染出來？**
A：Mermaid 語法有嚴格格式要求。打開 [mermaid.live](https://mermaid.live) 先測試你的語法。

**Q：`page.tsx` 同時用 Server Component（取 Supabase 資料）和 Client Component（Sidebar）？**
A：把 Supabase 取資料的部分抽到 `app/api/data/route.ts`，前端用 `useEffect` + `fetch('/api/data')` 取得。
或者，把 `page.tsx` 拆成兩個：Server Component 取資料 → 傳 props 給 Client Component。

---

> 下一步：完成作品後，參考 Module A 確認 MCP Server 工具定義完整，再執行 docker-compose 整合。
