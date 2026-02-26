# Data Science & AI Agent Learning (2026)

本專案是一套給 **資管系學生** 與 **AI/資料科學實作者** 的整合型學習系統。  
重點不是只學模型，而是建立「**資料能力 + AI 工程 + 治理能力**」三位一體的實戰能力。

---

## 專案定位

這個 repo 以「Project-First」為核心，將學習分成三層：

1. **知識層**：系統化教材（Pandas、scikit-learn、AI Agent Skills）
2. **實作層**：可運行專案（RAG、預測專案、自動化測試）
3. **治理層**：AI Agent governance（Constitution、Gates、HITL、Audit）

你可以把它理解成一個「可直接落地到企業場景」的資管 AI/DS 訓練基地。

---

## 你會學到什麼

- **資料科學基礎到進階**：資料清理、EDA、特徵工程、交叉驗證、模型比較
- **機器學習工程化**：Pipeline 思維、模型評估、可解釋性、模型治理
- **RAG 與 AI Agent 系統**：Embedding、Chunking、Retrieval Gate、MCP、Skills
- **企業治理能力**：權限隔離、品質門檻、審核機制、可追溯操作紀錄
- **可展示作品集**：從教材練習一路累積到可發表/可面試展示的專題

---

## 專案地圖

```text
.
├── agent-init/          # AI Agent 治理初始化範本（可移植）
├── books/               # 核心手冊（資管完全手冊、Skills 手冊）
├── docs/                # 課程教材（Pandas / scikit-learn / methodology / supabase）
├── project-first/       # 企業 RAG × MCP × Skills 教案與程式碼
├── project-forcasting/  # 預測任務專案（Forecasting）
├── project-playwright/  # 自動化測試與代理工作流專案
├── pdf/                 # 補充 PDF 資源
└── README.md
```

---

## 快速入口

- [資訊管理系完全學習手冊](docs/IM-Complete-Lesson-Handbook.md)
- [Agent Skills 完全手冊](docs/Skills-Handbook.md)
- [Pandas 教材](docs/pandas/README.md)
- [scikit-learn 教材](docs/scikit-learn/README.md)
- [project-first：企業 RAG 實作](project-first/index.md)
- [agent-init：治理框架範本](agent-init/README.md)
- [project-forcasting](project-forcasting/README.md)
- [project-playwright](project-playwright/README.md)

---

## 建議學習路徑（資管 AI + 資料科學）

1. **先建資料分析基本功**  
   先讀 `docs/pandas`，建立資料清理與分析能力。

2. **補上 ML 方法論與評估能力**  
   讀 `docs/scikit-learn`，特別是交叉驗證、模型比較與治理章節。

3. **進入 AI Agent 與企業級 RAG**  
   從 `project-first/00-setup.md` 啟動，按 `project-first/index.md` 章節完成整套實作。

4. **導入治理框架**  
   參考 `agent-init/`，把 Constitution、HITL、Audit 機制套進自己的專案。

5. **延伸到專題與作品集**  
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
