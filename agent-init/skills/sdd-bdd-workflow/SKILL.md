---
name: sdd-bdd-workflow
version: 2.1
description: "規格驅動開發工作流程，依複雜度分級適用。支援 Antigravity、Claude Code、Codex CLI"
tags: ["bdd", "tdd", "sdd", "spec", "testing", "workflow", "core"]

triggers:
  - "spec first"
  - "spec lite"
  - "spec standard"
  - "scenarios"
  - "tests first"
  - "refactor for swap"
  - "規格"
  - "BDD"
  - "TDD"
  - "sdd-bdd"

finish_conditions:
  - "所有規格項目標記為 [x]"
  - "lint/type 錯誤為 0"
  - "測試通過"

scripts:
  - scripts/validate-spec.sh
  - scripts/check-finish.sh

references:
  - references/error-taxonomy.md
  - references/scenario-patterns.md
  - references/agent-strategies.md

estimated_tokens:
  lite: 800
  standard: 2000
  full: 5000
---

# SDD-BDD 分級工作流程

> **核心理念**: 根據功能複雜度選擇適當的規格深度。
> **跨 Agent 相容**: 支援 Antigravity、Claude Code、Codex CLI

詳見 [README.md](./README.md) 獲取完整說明、複雜度評估表與指令參考。

## 快速選擇

| 模式 | 分數 | 適用 | 預估 Token |
|------|-----|-----|-----------|
| **Lite** | 0-2 | 簡單工具 | ~800 |
| **Standard** | 3-5 | 模組升級 | ~2000 |
| **Full** | 6+ | 複雜系統 | ~5000 |

## 執行流程

1. **評估**: [00-complexity-gate.md](./00-complexity-gate.md)
2. **規格**: [01-spec-gate.md](./01-spec-gate.md)
3. **實作**: [03-build-gate.md](./03-build-gate.md)
4. **驗證**: `./scripts/check-finish.sh`
