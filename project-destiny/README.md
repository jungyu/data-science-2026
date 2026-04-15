# project-destiny

八字解盤 RAG 系統 — 架構文件與可執行規格套件

## 專案定位

這不是一個「命理聊天機器人」。

這是一套以「規則先行、知識可計算、生成有根據」為核心原則的命理 RAG 系統。

核心設計假設：

> 八字是高結構化符號系統。LLM 在其中的角色是「有約束的口譯員」，不是「主推理者」。

## 目錄結構

```
project-destiny/
├── docs/
│   ├── architecture/
│   │   └── bazi-rag-system-plan.md   # 系統架構總覽
│   ├── adr/                          # Architecture Decision Records
│   │   ├── README.md
│   │   ├── ADR-001 ~ ADR-008
│   │   └── ADR-TEMPLATE.md
│   └── specs/                        # 實作規格
│       ├── README.md
│       └── spec-001 ~ spec-011
├── schemas/                          # JSON Schema 定義
│   ├── knowledge-atom.schema.json
│   ├── bazi-chart.schema.json
│   ├── rule-output.schema.json
│   ├── retrieval-result.schema.json
│   └── analysis-output.schema.json
└── migrations/
    └── 001_initial_schema.sql        # PostgreSQL + pgvector DDL
```

## 三層防呆骨架

1. **確定性排盤**：排盤不交給 LLM，由獨立 deterministic 模組處理 → ADR-003
2. **規則先行**：Rule Engine 先判定格局與特徵，再做 RAG 召回 → ADR-005
3. **Grounded Generation**：生成結果必須可追溯，不足時明示不確定性 → ADR-008

## 快速開始

### 0. 啟動本機 Postgres（選用）

```bash
docker compose up -d     # pgvector/pgvector:pg16，自動跑 migrations/
```

### 1. 建立 DB Schema 與 seed（若未使用 docker compose）

```bash
psql $DATABASE_URL -f migrations/001_initial_schema.sql
psql $DATABASE_URL -f migrations/002_seed_ziping_atoms.sql
psql $DATABASE_URL -f migrations/003_more_evaluation_cases.sql
```

### 2. 安裝 Python 套件

```bash
cp .env.example .env            # 填入 DATABASE_URL / OPENAI_API_KEY
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 3. 回填 embedding

```bash
destiny backfill-embeddings
```

### 4. 執行完整分析

```bash
# 排盤 → 規則 → 檢索（不呼叫 LLM）
destiny analyze --birth 1990-08-15T14:30:00 --tz Asia/Taipei

# 加上 LLM grounded 生成
destiny explain --birth 1990-08-15T14:30:00 --tz Asia/Taipei

# 含 Layer D 自動審查
destiny explain --birth 1990-08-15T14:30:00 --tz Asia/Taipei --judge

# 單獨呼叫各模組
destiny chart --birth 1990-08-15T14:30:00 --tz Asia/Taipei
destiny query --text "申月甲木正官格" --day-master 甲 --month-branch 申 --pattern 正官格
```

### 5. 跑評估集

```bash
destiny eval
```

輸出 chart / pattern / atom recall 三項 Phase 0 指標。

### 6. 匯入新古籍片段（半自動 ETL）

```bash
# examples/ingest-sample.jsonl 內含 3 段待標註的子平真詮原文
destiny ingest examples/ingest-sample.jsonl
```

流程：LLM 依 Spec-003a prompt 標註 → schema 驗證 → 寫入 `status='draft'`。
人工覆核後手動升級：

```sql
UPDATE bazi.knowledge_atoms SET status='active' WHERE atom_code='...';
```

再跑 `destiny backfill-embeddings` 即完成入庫。

或直接用 SQL：

```sql
SELECT * FROM bazi.match_knowledge_atoms(
  query_embedding := '[...]'::vector,
  p_day_master_tags := ARRAY['甲'],
  p_month_branch_tags := ARRAY['申'],
  p_pattern_tags := ARRAY['正官格']
);
```

### 5. 查閱文件

- 架構決策：[docs/adr/README.md](./docs/adr/README.md)
- 實作規格：[docs/specs/README.md](./docs/specs/README.md)
- 系統總覽：[docs/architecture/bazi-rag-system-plan.md](./docs/architecture/bazi-rag-system-plan.md)

## 文獻優先序

| Priority | 著作 | 角色 |
|----------|------|------|
| 1 | 子平真詮 | 格局、強弱、用神主骨架 |
| 2 | 滴天髓 | 高階修正、氣象、變格 |
| 3 | 三命通會 | 描述性擴展、案例對照 |
| 4 | 千里命稿 | 現代語境映射 |

## Phase 0 目標

- [ ] Bazi Engine MVP
- [ ] 子平真詮首批 atoms 入庫
- [ ] Metadata + Vector 檢索閉環
- [ ] Rule Engine v0（主流格局候選）
- [ ] Grounded generation 輸出格式
- [ ] 5+ 黃金評估案例通過
