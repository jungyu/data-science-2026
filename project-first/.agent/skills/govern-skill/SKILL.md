# govern-skill — 治理合規技能

## 概要

檢查知識庫系統的治理合規性，確保所有操作符合 Constitution 原則。

## 觸發條件

- 每週自動掃描（排程）
- 架構級變更前（HITL Level 1 操作）
- 手動呼叫 `/govern`

## 執行步驟

1. **Constitution 合規檢查**：驗證所有 active 文件符合 5 條原則
2. **Semantic Deny 掃描**：確認無違反 KA-* / MCP-* 規則的操作
3. **HITL 觸發回顧**：檢查近期操作是否有遺漏的 HITL 觸發
4. **Token 預算審查**：確認各 tier 的使用量在預算內
5. **ADR 完整性**：確認所有架構決策都有對應 ADR
6. **產出合規報告**並記錄 Action Log

## 審計清單

- [ ] Constitution 5 條原則均有程式碼執行
- [ ] Semantic Deny 規則無違反
- [ ] HITL 觸發條件涵蓋所有高風險操作
- [ ] Token 預算未超標
- [ ] 所有 namespace 都有 ADR 記錄
- [ ] Action Log 完整且可追溯

## 相關模組

- `.agent/memory/constitution.md` — 治理原則
- `.agent/rules/semantic-deny.md` — 語意禁止規則
- `.agent/rules/human-review-triggers.md` — HITL 觸發條件
- `src/governance/hitl_checker.py` — HITL 風險檢查
- `src/governance/drift_detector.py` — 知識漂移偵測
