# 從 Altair 到產品級視覺化：Spec 驅動的資料呈現

> 一套由淺入深的完整學習手冊 — 從「畫圖」到「描述圖」的思維革命

```
資料分析 (Python)
        ↓
    Altair（撰寫工具）
        ↓
    Vega-Lite Spec（中介表示）
        ↓
    Database（持久化）
        ↓
    API（服務化）
        ↓
    Next.js（渲染層）
        ↓
    Vega Runtime → Browser（互動呈現）
```

---

## 這本手冊教什麼？

這不只是一門「畫圖課」，而是一門 **資料視覺化工程課**。

完成本手冊後，你將掌握三件核心能力：

| 能力 | 說明 |
|------|------|
| **Declarative Thinking** | 從命令式轉向宣告式的思維革命 |
| **IR Architecture** | 理解中介表示（Intermediate Representation）的設計思維 |
| **AI-Operable System Design** | 建構 AI 可操作的系統架構 |

---

## 學習目標

完成本手冊後，你將能夠：

- 使用 Python + Altair 進行資料視覺化分析
- 理解 Declarative Visualization（宣告式視覺化）的核心概念
- 讀懂並修改 Vega-Lite JSON 規格
- 將圖表規格存入資料庫並由 API 提供
- 在 Next.js 前端渲染圖表
- 讓 AI 修改圖表規格

---

## 章節導覽

### 第零章 前導篇

| 章節 | 主題 | 說明 |
|------|------|------|
| [Chapter 00](00-matplotlib-plotly-intro.md) | matplotlib 與 plotly 簡介 | 認識兩大主流繪圖庫，理解它們的優勢與限制 |

### 核心課程（六週）

| 週次 | 章節 | 主題 | 關鍵概念 |
|------|------|------|----------|
| 第 1 週 | [Chapter 01](01-visualization-philosophy.md) | 視覺化思維的革命 | Imperative vs Declarative |
| 第 1-2 週 | [Chapter 02](02-altair-fundamentals.md) | Altair 入門 | Encoding、Mark、基本圖表 |
| 第 2 週 | [Chapter 03](03-chart-composition.md) | 圖表組合與視覺思考 | Layer / Facet / Concat / Selection |
| 第 3 週 | [Chapter 04](04-vegalite-ir.md) | Vega-Lite 是視覺化 IR | JSON Spec、中介表示、可版本化 |
| 第 4 週 | [Chapter 05](05-spec-storage-api.md) | Spec 存儲與 API 化 | Database、FastAPI、Supabase |
| 第 5 週 | [Chapter 06](06-nextjs-rendering.md) | Next.js 渲染圖表 | react-vega、Client Component |
| 第 6 週 | [Chapter 07](07-ai-spec-modification.md) | AI 修改圖表規格 | JSON Patch、Schema 驗證 |

### 總結與實戰

| 章節 | 主題 | 說明 |
|------|------|------|
| [Chapter 08](08-final-project.md) | 期末專案與架構總覽 | 圖表管理系統、完整架構 |
| [Appendix A](appendix-a-test-bank.md) | 測驗題庫 | 選擇題、是非題、短答題、實作題 |

---

## 先備知識

| 領域 | 程度 | 說明 |
|------|------|------|
| Python | 基礎 | 會用 pandas 讀取與處理資料 |
| JSON | 基礎 | 能讀懂 JSON 格式 |
| JavaScript | 入門 | 第 5-6 週需要，React 基本概念 |
| SQL | 入門 | 第 4 週 Database 操作 |
| 命令列 | 基礎 | npm、pip 安裝套件 |

---

## 環境準備

### Python 環境

```bash
pip install altair pandas vega_datasets jupyter
```

### Node.js 環境（第 5 週起）

```bash
npm install react-vega vega vega-lite vega-embed
```

### 推薦工具

- **JupyterLab** — 互動式 Python 開發
- **VS Code** — 編輯器（含 Vega Viewer 擴充）
- **Vega Editor** — 線上 Spec 編輯器 https://vega.github.io/editor/

---

## 學習路線圖

```
Week 1          Week 2          Week 3          Week 4          Week 5          Week 6
  │               │               │               │               │               │
  ▼               ▼               ▼               ▼               ▼               ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ 思維革命 │→│ 圖表組合  │→│ Vega-Lite │→│ Spec 存儲 │→│ 前端渲染  │→│ AI 修改   │
│ Altair   │  │ 視覺思考  │  │    IR     │  │   API 化  │  │  Next.js  │  │   Spec   │
│ 入門     │  │          │  │          │  │          │  │          │  │          │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
     │                                                                      │
     └──────────────────── 不只是畫圖，是工程化 ──────────────────────────────┘
```

---

## 這門課的深層價值

> 你其實在教三件事：
> 1. **Declarative thinking** — 從「怎麼畫」到「畫什麼」
> 2. **IR architecture** — 圖表是一份可操作的規格
> 3. **AI-operable system design** — AI 不畫圖，AI 改規格
>
> 這會讓學生比一般只會用 matplotlib 的人，高一個維度。
