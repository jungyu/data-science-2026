# .agent-init — AI Agent 治理初始化範本

> 為任何程式專案提供即開即用的 AI Agent 治理框架。
> 從個人 Side Project 到正式產品，漸進式建立信任與品質保障。

---

## 這是什麼？

`.agent-init/` 是一套**專案無關**的 AI Agent 治理範本，包含：

- **Constitutional Governance** — 定義 AI agent 必須遵守的核心原則
- **Decision Diary** — 記錄臨時決策，觀察後升級或淘汰
- **SDD-BDD-TDD Workflow** — 規格先行的開發流程（依複雜度分級）
- **Governance Gates** — 6 個自動化閘門防止架構漂移
- **Human-in-the-Loop** — 3 級觸發機制確保關鍵操作有人類確認
- **Semantic Deny** — 語意層級的程式碼意圖禁止清單
- **Token Budget** — AI agent 操作成本意識指引
- **Task Pack** — 最小權限的任務邊界控制
- **Action Log** — Session 操作記錄與可觀測性

這些方法論來自 30+ 種軟體工程、治理學、AI 安全領域的最佳實踐。

---

## 快速安裝（3 步驟）

### 1. 複製到你的專案

```bash
# 在你的專案根目錄執行
cp -r path/to/.agent-init .agent
```

### 2. 執行 symlink 設定

```bash
chmod +x .agent/scripts/setup-agent-links.sh
.agent/scripts/setup-agent-links.sh
```

這會建立以下 symlink：
- `.github/copilot-instructions.md` → `.agent/rules/copilot-instructions.md`
- `.claude/commands` → `.agent/prompts/commands`
- `.claude/settings.local.json` → `.agent/config/claude-settings.json`

### 3. 自訂佔位符

搜尋所有 `{{` 佔位符並替換為你的專案資訊：

```bash
grep -rn '{{' .agent/ | head -20
```

**必要的佔位符**：

| 佔位符 | 說明 | 範例 |
|--------|------|------|
| `{{PROJECT_NAME}}` | 專案名稱 | `My SaaS App` |
| `{{TECH_STACK}}` | 技術堆疊 | `Next.js + PostgreSQL + Redis` |
| `{{SRC_DIR}}` | 原始碼目錄 | `src/` 或 `lib/` |
| `{{API_DIR}}` | API 路由目錄 | `app/api/` 或 `routes/` |
| `{{TEST_DIR}}` | 測試目錄 | `tests/` 或 `__tests__/` |
| `{{LANGUAGE_SPECIFIC}}` | 語言特定規則 | TypeScript strict mode 設定 |
| `{{AUTH_FRAMEWORK}}` | 認證框架規則 | NextAuth / Passport / JWT |

---

## 目錄結構說明

```
.agent/                             # rename from .agent-init after copying
├── AGENT_POLICY.md                 # 🏛️ Agent 治理政策（最高指導原則）
│
├── memory/                         # 📝 持久化知識
│   ├── constitution.md             #   ├── 憲法：不可違反的核心原則
│   └── diary.md                    #   └── 日記：臨時決策孵化器
│
├── config/                         # ⚙️ 工具設定
│   ├── claude-settings.json        #   ├── Claude Code 權限矩陣
│   └── token-budget.yaml           #   └── Token 成本意識指引
│
├── rules/                          # 📏 開發規則
│   ├── copilot-instructions.md     #   ├── 所有 AI 工具統一規範
│   ├── AGENTS.md                   #   ├── 多 Agent 協作規則
│   ├── human-review-triggers.md    #   ├── 人類審核觸發條件（3 級）
│   ├── semantic-deny.md            #   ├── 語意層級禁止規則
│   ├── skill-development-guide.md  #   ├── Skill 開發規範
│   └── _module-rules-template.md   #   └── 模組規則範本（用於新增）
│
├── prompts/                        # 💬 命令提示詞
│   ├── BDD_Meta_Prompt.md          #   ├── BDD 場景生成元提示
│   └── commands/                   #   └── Claude Code slash commands
│       ├── analyze.md / clarify.md / implement.md
│       ├── plan.md / specify.md / tasks.md
│
├── logs/                           # 📋 操作記錄
│   └── README.md                   #   └── Session 摘要規範
│
├── tasks/                          # 📦 任務管理
│   ├── _template.task.yml          #   ├── Task Pack 範本
│   ├── inbox/ / running/ / done/   #   └── 任務生命週期目錄
│
├── templates/                      # 📄 文件範本
│   ├── agent-file-template.md      #   ├── Agent 檔案範本
│   ├── plan-template.md            #   ├── 實作計畫範本
│   ├── spec-template.md            #   ├── 功能規格範本
│   └── tasks-template.md           #   └── 任務清單範本
│
├── skills/                         # 🧠 可執行知識
│   ├── _skill-template.md          #   ├── Skill 建立範本
│   ├── governance/                 #   ├── 治理閘門框架
│   │   ├── SKILL.md                #   │   ├── 治理入口
│   │   └── rules/                  #   │   └── 6 個 YAML 閘門
│   │       ├── contract_first_gate.yaml
│   │       ├── adr_gate.yaml
│   │       ├── ai_quarantine_merge.yaml
│   │       ├── style_canon_enforcer.yaml
│   │       ├── intent_drift_detector.yaml
│   │       └── arch_health_report.yaml
│   └── sdd-bdd-workflow/           #   └── SDD-BDD 分級工作流程
│       ├── SKILL.md / README.md
│       ├── 00-complexity-gate.md ~ 05-execution-flow.md
│       ├── scripts/ (validate-spec.sh, check-finish.sh)
│       └── references/ (error-taxonomy, scenario-patterns, agent-strategies)
│
└── scripts/                        # 🔧 自動化腳本
    ├── setup-agent-links.sh        #   ├── Symlink 設定
    └── bash/common.sh              #   └── 共用 Bash 工具
```

