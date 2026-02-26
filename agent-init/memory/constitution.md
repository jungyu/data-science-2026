<!--
============================================
SYNC IMPACT REPORT - Constitution v1.0.0
============================================
Version change: 0.0.0 → 1.0.0 (MAJOR - 初始建立)

Modified principles: 無（首次建立）

Added sections:
  - Principle I: Test-First Development
  - Principle II: Type Safety First
  - Principle III: Security by Default
  - Principle IV: Code Quality & Maintainability
  - Principle V: Git Discipline

Removed sections: 無

Updated sections: 無

Templates requiring updates:
  ✅ .agent/templates/plan-template.md - 確認引用 Constitution v1.0.0
  ✅ .agent/templates/spec-template.md - 確認引用 Constitution v1.0.0

Follow-up TODOs:
  - 替換所有 {{PLACEHOLDER}} 為專案實際值
  - 根據專案需求新增領域專屬原則（例如資料庫、UI 架構、媒體儲存等）

Sync Status: 初始 Constitution 建立，5 項通用原則就緒。
============================================
-->

<!--
============================================
版本升級指引 (Version Bump Instructions)
============================================
何時升級 MAJOR (X.0.0)：
  - 新增或移除原則
  - 根本性變更現有原則的語意

何時升級 MINOR (x.Y.0)：
  - 在現有原則下新增子節
  - 新增具體規則但不改變原則語意

何時升級 PATCH (x.y.Z)：
  - 修正錯字、補充範例
  - 調整措辭但不改變規則內容

每次升級必須：
  1. 更新頂部 SYNC IMPACT REPORT（保留前一版摘要）
  2. 檢查所有引用 Constitution 版本的 templates
  3. 在 diary.md 記錄變更脈絡
============================================
-->

# {{PROJECT_NAME}} AI Agent Constitution

version: 1.0.0

> 本文件是 AI agent 在本倉庫中操作的最高權威。所有原則為**不可妥協**的底線。
> 若與其他文件衝突，Constitution 優先。

---

## Principle I: Test-First Development（測試先行，不可協商）

**TDD 是所有功能開發的強制要求。**

1. **先寫測試，後寫實作**：測試必須在實作程式碼之前撰寫，且必須先失敗（Red-Green-Refactor 循環）。
2. **測試金字塔**：單元測試為基礎，整合測試為支撐，E2E 測試為補充。避免反轉金字塔（過多 E2E、過少 unit）。
3. **覆蓋率目標**：單元測試覆蓋率目標 ≥80%，整合測試覆蓋率目標 ≥70%。新功能不得低於此門檻。
4. **Contract 測試**：所有 API endpoints 必須有 contract tests，確保請求/回應格式與狀態碼符合預期。
5. **不可跳過測試**：禁止以「先上線再補測試」為理由跳過。若時間不足，縮小功能範圍而非省略測試。

**理由**：測試先行確保需求明確、實作聚焦、回歸防護從一開始就內建。

---

## Principle II: Type Safety First（型別安全優先）

**嚴格型別是程式碼品質的基石。**

1. **禁止 `any`**：不得使用 `any` 型別（`{{LANGUAGE_SPECIFIC}}` 中的等效寬鬆型別亦同）。若確實需要動態型別，使用 `unknown` 並搭配 type guard。
2. **Schema 驅動型別**：從 API schema、資料庫 schema 或 OpenAPI spec 自動產生型別，避免手動維護重複定義。
3. **嚴格模式**：啟用語言/編譯器的最嚴格設定（例如 TypeScript `strict: true`、Rust edition 2021、Python `mypy --strict`）。
4. **型別匯出原則**：公共 API 的型別必須顯式匯出；內部型別不匯出以避免耦合。

> `{{LANGUAGE_SPECIFIC}}`：請替換為專案所用語言的具體規則。
> 範例（TypeScript）：`tsconfig.json 啟用 strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes`
> 範例（Python）：`pyproject.toml 啟用 mypy strict mode, pyright basic`
> 範例（Rust）：`#![deny(unsafe_code)] 除非有安全性文件說明`

**理由**：型別系統是成本最低的 bug 防護層，在編譯期捕捉的錯誤遠比執行期便宜。

---

## Principle III: Security by Default（安全為預設）

**安全不是功能，是前提。**

