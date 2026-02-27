# Ch03 — 你的第一個 Agent 助手

> **「一千個理論不如一次動手。」**

---

## 🎯 本章學習目標

讀完這章，你將能夠：

- [ ] 安裝並設定 Claude Code
- [ ] 完成第一次 Agent 互動
- [ ] 理解 Agent 的權限模型
- [ ] 用 Agent 完成一個真實的開發任務

---

## 準備工作

### 你需要什麼？

```
✅ 一台電腦（macOS / Linux / Windows WSL）
✅ Node.js 18+ 已安裝
✅ Git 已安裝
✅ 一個終端機（Terminal）
✅ 一個 Anthropic API 帳號（或 Claude Pro/Max 訂閱）
```

### 安裝 Claude Code

打開終端機，輸入：

```bash
# 使用 npm 安裝
npm install -g @anthropic-ai/claude-code

# 確認安裝成功
claude --version
```

> 💡 **其他安裝方式**：
> - Homebrew: `brew install claude-code`
> - 直接下載：參考 [官方文件](https://docs.anthropic.com/en/docs/claude-code)

### 首次啟動

```bash
# 進入你的專案目錄
cd ~/my-project

# 啟動 Claude Code
claude
```

首次啟動會要求你登入，按照提示完成認證即可。

---

## 第一次對話：Hello, Agent!

### 基本互動

啟動 Claude Code 後，你會看到一個互動式終端機：

```
╭─────────────────────────────────────╮
│  Claude Code                        │
│  Model: claude-sonnet-4-6           │
│  Working directory: ~/my-project    │
╰─────────────────────────────────────╯

> _
```

試試這些基本指令：

```
> 這個專案是做什麼的？

Claude 會自動：
1. 讀取 README.md
2. 掃描目錄結構
3. 查看 package.json 或其他配置
4. 給你一個專案總覽
```

### 觀察 Agent 的行動

注意 Agent 的回應中會顯示它使用了哪些工具：

```
> 找出這個專案中所有的 TODO 註解

[Claude 的行動]
🔍 Grep: 搜尋 "TODO" 在所有檔案中
📖 Read: 讀取找到的檔案以了解上下文
📋 回報結果：

找到 8 個 TODO 註解：
1. src/auth.js:23 — TODO: 加入 rate limiting
2. src/api/users.js:45 — TODO: 驗證 email 格式
3. ...
```

> 🎯 **觀察重點**：Agent 不只是搜尋文字，它還會讀取上下文，
> 告訴你每個 TODO 的含義和優先順序。

---

## 理解權限模型

### Agent 不是無所不能的

Claude Code 有一個權限系統，確保 Agent 不會做出危險的操作：

```
┌────────────────────────────────────────────────┐
│             權限三級制度                          │
│                                                  │
│  🟢 自動允許（不需確認）                          │
│  ─────────────────────                           │
│  - 讀取檔案                                      │
│  - 搜尋程式碼                                    │
│  - 列出目錄                                      │
│                                                  │
│  🟡 需要確認（Agent 會詢問你）                    │
│  ─────────────────────────                       │
│  - 修改檔案                                      │
│  - 執行 Shell 命令                               │
│  - 安裝套件                                      │
│                                                  │
│  🔴 永遠禁止（即使你要求也不行）                  │
│  ─────────────────────────────                   │
│  - Force push to main                            │
│  - rm -rf /                                      │
│  - 刪除 .git 目錄                                │
│                                                  │
└────────────────────────────────────────────────┘
```

### 權限設定檔

在專案中建立 `.claude/settings.json`：

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(npm test)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Bash(git push --force)",
      "Bash(rm -rf)",
      "Bash(git reset --hard)"
    ]
  }
}
```

> 💡 **最佳實踐**：一開始用較嚴格的權限，隨著你對 Agent 的信任增加，
> 再逐步放寬。這就像帶新人 —— 先觀察，再授權。

---

## 實戰練習：用 Agent 完成真實任務

### 任務：建立一個簡單的待辦事項 API

讓我們一步步用 Agent 來完成一個真實的小專案。

#### Step 1：初始化專案

```
> 幫我初始化一個 Node.js 專案，使用 Express 框架，
  包含基本的待辦事項 CRUD API。
  請先告訴我你的計畫，不要直接動手。
```

Agent 會回應一個計畫，例如：

```
我的計畫如下：

1. 初始化 npm 專案
2. 安裝依賴：express
3. 建立目錄結構：
   - src/
     - index.js      (入口)
     - routes/
       - todos.js    (路由)
     - controllers/
       - todoController.js (邏輯)
4. 實作 CRUD 端點：
   - GET    /api/todos
   - POST   /api/todos
   - PUT    /api/todos/:id
   - DELETE /api/todos/:id
5. 新增基本的錯誤處理

要我繼續嗎？
```

> 🎯 **關鍵技巧**：注意我們說了「先告訴我你的計畫」。
> 這是一個重要的習慣 —— 讓 Agent 先規劃，你審閱後再執行。
> 這就是 Plan-and-Execute 模式的應用。

#### Step 2：審閱並執行

```
> 計畫看起來不錯。請按計畫執行，
  但用 ES Modules (import/export) 而不是 CommonJS。
```

Agent 會開始：
1. 建立檔案
2. 寫程式碼
3. 每個步驟都會顯示它在做什麼

#### Step 3：驗證結果

```
> 啟動伺服器，用 curl 測試所有端點。
```

Agent 會：
1. 啟動伺服器
2. 逐一測試每個端點
3. 報告結果

#### Step 4：改進

```
> 幫我加上輸入驗證 —— title 不能為空，
  超過 100 個字要截斷。
