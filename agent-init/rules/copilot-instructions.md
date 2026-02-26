# {{PROJECT_NAME}} — AI 開發指南

> 本指南為所有 AI 工具（Copilot、Claude、Cursor 等）的統一規範。
> 所有 AI 生成的程式碼與文件皆須遵守此指南。

---

## AI 工具生成文件規範

### 目錄結構

所有 AI 生成的規劃、分析、報告文件統一放置於 `docs/AI/` 目錄：

```
docs/AI/
├── planning/     # 實作計畫、架構設計
├── analysis/     # 程式碼分析、技術調查
├── reports/      # 進度報告、審計結果
└── decisions/    # 技術決策記錄 (ADR)
```

### 檔名規範

格式：`YYYYMMDD_[Module]_[Type]_[Subject].md`

- **Module 標籤**：{{PROJECT_MODULES}}
- **Type 標籤**：Fix、Task、Plan、Audit、Report、Refactor、Feature、Analysis、Progress
- 範例：`20260226_Auth_Plan_OAuth_Integration.md`

### 文件內容規範

1. 每份文件開頭須包含 metadata（日期、作者、模組、狀態）
2. 使用 Markdown 格式，標題層級不超過 4 層
3. 程式碼區塊須標明語言
4. 決策文件須包含「背景」「選項」「決定」「後果」四區塊

---

## 編碼風格與慣例

### 檔案命名

| 類型 | 慣例 | 範例 |
|------|------|------|
| 一般檔案 | kebab-case | `user-service.ts` |
| 元件 | PascalCase | `UserProfile.tsx` |
| 測試 | 原檔名 + `.test` | `user-service.test.ts` |
| 型別 | 原檔名 + `.types` | `user-service.types.ts` |
| 常數 | kebab-case | `error-codes.ts` |

### Import 排序規則

```
1. 語言/框架內建模組
2. 第三方套件
3. 專案內部 alias（如 @/lib, @/components）
4. 相對路徑 import
5. Type-only import
（各區塊間空一行）
```

### Error Handling 規範

```
1. 使用專案統一的 error class / error factory
2. 所有 async 操作必須有 error boundary 或 try-catch
3. 錯誤訊息須包含足夠 context（操作名稱、相關 ID、失敗原因）
4. 使用者可見的錯誤訊息與開發者 log 分離
5. 不得吞掉（swallow）error — 至少要 log
```

### Logging 規範

```
1. 使用專案的 logging framework，不用 console.log（見 semantic-deny GEN-4）
2. 結構化 log（JSON 格式，含 timestamp、level、context）
3. 敏感資訊不得出現在 log 中（見 semantic-deny GEN-5）
4. Log level 使用規範：
   - error: 需要立即處理的異常
   - warn: 可能的問題，但不影響正常運作
   - info: 重要的業務事件
   - debug: 開發階段除錯資訊（不進 production）
```

---

## 技術堆疊

{{TECH_STACK}}

<!--
填寫範例：
- Language: TypeScript 5.x (strict mode)
- Framework: Next.js 15 (App Router)
- Database: PostgreSQL + Prisma ORM
- Auth: NextAuth.js v5
- Styling: Tailwind CSS + Shadcn/ui
- Testing: Vitest + Playwright
- CI/CD: GitHub Actions
-->

---

## 模組分類

{{MODULE_TAXONOMY}}

<!--
填寫範例：
| 模組 | 路徑 | 職責 |
|------|------|------|
| Auth | lib/auth/, app/api/auth/ | 認證與授權 |
| Core | lib/core/ | 共用基礎設施 |
| UI | components/shared/ | 共用 UI 元件 |
| API | app/api/ | API route handlers |
-->

---

## AI 行為準則

### 必須遵守

1. **先讀後寫**：修改任何檔案前，先讀取並理解現有內容
2. **遵循現有模式**：觀察專案中的既有 pattern，保持一致性
3. **最小變更原則**：只修改達成目標所需的最少程式碼
4. **保留註解與文件**：不得刪除有意義的註解或 JSDoc
5. **型別安全**：不得引入 `any` type，除非有明確 justification
6. **測試覆蓋**：新增功能須附帶對應測試

### 禁止事項

1. 不得違反 `semantic-deny.md` 中的任何規則
2. 不得跳過 `human-review-triggers.md` 中定義的審查流程
3. 不得自行 commit / push，除非人類明確要求
4. 不得刪除或修改 `.agent-init/` 目錄下的治理文件（LEVEL 1 觸發）
5. 不得在回應中捏造不存在的 API、函式、或套件

### 不確定時

1. 明確告知人類「我不確定」
2. 列出可能的選項與各自的 trade-off
3. 等待人類決定後再執行