1. **輸入驗證**：所有外部輸入（使用者輸入、API 請求、環境變數）必須經過驗證與消毒（sanitize），使用 schema validation library（如 Zod、Pydantic、serde）。
2. **認證與授權**：每個受保護的 endpoint 必須驗證身份（authentication）與權限（authorization）。不得僅依賴前端檢查。
3. **機密資訊零容忍**：禁止在程式碼、日誌、錯誤訊息或版本控制中出現 secrets（API keys、passwords、tokens）。所有機密透過環境變數或 secret manager 注入。
4. **最小權限原則**：服務帳號、API tokens、資料庫連線一律使用最小必要權限。

> `{{AUTH_FRAMEWORK}}`：請替換為專案所用的認證/授權框架規則。
> 範例（Database RLS）：`所有 RLS 政策變更必須附帶越權反例測試（adversarial test）`
> 範例（NextAuth）：`middleware.ts 必須保護所有 /api/ 與 /dashboard/ 路由`
> 範例（自建 JWT）：`Token 過期時間 ≤ 1 小時，refresh token 必須綁定裝置`

**理由**：安全漏洞的修復成本隨時間指數增長。預設安全比事後補救有效且便宜。

---

## Principle IV: Code Quality & Maintainability（程式碼品質與可維護性）

**程式碼是寫給人讀的，順便讓機器執行。**

1. **Linting 強制執行**：所有程式碼必須通過 linter 檢查，零 warning 為目標。CI 中 lint 失敗必須阻擋合併。
2. **一致的命名慣例**：遵循專案既定命名風格（`{{LINTER_CONFIG}}` 中定義）。新程式碼必須與現有模式一致。
3. **單一職責**：每個函式、類別、模組只做一件事。若函式超過 50 行或 cyclomatic complexity > 10，必須重構。
4. **禁止死碼**：不得提交被註解掉的程式碼、未使用的 imports、空函式。git history 已保留所有歷史。
5. **文件與程式碼同步**：若修改了行為，對應的文件（JSDoc、README、API docs）必須同步更新。

> `{{LINTER_CONFIG}}`：請替換為專案的 linter 設定路徑與工具。
> 範例（TypeScript + ESLint）：`eslint.config.mjs 使用 @typescript-eslint/recommended-type-checked`
> 範例（Python + Ruff）：`pyproject.toml [tool.ruff] 啟用 E, W, F, I, N, UP rule sets`
> 範例（Rust）：`clippy::pedantic + rustfmt 預設設定`

**理由**：可維護性決定專案的長期生存能力。技術債的複利比金融債更無情。

---

## Principle V: Git Discipline（Git 紀律）

**版本控制是團隊協作的基礎設施，不是個人筆記本。**

1. **Conventional Commits**：所有 commit 訊息必須遵循 [Conventional Commits](https://www.conventionalcommits.org/) 格式：
   ```
   <type>(<scope>): <description>

   [optional body]
   [optional footer]
   ```
   允許的 type：`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`, `build`, `style`

2. **禁止 Force Push 到主分支**：`main`（或 `master`）分支禁止 `git push --force`。例外情況需人類明確授權並記錄原因。

3. **有意義的 Commit**：每個 commit 應代表一個邏輯完整的變更單元。禁止「WIP」、「fix」（無描述）、「update」等模糊訊息。

4. **分支命名規範**：
   - 功能：`feature/<描述>`
   - 修復：`fix/<描述>`
   - 重構：`refactor/<描述>`
   - 文件：`docs/<描述>`
   - 實驗：`experiment/<描述>`

5. **PR 先於合併**：非 trivial 變更應透過 Pull Request 流程，附帶描述與測試證據。

**理由**：清晰的版本歷史是團隊溝通的永久紀錄，也是未來 debug 與 audit 的關鍵資產。

---

## 版本歷史

| 版本    | 日期       | 變更摘要                           |
|---------|------------|-----------------------------------|
| v1.0.0  | {{DATE}}   | 初始建立：5 項通用原則             |

---

## 擴充指引

當專案成長時，建議依需求新增領域專屬原則，例如：

- **Principle VI: Database Architecture** — 主鍵策略、遷移規範、RLS 政策
- **Principle VII: UI/UX Consistency** — 設計系統、元件庫、佈局架構
- **Principle VIII: API Design** — RESTful 慣例、版本控制、錯誤格式
- **Principle IX: Media & Storage** — 檔案上傳、CDN、配額管理

每次新增原則：
1. 版本號 MAJOR +1
2. 更新 SYNC IMPACT REPORT
3. 在 `diary.md` 記錄決策脈絡
4. 檢查所有引用 Constitution 的 templates
