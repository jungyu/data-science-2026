# Repository Guidelines

本專案開發規範請優先參照 `.agent/rules/copilot-instructions.md`；若本檔內容與該文件衝突，以該文件為準。

## Copilot 指南摘要（重點索引）
- AI 產出文件需放在 `docs/AI/**`，依 `YYYYMMDD_name.md` 命名，未明確要求則避免自動生成文件。
- 模組規則優先讀 `/.agent/skills/`，技術文件看 `docs/AI/llms/`，提示詞集中在 `/.agent/prompts/`。
- 全域狀態管理統一使用專案選定的狀態管理方案（如 Zustand stores、Redux、Pinia 等）。
- 通知統一使用專案的通知系統；禁止自建重複的通知元件。
- 資料庫操作必須通過專案統一的 ORM / client library；mutation 優先使用 Server Actions 或對應的後端處理方式。

## 統一 Agent 架構 (.agent)

本專案採用 **`.agent/`** 作為所有 AI/Agent 工具的單一真相來源 (Single Source of Truth)。相關目錄結構如下：

- `.agent/rules/`：放置 Copilot Instructions, Docker Rules 等規範文件。
- `.agent/prompts/`：放置 Claude Commands, System Prompts。
- `.agent/config/`：放置工具設定檔 (e.g. `claude-settings.json`)。
- `.agent/skills/`：放置可執行的 Skill 文件。

### Tool Compatibility (Symlinks)

為了確保舊有工具 (Codex, Claude CLI, GitHub Copilot) 能正常運作，我們使用 **Symlinks** 保持相容性：

- `.github/copilot-instructions.md` -> `.agent/rules/copilot-instructions.md`
- `.claude/commands/` -> `.agent/prompts/commands/`
- `.claude/settings.local.json` -> `.agent/config/claude-settings.json`

若發現這些連結遺失，請執行 `.agent/scripts/setup-agent-links.sh` 進行修復。

## 資料庫與安全
- RLS / 權限政策在同一 migration 內啟用並定義；資料表/欄位使用 snake_case；型別使用自動生成（typegen）。
- UI 遵循專案設計系統規範，符合 WCAG 2.1 AA。
- 模組間的存取控制依 `{{AUTH_FRAMEWORK}}` 設定的 ACL 規則。
- API 權限使用統一的 access check middleware；Client 端上下文使用全域狀態管理。

## Project Structure & Module Organization
{{PROJECT_STRUCTURE}}

<!--
填寫範例：
程式碼採 Next.js 15 App Router。登入後頁面位於 `app/(authenticated)/**`。
共用 React 元件放在 `components/`，服務與 ACL 工具在 `lib/`，型別定義集中於 `types/`。
資料庫 migration 維護於 `migrations/`，輔助腳本放在 `scripts/`。
-->

## Build, Test, and Development Commands
{{BUILD_COMMANDS}}

<!--
填寫範例：
統一使用 pnpm。`pnpm dev` 啟動開發伺服器，`pnpm build && pnpm start` 模擬正式環境。
提交前須通過 `pnpm lint`、`pnpm type-check`、`pnpm test`（Vitest）與 `pnpm test:e2e`（Playwright）。
-->

## Coding Style & Naming Conventions
{{CODING_STYLE}}

<!--
填寫範例：
TypeScript 為 strict 模式，路徑使用 `@/*` alias。
React 元件以 PascalCase 命名，hooks 採 `useXxx`，`lib/` 下的工具維持 kebab-case。
Tailwind CSS 為主要樣式，複用樣式寫入 `app/globals.css`。
資料庫欄位採 snake_case。
-->

## Testing Guidelines
單元與小型整合測試可放在原檔旁或 `__tests__/`。契約與 API 驗證集中於 `tests/contract/`。E2E 測試需覆蓋關鍵使用者流程與 ACL 行為。請於 CI 中留意測試覆蓋率是否持續達成既定門檻。

## Commit & Pull Request Guidelines
沿用慣例：`feat(module): ...`、`fix(module): ...` 或必要時使用精簡的描述。標題保持命令式並少於 72 字元，避免堆疊雜訊 commit。PR 描述需列出執行的 lint/測試指令、影響路由、對應文檔以及任何新的環境變數或資料庫動作。

## Documentation & Knowledge Share
功能啟動前請更新對應規劃文件與執行追蹤。新增腳本需在 `README.md` 補充使用方式。涉及外部服務介接的 TODO 務必在對應追蹤文件中標註狀態，並記錄在 `CHANGELOG` 以利後續稽核。