```

觀察 Agent 如何：
1. 讀取現有程式碼
2. 找到正確的修改位置
3. 加入驗證邏輯
4. 保持程式碼風格一致

---

## Agent 溝通的黃金法則

從這次實戰中，我們可以總結出幾個和 Agent 溝通的基本原則：

### 1. 先規劃，後執行

```
❌ 不好：「幫我寫一個 API。」
✅ 好的：「幫我寫一個 API，先告訴我你的計畫。」
```

### 2. 提供充足的上下文

```
❌ 不好：「修好這個 Bug。」
✅ 好的：「src/auth.js 的 login 函式在 token 過期時
         回傳 500 而不是 401。請修好這個 Bug。」
```

### 3. 指定約束條件

```
❌ 不好：「新增使用者認證。」
✅ 好的：「新增使用者認證，使用 JWT，
         token 有效期 24 小時，
         密碼用 bcrypt 加密。」
```

### 4. 要求解釋

```
❌ 不好：（直接接受 Agent 的修改）
✅ 好的：「為什麼你選擇這個方案而不是另一個？」
```

### 5. 分步驟進行

```
❌ 不好：「幫我重構整個專案。」
✅ 好的：「先分析目前的程式碼品質問題，
         然後按優先順序列出要重構的部分，
         我們一個一個來。」
```

---

## CLAUDE.md：你的 Agent 說明書

每個專案可以有一個 `CLAUDE.md` 檔案，告訴 Agent 專案的規則和偏好。

### 基本範例

在專案根目錄建立 `CLAUDE.md`：

```markdown
# 專案規則

## 技術堆疊
- Runtime: Node.js 20
- Framework: Express 5
- Language: TypeScript (strict mode)
- Database: PostgreSQL + Prisma ORM
- Testing: Vitest

## 編碼規範
- 使用 ES Modules (import/export)
- 函式優先於 class
- 所有 API 回應使用統一格式：{ data, error, meta }
- 錯誤處理使用自定義 AppError class

## Git 規範
- Commit message 使用 Conventional Commits
- 不允許直接 push 到 main
- PR 必須附帶測試

## 禁止事項
- 不使用 any 型別
- 不使用 console.log（使用 logger）
- 不在程式碼中硬編碼密鑰
```

> 💡 **這很重要**：CLAUDE.md 會自動載入到 Agent 的上下文中。
> 寫好這個檔案，Agent 就會遵守你的專案規範。
> 我們會在 Ch07-Ch10 深入討論如何設計完整的治理規則。

---

## 常見問題排解

### 「Agent 不理解我的需求」

```
可能原因：
1. 指令太模糊 → 提供更具體的上下文
2. 專案結構複雜 → 先讓 Agent 了解專案（「分析這個專案的架構」）
3. 對話太長 → 開新對話，重新提供關鍵上下文
```

### 「Agent 修改了不該改的檔案」

```
解決方法：
1. 在指令中明確指定範圍（「只修改 src/auth.js」）
2. 設定權限（deny list 中加入敏感檔案）
3. 要求先展示計畫
```

### 「Agent 的程式碼風格和專案不一致」

```
解決方法：
1. 在 CLAUDE.md 中定義編碼規範
2. 指定參考檔案（「請參考 src/api/users.js 的風格」）
3. 如果有 ESLint/Prettier，讓 Agent 跑一次格式化
```

### 「Agent 卡住了，一直重複同樣的錯誤」

```
解決方法：
1. 中斷 Agent（按 Escape）
2. 描述你觀察到的問題
3. 給出不同方向的提示
4. 如果仍然卡住，開新對話
```

---

## 章末練習

### 🧪 動手做

1. **安裝 Claude Code** 並完成首次設定

2. **專案探索**：在你現有的專案中啟動 Claude Code，讓它分析：
   - 專案結構和技術堆疊
   - 程式碼品質問題
   - 潛在的安全風險

3. **小任務**：讓 Agent 完成以下任一任務：
   - 幫你的專案新增一個簡單的功能
   - 修復一個已知的 Bug
   - 為某個函式寫單元測試

4. **建立 CLAUDE.md**：為你的專案寫一個基本的 CLAUDE.md 檔案

### 🤔 思考題

1. 為什麼「先規劃再執行」比「直接開始做」更好？
2. 權限模型的目的是什麼？如果沒有權限限制會發生什麼？
3. CLAUDE.md 和程式碼中的註解有什麼不同？

---

## 關鍵概念回顧

| 概念 | 一句話總結 |
|------|-----------|
| Claude Code | Anthropic 的 CLI AI Agent 工具 |
| 權限模型 | 三級制度：自動允許、需確認、永遠禁止 |
| CLAUDE.md | 專案級的 Agent 規則設定檔 |
| Plan-and-Execute | 讓 Agent 先規劃再執行的最佳實踐 |
| 上下文提供 | 給 Agent 越多相關資訊，結果越好 |

---

> **下一章預告**：[Ch04 — 提示工程：與 Agent 溝通的藝術](ch04-prompt-engineering.md)
>
> 你已經會基本的 Agent 互動了。但要真正發揮 Agent 的力量，
> 你需要學會「提示工程」—— 讓 Agent 精確理解你意圖的技術。
