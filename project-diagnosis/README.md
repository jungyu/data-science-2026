# project-diagnosis

中醫診斷 RAG 系統 — 以「症狀 → 證型 → 治法」為主軸的可解釋檢索增強生成架構。

## 核心理念

**Ontology-first + Hybrid Retrieval + Evidence-based Generation**

中醫診斷不是關鍵字比對，而是多訊號、跨層級、帶矛盾消解的辨證過程。
本系統把辨證過程轉成可檢索、可排序、可解釋、可反駁的知識系統。

## 目錄結構

```
project-diagnosis/
├── docs/
│   ├── adr/
│   │   └── ADR-001-tcm-rag-architecture.md   # 架構決策記錄
│   └── whitepaper/
│       └── tcm-rag-whitepaper.md             # 系統白皮書
├── docs/specs/                                # 12 份模組化 spec（權威）
│   ├── spec-001-system-overview.md
│   ├── spec-002-feature-extractor.md
│   ├── ... (003 ~ 011)
│   └── README.md
├── spec/
│   └── tcm-rag-system-spec.md                # 已 deprecated，重定向到 docs/specs/
├── sql/
│   ├── tcm-rag.schema.sql                    # PostgreSQL schema
│   └── tcm-rag.seed.sql                      # 最小可用 seed 資料
├── schemas/
│   └── knowledge-atom.schema.json            # 知識原子 JSON Schema
└── scripts/
    └── embed_atoms.py                        # Embedding pipeline
```

## 快速開始

### 1. 建立資料庫

```bash
# Supabase / PostgreSQL 15+
psql $DATABASE_URL -f sql/tcm-rag.schema.sql
psql $DATABASE_URL -f sql/tcm-rag.seed.sql
```

### 2. 執行 embedding

```bash
pip install psycopg openai

export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."

# 先做 dry run 確認
EMBEDDING_DRY_RUN=true python scripts/embed_atoms.py

# 正式執行
python scripts/embed_atoms.py
```

### 3. 環境變數

| 變數                      | 預設值                    | 說明                  |
| ------------------------- | ------------------------- | --------------------- |
| `DATABASE_URL`            | —（必填）                 | PostgreSQL 連線字串   |
| `OPENAI_API_KEY`          | —（必填）                 | OpenAI API 金鑰       |
| `OPENAI_EMBEDDING_MODEL`  | `text-embedding-3-small`  | Embedding 模型        |
| `EMBEDDING_BATCH_SIZE`    | `20`                      | 每批處理的 atom 數量  |
| `EMBEDDING_DRY_RUN`       | `false`                   | 是否只印 log 不寫入   |
| `EMBEDDING_ONLY_ACTIVE`   | `true`                    | 只處理 is_active 的   |
| `EMBEDDING_SLEEP_SECONDS` | `0.5`                     | 批次間休眠秒數        |

## 知識原子類型

| atom_type           | 說明    | 例子                  |
| ------------------- | ------- | --------------------- |
| `symptom`           | 症狀    | 盜汗、自汗、潮熱      |
| `sign`              | 體徵    | 面赤、肢冷、神疲      |
| `tongue_feature`    | 舌象    | 舌紅少苔、舌淡        |
| `pulse_feature`     | 脈象    | 脈細數、脈虛          |
| `pattern`           | 證型    | 陰虛內熱、衛氣不固    |
| `pathomechanism`    | 病因病機| 陰虛火旺、氣虛不固    |
| `treatment_principle` | 治法  | 養陰清熱、益氣固表    |
| `formula`           | 方劑    | 知柏地黃丸、玉屏風散  |
| `herb`              | 藥物    | 黃耆、浮小麥          |
| `citation`          | 引文    | 傷寒論條文            |
| `case`              | 醫案    | 臨床案例              |

## 實作路線

- **Phase 1 (MVP)**：症狀 → 候選證型 → 證據引用
- **Phase 2**：加入反證與鑑別診斷邏輯
- **Phase 3**：接入經典文獻與醫案

## 相關文件

- [白皮書](docs/whitepaper/tcm-rag-whitepaper.md)
- [ADR-001](docs/adr/ADR-001-tcm-rag-architecture.md)
- [Specifications 索引](docs/specs/README.md)（12 份模組化 spec）
