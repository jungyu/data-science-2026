# drone_data — 無人機 / 機器人主題的完整 ingest 範例

把三個真實站點接入 ch08 Supabase pipeline，最終供 ch09 RAG bridge 使用。
每支腳本獨立可跑，也可一次跑完做端對端示範。

## 來源組合

| # | 來源 | 性質 | 寫入路徑 | 合規性 |
|---|------|------|----------|--------|
| 01 | [PX4 Autopilot Docs](https://docs.px4.io/main/en/) | Docusaurus 文件站 | Playwright → crawl_queue → worker → articles | CC-BY，可放心爬 |
| 02 | [IEEE Robotics & Automation Society](https://www.ieee-ras.org/) | WordPress 學會站 | Playwright → crawl_queue → worker → articles | 公開頁面，請額外檢查 robots.txt |
| 03 | [OpenAlex API](https://api.openalex.org/) (drone, 2020-2026) | REST API | 直接 API → articles（繞過 crawl_queue） | 完全免費、無 ToS 限制 |

> 第 03 號刻意**取代** IEEE Xplore 搜尋頁。IEEE Xplore 的服務條款明確禁止
> 自動化爬取，OpenAlex 是合規的 metadata 替代方案，涵蓋 IEEE 收錄項。

## 架構

```
                                ┌────────────────────┐
                                │  crawler.sources   │
                                │  ──────────────    │
                                │  px4-docs          │  ← 01
                                │  ieee-ras          │  ← 02
                                │  openalex-drone    │  ← 03
                                └─────────┬──────────┘
                                          │
                ┌─────────────────────────┼─────────────────────────┐
                ▼                         ▼                         ▼
       ┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
       │  crawl_queue    │       │  crawl_queue    │       │   (no queue)     │
       │  PX4 種子 URLs  │       │  RAS 種子 URLs  │       │  直接 API ingest │
       └────────┬────────┘       └────────┬────────┘       └────────┬─────────┘
                │                         │                         │
                └────────────┬────────────┘                         │
                             ▼                                      ▼
              ┌──────────────────────────────┐         ┌──────────────────────┐
              │   utils/worker/main.py       │         │  urllib + API        │
              │   PageRunner（async）         │         │  inverted_index →    │
              │   schema-driven extractors   │         │  abstract            │
              └──────────────┬───────────────┘         └──────────┬───────────┘
                             │                                    │
                             └────────────────┬───────────────────┘
                                              ▼
                                  ┌────────────────────┐
                                  │ crawler.articles   │
                                  └─────────┬──────────┘
                                            ▼
                                   ch09 RAG bridge
                                   ingest → embed → LINE Bot
```

## 執行流程

### 一次跑完三支來源

```bash
cd project-playwright

# 1. 啟用 [supabase] 與 [all] extras（首次）
uv pip install -e ".[all]"

# 2. .env 必須有 SUPABASE_URL、SUPABASE_SERVICE_KEY、PROJECT_ID
cp .env.example .env
# … 編輯 .env …

# 3. 寫入三個 source + 兩個來源的 crawl_queue 種子
python examples/drone_data/01_seed_px4_docs.py
python examples/drone_data/02_seed_ieee_ras.py

# 4. 啟動 async worker（消費 px4-docs + ieee-ras 的佇列）
python -m utils.worker.main

# 5. 第三支直接呼叫 OpenAlex API 寫入 articles
python examples/drone_data/03_ingest_openalex.py --max-pages 4

# 6. 驗收 articles 是否落地
python ch09-rag-bridge/04_end_to_end_demo.py
```

### 只跑單一來源

每支腳本都可獨立執行，無互相依賴。建議第一次先跑 PX4（最穩定），
驗證環境後再跑其他。

## 學習重點

| 範例 | 教學意圖 |
|------|----------|
| 01 PX4 | schema-driven extractor — 不寫 Python 也能定義新站點，靠 `extractor_schema` jsonb |
| 02 IEEE RAS | 對「結構不那麼穩定」的站點，selector 容許多種 fallback（`h2 a, h3 a, .field-content > a`） |
| 03 OpenAlex | API 路徑取代爬蟲：當合規或品質允許，REST API 永遠優於 HTML scraping；展示 inverted_index abstract 重建 |

## 客製化指引

### 改查詢字串

```bash
python examples/drone_data/03_ingest_openalex.py \
  --query "swarm robotics" --year-from 2023 --max-pages 10
```

### 改 PX4 / IEEE RAS 的擷取 selector

編輯 `01_seed_px4_docs.py` 或 `02_seed_ieee_ras.py` 內的
`ExtractorSchema`，重跑該腳本即可（會 upsert source 設定）。
不需要動 worker 程式碼。

### OpenAlex polite pool（推薦）

```bash
echo 'OPENALEX_MAILTO=you@example.com' >> .env
```

OpenAlex 鼓勵帶 mailto 進入 polite pool，回應更快、優先級更高。

## 與 ch09 RAG bridge 的串接

執行完上述任一來源並有 articles 落地後，到 project-linebot-rag-skills 跑：

```bash
cd ../project-linebot-rag-skills
python scripts/ingest.py articles --category robotics   # 依分類 embed
```

完成後即可向 LINE Bot 提問「PX4 的 flight modes 有哪些？」或
「2024 年的 drone 論文有什麼主題？」，驗證跨專案 pipeline 完整貫通。

## 已知限制

- IEEE RAS 站點若改版，`ExtractorSchema` 內的 selector 可能失效 —
  worker 不會誤判為 bug，會留下空 articles，建議定期人工抽查
- OpenAlex 的 `abstract_inverted_index` 偶爾為 null（出版社未授權），
  此時 `abstract` 欄位會是 None，下游 RAG 仍可用 title + meta 索引
- 三支腳本都假設你已執行 `ch08-supabase/00_apply_schema.py` 之類的
  migration，把 `crawler.sources` / `crawl_queue` / `articles` 表建好
