# W1 Demo 拍片腳本（5 分鐘）

> 目標：5 分鐘讓學生看完 W1 milestone 的完整 e2e — 抓網頁 → ingest → 跑 graph → 看 cost。
>
> 設備：terminal 螢幕錄製（OBS / QuickTime / asciinema）。建議字級 14–16 pt，顯示 100×30 字元以上。
>
> 配套：[w1-demo-runbook.sh](#預錄環境準備腳本) 一次跑完所有準備工作；攝影師只要照著本腳本逐幕念白 + 跑指令。

## Total budget: 5 分鐘

| 幕 | 時長 | 主題 |
|----|------|------|
| 1 | 0:00–0:20 | 開場 + 環境檢查 |
| 2 | 0:20–1:20 | 爬 2 個 URL → markdown |
| 3 | 1:20–1:35 | 看 frontmatter |
| 4 | 1:35–2:35 | Ingest 到 sqlite-vec |
| 5 | 2:35–4:05 | 跑 graph 端對端 |
| 6 | 4:05–4:35 | 看 trace + cost |
| 7 | 4:35–5:00 | 收尾 + 下一步 |

---

## 預錄環境準備腳本

把這份存成 `scripts/w1_demo_setup.sh`，**錄影前**跑一次（不收錄）：

```bash
#!/bin/bash
# W1 demo 錄影前的環境準備（不收錄）
set -e
cd /path/to/project-linebot-rag-skills

# 確保依賴齊全
python -m pip install -e ".[dev,crawler]" --quiet
python -m playwright install chromium

# 預先 crawl（避免錄影時等網路）
mkdir -p /tmp/w1_demo
cat > /tmp/w1_demo/urls.txt << 'EOF'
https://nextjs.org/docs/app/building-your-application/rendering/server-components
https://nextjs.org/docs/app/building-your-application/rendering/client-components
EOF

# 清掉舊 db 與 markdown
rm -f /tmp/w1_demo/test_kb.db
rm -rf /tmp/w1_demo/crawled
mkdir -p /tmp/w1_demo/crawled

echo "✅ 環境就緒，開始錄影"
```

---

## 幕 1：開場（0:00 – 0:20，20 秒）

### [螢幕]

```bash
$ pwd
/Users/aaron/Projects/data-science-2026/project-linebot-rag-skills

$ ls
README.md  app  docs  pyproject.toml  scripts  skills  supabase  tests
```

### [念白]

> 「今天 5 分鐘走 W1 — RAG + LangGraph 教學專案的第一週 milestone：抓網頁、進知識庫、跑 graph，全部用真 OpenAI key + sqlite-vec、不需要任何雲端帳號。」

---

## 幕 2：爬 2 個 URL（0:20 – 1:20，60 秒）

### [螢幕]

```bash
$ cat /tmp/w1_demo/urls.txt
https://nextjs.org/docs/app/building-your-application/rendering/server-components
https://nextjs.org/docs/app/building-your-application/rendering/client-components

$ python scripts/crawl_to_markdown.py \
    --urls /tmp/w1_demo/urls.txt \
    --out /tmp/w1_demo/crawled \
    --category engineering \
    --concurrency 2
```

**[等待輸出 ~10s]**

```
2026-05-05 21:49:22 INFO wrote nextjs_org__docs_..._server-components.md (14618 chars)
2026-05-05 21:49:22 INFO wrote nextjs_org__docs_..._client-components.md (14618 chars)
2026-05-05 21:49:22 INFO done: {'wrote': 2}
```

### [念白]

> 「Playwright 開無頭 chromium，抓 2 個 Next.js docs 頁面。內建 robots.txt 檢查、user-agent 標明意圖、1 秒節流。」
>
> 「**注意我用 `--category engineering`，這要對齊待會兒 router 路由到 tech_architect skill 時的 rag_categories**——這是 W1 第一個常見坑。」
>
> 「14600 字元抽出主內容，約 10 秒搞定。」

---

## 幕 3：看 frontmatter（1:20 – 1:35，15 秒）

### [螢幕]

```bash
$ head -10 /tmp/w1_demo/crawled/nextjs_org__docs_*_server-components.md
```

```yaml
---
source_url: https://nextjs.org/docs/app/building-your-application/rendering/server-components
source_title: 'Getting Started: Server and Client Components | Next.js'
crawled_at: '2026-05-05T13:49:22+00:00'
content_hash: ae2a68f5c80e1389
category: engineering
tags:
- nextjs.org
---
```

### [念白]

> 「frontmatter 是 task-18 的設計重點：**source_url、content_hash、category 全部隨檔案走**，後面 ingest 時 metadata 會流到每個 chunk，最後出現在 narrative 的 `[來源 N]` 標記。」

---

## 幕 4：Ingest 到 sqlite-vec（1:35 – 2:35，60 秒）

### [螢幕]

```bash
$ KNOWLEDGE_STORE_BACKEND=sqlite_vec \
    SQLITE_VEC_PATH=/tmp/w1_demo/test_kb.db \
    python scripts/ingest.py markdown \
    --paths "/tmp/w1_demo/crawled/*.md" \
    --category engineering
```

**[等待輸出 ~30s — embedding API 呼叫]**

```
[markdown] docs=2 chunks=28 skipped=0
```

```bash
$ ls -lh /tmp/w1_demo/test_kb.db
-rw-r--r--  1 aaron  wheel   6.4M May  5 14:22 /tmp/w1_demo/test_kb.db
```

### [念白]

> 「`KNOWLEDGE_STORE_BACKEND=sqlite_vec` 切到離線 backend——學生不需要 Supabase 帳號就能跑通整套。」
>
> 「2 份檔案切成 28 chunks，每個 chunk 經 OpenAI embedding API 算 1536 維向量，存進 6.4MB sqlite 檔。embedding 成本約 $0.0008。」

---

## 幕 5：跑 graph 端對端（2:35 – 4:05，90 秒）

### [螢幕]

```bash
$ AI_PROVIDER=openai EMBEDDING_PROVIDER=openai \
    KNOWLEDGE_STORE_BACKEND=sqlite_vec \
    SQLITE_VEC_PATH=/tmp/w1_demo/test_kb.db \
    SUFFICIENCY_MIN_FEATURE_OVERLAP=0 \
    JUDGE_ENABLED=false \
    python scripts/w1_demo_run.py \
    "我在做 Next.js 系統設計，要怎麼落地決定哪些用 Server Components 哪些用 Client Components？" \
    selfrag
```

**[等待 ~30s — multi-seed embedding × 4、router、generator]**

```
=== W1 e2e: variant=selfrag provider=openai store=sqlite_vec ===

router_result.target_skill: tech_architect
router_result.is_rag_required: True

features:
  primary_topic: 'Next.js 系統設計中的 Server Components 與 Client Components 選擇'
  qualifiers:    ['Next.js']
  intent:        decide
  entities:      ['Next.js', 'Server Components', 'Client Components']

seeds: 4 條
hits_per_seed: [8, 8, 8, 8]
rag_chunks: 4

answer_contract:
  summary:    關於「Next.js 系統設計中的 Server Components 與 Client Components 選擇」的如何決定。
  findings:   4
  citations:  4

responses (first 800 chars):
  ## 回覆：Next.js 系統設計中的 Server Components 與 Client Components 選擇
  ### 主要發現
  1. ...詳細說明文件，路徑為 `/docs/app/...`[來源 1][來源 2]
  ...
  ### 來源
  1. https://nextjs.org/docs/app/building-your-application/rendering/client-components
  2. https://nextjs.org/docs/app/building-your-application/rendering/server-components
```

### [念白]

> 「跑 selfrag variant — task-12 的 graph 實作。注意觀察 4 個關鍵欄位：」
>
> 1. **router**：把 query 路由到 tech_architect skill，is_rag_required=True
> 2. **features**：LLM 結構化抽取——primary_topic、qualifiers、intent、entities 全都對
> 3. **seeds × 4 → hits_per_seed=[8,8,8,8]**：multi-seed fan-out + 並行檢索 + fusion
> 4. **answer_contract**：4 個 findings、4 個 citations，每個 finding 都標 `[來源 N]`
>
> 「最重要的：`[來源 1]` 後面真的是 nextjs.org URL——這是 **grounded generation** 的承諾。」

---

## 幕 6：看 trace + cost（4:05 – 4:35，30 秒）

### [螢幕]

```
[stub channel] pushed:
  to=U_test_e2e chars=1152

[tracer] events=36 input_tokens=1900 output_tokens=611 cost=$0.007382
```

### [念白]

> 「這次完整 invocation：36 個 trace events、1900 input + 611 output tokens、總成本 7 厘錢。」
>
> 「task-22 observability 把每個 node 的耗時、每個 LLM 呼叫的 token 都記下來。學生跑完整 8 週 lesson plan 估算 $5–10。」

---

## 幕 7：收尾 + 下一步（4:35 – 5:00，25 秒）

### [螢幕]

```bash
$ ls docs/ai-agent/plan/
lesson-plan.md  roadmap.md

$ ls docs/ai-agent/examples/
crawl-recipe-nextjs.md       hitl-walkthrough.md
eval-baseline.md             ingest-csv-walkthrough.md
feature-extractor-medical.md ingest-pdf-walkthrough.md
graph-basic.mermaid          variants-comparison.md
graph-selfrag.mermaid        w1-e2e-verification.md
graph-reflection.mermaid     w2-w8-e2e-verification.md
```

### [念白]

> 「W1 走完。剩下 7 週的進度都在 `lesson-plan.md`，每週一個 milestone。」
>
> 「W2 multi-seed 細節 / W3 sufficiency / W4 reflection / W5 eval / W6 多 channel + 多 store / W7 PDF + HITL / W8 自選領域 demo。」
>
> 「想轉成自己的領域？看 `doc-01-transferability-guide.md`，4 個 Tier 的 swap diff 都列好了。」
>
> 「教學主線結束。」

---

## 拍片注意事項

### 攝影前

- 終端機放大字級至 14–16 pt
- 清空螢幕空間（Cmd-K 或 `clear`）
- 切換到專案根目錄
- 預先跑 `w1_demo_setup.sh`
- 確認 `.env` 已設 `OPENAI_API_KEY`
- 把 `scripts/w1_demo_run.py` 複製到 `scripts/w1_demo.py` 方便指 caller

### 拍片中

- 每個指令貼上去後**停 1–2 秒**等待，讓觀眾看清
- 輸出長段（如 narrative）滾動時口頭重複關鍵字（「來源 1」、「來源 2」）
- cost 數字念出來（讓觀眾感受規模）

### 後製

- 標題卡：「W1 — RAG + LangGraph 教學第一週 milestone」
- 章節 marker：每幕一個（YouTube chapter）
- 字幕 burn-in：螢幕字級 14 pt 對行動裝置不夠清楚

### 上線檢查

- [ ] 影片 ≤ 5 分 30 秒（5 分目標 + 30 秒寬限）
- [ ] 含 `lesson-plan.md` 連結（影片描述）
- [ ] 含 `w1-e2e-verification.md` 連結
- [ ] 含 GitHub repo 連結
- [ ] 字幕至少有英文（國際學生）

---

## 進階（≤10 分鐘版）

如果有 10 分鐘預算可加幕：

| 幕 | 時長 | 內容 |
|---|------|------|
| 8 | 5:00–6:30 | 切 basic variant 跑同 query，**看 narrative 多醜**（無 citation、無結構） |
| 9 | 6:30–7:30 | 切 reflection variant，**啟用 judge** 看 retry 行為 |
| 10 | 7:30–9:00 | 跑 `eval.py --quick`，看三變體 metric 對比表 |
| 11 | 9:00–10:00 | 簡介 doc-01 transferability guide |

幕 8 是「為什麼要 selfrag」最有力的視覺證據——basic 沒有 grounded constraint 時 hallucination 風險直觀。

---

*本腳本配套：[w1-e2e-verification.md](./w1-e2e-verification.md) 是真實跑過的 log；攝影師若想看每行指令的「實際輸出長什麼樣」就翻那份。*
