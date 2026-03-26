# Ch13 — 畢業專案：打造你的 Agent 治理框架

> **「學習的最高境界，是能夠教別人。」**

---

## 🎯 本章學習目標

完成這章，你將能夠：

- [ ] 從零建立一個完整的 Agent 治理框架
- [ ] 將所有學到的知識整合到實際專案中
- [ ] 為團隊設計可擴展的治理系統
- [ ] 持續演化和改進你的框架

---

## 畢業專案概述

### 你要打造什麼？

一個**完整的 Agent 治理框架**，包含以下元件：

```
你的治理框架/
├── CLAUDE.md                # Agent 總指令
├── memory/
│   ├── constitution.md      # 治理憲法（L0）
│   ├── diary.md             # 決策日誌（L1）
│   ├── patterns.md          # 模式記憶
│   └── context.md           # 專案脈絡
├── rules/
│   ├── semantic-deny.md     # 語意禁止（L3）— 含 GEN/DB/SEC/AR/SUPPLY 五大類
│   └── human-review.md      # 人類審查（L2）
├── config/
│   ├── settings.json        # Agent 權限設定
│   ├── token-budget.yaml    # Token 預算
│   └── semgrep-deny.yaml    # Semgrep CI 規則（semantic-deny 自動化）
├── templates/               # 含 YAML frontmatter 供機器驗證
│   ├── spec-template.md     # 規格範本
│   └── task-template.md     # 任務範本
├── scripts/
│   ├── setup-wizard.sh      # 互動式佔位符設定精靈
│   └── setup-agent-links.sh # Symlink 設定
├── evals/                   # Agent 行為評估案例
│   └── cases/               # 驗證 Agent 是否遵守治理規則
└── logs/
    └── README.md            # 日誌格式說明
```

> 💡 **快速開始**：`agent-init/` 目錄已經包含上述所有元件的範本。
> 只要複製到你的專案、跑 `setup-wizard.sh` 填寫佔位符，就能立即啟用。

---

## Step 1：定義你的憲法

### 1.1 識別核心原則

回答以下問題：

```
1. 你的專案最重要的品質是什麼？
   □ 安全性    □ 效能    □ 可維護性
   □ 使用者體驗  □ 可靠性

2. 什麼錯誤是你絕對無法接受的？
   （列出 3-5 個）

3. 你的團隊最常犯的技術錯誤是什麼？
   （列出 3 個）
```

### 1.2 撰寫 constitution.md

```markdown
# 專案憲法 — [你的專案名稱]

> 以下原則不可妥協。

## Principle I: [你的第一原則]
- 規則：[具體規則]
- 理由：[為什麼不可妥協]
- 驗證：[如何檢查]

## Principle II: [你的第二原則]
...

## Principle III: [你的第三原則]
...
```

---

## Step 2：設定紅線規則

### 2.1 語意禁止規則

根據你的專案，從以下模板中選擇或自訂：

```markdown
# 語意禁止規則

## 通用
- [ ] GEN-001: [你的規則]
- [ ] GEN-002: [你的規則]

## 安全
- [ ] SEC-001: [你的規則]
- [ ] SEC-002: [你的規則]

## 架構
- [ ] AR-001: [你的規則]

## 專案特定
- [ ] PRJ-001: [你的專案特有規則]
```

### 2.2 人類審查觸發

```markdown
# 人類審查觸發規則

## L1 — 必須停止
- [ ] [你的 L1 規則]
- [ ] [你的 L1 規則]

## L2 — 應該確認
- [ ] [你的 L2 規則]
- [ ] [你的 L2 規則]

## L3 — 事後通知
- [ ] [你的 L3 規則]
```

---

## Step 3：建立記憶系統

### 3.1 Decision Diary

記錄你專案目前的 3 個關鍵決策：

```markdown
# Decision Diary

## [日期] [決策 1]
Context: ...
Decision: ...
Rationale: ...
Status: active

## [日期] [決策 2]
...

## [日期] [決策 3]
...
```

### 3.2 專案脈絡

```markdown
# 專案脈絡

## 背景
[一段話描述專案]

## 技術選擇
[列出主要技術和選擇原因]

## 團隊
[團隊規模和組成]

## 已知技術債
[列出 3-5 個]
```

---

## Step 4：設定 CLAUDE.md

把所有元件串起來：

```markdown
# CLAUDE.md — [專案名稱]

## 技術堆疊
- Language: [語言]
- Framework: [框架]
- Database: [資料庫]
- Testing: [測試框架]

## 治理參考
- 憲法：memory/constitution.md
- 決策日誌：memory/diary.md
- 禁止規則：rules/semantic-deny.md
- 審查觸發：rules/human-review.md

## 編碼規範
[列出 5-10 條規範]

## Agent 規則
- 修改超過 5 個檔案時先展示計畫
- 做技術決策時先查 diary.md
- 完成任務後執行品質檢查
- 觸發 L1 規則時立即停止

## Git Commit 規範
- AI 輔助的 commit 須附 trailer：AI-Assisted-By: claude-code
- 觸及核心模組的 AI 輔助 commit 須附 ADR 或 AI-INTENT: 說明
```

