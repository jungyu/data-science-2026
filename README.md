# Data Science & AI Agent Learning (2026)

本專案是一套給 **資管系學生** 與 **AI/資料科學實作者** 的整合型學習系統。  
重點不是只學模型，而是建立「**資料能力 + AI 工程 + 治理能力**」三位一體的實戰能力。

---

## 專案定位

這個 repo 以「Project-First」為核心，將學習分成三層：

1. **知識層**：系統化教材（Pandas、scikit-learn、AI架構師、AI Agent協作、Altair）
2. **實作層**：可運行專案（RAG、預測專案、自動化測試）
3. **治理層**：AI Agent governance（Constitution、Gates、HITL、Audit）

你可以把它理解成一個「可直接落地到企業場景」的資管 AI/DS 訓練基地。

### 系統架構總覽

```text
User
 ↓
AI Agent (Planner)
 ↓
MCP Server (Tool Contracts)
 ├── RAG Service
 ├── KPI Service
 ├── Ticket Service
 └── Automation Trigger
 ↓
Data Layer (DB / KB / Logs)
```

---

## AI 協作架構師能力階梯

| Level | 能力 | 對應教材 |
|-------|------|----------|
| 1 | 能使用 AI | `docs/pandas`、`docs/altair` |
| 2 | 能設計 RAG | `project-first`、`docs/scikit-learn` |
| 3 | 能設計 Tool Contract | `docs/architect`、`docs/ai-agent` |
| 4 | 能設計治理與觀測 | `agent-init`、`docs/architect` |
| 5 | 能設計可演進系統 | 全課程整合 + 作品集 |

---

## 你會學到什麼

- **資料科學基礎到進階**：資料清理、EDA、特徵工程、交叉驗證、模型比較
- **機器學習工程化**：Pipeline 思維、模型評估、可解釋性、模型治理
- **AI 架構師思維**：系統架構藍圖、RAG 架構設計、MCP 治理、風險護欄、可觀測性
- **AI Agent 協作**：多 Agent 協作模式、任務分解與委派、工具整合、品質門檻
- **資料視覺化 Altair**：宣告式視覺化、互動圖表、多圖組合、進階資料探索
- **RAG 與 AI Agent 系統**：Embedding、Chunking、Retrieval Gate、MCP、Skills
- **企業治理能力**：權限隔離、品質門檻、審核機制、可追溯操作紀錄
- **可展示作品集**：從教材練習一路累積到可發表/可面試展示的專題

## 本課程不教什麼

- Prompt engineering 技巧炫技
- 單純模型調參（hyperparameter tuning only）
- 只做 demo 的 chatbot
- 黑箱式 AI 使用

> 我們的重點是：**架構設計、工程落地、治理機制**——能進企業、能上線、能被審核的 AI 系統。

---

## LangGraph 核心的不可取代性

LangGraph 的核心價值，主要體現在三個維度：**確定性的狀態圖與 Time-Travel、人機協同（Human-in-the-Loop）、以及背靠 LangChain / LangSmith 生態系的可觀測性**。

### 一、確定性的狀態圖與時鐘級的狀態持久化（Time-Travel）

許多新工具追求「非同步事件驅動」，但事件驅動最大的代價是非確定性（Non-determinism）與偵錯地獄。LangGraph 選擇了相反的路徑：它本質上是一個強型別、集中式的狀態機，概念上接近 Redux 或 Git。

- **記憶體與外部儲存的抽象（Saver / Checkpointer）**：LangGraph 原生支援在圖的每一個節點執行完畢後自動進行快照。這意味著如果 RAG 流程在第 4 步因為網路超時或 LLM 速率限制而崩潰，系統可以從第 4 步無縫重啟，不需要重新執行前 3 步昂貴的檢索與生成。
- **時間旅行偵錯（Time-Travel Debugging）**：因為 LangGraph 基於狀態快照，你可以將系統狀態回滾到 10 分鐘前的特定節點，修改當時的變數，再沿著另一條分支重新執行。在複雜 RAG 的開發與測試階段，這種除錯效率遠高於一般事件驅動工具。

