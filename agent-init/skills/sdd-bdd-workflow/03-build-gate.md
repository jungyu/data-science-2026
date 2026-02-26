# Build Gate Prompt - 建置關

> **目的**: 工匠式落地與重構，遵循 TDD 流程。

## 🎯 核心任務

1. **測試骨架 (Red)** - 先建立失敗的測試
2. **最小實作 (Green)** - 以最快路徑達成測試通過
3. **架構重構 (Refactor)** - 抽離具體實現至 Adapter

## 🔧 介面抽象化要求

確保核心邏輯與單一工具解耦：
- **RendererAdapter** - 渲染引擎可替換
- **Exporter 模式** - I/O 操作與 UI 層隔離
- **Repository 模式** - 資料存取抽象化

## 📊 可觀測性要求

- **日誌 (Logs)**: 輸出執行步驟與耗時
- **錯誤處理**: 對應 `01-spec.md` 中的錯誤分類
- **指標 (Metrics)**: 監控失敗率

---

## Prompt Template

```markdown
# Role
你是一位資深軟體工程師，負責實作功能並確保程式碼品質。

# Context
我已完成規格 (`01-spec.md`) 與情境 (`02-scenarios.feature`)，現在進入實作階段。

# Task
請依照 TDD 流程實作功能。

## Phase 1: Red (建立測試骨架)

根據 `02-scenarios.feature`，建立對應的測試檔案：

test/[feature-name]/[feature].test.ts
describe('[Feature Name]', () => {
  describe('Happy Path', () => {
    it('should [expected behavior]', async () => {
      // Arrange
      // Act
      // Assert
      expect(true).toBe(false); // Red - 故意失敗
    });
  });
});


## Phase 2: Green (最小實作)

實作最少量的程式碼使測試通過：
- 不要過度設計
- 不要提前優化
- 專注於功能正確性

## Phase 3: Refactor (架構重構)

確保程式碼符合以下原則：

### 介面抽象化
ts
// 定義 Adapter 介面
interface ThemeExporter {
  export(theme: Theme): Promise<ExportResult>;
}

// 具體實作
class MarkdownThemeExporter implements ThemeExporter {
  async export(theme: Theme): Promise<ExportResult> {
    // Markdown 格式專屬實作
  }
}


### 可觀測性
ts
logger.info('[ThemeCopy] Starting copy', { 
  sourceId, 
  userId,
  timestamp: new Date().toISOString() 
});

const startTime = performance.now();
// ... 執行邏輯
const duration = performance.now() - startTime;

logger.info('[ThemeCopy] Completed', { duration, newThemeId });


# Constraints
- 每次只實作 1-2 個任務
- 完成後列出變更檔案清單
- 標註對應的 BDD Scenario
```

---

## 原子化任務規範

> [!IMPORTANT]
> 每次只允許 AI 執行 **1-2 個任務**。

完成後必須附上：
- ✅ 變更檔案列表
- ✅ 新增 API 端點
- ✅ 對應的 BDD Scenario

範例回報格式：

```markdown
## 完成任務：建立測試骨架

### 變更檔案
- `tests/themes/theme-copy.test.ts` [NEW]
- `lib/themes/types.ts` [MODIFIED]

### 對應 Scenario
- ✅ Scenario: 成功複製主題
- ✅ Scenario: 無權複製他人主題

### 下一步
- [ ] Phase 2: 實作 ThemeCopyService
```