---

## Step 5：設定品質管線

### 建立品質檢查（推薦：使用 check-finish.sh）

```bash
# 自動偵測技術棧，執行 lint + test
.agent/skills/sdd-bdd-workflow/scripts/check-finish.sh

# 或自訂 package.json scripts（Node.js 專案）
# npm run validate
```

> `check-finish.sh` 支援 TypeScript/Python/Rust/Go 自動偵測，
> 不需要為每個技術棧寫不同的指令。

### 在 CLAUDE.md 中加入

```markdown
## 品質檢查
- 每次修改後執行：.agent/skills/sdd-bdd-workflow/scripts/check-finish.sh
- 新增功能必須有測試
- 提交前確認所有檢查通過
```

---

## Step 6：驗證你的框架

### 驗證清單

用以下場景測試你的治理框架：

```
□ 場景 1：讓 Agent 修一個簡單的 Bug
  → 框架不會過度干預嗎？

□ 場景 2：讓 Agent 做一個中等功能
  → 工作流程順暢嗎？品質可接受嗎？

□ 場景 3：讓 Agent 嘗試做一個被禁止的操作
  → 紅線規則有效嗎？

□ 場景 4：讓 Agent 做一個需要審查的操作
  → 人類審查觸發正確嗎？

□ 場景 5：讓 Agent 做一個技術決策
  → 它有查看 diary 嗎？有記錄嗎？
```

### 迭代改善

```
第一輪驗證後，你可能會發現：

- 某些規則太嚴格 → 放寬或降級
- 某些場景沒被覆蓋 → 增加規則
- 某些格式不方便 → 調整模板
- 某些工作流太慢 → 簡化步驟

這是正常的。治理框架是活的，需要持續演化。
```

---

## 學習路徑回顧

```
你走過的路：

Ch01  為什麼需要 Agent？        ← 理解價值
Ch02  Agent 的大腦解剖學        ← 理解原理
Ch03  你的第一個 Agent          ← 動手體驗
Ch04  提示工程                  ← 學會溝通
Ch05  SDD × BDD × TDD         ← 開發流程
Ch06  工具與 MCP               ← 能力擴展
Ch07  治理憲法                  ← 建立原則
Ch08  紅線與護欄                ← 設定邊界
Ch09  記憶與決策                ← 持續成長
Ch10  品質閘門                  ← 確保品質
Ch11  多 Agent 協作             ← 團隊協作
Ch12  走向生產                  ← 實際部署
Ch13  畢業專案                  ← 整合實踐  ★ 你在這裡
```

---

## 持續精進的建議

### 1. 定期回顧

```
每月回顧：
- constitution.md 是否需要更新？
- diary 中有哪些決策需要升級或廢棄？
- patterns.md 有新的有效模式嗎？
- Token 使用效率如何？
```

### 2. 關注社群

```
AI Agent 領域快速發展，持續關注：
- 新的 Agent 能力和工具
- 社群的最佳實踐
- 安全和治理的新方法
- 新的 MCP 伺服器和整合
```

### 3. 分享經驗

```
你的治理框架可以：
- 分享給團隊的其他成員
- 開源給社群參考
- 在技術文章中分享經驗
- 在團隊回顧中討論改進
```

---

## 畢業清單

在你完成畢業專案之前，確認以下每一項都已完成：

```
基礎篇
□ 理解 AI Agent 的核心概念
□ 能區分 AI 工具和 AI Agent
□ 已安裝並使用過 Claude Code
□ 能寫結構化的 Agent 指令

實戰篇
□ 理解 SDD-BDD-TDD 工作流
□ 能使用四問題法評估複雜度
□ 理解 MCP 和 Tool Use

治理篇
□ 已撰寫 constitution.md
□ 已設計語意禁止規則
□ 已建立人類審查觸發機制
□ 已建立記憶系統（diary + patterns + context）
□ 已設定品質閘門

進階篇
□ 理解多 Agent 協作模式
□ 已設定 Token 預算
□ 已建立操作日誌格式
□ 已完成完整的治理框架
```

---

## 結語

> **你已經從一個 AI Agent 的「使用者」，成長為一個「治理者」。**
>
> 記住：
> - Agent 的能力會越來越強，但治理的必要性不會消失
> - 好的治理不是限制 Agent，而是確保它的力量被正確運用
> - 治理框架是活的，需要和專案一起成長
>
> **恭喜畢業！現在去打造更好的軟體吧。**

---

## 附錄參考

- [附錄 A — 快速參考卡](appendix-a-cheatsheet.md)：指令、規則、模式速查表
- [附錄 B — 教學指南](appendix-b-teaching-guide.md)：18 週課程規劃

---

> 📖 **配套資源**：完整的生產級治理框架請參考 `agent-init/` 目錄
