# Data Science & AI Agent Learning (2026)

這是一個專注於 **資料科學 (Data Science)** 與 **AI 代理人 (AI Agent)** 的整合式學習資源庫。本專案包含全方位的教學手冊、實作導向的課程設計，以及針對企業級 AI 技能（Skills）的深度指南。

---

## 📌 快速導覽

- [核心手冊：資訊管理系完全學習手冊](books/IM-Complete-Lesson-Handbook.md)
- [核心手冊：Agent Skills 完全手冊](books/Skills-Handbook.md)
- [治理範本：agent-init](agent-init/README.md)
- [實作教案：project-first](project-first/index.md)

---

## 🎯 適合誰使用

- **資訊管理 / 軟體工程學生**：建立從理論到實作的完整能力地圖。
- **轉職或自學開發者**：用 Project-First 路徑累積可展示的作品集。
- **AI Agent 導入團隊**：快速導入治理框架（Constitution、Gates、HITL）。
- **技術主管 / PM**：建立可追溯、可維護的企業知識庫與 RAG 流程。

---

## 📚 核心手冊

本專案圍繞兩本核心。

### 1. [資訊管理系完全學習手冊](books/IM-Complete-Lesson-Handbook.md)
**理論 × 實作 × 職涯 — Project-First 整合課程**
這本手冊專為資管系學生與自學者設計，採用「概念 → 示範 → 練習 → 反思 → 提交」的節奏。
- **Unit 0-3**: 計算思維、資料結構與系統常識（OS/HTTP）。
- **Unit 4-7**: Python 進階、Git 版控、系統設計與 SQL 資料庫。
- **Unit 8-12**: 資料分析、NoSQL、資安基礎、敏捷開發與 AI 整合。

### 2. [Agent Skills 完全手冊](books/Skills-Handbook.md)
**從零到精通：讓 AI Agent 真正學會做事**
這是一份針對 AI Agent（如 Claude, Gemini, GPT）專業技能開發的實戰指南。
- **核心理念**: Skills = 組織好的檔案集合，打包了可組合的程序性知識。
- **三角架構**: Agent (調度) + MCP (連接) + Skills (知識)。
- **Scripts as Tools**: 告別模糊的 Function Calling，採用「程式碼即文件」的開發模式。

---

## 📁 目錄結構

```text
.
├── LICENSE          # 授權資訊 (MIT)
├── README.md        # 本說明文件
├── agent-init/      # AI Agent 治理初始化範本（可複用到其他專案）
├── books/           # 核心學習手冊
│   ├── IM-Complete-Lesson-Handbook.md
│   └── Skills-Handbook.md
├── project-first/   # 企業知識 RAG 系統建構教案（OpenAI API × MCP × Skills）
└── pdf/             # 深度學習資源
    └── AI_Agent_Skills_Mastery.pdf
```

---

## 🚀 如何開始

1. **基礎建立**: 從 [IM 完全學習手冊 Unit 0](books/IM-Complete-Lesson-Handbook.md) 開始，建立計算思維與基礎開發環境。
2. **AI 賦能**: 閱讀 [Skills 完全手冊](books/Skills-Handbook.md)，學習如何把專業知識轉化為 AI Agent 可執行的 Skills。
3. **治理初始化**: 參考 [agent-init/README.md](agent-init/README.md)，把 Constitution、SDD-BDD、Gates 導入你的專案。
4. **Project-First 實作**: 先跑 [00-setup.md](project-first/00-setup.md)，再依 [project-first/index.md](project-first/index.md) 章節地圖完成企業級 RAG 範例。
5. **實戰驗證**: 每個單元都要求將成果提交至 GitHub，四年的累積將成為你最強大的作品集。

---

## 🗓️ 建議 7 天學習節奏

1. **Day 1**: 閱讀 IM 手冊前段（Unit 0-3），完成基礎環境建置。
2. **Day 2**: 閱讀 Skills 手冊核心概念，理解 Agent/MCP/Skills 三角架構。
3. **Day 3**: 導入 `agent-init/`，完成最小治理設定（Constitution + 基本規則）。
4. **Day 4**: 完成 `project-first/00-setup.md`，跑通測試與本地依賴。
5. **Day 5**: 依序閱讀 `project-first/01` 到 `05`，建立查詢與治理骨架。
6. **Day 6**: 依序閱讀 `project-first/06` 到 `09`，補齊 embedding、安全與 MCP 流程。
7. **Day 7**: 完成 `project-first/10`，整理成果並提交到 GitHub。

---

## 🧭 資管 AI/DS 核心能力矩陣

完成本課程後，學習者將在四大維度建立可量化的能力基礎。每項能力對應具體的職涯任務與可驗證的產出。

