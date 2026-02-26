# 四句咒語協議 - AI 任務交辦指令

> **目的**: 標準化與 AI Agent 的溝通協議，確保規格驅動開發。

---

## 🔮 四句咒語

在與 AI Agent（Copilot CLI, Antigravity, Claude Code, Codex）交辦任務時，請使用以下指令：

### 1️⃣ Spec first

```
Spec first: 更新 specs/[feature-name]/01-spec.md，列出缺口、狀態機與錯誤風險，暫不寫碼。
```

**AI 應該做的事**:
- 分析需求，找出模糊地帶
- 定義狀態機
- 列出錯誤分類
- 定義 NFR

**AI 不該做的事**:
- ❌ 開始寫程式碼
- ❌ 建立檔案結構

---

### 2️⃣ Scenarios

```
Scenarios: 萃取 3-7 條 specs/[feature-name]/02-scenarios.feature，並標註測試層級（e2e/int/unit）。
```

**AI 應該做的事**:
- 從 `01-spec.md` 萃取關鍵情境
- 撰寫 Gherkin Feature 文件
- 標註測試層級 Tag

**AI 不該做的事**:
- ❌ 寫超過 7 條情境
- ❌ 追求 100% 覆蓋率

---

### 3️⃣ Tests first

```
Tests first: 建立對應測試骨架，確保先紅燈、後綠燈。
```

**AI 應該做的事**:
- 根據 `02-scenarios.feature` 建立測試檔案
- 寫出 Arrange/Act/Assert 結構
- 確保測試先失敗 (Red)

**AI 不該做的事**:
- ❌ 同時完成實作
- ❌ 寫空的測試

---

### 4️⃣ Refactor for swap

```
Refactor for swap: 確保具備 Adapter 介面層，並補強可觀測性日誌。
```

**AI 應該做的事**:
- 抽離具體實作到 Adapter
- 加入 logger 記錄關鍵步驟
- 確保底層技術可替換

**AI 不該做的事**:
- ❌ 過度設計
- ❌ 加入未使用的抽象層

---

## 📋 完整交辦範例

```markdown
## 任務：實作主題複製功能

### Step 1
Spec first: 更新 specs/theme-copy/01-spec.md，定義複製流程的狀態機、錯誤分類與權限規則。

### Step 2
Scenarios: 萃取 5 條 specs/theme-copy/02-scenarios.feature，覆蓋：
1. Happy path (複製成功)
2. 權限檢查 (無權複製)
3. 名稱重複檢查
4. 儲存空間不足
5. 並發複製衝突

### Step 3
Tests first: 建立 tests/themes/theme-copy.test.ts 測試骨架。

### Step 4
Refactor for swap: 確保 ThemeExporter 可替換為不同輸出格式 (Markdown/JSON/YAML)。
```

---

## 🚫 反模式警告

| 反模式 | 問題 | 正確做法 |
|--------|------|----------|
| 一次交辦所有步驟 | AI 會跳過規格直接寫碼 | 逐步交辦，確認完成再下一步 |
| 模糊的需求描述 | AI 會自行假設並產生錯誤實作 | 先完成 Spec Gate |
| 要求「盡快完成」 | AI 會省略測試與重構 | 堅持 TDD 流程 |
| 不檢查產出 | 錯誤累積難以回溯 | 每個 Gate 都要驗收 |