### 二、業界成熟的人機協同（Human-in-the-Loop）設計

在企業級 RAG 應用中，我們不可能完全信任 AI 的動態路由或關鍵報告生成。在特定節點，例如 AI 決定刪除資料庫、或生成高風險財務建議時，系統必須讓人確認後才能繼續。

LangGraph 在架構上將這個需求視為一等公民（First-class citizen）：

- **原生中斷機制（Interrupts）**：你可以指定圖在某個特定邊（Edge）或節點（Node）前自動暫停（Pause）。此時圖會將當前所有狀態序列化存入資料庫，並釋放計算資源。
- **狀態編輯與恢復（State Mutation）**：當系統暫停並等待人類審核時，人類不只能點擊「同意 / 拒絕」，也能直接修改當前 State，例如手動修正錯誤的檢索關鍵字，或改寫一段生成內容。按下繼續後，AI 會帶著人類修改後的狀態繼續往下執行。

其他工具若要實作這種「持久化、跨 Web 請求、可中途修改狀態」的人類介入，通常需要工程師手動撰寫大量外部資料庫讀寫與 API 鎖定邏輯；LangGraph 則可以在定義圖時透過 `interrupt_before=["node_name"]` 這類機制直接表達。

### 三、背靠 LangChain 生態系與 LangSmith 的觀測性（Observability）

工具的強大不只看框架本身，也要看它的工具鏈（Tooling）。

- **LangSmith 的無縫整合**：任何 LangGraph 的圖，只要設定好環境變數，就能在 LangSmith 網頁上自動渲染出可視化的動態圖。
- **高密度執行軌跡**：你可以即時看到 Token 在哪個節點流動、哪一條條件邊（Conditional Edge）被觸發、哪一次檢索花了多少毫秒，甚至追蹤每一步的 State 變更軌跡（Diff）。

在生產環境（Production）中，這代表團隊擁有高密度的可觀測性與異常監控能力。相較之下，DSPy、AutoGen 等工具在生產環境監控與可視化除錯體驗上，仍難以取代 LangSmith 生態的整合優勢。

### 總結：LangGraph 的核心生態位

> 事件驅動（LlamaIndex / AutoGen）追求的是靈活性與天花板；狀態機（LangGraph）追求的是控制力與底線。

LangGraph 不可取代的優點，可以用一句話概括：**它是目前少數能將「極度不確定」的 LLM 決策流程，放進「極度確定、可控、可觀測」的傳統軟體工程框架中的工具。**

如果你的 RAG 系統需要：

- 確保商務邏輯的邊界絕不被逾越（Determinism）
- 在關鍵時刻讓人類介入審查與修改數據（HITL）
- 具備嚴格的錯誤恢復與生產環境可視化監控

那麼，LangGraph 目前在工程落地上的綜合優勢依然具有高度不可取代性。

---

## 專案地圖

```text
.
├── _project-fullstack/  # 期末專題基礎設施模板（nginx + crawler + qdrant + mcp-server）
├── _project-nextjs/     # Next.js + DaisyUI Dashboard 起始模板（Chart.js + Mermaid + AI 側欄）
├── agent-init/          # AI Agent 治理初始化範本（可移植）
├── books/               # 核心手冊（資管完全手冊、Skills 手冊）
├── docs/                # 課程教材
│   ├── RAG/             # RAG 完全實戰課程（ch01–ch06 + Module A/B）
│   ├── pandas/          # pandas 資料分析
│   ├── scikit-learn/    # 機器學習入門
│   ├── ai-agent/        # AI Agent 設計與治理
│   ├── altair/          # 資料視覺化
│   └── ...              # 其他教材
├── project-first/       # 企業 RAG × MCP × Skills 專案程式碼
├── project-forcasting/  # 預測任務專案（Forecasting）
├── project-playwright/  # 自動化測試與代理工作流專案
├── pdf/                 # 補充 PDF 資源
└── README.md
```

