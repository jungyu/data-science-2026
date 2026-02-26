# Data Science & AI Agent Learning (2026)

這是一個專注於 **資料科學 (Data Science)** 與 **AI 代理人 (AI Agent)** 的整合式學習資源庫。本專案包含全方位的教學手冊、實作導向的課程設計，以及針對企業級 AI 技能（Skills）的深度指南。

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

1. **基礎建立**: 從 `books/IM-Complete-Lesson-Handbook.md` 的 Unit 0 開始，建立計算思維與基礎開發環境。
2. **AI 賦能**: 閱讀 `books/Skills-Handbook.md`，學習如何將專業領域知識（如稅務、財報、SOP）轉化為 AI Agent 可使用的 Skills。
3. **治理初始化**: 參考 `agent-init/README.md`，把 AI Agent 治理框架（Constitution、SDD-BDD、Gates）導入你的專案。
4. **Project-First 實作**: 從 `project-first/00-setup.md` 建置環境，再依序閱讀 `project-first/index.md` 的章節地圖完成企業級 RAG 範例。
5. **實戰驗證**: 每個單元都要求將成果提交至 GitHub，四年的累積將成為你最強大的作品集。

---

## 🛡️ 授權資訊

本專案採用 [MIT License](LICENSE)。
