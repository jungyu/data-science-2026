# 第零章：環境建置

## 學習目標

讀完本章，你將能夠：
- 建立完整的本地開發環境（Python、Docker、向量資料庫）
- 執行單元測試驗證安裝正確性
- 理解專案目錄結構與各模組的角色
- 啟動 MCP Server 進行知識庫操作

---

## 0.1 系統需求

| 項目 | 最低版本 | 用途 |
|------|---------|------|
| Python | 3.11+ | 核心執行環境 |
| Docker Desktop | 4.x | 執行 Qdrant 向量資料庫 |
| Git | 2.x | 版本控制 |
| OpenAI API Key | — | 嵌入向量與答案生成 |

> 💡 建議使用 macOS 或 Linux。Windows 用戶請使用 WSL2。

---

## 0.2 快速開始（7 步驟）

### Step 1：取得專案

```bash
git clone <repository-url>
cd project-first
```

### Step 2：建立虛擬環境

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows (PowerShell)
```

### Step 3：安裝依賴

```bash
pip install -r requirements.txt
```

安裝完成後應可成功匯入核心模組：

```bash
python -c "from src.ingestion.chunker import RecursiveChunker; print('✅ Import OK')"
```

### Step 4：設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入你的 OpenAI API Key：

```
OPENAI_API_KEY=sk-your-key-here
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=enterprise_knowledge
LOG_LEVEL=INFO
```

> 🔑 **絕對不要**把 `.env` 加入版本控制。專案已在 `.gitignore` 中排除。

### Step 5：啟動向量資料庫

```bash
docker compose up -d
```

驗證 Qdrant 正在執行：

```bash
curl http://localhost:6333/healthz
# 預期回傳: OK
```

Qdrant Web UI 可在 `http://localhost:6333/dashboard` 查看。

### Step 6：執行測試

```bash
# 執行單元測試（不需要 Qdrant 和 API Key）
pytest tests/unit/ -v

# 執行整合測試（需要 Qdrant 運行中）
pytest tests/evaluation/ -v -m integration
```

所有單元測試應全部通過。整合測試需要 Qdrant 運行中且 `.env` 設定正確。

### Step 7：啟動 MCP Server（選做）

```bash
cd mcp-servers/knowledge-mcp
pip install -r requirements.txt
python3 server.py --namespace hr-* --readonly
```

目前範例為 **scaffold 模式**：已提供 3 個工具介面與參數驗證，但尚未接入真實向量資料庫與文件 registry。
可先用它驗證工具契約；完成 Ch09 實作後再接入實際 retrieval pipeline。

---

## 0.3 專案結構總覽

