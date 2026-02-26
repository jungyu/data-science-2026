# SDD→BDD 規格編排器工作流程 v2.1

> **核心理念**: 根據功能複雜度選擇適當的規格深度，避免過度工程或規格不足。
> **跨 Agent 相容**: 支援 Antigravity、Claude Code、Codex CLI

---

## 🤖 AI Agent 適配指南

不同 Agent 有不同強項，選擇正確的工具可提高效率：

| Agent | 強項 | 適合任務 | 注意事項 |
|-------|------|---------|---------|
| **Antigravity** | 長上下文、多檔案編輯 | 規格撰寫、重構 | 使用 browser_subagent 驗證 UI |
| **Claude Code** | LSP 診斷、迭代修復 | 自動修復、迭代調試 | 設定 finish condition 避免無限迴圈 |
| **Codex CLI** | 快速單次生成 | 快速原型、小修改 | 每次任務保持簡單 |

---

## 📊 複雜度評估與模式選擇

詳細評估流程請見 [00-complexity-gate.md](./00-complexity-gate.md)

| 模式 | 複雜度分數 | 預估 Token 成本 | 適用場景 | 產出 |
|------|-----------|----------------|---------|-----|
| **Lite** | 0-2 | ~800 | 純工具函數、型別定義 | `spec-lite.md` |
| **Standard** | 3-5 | ~2000 | 中等功能、元件升級 | `spec.md` + 測試 |
| **Full** | 6+ | ~5000 | 多服務整合、高風險 | 完整三關 + ADR |

---

## 🚦 執行流程

詳見 [05-execution-flow.md](./05-execution-flow.md)

1. **評估** (Complexity Gate)
2. **規格** (Spec Gate)
3. **實作** (Build Gate)
4. **驗證** (Check Finish)

---

## 📁 文件結構

```
.agent/skills/sdd-bdd-workflow/
├── SKILL.md                    # Skill 入口 (Metadata only)
├── README.md                   # 本文件 (詳細說明)
├── 00-complexity-gate.md       # 複雜度評估
├── 01-spec-gate.md             # Spec Gate Prompt
├── 02-scenario-gate.md         # Scenario Gate Prompt
├── 03-build-gate.md            # Build Gate Prompt
├── 04-commands.md              # 四句咒語協議
├── 05-execution-flow.md        # 執行流程圖
├── scripts/                    # 驗證腳本
│   ├── validate-spec.sh
│   └── check-finish.sh
└── references/                 # 按需參考資料
    ├── error-taxonomy.md
    ├── scenario-patterns.md
    └── agent-strategies.md
```

---

## 🔮 快速指令

### 所有 Agent 通用

```bash
# Lite 模式
Spec lite: 建立 specs/[feature]/spec-lite.md

# Standard 模式
Spec standard: 建立 specs/[feature]/spec.md

# Full 模式
Spec first: 更新 spec.md
Scenarios: 萃取 scenarios.feature
Tests first: 建立測試骨架
Refactor for swap: 確保 Adapter 層
```

---

## 📚 相關文件連結

- [00-complexity-gate.md](./00-complexity-gate.md)
- [01-spec-gate.md](./01-spec-gate.md)
- [04-commands.md](./04-commands.md)
- [scripts/validate-spec.sh](./scripts/validate-spec.sh)
