# Ch12 — 走向生產：部署、監控與成本控制

> **「能在本地跑起來只是開始，能在生產環境可靠運行才是真功夫。」**

---

## 🎯 本章學習目標

讀完這章，你將能夠：

- [ ] 設計 Agent 系統的生產部署策略
- [ ] 建立 Token 預算管理機制
- [ ] 監控 Agent 的運行狀況和品質
- [ ] 制定團隊的 Agent 使用規範

---

## 從實驗到生產

### 個人使用 vs 團隊使用

```
個人使用：
- 自己設定 CLAUDE.md
- 自己控制 Agent 行為
- Token 成本自己承擔
- 出了問題自己修

團隊使用：
- 統一的治理框架
- 一致的品質標準
- 共享的 Token 預算
- 團隊的審查機制
```

---

## Token 預算管理

### 為什麼要管理 Token？

```
Token = 💰 金錢

一次簡單的互動：~5K tokens ≈ $0.01
一次中等任務：~30K tokens ≈ $0.10
一次大型重構：~100K tokens ≈ $0.50
一天高強度使用：~500K tokens ≈ $2.50
一個月團隊使用：~30M tokens ≈ $150

不管理 = 帳單驚喜
```

### Token 預算策略

```yaml
# config/token-budget.yaml

budgets:
  simple:
    target: 5K
    max: 10K
    examples:
      - 修正錯字
      - 單一函式修改
      - 簡單查詢

  moderate:
    target: 15K
    max: 30K
    examples:
      - 3-5 個檔案修改
      - 新增 API 端點
      - 中等重構

  complex:
    target: 30K
    max: 60K
    examples:
      - 架構變更
      - 跨模組重構
      - 大型功能開發

  research:
    target: 10K
    max: 20K
    examples:
      - 方案評估
      - 框架選擇
      - 技術調研
```

### 省 Token 的技巧

```
┌──────────────────────────────────────────────────┐
│          Token 節省最佳實踐                       │
│                                                    │
│  ✅ 做                                             │
│  ────                                              │
│  1. 指定檔案路徑，避免全域搜尋                     │
│  2. 一次性提供完整需求                             │
│  3. 使用 CLAUDE.md 減少重複說明                    │
│  4. 適當的時候開新對話（避免上下文膨脹）           │
│  5. 簡單任務用較小的模型                           │
│                                                    │
│  ❌ 不做                                           │
│  ────                                              │
│  1. 不要讓 Agent 讀整個目錄才開始                  │
│  2. 不要重複讀同一個檔案                           │
│  3. 不要在簡單任務上用 --ultrathink                │
│  4. 不要濫用 Task 子代理（有成本）                 │
│  5. 不要擠牙膏式對話（一次比一次多說一點）         │
│                                                    │
└──────────────────────────────────────────────────┘
```

---

## 操作日誌（Action Logs）

### 為什麼需要日誌？

```
沒有日誌：
「上週 Agent 改了什麼？」 → 「不知道」
「那次 Bug 是怎麼修的？」 → 「找不到記錄」
「這個月 Token 花在哪了？」 → 「查帳單吧」

有日誌：
「上週 Agent 改了什麼？」 → 查看 logs/2024-03-W12.md
「那次 Bug 是怎麼修的？」 → 查看 logs/2024-03-10-auth-fix.md
「這個月 Token 花在哪了？」 → 查看 logs/ 的 Token 統計
```

### 日誌格式

```markdown
# Session Log: 2024-03-15 Auth 重構

## 基本資訊
- 日期：2024-03-15
- 執行者：Alice
- Agent：Claude Code (claude-sonnet-4-6)
- 持續時間：45 分鐘
- Token 消耗：~28K

## 任務摘要
將 auth 模組從 Session-based 遷移到 JWT

## 變更清單
- ✅ src/auth/middleware.ts — 改用 JWT 驗證
- ✅ src/auth/login.ts — 回傳 JWT token
- ✅ src/auth/register.ts — 同步修改
- ✅ tests/auth/ — 更新所有測試
- ✅ .env.example — 新增 JWT_SECRET

## 觸發的治理規則
- L1 MUST STOP: Auth 系統修改 → 人類已審查
- SEC-002: 確認密碼處理正確

## 決策記錄
- 選擇 RS256 而非 HS256（已記入 diary）
- Token 有效期設為 24h（PM 確認）

## 未完成項目
- [ ] 重整 token 刷新機制
- [ ] 舊 session 的清理腳本
```

---

## 團隊 Agent 使用規範

### 建立共同約定

