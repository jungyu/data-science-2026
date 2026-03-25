# 期末專題（40 分）

---

## 題目選擇（擇一）

1. 股票分析 API 平台
2. YouTube 數據分析平台
3. 電商銷售預測平台
4. AI 文本分析平台

---

## 專題要求

### 必須包含的技術元素

| 項目 | 必須 | 說明 |
|------|------|------|
| PostgreSQL 設計 | ✔ | 至少 3 個資料表，含 Foreign Key |
| JSONB 使用 | ✔ | 至少 1 個 JSONB 欄位，含查詢 |
| Index 設計 | ✔ | 至少 1 個 Index，說明理由 |
| Python API | ✔ | 使用 supabase-py 進行 CRUD |
| RLS | ✔ | 至少 2 條 Policy |
| REST 測試 | ✔ | 使用 curl 或 Python 測試 API |
| Docker 本地開發 | ✔ | 使用 `supabase init` + `supabase start` |
| Migration | ✔ | 所有 DDL 透過 Migration 管理 |

---

## 繳交內容

### 1. 程式碼（Git Repository）

```
project/
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   │   ├── 001_create_tables.sql
│   │   ├── 002_add_indexes.sql
│   │   └── 003_add_rls.sql
│   └── seed.sql
├── src/
│   ├── main.py          # 主程式
│   └── test_api.py      # API 測試
├── requirements.txt
└── README.md
```

### 2. 簡報（10 分鐘）

- 系統架構圖
- 資料模型（ER Diagram）
- 核心功能展示
- RLS 效果展示
- 遇到的問題與解決方式

### 3. 文件

- README.md（專案說明、安裝方式、使用方式）
- 資料模型說明

---

## 各題目詳細需求

### 選項 1：股票分析 API 平台

- `stocks` — 股票基本資料
- `prices` — 歷史價格（含 JSONB 技術指標）
- `predictions` — 模型預測結果
- RLS：使用者只能看到自己的預測

### 選項 2：YouTube 數據分析平台

- `channels` — 頻道資料
- `videos` — 影片資料（含 JSONB metadata）
- `analytics` — 分析結果
- RLS：各頻道管理者只能看到自己的資料

### 選項 3：電商銷售預測平台

- `products` — 商品資料
- `sales` — 銷售紀錄
- `forecasts` — 銷售預測（含 JSONB 模型輸出）
- RLS：各店家只能看到自己的預測

### 選項 4：AI 文本分析平台

- `documents` — 文件資料
- `analyses` — 分析結果（含 JSONB NLP 輸出）
- `users` — 使用者資料
- RLS：使用者只能看到自己上傳的文件

---

## 評分 Rubric（40 分）

| 指標 | 分數 | 詳細說明 |
|------|------|----------|
| 資料模型合理性 | 10 | 資料表設計合理、正規化程度適當、關聯正確 |
| SQL 技術能力 | 10 | DDL/DML 正確、JSONB 使用得當、Index 有依據 |
| Supabase 使用 | 10 | Python SDK 使用正確、REST API 測試通過、Migration 管理 |
| 安全設計（RLS） | 5 | Policy 正確且有效、能說明設計理由 |
| 簡報清晰度 | 5 | 架構圖清楚、展示流暢、問答表現 |

### 各等級說明

#### 資料模型合理性（10 分）

| 等級 | 分數 | 標準 |
|------|------|------|
| 優秀 | 9-10 | 資料表設計優良，正規化合理，關聯完整且有意義 |
| 良好 | 7-8 | 資料表設計正確，有適當關聯，小缺陷 |
| 及格 | 5-6 | 基本結構正確，但設計有明顯改進空間 |
| 不及格 | 0-4 | 結構錯誤或不完整 |

#### SQL 技術能力（10 分）

| 等級 | 分數 | 標準 |
|------|------|------|
| 優秀 | 9-10 | SQL 語法完全正確，JSONB 查詢靈活，Index 有效 |
| 良好 | 7-8 | SQL 語法正確，有基本 JSONB 查詢和 Index |
| 及格 | 5-6 | 基本 SQL 正確，但進階功能使用不足 |
| 不及格 | 0-4 | SQL 語法錯誤或缺少必要功能 |

#### Supabase 使用（10 分）

| 等級 | 分數 | 標準 |
|------|------|------|
| 優秀 | 9-10 | SDK 使用完整，API 測試充分，Migration 管理良好 |
| 良好 | 7-8 | SDK 基本操作正確，有 API 測試和 Migration |
| 及格 | 5-6 | 能連線和基本操作，但功能不完整 |
| 不及格 | 0-4 | 無法正確使用 Supabase |

---

## 時程建議

| 週次 | 工作內容 |
|------|----------|
| Week 16 | 選題、設計資料模型、建立 Migration |
| Week 17 | 實作 Python API、RLS、測試 |
| Week 18 | 簡報準備、最終測試、發表 |
