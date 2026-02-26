# {{PROJECT_NAME}} Decision Diary

> 推演與脈絡紀錄區。可長、可亂、可淘汰。
> 一旦規則/決策被證實「穩定且長期成立」，必須升級到 constitution.md 或 ADR。
> **升級路徑：diary → constitution.md 修正 (version bump) 或 docs/architecture/ADR-XXX.md**

## 本 Diary 的用途

本檔案記錄 AI agent 與人類開發者在開發過程中的**臨時決策與推演脈絡**。
它不是正式文件，而是決策的「孵化器」：

- **短期決策**：記錄當下的技術選擇與理由，日後回顧時能理解「為什麼這樣做」
- **實驗追蹤**：記錄嘗試過但可能需要調整的做法
- **升級候選**：當某個決策被 2-3 次實作驗證後，考慮升級為正式規則

## Entry Template

```
### YYYY-MM-DD — 主題

- Context: 背景與觸發原因
- Options: 考慮過的選項（編號列出）
- Decision (temporary): 當前選擇與理由
- Risks / Unknowns: 已知風險與未知因素
- Next validation step: 下一步驗證方式
- Promote-to: keep-in-diary | promote-to-constitution | promote-to-adr | resolved
```

### `promote-to` 選項說明

| 選項                    | 意義                                                         |
|------------------------|--------------------------------------------------------------|
| `keep-in-diary`        | 尚未驗證，繼續觀察                                           |
| `promote-to-constitution` | 決策穩定，應升級到 `constitution.md`（觸發 version bump）     |
| `promote-to-adr`       | 決策涉及架構層級，應建立 `docs/architecture/ADR-XXX.md`       |
| `resolved`             | 問題已解決或不再適用，保留紀錄但不需進一步行動                 |

---

### {{DATE}} — 治理系統初始化

- Context: 專案建立 `.agent/` 治理系統，包含 AGENT_POLICY.md（操作政策）、
  constitution.md（5 項不可妥協原則）、diary.md（本檔，決策孵化器）。
  目標是讓 AI agent 在本倉庫中有明確的行為邊界與品質底線。
- Options:
  1. 不建治理系統，依賴 AI agent 的預設行為
  2. 輕量治理：僅 constitution + diary，逐步擴充
  3. 完整治理：constitution + diary + skills + rules + governance gates
- Decision (temporary): 採用 Option 2（輕量啟動）。
  先建立核心原則與決策記錄機制，待專案規模成長後再逐步擴充 skills、rules、
  governance gates 等進階治理層。
- Risks / Unknowns:
  - 輕量治理可能在專案快速成長時覆蓋不足
  - Constitution 的 5 項原則可能需要根據專案領域新增（例如資料庫、UI 架構）
  - `{{PLACEHOLDER}}` 尚未全部替換為專案實際值
- Next validation step: 第一次實際開發任務時驗證 Constitution 原則是否有效約束 agent 行為。
  完成後在本 diary 記錄結果。
- Promote-to: keep-in-diary（待 2-3 次任務驗證後評估）
