---
name: rag-workflow
version: 1.0
description: "RAG 知識管理的標準工作流程，含 5 個品質閘門"
triggers: ["ingest", "query", "evaluate", "knowledge update", "rag workflow"]
finish_conditions: ["所有閘門通過", "Action Log 已記錄", "驗證查詢成功"]
estimated_tokens: { lite: 5000, standard: 20000, full: 60000 }
---

# RAG Workflow Skill

## 概述
整合 SDD-BDD 方法論的 RAG 專屬工作流程，包含 5 個品質閘門。

## 複雜度模式

| 模式 | 分數 | 適用場景 | Token 預算 |
|------|------|---------|-----------|
| Lite | 0-2 | 單一文件更新、常規查詢 | ~5K |
| Standard | 3-5 | 批次攝取、新增 namespace | ~20K |
| Full | 6+ | 模型更換、跨系統整合 | ~60K |

## 閘門流程

```
00-complexity-gate → 01-spec-gate → 02-scenario-gate → 03-build-gate → 04-eval-gate
     (必須)           (Standard+)      (Standard+)       (所有模式)      (Standard+)
```

## 相關檔案
- [00-complexity-gate.md](00-complexity-gate.md) — 複雜度評估
- [01-spec-gate.md](01-spec-gate.md) — 規格完整性
- [02-scenario-gate.md](02-scenario-gate.md) — BDD 場景
- [03-build-gate.md](03-build-gate.md) — 建置品質
- [04-eval-gate.md](04-eval-gate.md) — RAG 評測
