# SDD→BDD 規格編排器工作流程 v3.0

> **核心理念**: 根據功能複雜度選擇適當的規格深度，避免過度工程或規格不足。

---

## 統一工作流程

本框架提供兩種使用方式，共用相同的 complexity gate、spec 模板、和驗證腳本：

### 方式 1: Slash Commands（推薦）

透過 `.agent/prompts/commands/` 中的 Claude Code slash commands 驅動：

```
/specify <描述>  →  建立 feature branch + spec.md
/clarify         →  互動式釐清模糊需求（≤5 題）
/plan            →  產生 research.md, data-model.md, contracts/, plan.md
/tasks           →  產生 tasks.md（依賴排序、TDD 順序）
/implement       →  逐步執行 tasks.md
/analyze         →  跨 artifact 一致性分析（唯讀）
```

### 方式 2: 四��咒語（輕量版）

適合快速開發或非 Claude Code 環境，詳見 [04-commands.md](./04-commands.md)：

```
Spec first       →  對應 /specify + /clarify
Scenarios         →  對應 /plan 中的 scenario 產出
Tests first       →  對應 /tasks + /implement（測試階段）
Refactor for swap →  對應 /implement（重構階段）
```

### 流程對照表

| 階段 | Slash Command | 四句咒語 | SDD-BDD Gate | 複雜度門檻 |
|------|--------------|---------|--------------|-----------|
| 評估 | ���自動） | （自動） | [00-complexity-gate](./00-complexity-gate.md) | 所有 |
| 規格 | `/specify` + `/clarify` | `Spec first` | [01-spec-gate](./01-spec-gate.md) | Standard+ |
| 場景 | `/plan` | `Scenarios` | [02-scenario-gate](./02-scenario-gate.md) | Full |
| 建置 | `/tasks` + `/implement` | `Tests first` + `Refactor for swap` | [03-build-gate](./03-build-gate.md) | Standard+ |
| 驗證 | `/analyze` | `check-finish.sh` | 完成檢查 | 所有 |

---

## 複雜度評估與模式選擇

詳細評估流程請見 [00-complexity-gate.md](./00-complexity-gate.md)

| 模式 | 複雜度分數 | 適用場景 | 產出 |
|------|-----------|---------|-----|
| **Lite** | 0-2 | 純工具函數、型別定義 | `spec.md`（精簡版） |
| **Standard** | 3-5 | 中等功能、元件升級 | `spec.md` + `plan.md` + `tasks.md` |
| **Full** | 6+ | 多服務整合、高風險 | 完整三關 + ADR |

---

## 文件結構

```
.agent/skills/sdd-bdd-workflow/
├── SKILL.md                    # Skill 入口 (Metadata)
├── README.md                   # 本文件
├── 00-complexity-gate.md       # 複雜度評估
├── 01-spec-gate.md             # Spec Gate Prompt
├── 02-scenario-gate.md         # Scenario Gate Prompt
├── 03-build-gate.md            # Build Gate Prompt
├── 04-commands.md              # 四句咒語協議（輕量版）
├── 05-execution-flow.md        # 執行流程圖
├── scripts/                    # 驗證腳本
│   ├── validate-spec.sh
│   └── check-finish.sh
└── references/                 # 按需參考資料
    ├── error-taxonomy.md
    ├── scenario-patterns.md
    └── agent-strategies.md

.agent/prompts/commands/         # Slash Commands（完整版）
├── specify.md                   # /specify — 建立 spec
├── clarify.md                   # /clarify — 釐清需求
├── plan.md                      # /plan — 產生設計 artifact
├── tasks.md                     # /tasks — 產生任務清單
├── implement.md                 # /implement — 執行實作
└── analyze.md                   # /analyze — 一致性分析
```

---

## 相關文件連結

- [00-complexity-gate.md](./00-complexity-gate.md) — 複雜度評估
- [01-spec-gate.md](./01-spec-gate.md) — 規格關
- [04-commands.md](./04-commands.md) — 四句咒語
- [05-execution-flow.md](./05-execution-flow.md) — 執行流程圖
- [scripts/validate-spec.sh](./scripts/validate-spec.sh) — Spec 驗證
- [scripts/check-finish.sh](./scripts/check-finish.sh) — 完成檢查