---

## 漸進式採用指南

不是所有專案都需要完整的治理體系。根據規模選擇：

### Minimal（個人專案）

**建置時間**：~2 小時

只啟用核心檔案：

```
使用的檔案：
├── memory/constitution.md      ← 寫 3-5 條核心原則
├── config/claude-settings.json ← 設定 deny rules
└── rules/semantic-deny.md      ← 5-10 條基本禁止規則
```

### Standard（小團隊 2-5 人）

**建置時間**：1-2 天

加入決策追蹤和開發流程：

```
Minimal 之上再加：
├── memory/diary.md             ← 開始記錄決策
├── rules/human-review-triggers.md ← 設定審核觸發
├── skills/governance/          ← 啟用 2-3 個關鍵閘門
└── skills/sdd-bdd-workflow/    ← 複雜度分級工作流
```

### Full（正式產品）

**建置時間**：漸進建立（不要一次做完！）

啟用所有機制：

```
Standard 之上再加：
├── config/token-budget.yaml    ← 成本控制
├── tasks/                      ← Task Pack 邊界控制
├── logs/                       ← Session 操作記錄
├── templates/                  ← 完整文件範本
└── 自建 rules/xxx-rules.md    ← 每個模組專屬規則
```

> **重要**：Full 方案是**逐步演化**的結果，不是一次性建立的。
> 建議從 Minimal 開始，遇到問題時再逐步增加。

---

## 自訂指南

### 如何新增模組規則

1. 複製 `rules/_module-rules-template.md`
2. 重新命名為 `rules/{{module-name}}-rules.md`
3. 填入模組特定的架構邊界、不變量、測試策略
4. 若有語意禁止規則，同步更新 `rules/semantic-deny.md`

### 如何新增技能

1. 複製 `skills/_skill-template.md` 到 `skills/{{skill-name}}/SKILL.md`
2. 填入 YAML frontmatter（name, triggers, finish_conditions）
3. 根據需要新增 scripts/、references/、templates/ 子目錄
4. 詳見 `rules/skill-development-guide.md`

### 如何新增治理閘門

1. 在 `skills/governance/rules/` 新增 YAML 檔案
2. 定義 id、name、purpose、inputs、outputs、rules、block_conditions
3. 在 `skills/governance/SKILL.md` 中註冊新閘門
4. 參考現有 6 個閘門的格式

---

## 方法論總覽

| 方法論 | 理論根源 | 實作位置 | 治理層級 |
|--------|---------|----------|---------|
| Constitutional Governance | 憲法學 | `memory/constitution.md` | L0 原則 |
| Decision Diary | 決策日誌學 | `memory/diary.md` | L1 決策 |
| ADR | 軟體架構（Nygard 2011） | `docs/ADR/` | L1 架構 |
| SDD | 規格先行開發 | `prompts/commands/specify.md` | L3 流程 |
| BDD | 行為驅動（North 2006） | `prompts/BDD_Meta_Prompt.md` | L3 流程 |
| TDD | 測試驅動（Beck 2003） | `constitution.md` Principle I | L0 原則 |
| Complexity Gate | 複雜度理論 | `skills/sdd-bdd-workflow/00-*` | L3 流程 |
| Design by Contract | DbC（Meyer 1986） | `governance/rules/contract_first_gate.yaml` | L4 閘門 |
| Intent Drift Detection | 產品策略 | `governance/rules/intent_drift_detector.yaml` | L4 閘門 |
| Defense in Depth | 軍事/資安 | 四層防護體系 | L1-L4 |
| HITL | AI 安全 | `rules/human-review-triggers.md` | L2 操作 |
| Semantic Deny | 語意分析 | `rules/semantic-deny.md` | L2 語意 |
| Task Pack | 最小權限（POLA） | `tasks/` | L5 操作 |
| Token Budget | 成本管理 | `config/token-budget.yaml` | Config |
| Action Log | 可觀測性 | `logs/` | Ops |

---

## FAQ

### Q: 可以只用部分檔案嗎？
A: 完全可以。建議從 Minimal 方案開始，只複製需要的檔案。

### Q: 支援哪些 AI 工具？
A: 設計上支援 Claude Code、GitHub Copilot、Gemini CLI、Codex CLI。核心概念（constitution、governance gates）與工具無關。

### Q: 佔位符一定要全部填完嗎？
A: 不需要。只填你目前會用到的即可，其餘保留佔位符，未來再填。

### Q: 可以用在非 TypeScript 專案嗎？
A: 可以。雖然範例多用 TypeScript 語法，但所有方法論都是語言無關的。只需調整 `constitution.md` 中的語言特定規則。

### Q: 如何與現有 CI/CD 整合？
A: `skills/governance/rules/*.yaml` 中的閘門可以寫成 CI 檢查腳本。例如 `contract_first_gate` 可以在 PR 時自動檢查 contracts/ 是否同步更新。

### Q: 和 `.github/` 目錄的關係？
A: `scripts/setup-agent-links.sh` 會建立 symlink，讓 `.github/copilot-instructions.md` 指向 `.agent/rules/copilot-instructions.md`，統一維護。

---

## 延伸閱讀

- Kent Beck,《Test-Driven Development: By Example》(2003)
- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (2011)
- Bertrand Meyer,《Object-Oriented Software Construction》(1988) — Design by Contract
- Dan North, [Introducing BDD](https://dannorth.net/introducing-bdd/) (2006)

---

*本範本源自一個 121 檔案、30+ 種方法論、經過 6 個月實戰驗證的 AI Agent 治理體系。*