```
project-first/
├── index.md                          # 課程首頁（章節地圖）
├── 00-setup.md                       # ← 你在這裡
├── 01-introduction.md ~ 10-putting-it-together.md  # 10 個章節
│
├── src/                              # Python 原始碼
│   ├── utils.py                      # 共用工具（Chunk、tokenize、例外類別）
│   ├── rag/core.py                   # RAG 核心函式（Ch01）
│   ├── config/llm_config.py          # LLM 硬限制設定（Ch08）
│   ├── models/knowledge.py           # KnowledgeDocument 資料模型（Ch07）
│   ├── ingestion/                    # 知識攝取模組
│   │   ├── chunker.py               #   遞迴分塊器（Ch06）
│   │   ├── embedder.py              #   OpenAI 嵌入器（Ch06）
│   │   ├── ingestor.py              #   契約式攝取器（Ch05）
│   │   ├── versioned_ingestor.py    #   版本化攝取器（Ch07）
│   │   └── atomic_ingest.py         #   原子性更新（Ch07）
│   ├── retrieval/
│   │   └── retrieval_gate.py        # 檢索品質閘門（Ch05）
│   ├── query/
│   │   ├── query_pipeline.py        # RAG 查詢管線（Ch05）
│   │   └── hallucination_shield.py  # 幻覺防護盾（Ch08）
│   └── governance/
│       ├── drift_detector.py        # 知識漂移偵測（Ch05）
│       └── hitl_checker.py          # HITL 風險檢查（Ch08）
│
├── tests/                            # 測試
│   ├── conftest.py                   # 共用 fixtures
│   ├── unit/test_chunking.py         # 分塊器單元測試（Ch03）
│   └── evaluation/test_retrieval_quality.py  # 檢索品質評測（Ch03）
│
├── features/                         # BDD 場景（Gherkin）
│   ├── knowledge_ingestion.feature   # 攝取場景（Ch03）
│   └── knowledge_query.feature       # 查詢場景（Ch03）
│
├── mcp-servers/knowledge-mcp/        # MCP Server（Ch09）
│   ├── server.py                     # 3 個知識庫工具
│   └── requirements.txt
│
├── docs/ADR/                         # 架構決策記錄（Ch02）
│   ├── ADR-001-embedding-model.md
│   ├── ADR-002-chunking-strategy.md
│   └── README.md
│
├── .agent/                           # AI Agent 治理層
│   ├── memory/
│   │   ├── constitution.md           # 憲法（5 條原則）（Ch02）
│   │   └── diary.md                  # 決策日記（Ch02）
│   ├── config/
│   │   └── token-budget.yaml         # Token 預算（Ch09）
│   ├── rules/
│   │   ├── semantic-deny.md          # 語意禁止規則（Ch08）
│   │   └── human-review-triggers.md  # HITL 觸發條件（Ch08）
│   ├── skills/
│   │   ├── ingest-skill/SKILL.md     # 攝取技能（Ch09）
│   │   ├── query-skill/SKILL.md      # 查詢技能（Ch09）
│   │   ├── governance/rules/         # 品質閘門規則（Ch08）
│   │   └── rag-workflow/             # RAG 工作流（Ch03-04）
│   │       ├── SKILL.md
│   │       ├── 00-complexity-gate.md # 複雜度評估
│   │       ├── 01-spec-gate.md       # 規格完整性
│   │       ├── 02-scenario-gate.md   # BDD 場景
│   │       ├── 03-build-gate.md      # 建置品質
│   │       ├── 04-eval-gate.md       # RAG 評測
│   │       └── templates/            # Lite / Standard 模板
│   ├── tasks/inbox/                  # 任務包範例（Ch09）
│   ├── logs/                         # Action Log（Ch09）
│   └── mcp-servers/                  # MCP 組態（Ch09）
│
├── pyproject.toml                    # Python 套件定義
├── requirements.txt                  # 依賴清單
├── .env.example                      # 環境變數模板
└── docker-compose.yml                # Qdrant 向量資料庫
```

---

## 0.4 常見問題排除

### Q1：`ModuleNotFoundError: No module named 'src'`

確認你在 `project-first/` 目錄下，且虛擬環境已啟動：

```bash
cd project-first
source .venv/bin/activate
python -c "import src; print('OK')"
```

若仍有問題，檢查 `tests/conftest.py` 是否正確將 `src/` 加入 `sys.path`。

### Q2：`docker compose up` 失敗

確認 Docker Desktop 正在執行：

```bash
docker info    # 應顯示 Docker Engine 資訊
```

若 port 6333 被占用：

```bash
lsof -i :6333  # 查看占用程序
```

### Q3：OpenAI API 回傳 401 Unauthorized

確認 `.env` 中的 `OPENAI_API_KEY` 正確且未過期：

```bash
# 快速測試 API Key
python -c "
from openai import OpenAI
client = OpenAI()
print(client.models.list().data[0].id)
"
```

### Q4：pytest 找不到測試

確認從專案根目錄執行：

```bash
cd project-first
pytest tests/unit/ -v --tb=short
```

---

## 0.5 下一步

環境建置完成後，建議的學習路徑：

1. **Ch01**：了解 RAG 的基本原理和為何需要治理
2. **Ch02**：建立憲法式治理的思維框架
3. 按照 `index.md` 的章節地圖依序閱讀

> 💡 每章的「練習」部分會用到本章建好的開發環境。建議邊讀邊跑程式碼。
