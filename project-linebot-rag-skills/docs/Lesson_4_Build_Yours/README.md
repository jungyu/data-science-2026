# Lesson 4：Build Yours — 換成你的領域

> **時間**：約 6–8 小時（含知識庫建置）

## 先修：Lesson 1–3 必須完成

| 前置條件 | 說明 |
|----------|------|
| ✅ Supabase schema 已建立、示範 KB 已入庫 | 見 [Lesson 1](../Lesson_1_Supabase_Vector_db/README.md)、[Lesson 2](../Lesson_2_Playwright_to_Vector_db/README.md) |
| ✅ `selfrag` 和 `reflection` graph variant 跑通過 | 見 [Lesson 3](../Lesson_3_LangGraph_RAG/README.md) |
| ✅ `.env` 已設定（`GRAPH_VARIANT`、`ROUTER_MODEL`、`GENERATOR_MODEL`） | 見 [.env.GUIDE.md](../.env.GUIDE.md) |

Lesson 4 假設你已理解 Graph 的架構；本課只針對「換領域」的四個替換點，不重複解釋 LangGraph 基礎。

---

```
╔══════════════════════════════════════════════════════════╗
║  你會做到：                                              ║
║  ✅ bot 回答的是你自己領域的問題，不是 Next.js 示範      ║
║  ✅ eval 的 6 個 metric 都有你自己的數字                 ║
║  ✅ 能選你想要的表達層（LINE / HTTP / Telegram / Web）   ║
╚══════════════════════════════════════════════════════════╝
```

## 四個替換點

```
替換點 1  scripts/site_rules.py    加你的域名 + CSS selector
替換點 2  skills/<你的領域>/        定義 skill（rag_categories 對齊 KB）
替換點 3  app/graph/feature_extractor.py  rule-based / LLM / hybrid 選一
替換點 4  app/channels/            選你的表達層
```

每個替換點完成後都有一個 **eval gate**（可量化的驗收門檻）。

## 章節地圖

| 章 | 替換點 | 核心程式 |
|----|--------|---------|
| [Ch 01](ch01-site-rules-kb.md) | 知識庫（site_rules + ingest） | `scripts/site_rules.py` |
| [Ch 02](ch02-skills.md) | Skill 定義 | `skills/*/SKILL.md`、`scripts/seed_skills.py` |
| [Ch 03](ch03-feature-extractor.md) | Feature Extractor | `app/graph/feature_extractor.py` |
| [Ch 04](ch04-channel.md) | 表達層（channel） | `app/channels/` |
| [Ch 05](ch05-eval-gate.md) | Eval Gate | `scripts/eval.py`、`tests/cases/golden.yaml` |

---

## 驗收：pytest + eval

**每個替換點做完後**：

```bash
# 確認現有測試沒有退步
pytest --tb=short -q

# Eval Gate 1–3：確認 KB / skill / extractor 正常
pytest tests/ -k "your_domain or skill or extractor" -v

# Eval Gate 最終驗收（Ch05，需要 golden.yaml）
python scripts/eval.py \
  --cases tests/cases/golden_your_domain.yaml \
  --variants basic selfrag reflection \
  --output reports/eval_YOUR_DOMAIN.md

cat reports/eval_YOUR_DOMAIN.md   # 確認三個必過門檻
```

**三個必過門檻**（任一未達成 = Capstone 不完整）：

| 門檻 | 標準 |
|------|------|
| `chunk_recall (selfrag)` | ≥ 0.60 |
| `clarify_accuracy` | ≥ 0.75 |
| `forbidden_phrase_rate (reflection)` | = 0.00 |
