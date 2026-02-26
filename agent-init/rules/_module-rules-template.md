---
name: {{module-name}}-rules
description: "{{MODULE_NAME}} 模組開發規則"
tags: ["rules", "{{module-name}}"]
---

# {{MODULE_NAME}} 模組規則

> 本文件定義 {{MODULE_NAME}} 模組的架構邊界、不變量與開發規範。
> AI agent 在修改此模組時必須遵守以下規則。

---

## 目的

{{MODULE_PURPOSE}}

<!--
填寫範例：
此模組負責使用者認證與授權，包含 login/register/OAuth 流程、
session 管理、權限檢查等功能。是系統安全的核心防線。
-->

---

## 架構邊界

### 允許路徑（Allowed Paths）

此模組的程式碼僅限存在於以下路徑：

```
{{ALLOWED_PATHS}}
```

<!--
填寫範例：
lib/auth/
app/api/auth/
components/auth/
__tests__/auth/
-->

### 禁止路徑（Forbidden Paths）

此模組的程式碼**不得**出現在以下路徑：

```
{{FORBIDDEN_PATHS}}
```

<!--
填寫範例：
components/shared/    # 不得將 auth 邏輯混入共用元件
lib/core/             # 不得將 auth 邏輯混入核心基礎設施
app/api/writer/       # 不得在其他 domain 的 API route 中直接處理 auth
-->

### 依賴方向

```
{{DEPENDENCY_DIRECTION}}
```

<!--
填寫範例：
lib/core/ → lib/auth/ → app/api/auth/ → components/auth/
（箭頭方向為「被依賴 → 依賴者」，禁止反向依賴）
-->

---

## 不變量（Invariants）

以下為此模組的不可違反規則，AI agent 須在每次修改後自我檢查：

| ID | 不變量 | 檢查方式 |
|----|--------|----------|
| INV-{{M}}-1 | {{INVARIANT_1}} | {{CHECK_METHOD_1}} |
| INV-{{M}}-2 | {{INVARIANT_2}} | {{CHECK_METHOD_2}} |
| INV-{{M}}-3 | {{INVARIANT_3}} | {{CHECK_METHOD_3}} |

<!--
填寫範例：
| ID | 不變量 | 檢查方式 |
|----|--------|----------|
| INV-AUTH-1 | 所有 API route 必須經過 auth middleware | grep 檢查 route handler 是否呼叫 requireAuth() |
| INV-AUTH-2 | Token 必須設定 expiry（不得永久有效） | 搜尋 token 建立處，確認有 expiresIn 參數 |
| INV-AUTH-3 | 密碼 hash 只能使用 bcrypt/argon2 | 搜尋 password 相關處理，確認使用核准的 hash 函式 |
-->

---

## 命名慣例

| 類型 | 慣例 | 範例 |
|------|------|------|
| 檔案 | {{FILE_NAMING}} | {{FILE_EXAMPLE}} |
| 函式 | {{FUNCTION_NAMING}} | {{FUNCTION_EXAMPLE}} |
| 型別 | {{TYPE_NAMING}} | {{TYPE_EXAMPLE}} |
| 常數 | {{CONST_NAMING}} | {{CONST_EXAMPLE}} |
| 測試 | {{TEST_NAMING}} | {{TEST_EXAMPLE}} |

<!--
填寫範例：
| 類型 | 慣例 | 範例 |
|------|------|------|
| 檔案 | kebab-case | auth-service.ts |
| 函式 | camelCase，動詞開頭 | verifyToken(), createSession() |
| 型別 | PascalCase | AuthSession, UserCredentials |
| 常數 | UPPER_SNAKE_CASE | MAX_LOGIN_ATTEMPTS, TOKEN_TTL |
| 測試 | describe("模組名") > it("行為") | describe("AuthService") > it("應拒絕過期 token") |
-->

---

## 測試策略

### 必要測試

| 測試類型 | 覆蓋目標 | 最低覆蓋率 |
|----------|----------|------------|
| 單元測試 | {{UNIT_TARGET}} | {{UNIT_COV}}% |
| 整合測試 | {{INTEGRATION_TARGET}} | {{INTEGRATION_COV}}% |
| E2E 測試 | {{E2E_TARGET}} | {{E2E_COV}} |

<!--
填寫範例：
| 測試類型 | 覆蓋目標 | 最低覆蓋率 |
|----------|----------|------------|
| 單元測試 | 所有 service 函式、utility 函式 | 80% |
| 整合測試 | API route handler + middleware chain | 70% |
| E2E 測試 | login、register、OAuth 完整流程 | 關鍵路徑 100% |
-->

### 測試命名規範

```
describe("{{ModuleName}}") {
  describe("{{functionName}}") {
    it("應在 [條件] 時 [預期行為]")
    it("應在 [邊界情況] 時 [預期行為]")
    it("不應在 [異常情況] 時 [非預期行為]")
  }
}
```

---

## 常見錯誤

AI agent 在修改此模組時，須特別注意以下常見錯誤：

| ID | 錯誤描述 | 正確做法 |
|----|----------|----------|
| ERR-{{M}}-1 | {{ERROR_1}} | {{CORRECT_1}} |
| ERR-{{M}}-2 | {{ERROR_2}} | {{CORRECT_2}} |
| ERR-{{M}}-3 | {{ERROR_3}} | {{CORRECT_3}} |

<!--
填寫範例：
| ID | 錯誤描述 | 正確做法 |
|----|----------|----------|
| ERR-AUTH-1 | 在 middleware 中吞掉認證錯誤 | 必須 throw 或 return 401/403 |
| ERR-AUTH-2 | 用 == 比較 token 字串 | 使用 timingSafeEqual 防止 timing attack |
| ERR-AUTH-3 | 忘記在 OAuth callback 中驗證 state 參數 | 必須驗證 state 以防 CSRF |
-->

---

## 參考文件

| 文件 | 路徑 | 說明 |
|------|------|------|
| {{REF_1_NAME}} | {{REF_1_PATH}} | {{REF_1_DESC}} |
| {{REF_2_NAME}} | {{REF_2_PATH}} | {{REF_2_DESC}} |

<!--
填寫範例：
| 文件 | 路徑 | 說明 |
|------|------|------|
| 架構文件 | docs/architecture/AUTH.md | 認證模組架構設計 |
| ADR | docs/AI/decisions/ADR-003-auth-strategy.md | 認證策略決策記錄 |
| API 規格 | docs/api/auth-endpoints.md | 認證 API endpoint 規格 |
-->

---

## 使用說明

1. 複製本模板，將所有 `{{PLACEHOLDER}}` 替換為實際值
2. 儲存至 `.agent-init/rules/{{module-name}}-rules.md`
3. 在 `copilot-instructions.md` 的模組分類中加入此模組
4. 由模組負責人 review 後合併

> 模板最後更新：{{DATE}}
