# Agent Action Log

## 目的

記錄 AI agent 每次 session 的操作摘要，建立可追溯的操作歷史。
這不是即時日誌，而是 session 結束時的**結構化摘要**。

## 命名規範

```
.agent/logs/YYYY-MM-DD-{short-topic}.md
```

範例：
- `2026-02-26-agent-governance-audit.md`
- `2026-02-27-ir-parser-bugfix.md`
- `2026-02-28-new-api-endpoint.md`

同日多次 session 加序號：`2026-02-26-01-topic.md`、`2026-02-26-02-topic.md`

## Session 摘要模板

```markdown
# Session: {topic}

- **Date**: YYYY-MM-DD
- **Agent**: Claude Code / Codex / other
- **Duration**: ~{estimate}
- **Token Budget**: {tier} ({actual} / {target})

## 任務摘要

{1-3 句描述本次 session 完成了什麼}

## 變更清單

| 操作 | 檔案/路徑 | 說明 |
|------|----------|------|
| Created | path/to/file.ts | 新增功能 |
| Modified | path/to/other.ts | 修正 bug |
| Deleted | path/to/old.ts | 移除過時程式碼 |

## 觸發的治理規則

- [ ] human-review-triggers: {是否觸發，哪一條}
- [ ] semantic-deny: {是否觸及，哪一條}
- [ ] governance gates: {是否觸發，哪一條}

## 決策記錄

{列出本次做的重要決策，若需長期保留則同步寫入 diary.md}

## 未完成項目

{列出未完成的工作，供下次 session 接續}
```

## 何時產生

### 建議產生 Log 的情況

1. **複雜操作**（修改 >5 檔案）
2. **架構變更**（新增模組、修改 IR、變更 API）
3. **治理操作**（修改 rules、constitution、governance gates）
4. **人類明確要求**

### 不需要 Log 的情況

1. 簡單 Q&A（回答問題、解釋程式碼）
2. 單檔小修改（typo fix、設定調整）
3. 探索/研究（未做任何變更）

## 保留策略

- **最近 30 天**：完整保留
- **30-90 天**：保留重要 session，刪除瑣碎操作
- **90 天以上**：重要決策已升級到 diary.md 或 ADR，log 可刪除

## 與其他記錄的關係

```
action log (本目錄)  → 操作級：「做了什麼」（短期）
diary.md             → 決策級：「為什麼這樣做」（中期）
constitution.md      → 原則級：「永遠這樣做」（長期）
ADR                  → 架構級：「系統為什麼是這樣」（永久）
```
