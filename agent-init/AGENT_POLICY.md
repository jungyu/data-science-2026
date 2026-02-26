# Agent Policy — Skills 重建與維護

本倉庫採用 **skills 作為可執行工程知識**，而非單純文件。

任何 AI agent（Codex、Claude Code 等）在本倉庫操作時，**必須**遵守本政策。

---

## 1. 核心原則

**倉庫現實（Repo Reality）是唯一事實來源。**

優先順序（嚴格）：
1. 倉庫實際狀態（現有檔案、目錄、程式碼、設定檔）
2. docs/ 目錄（僅作為歷史意圖參考）
3. 官方文件（僅作為概念與 API 驗證用途）

若有任何衝突，**倉庫現實優先**。

### 1.1 治理架構

`.agent/` 治理系統的完整地圖（層級、權限矩陣、執行流程），請參閱：

**See: `{{GOVERNANCE_ARCHITECTURE_PATH}}`**

> 提示：首次使用時，請將 `{{GOVERNANCE_ARCHITECTURE_PATH}}` 替換為你的治理架構文件路徑，
> 例如 `docs/architecture/GOVERNANCE-ARCHITECTURE.md`。

---

## 2. 目標

重建並維護以下位置的 skills：

```
.agent/skills/*.md
```

Skills 必須滿足：
- 可執行（Executable）
- 可驗證（Verifiable）
- 可被未來工程師維護（Maintainable）
- 與當前倉庫架構一致（Aligned）

---

## 3. 強制架構掃描

在建立或更新任何 skill 之前，agent **必須**：

1. 掃描倉庫
2. 產生或更新：
   ```
   .agent/skills/ARCHITECTURE.md
   ```
3. 以此檔案作為架構真相地圖

架構檔案必須包含：
- 根層級設定檔
- 目錄樹（2-3 層深）
- `package.json` scripts（或等效的建置工具命令）
- **僅從倉庫檔案推斷**的技術堆疊

不允許假設。

---

## 4. Skills 分類

每個 skill 必須歸類為以下之一：

- **CORE** — 目前倉庫中正在使用
- **SUPPORT** — 支援性工作流程
- **OPTIONAL** — 目前未使用；僅為未來擴充

OPTIONAL skills **必須**：
- 明確標註
- 不得以現行工作流程的口吻撰寫

---

## 5. Skill 必要結構

每個 `.agent/skills/*.md` **必須**遵循以下結構：

```md
# 標題

## 目的 / 能解決什麼問題

## 何時該用 / 何時不該用

## Repo Reality
- 現有檔案路徑（必須存在）
- 相關 scripts 或進入點

## Inputs
- 格式
- 範例

## Outputs
- 格式
- 驗證方法

## Workflow
1. 工作目錄
2. 命令或動作
3. 預期結果

## 常見錯誤與排除

## 相容性與版本注意事項
- 若技術版本敏感則為必要欄位

## 參考來源
- 倉庫檔案
- 官方文件（若適用）
```

---

## 6. 快速演化技術（雙錨點策略 Dual Anchoring）

以下技術被視為**快速演化**：

`{{RAPIDLY_EVOLVING_TECH}}`

> **填寫指引**：列出你的專案中版本迭代頻繁、API 經常變動的技術。
> 例如：`React Native, TailwindCSS v4, GraphQL Yoga, tRPC`。
> 每項技術在 skill 中都需要雙錨點驗證。

對於這些技術的 skills，**雙錨點策略為強制要求**：

### 倉庫錨點（主要）
- 倉庫目前如何實作該技術

### 官方錨點（次要）
- 官方文件用於概念與 API 驗證

### 遷移備註（若存在不一致則為必要）
- 目前倉庫行為
- 官方建議
- 具體遷移步驟（檔案層級）

每個此類 skill **必須**包含：
```
Last verified: YYYY-MM-DD
```

---

## 7. 禁止行為

Agents **禁止**：
- 虛構檔案路徑、scripts 或元件
- 假設工具已安裝或正在使用
- 在缺乏倉庫依據的情況下逐字複製官方文件
- 留下未解決的 TODO / TBD / NEEDS_VERIFICATION

---

## 8. 最終驗證

產生 skills 後，agents **必須**：

1. 驗證所有引用的路徑確實存在
2. 驗證所有命令可執行
3. 移除占位符
4. 更新：
   ```
   .agent/skills/CHANGELOG.md
   ```
   描述：
   - 新增了什麼
   - 修正了什麼
   - 與官方文件或指引有何差異

---

## 9. 完成定義（Definition of Done）

一個 skill 只有在以下條件全部滿足時才視為完成：
- 另一位工程師能逐步依照執行
- 所有倉庫引用都是真實的
- 所有工作流程都可驗證
- 不包含任何架構假設

---

**Skills 是操作記憶。
如果無法被執行，就不屬於這裡。**