| 維度 | 核心能力 | 對應單元 | 可勝任的職場任務 |
|------|----------|----------|-----------------|
| **技術 Technical** | Python 資料處理與自動化 | Unit 4-5 | 資料工程師：ETL pipeline 建置與維護 |
| | SQL / NoSQL 資料建模 | Unit 7, 9 | 資料分析師：商業報表查詢與資料倉儲設計 |
| | ML 模型訓練與評估 | Unit 8, 12 | ML 工程師：模型選擇、交叉驗證、A/B 測試 |
| | Embedding / RAG 系統 | project-first 06-09 | AI 應用工程師：企業知識檢索系統開發 |
| **治理 Governance** | AI Agent 治理框架 | agent-init | AI PM：Constitution 制定與 HITL 審核流程 |
| | 資料品質與血緣追蹤 | project-first 03-05 | 資料治理專員：Lineage tracking、Schema 管理 |
| | 安全與合規 | Unit 10, project-first 08 | 資安分析師：OWASP 基礎防護、權限稽核 |
| **商業 Business** | 問題框定與假說驅動分析 | Unit 8 | 商業分析師：將業務痛點轉為可驗證的數據問題 |
| | 成本效益與 ROI 評估 | Skills 手冊 | 技術 PM：AI 專案可行性評估與資源規劃 |
| | 敏捷開發與迭代交付 | Unit 11 | Scrum Master：Sprint 規劃與持續交付流程 |
| **溝通 Communication** | 技術文件撰寫 | 全課程 GitHub 提交 | 技術寫手：API 文件、系統架構文件 |
| | 資料敘事與視覺化 | Unit 8 | 數據分析師：Dashboard 設計與管理層簡報 |
| | 跨部門協作 | Unit 11-12 | 產品經理：需求訪談、技術方案溝通 |

> **能力等級參考**：L1 知道概念 → L2 能跟著做 → L3 能獨立完成 → L4 能教別人。完成全課程預期達到 L3，持續實作半年可達 L4。

---

## 📐 作品集評分規準 (Portfolio Rubric)

所有課程作業與專題均依以下五大構面評分，滿分各 20 分，總分 100 分。

| 構面 | 優秀 (17-20) | 良好 (13-16) | 待改進 (9-12) | 不足 (0-8) |
|------|-------------|-------------|--------------|-----------|
| **可重現性 Reproducibility** | `git clone` → 一鍵可跑；含 `requirements.txt` / `pyproject.toml`、seed 固定、README 清楚 | 需少量手動設定即可跑通；文件大致完整 | 缺少依賴說明或環境變數；需口頭補充才能重現 | 無法在他人機器上重現 |
| **資料品質 Data Quality** | 有 schema 驗證、缺值處理策略明確記錄、資料來源與授權標註完整 | 基本清洗完成；來源有註明但未驗證 schema | 原始資料未清洗或清洗邏輯不透明 | 資料來源不明或含明顯錯誤未處理 |
| **實驗嚴謹度 Rigor** | 有對照組、交叉驗證、效果量報告、統計顯著性檢定 | 有基本 train/test split 與指標報告 | 僅報告單一指標，無驗證策略 | 無評估或僅有主觀判斷 |
| **商業價值 Business Value** | 明確定義商業問題、量化預期效益、含成本分析與可行性評估 | 有業務背景說明與基本效益推估 | 技術導向，商業連結薄弱 | 純技術練習，無商業脈絡 |
| **程式品質 Code Quality** | 模組化設計、型別提示、docstring、CI 通過、lint 零警告 | 結構合理、命名清晰、有基本註解 | 能跑但結構混亂、重複程式碼多 | 無法執行或有嚴重安全漏洞 |

> **評分流程**：自評 → 同儕互評 → 助教/教師終評。每次提交須附「自評表」說明各構面得分理由。

---

## 🔬 研究路徑：從課堂專題到可發表的 Mini Research

提供一條從課程作業逐步升級為可投稿研究的路徑，幫助有志深造或發表的學習者。

### Stage 1：課堂專題 (Week 1-7)
- **產出**：完成 project-first 全教案，產生一個可運作的 RAG 系統
- **研究素養**：學會文獻引用格式、學會描述「方法」與「結果」

### Stage 2：延伸實驗 (Week 8-12)
- **動作**：針對 Stage 1 的系統提出一個可驗證的改進假說
  - 例：「使用 HyDE 重寫查詢可提升 Top-5 Recall 至少 10%」
- **產出**：實驗報告（含假說、實驗設計、對照組、統計檢定、結果討論）
- **格式**：遵循 IMRaD 結構（Introduction, Methods, Results, and Discussion）

### Stage 3：Mini Paper 撰寫 (Week 13-16)
- **動作**：將 Stage 2 報告擴充為 4-6 頁短論文
- **必備要素**：
  - Related Work（至少引用 5 篇近兩年論文）
  - Ablation Study（拆解各元件的貢獻度）
  - Reproducibility Checklist（資料集、程式碼、超參數全公開）
- **投稿目標**（依難度排列）：
  - 校內：資管學會年會、畢業專題競賽
  - 國內：TANET、ICIM、資管學報
  - 國際：Workshop paper（ACL/EMNLP/AAAI Student Workshop）

### Stage 4：開源與社群回饋 (持續)
- 將程式碼與資料集發布為 GitHub 開源專案
- 撰寫技術部落格（Medium / HackMD）擴大影響力
- 向上游套件提交 PR 或 Issue，建立開源社群貢獻紀錄

```
課堂作業 → 延伸假說 → 實驗驗證 → Mini Paper → 投稿/開源
   L2          L3          L3-L4        L4          L4+
```

> **指導教師角色**：Stage 1-2 以助教帶領為主；Stage 3 起需指導教師參與研究方向與論文修訂。

---

## 🛡️ 授權資訊

本專案採用 [MIT License](LICENSE)。

---

## 👤 作者

- Aaron Yu
- Email: <jungyuyu@gmail.com>
- Contact: <aaron@makiot.com>