```markdown
# Team Agent Policy

## 誰可以使用 Agent？
- 所有團隊成員都可以使用
- 新人前 2 週需要有人 pair review Agent 的產出

## 什麼時候使用 Agent？
- ✅ 重構、Bug 修復、新功能開發
- ✅ 程式碼審查、品質分析
- ⚠️ 安全相關修改（需要第二人審查）
- ❌ 直接部署到 production

## Agent 的產出需要審查嗎？
- 修改 < 3 個檔案：自行審查
- 修改 3-10 個檔案：至少 1 人 code review
- 修改 > 10 個檔案：需要 2 人 code review

## Token 預算
- 每人每天：100K tokens
- 超出需要申請
- 每月團隊回顧 Token 使用情況

## 記錄要求
- 每次重大操作需要寫 session log
- 技術決策需要記入 diary
- 觸發 L1 規則時需要留下審查記錄
```

---

## 漸進式導入 Agent

### 第一階段：試水（1-2 週）

```
目標：讓團隊熟悉 Agent 的基本操作

做什麼：
- 1-2 位先驅者先用
- 只用在低風險任務（Bug 修復、測試撰寫）
- 收集經驗和回饋
- 建立初步的 CLAUDE.md

不做什麼：
- 不在核心模組使用
- 不做大型重構
- 不修改治理框架
```

### 第二階段：擴展（2-4 週）

```
目標：擴大使用範圍，建立治理框架

做什麼：
- 全團隊開始使用
- 建立 constitution.md 和 semantic-deny
- 設定 human-review-triggers
- 開始記錄 decision diary
- 建立 Token 預算

不做什麼：
- 不做自動化部署
- 不讓 Agent 無監督地大量修改
```

### 第三階段：成熟（持續）

```
目標：Agent 成為團隊的日常工具

做什麼：
- 多 Agent 協作
- 自動化品質管線
- 定期回顧和優化治理框架
- 用 Agent 做 code review
- 持續更新 patterns.md

持續改善：
- 每月回顧 Token 使用效率
- 每季回顧治理框架的有效性
- 收集團隊的最佳實踐
```

---

## 常見的生產問題

### 問題 1：Agent 和 CI/CD 衝突

```
症狀：Agent 的修改在 CI/CD 中失敗

原因：
- Agent 沒有跑 CI 中的某些檢查
- Agent 使用了 CI 環境中沒有的工具

解決：
- 在 CLAUDE.md 中列出 CI 的所有檢查命令
- 要求 Agent 在提交前跑完所有 CI 檢查
```

### 問題 2：多人同時使用 Agent 修改同一個檔案

```
症狀：合併衝突頻繁

解決：
- 使用 feature branch
- 在 standup 中同步 Agent 任務分配
- 避免讓 Agent 修改共用的核心檔案（除非協調好）
```

### 問題 3：Token 成本失控

```
症狀：月底帳單比預期高

解決：
- 設定每日 Token 上限
- 使用 dashboard 追蹤消耗
- 定期分析哪些操作最消耗 Token
- 優化高消耗的工作流程
```

---

## 章末練習

### 🧪 動手做

1. **Token 分析**：追蹤你使用 Agent 一天的 Token 消耗，
   分析哪類操作消耗最多，有沒有優化空間。

2. **團隊規範**：為你的團隊草擬一份「Agent 使用規範」，
   涵蓋使用範圍、審查要求、Token 預算。

3. **操作日誌**：為你今天的 Agent 操作寫一份 session log，
   包含任務摘要、變更清單、決策記錄。

### 🤔 思考題

1. 如果 Agent 的 Token 成本降低 10 倍，你會改變使用策略嗎？怎麼改？
2. Agent 的操作日誌和 Git commit history 有什麼互補關係？
3. 團隊中有人過度依賴 Agent，不再自己思考怎麼辦？

---

## 關鍵概念回顧

| 概念 | 一句話總結 |
|------|-----------|
| Token 預算 | 按操作類型設定 Token 上限，控制成本 |
| 操作日誌 | 記錄 Agent 的每次重大操作，保持可追溯 |
| 團隊規範 | 統一的 Agent 使用政策和審查機制 |
| 漸進式導入 | 試水 → 擴展 → 成熟，逐步建立信任 |

---

> **下一章預告**：[Ch13 — 畢業專案：打造你的 Agent 治理框架](ch13-capstone.md)
>
> 恭喜你走到這裡！最後一章，我們將把所有學到的知識整合起來，
> 從零打造一個完整的 Agent 治理框架。
