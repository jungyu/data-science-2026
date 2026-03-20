# 資訊管理系完全學習手冊
### 理論 × 實作 × 職涯 — Project-First 整合課程

---

> **給學習者的話**
>
> 這本手冊不是課本，是你的**工作台**。每個單元都有明確的目標、課堂流程、可執行的程式碼、作業規格與評分規準。
>
> 貫穿全課的核心節奏只有一句話：
> **概念（Why）→ 示範（How）→ 練習（Do）→ 反思（Improve）→ 提交（Ship）**
>
> 每次產出都進 GitHub。四年後，你的倉庫就是你的履歷。

---

## 課程大綱

完整教案詳見 👉 [00-Information-Management-Syllabus.md](00-Information-Management-Syllabus.md)

| Unit | 主題 | 核心技能 |
|------|------|---------|
| 0 | 課程設定與學習契約 | 環境建置、學習目標 |
| 1 | 計算思維與效能直覺 | 分解、Big-O、Benchmark |
| 2 | 資料結構選型與小系統 | list / dict / set、圖書館系統 |
| 3 | 系統常識 — OS、Thread、HTTP | Process、HTTP 狀態碼、API 呼叫 |
| 4 | Python 進階與程式碼品質 | Comprehension、Generator、Decorator、OOP |
| 5 | Git 與作品集系統化 | Git 工作流、Commit 規範、Portfolio |
| 6 | 系統設計入門 | 單體 vs 微服務、Cache、短網址設計 |
| 7 | 關聯式資料庫與 SQL | ERD、正規化、JOIN、Window Functions |
| 8 | 資料分析與視覺化 | pandas EDA、RFM 分群、儀表板 |
| 9 | NoSQL 選型與快取思維 | Redis、MongoDB、Session 管理 |
| 10 | 系統分析與資安基礎 | UML、REST API、SQL Injection、JWT |
| 11 | 敏捷開發與專案管理 | Scrum、User Story、GitHub Issues |
| 12 | AI 整合與職涯路線 | ML Pipeline、AI API、職涯路線圖 |

---

## 📚 課程配套教材索引

> 以下教材已整理於 `docs/` 目錄，依學習階段編號。建議搭配各 Unit 對應閱讀。

### 獨立手冊

| 編號 | 教材 | 對應 Unit | 說明 |
|------|------|-----------|------|
| 01 | [WSL 環境手冊](01-Environment-WSL-Manual.md) | Unit 0 | Windows 子系統 Linux 開發環境建置 |
| 02 | [Git 版本控制手冊](02-Git-Version-Control-Manual.md) | Unit 5 | Git 完整操作指南 |
| 03 | [Markdown & Frontmatter](03-Markdown-Frontmatter-Handbook.md) | Unit 0 | 文檔寫作規範與 YAML 前導區 |
| 04 | [Chrome DevTools](04-Chrome-DevTools-Manual.md) | Unit 3 | 瀏覽器開發者工具偵錯指南 |
| 05 | [正規表達式](05-Regex-Text-Processing-Handbook.md) | Unit 4 | 文字處理與模式匹配 |
| 06 | [XPath 導航](06-XPath-Web-Navigation-Handbook.md) | Unit 3 | 網頁元素定位與資料擷取 |
| 07 | [CSV / JSON 格式](07-CSV-JSON-Data-Formats-Manual.md) | Unit 3 | 資料交換格式完整指南 |
| 08 | [資料收集策略](08-Data-Collection-Strategy-Handbook.md) | Unit 8 | 資料收集方法論與原則 |
| 09 | [資料資源總覽](09-Data-Resource-Inventory-Handbook.md) | Unit 8 | 台灣與國際開放資料來源清單 |
| 10 | [Playwright 自動化](10-Playwright-Web-Automation-Handbook.md) | Unit 3 | 瀏覽器自動化爬蟲與反偵測 |
| 12 | [AI Agent Skills](12-AI-Agent-Skills-Handbook.md) | Unit 12 | AI Agent 技能系統設計 |
| 13 | [Supabase vs PostgreSQL](13-Database-Supabase-vs-PostgreSQL.md) | Unit 7 | 資料庫平台選型比較 |
| 14 | [PostgreSQL 核心架構](14-PostgreSQL-Kernel-Architecture.md) | Unit 7 | PostgreSQL 底層架構深度解析 |
| 15 | [AI Agent CLI 趨勢](15-AI-Agent-CLI-Trends-Intro.md) | Unit 12 | AI Agent 與 CLI 開發工具趨勢 |

### 系列教材（子目錄）

| 目錄 | 主題 | 對應 Unit | 章節數 |
|------|------|-----------|--------|
| [`pandas/`](pandas/) | pandas 資料分析完整課程 | Unit 8 | 11 章 + 附錄 |
| [`altair/`](altair/) | Altair 視覺化與 Vega-Lite | Unit 8 | 10+ 章 |
| [`supabase/`](supabase/) | Supabase 雲端資料庫實戰 | Unit 7 | 多章 + 作業 |
| [`scikit-learn/`](scikit-learn/) | scikit-learn 機器學習入門 | Unit 12 | 多章 + 速查表 |
| [`ai-agent/`](ai-agent/) | AI Agent 設計與治理 | Unit 12 | 13 章 + 附錄 |
| [`RAG/`](RAG/) | RAG 完全實戰課程（含 MCP Server + Dashboard） | Unit 12 | 6 章 + Module A/B |
| [`MCP-Server/`](MCP-Server/) | MCP Server 完全實戰課程（Tools / Resources / Prompts / 部署） | Unit 12 | 5 章 |
| [`methodology/`](methodology/) | 資料科學研究方法論 | Unit 8 | 按週進度 |
| [`architect/`](architect/) | 系統架構師思維 | Unit 6 | 多章 |
| [`project-first/`](project-first/) | Project-First 教學法 | Unit 0 | 多章 |
| [`homework/`](homework/) | 作業範本與規格 | 全課程 | 依需要 |

---

## 主線專案的演進

```
Lesson 4   →  圖書館管理系統（資料結構）
Lesson 17  →  短網址服務（系統設計）
Lesson 21  →  電商 DB 模型（資料庫）
Lesson 24  →  銷售分析報告（資料分析）
Lesson 29  →  資安強化版登入（資安）
Lesson 35  →  期末 Demo Day（全整合）
```

---

## 評量設計

| 項目 | 比例 |
|------|------|
| 平時練習提交（小作業） | 40% |
| 單元專案（中作業） | 30% |
| 期末整合專案 | 25% |
| 學習反思與職涯路線圖 | 5% |

---

*本手冊版本：2026 年版*
*建議每學期結束後 review 一次，更新作品集連結與學習反思*