---

## 快速入口

### 期末專題（起點在這裡）
- [RAG 完全實戰課程](docs/RAG/README.md) — ch01–ch06 + Module A/B，從 RAG 到可展示作品
- [MCP Server 完全實戰課程](docs/MCP-Server/README.md) — 5 章，Tools / Resources / Prompts / 安全 / 部署
- [_project-fullstack 基礎設施模板](_project-fullstack/README.md) — Docker：nginx + qdrant + MCP Server
- [_project-nextjs Dashboard 模板](_project-nextjs/README.md) — Next.js + DaisyUI + Chart.js + AI 側欄

### 課程教材
- [資訊管理系完全學習手冊](docs/IM-Complete-Lesson-Handbook.md)
- [Agent Skills 完全手冊](docs/Skills-Handbook.md)
- [Pandas 教材](docs/pandas/README.md)
- [scikit-learn 教材](docs/scikit-learn/README.md)
- [AI 架構師教材](docs/architect/00-philosophy.md)
- [AI Agent 協作教材](docs/ai-agent/README.md)
- [資料視覺化 Altair 教材](docs/altair/README.md)
- [project-first：企業 RAG 實作](docs/project-first/README.md)
- [agent-init：治理框架範本](agent-init/README.md)
- [project-forcasting](project-forcasting/README.md)
- [project-playwright](project-playwright/README.md)

---

## 建議學習路徑（資管 AI + 資料科學）

1. **先建資料分析基本功**
   先讀 `docs/pandas`，建立資料清理與分析能力。

2. **補上 ML 方法論與評估能力**
   讀 `docs/scikit-learn`，特別是交叉驗證、模型比較與治理章節。

3. **建立 AI 架構師思維**
   讀 `docs/architect`，學會系統架構設計、RAG 架構、MCP 治理與風險護欄。

4. **學習資料視覺化**
   讀 `docs/altair`，掌握宣告式視覺化與互動圖表技術。

5. **RAG 完全實戰課程**（核心期末專題路徑）
   依序完成 `docs/RAG/` 的 ch01–ch06，建立 RAG Pipeline 並以 Ragas 評估品質。

6. **整合上線：MCP Server + Dashboard**
   完成 Module A（MCP Server）讓 Claude Desktop 可呼叫你的 RAG；
   完成 Module B（Dashboard）用 `_project-nextjs/` 模板建立視覺化介面；
   透過 `_project-fullstack/` 的 docker-compose 整合所有服務，交出期末作品。

7. **進入 AI Agent 協作**
   讀 `docs/ai-agent` 了解多 Agent 協作模式，再從 `project-first/index.md` 完成整套實作。

8. **導入治理框架**
   參考 `agent-init/`，把 Constitution、HITL、Audit 機制套進自己的專案。

9. **延伸到專題與作品集**
   使用 `project-forcasting/`、`project-playwright/` 擴充實戰範圍，形成完整 portfolio。

---

## 適合對象

- 資訊管理 / 軟體工程相關科系學生
- 想轉職資料分析、ML 工程、AI 應用工程的人
- 需要導入 AI Agent 但同時重視治理與合規的團隊
- 想把課堂專題升級為可發表 mini research 的學習者

---

## 預期成果

完成這個 repo 的核心路徑後，你應能做到：

- 獨立完成一個可運行的資料科學專案（從資料到模型與評估）
- 設計並實作一個具治理機制的企業 RAG 系統
- 使用 MCP + Skills 建立可操作、可審核的 AI Agent 工作流
- 產出可重現、可展示、可持續迭代的 GitHub 作品集

---

## 授權

本專案採用 [MIT License](LICENSE)。

---

## 作者

- Aaron Yu
- Email: <jungyuyu@gmail.com>
