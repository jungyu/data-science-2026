# Ch 08：Capstone 整合

> **本章對應**：[capstone-spec.md](../ai-agent/plan/capstone-spec.md)（評分標準）+
> [task-26](../ai-agent/tasks/task-26-capstone-integration.md)（整合驗收）
>
> **本章目標**：把你的 bot 換成你自己的領域，跑通完整 eval，準備 Demo。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ 4 個替換點全部換成你自己的領域                       ║
║  ✅ 12 個 golden cases，eval 跑通                        ║
║  ✅ 5 分鐘 Demo 腳本能順跑                               ║
╚══════════════════════════════════════════════════════════╝
```

---

## 8-1  Capstone 的核心問題：「換成你的領域」

前七章用 Next.js / 技術文件作為示範領域。
Capstone 的核心任務是：**把這個 bot 換成你真正關心的領域**。

換領域只需要動 4 個地方：

```
╔══════════════════════════════════════════════════════════╗
║  替換點 1：skills/             你的技能路由定義          ║
║  替換點 2：site_rules.py       你的知識庫爬蟲規則        ║
║  替換點 3：知識庫（KB）        你自己抓或整理的文件      ║
║  替換點 4：Feature Extractor   你的領域詞彙              ║
╚══════════════════════════════════════════════════════════╝
```

---

## 8-2  替換點 1：Skills

```python
# skills/your_domain.py

from app.skills.registry import Skill

YOUR_SKILLS = [
    Skill(
        id="domain_faq",
        name="你的領域 FAQ",
        description="回答關於 [你的主題] 的常見問題",
        rag_categories=["your_category"],
        is_rag_required=True,
        always_hitl=False,
    ),
    Skill(
        id="domain_urgent",
        name="緊急情況",
        description="處理 [你的領域] 的緊急情況",
        rag_categories=["your_category", "emergency"],
        is_rag_required=True,
        always_hitl=True,   # 高風險 skill，一律人工審查
    ),
]
```

---

## 8-3  替換點 2：Site Rules（知識庫來源）

```python
# scripts/site_rules.py — 告訴爬蟲哪些 URL / 哪些格式

SITE_RULES = {
    "your_domain": {
        "urls": [
            "https://your-source-1.com/docs/",
            "https://your-source-2.org/guidelines/",
        ],
        "category": "your_category",
        "include_patterns": [r"/docs/", r"/guidelines/"],
        "exclude_patterns": [r"/login", r"/admin"],
    }
}
```

---

## 8-4  替換點 3：知識庫

```bash
# 方案 A：爬網頁
python scripts/crawl_to_markdown.py \
  --rules scripts/site_rules.py \
  --domain your_domain \
  --out docs/RAG/crawled/your_domain/

python scripts/ingest.py \
  --source docs/RAG/crawled/your_domain/ \
  --type markdown

# 方案 B：PDF 入庫（Ch07 學的）
python scripts/ingest.py \
  --source docs/RAG/your_domain.pdf \
  --type pdf \
  --category your_category

# 方案 C：CSV 入庫
python scripts/ingest.py \
  --source docs/RAG/your_data.csv \
  --type csv \
  --text-columns "name,description" \
  --category your_category

# 確認 chunk 數量（建議至少 30 chunks）
python -c "
from app.storage.supabase_client import get_supabase_client
from app.config import Settings
c = get_supabase_client(Settings())
r = c.table('private_knowledge').select('id', count='exact').execute()
print(f'Total chunks: {r.count}')
"
```

---

## 8-5  替換點 4：Feature Extractor

針對你的領域，選擇合適的 extractor 策略：

**封閉詞彙領域**（症狀、法條、程式語言名稱）→ Rule-based：

```python
# app/graph/feature_extractor.py — 你的領域

YOUR_TERMS = {"你的", "領域", "關鍵詞", "列表", ...}

class YourDomainExtractor:
    async def extract(self, user_input: str, **kwargs) -> ExtractedFeatures:
        entities = [t for t in YOUR_TERMS if t in user_input]
        return ExtractedFeatures(
            primary_topic=entities[0] if entities else user_input[:50],
            entities=entities,
            qualifiers=[],
            intent="explain",
            raw_query=user_input,
        )
```

**開放詞彙領域**（一般問答、創意寫作）→ LLM-based（預設即可）。

---

## 8-6  Eval：跑你的 golden case set

確認 `tests/cases/golden.yaml` 已有 12 個你自己領域的 case：

```bash
python scripts/run_eval.py \
  --cases tests/cases/golden.yaml \
  --variants basic selfrag reflection \
  --output reports/eval_baseline.md
```

**Capstone 通過門檻**（取自 capstone-spec.md）：

```
必過門檻（fail 一項 = 不及格）：
  ✅ chunk_recall (selfrag) ≥ 0.60
  ✅ clarify_accuracy ≥ 0.75
  ✅ forbidden_phrase_rate (reflection) = 0.00
  ✅ 至少 30 個你自己領域的 chunk

評分（100 分）：
  A 組（30分）：知識庫品質 + chunk_recall
  B 組（25分）：自動評估品質（groundedness, forbidden）
  C 組（25分）：系統工程（Protocol 解耦, HITL, 多格式）
  D 組（20分）：分析報告（eval baseline, 改善說明）
```

---

## 8-7  Distinction 的加分項目

達到 90 分以上（distinction 等級）通常需要做其中幾項：

```
+3 分：domain-specific Judge axis（例如醫療的 safety、法規的 jurisdiction）
+3 分：自製 Ingester（DrugCSVIngester、CourtDecisionPDFIngester 等）
+3 分：cross-variant A/B eval 報告（不只有數字，有分析和結論）
+2 分：HITL review queue 有 Web UI（不只是 curl）
+1 分：Capstone README 說清楚「2 天換領域」的步驟
```

參考範例：[capstone-medical-distinction.md](../ai-agent/examples/capstone-medical-distinction.md)（107/110 分）

---

## 8-8  Demo 腳本（5 分鐘）

Capstone 的最後是一個 5 分鐘 Demo。建議腳本：

```
時間    內容

0:00   「我做的是 [你的領域] 問答 bot」
        展示：問一個 faq 問題，bot 給出有引用的回答

1:00   「它怎麼處理複合條件問題？」
        展示：問一個 multi_condition 問題，切換 basic vs selfrag
        說明：selfrag 多撈到哪些 chunk，multi-seed 的效果

2:00   「它怎麼知道自己不知道？」
        展示：問一個知識庫沒有的問題
        bot 回「我不確定」而不是亂答

3:00   「它怎麼保證品質？」
        展示：reflection 版本，judge 退件 → reflect → 再審查
        展示：eval baseline 數字，basic vs selfrag vs reflection 比較

4:00   「高風險情況怎麼辦？」
        展示：HITL 觸發 → /api/review/pending 看到暫停的對話
        執行 approve，bot 送出回答

4:45   總結：「換領域只需要動 4 個地方，這個系統設計讓它可以
              在 2 天內換成任何領域」

5:00   結束
```

---

## 8-9  Capstone Checklist

在提交前對照這份清單：

```
知識庫
  □ ≥30 個你自己領域的 chunk
  □ 至少一個非 markdown 格式（PDF 或 CSV）
  □ chunk 有正確的 category 和 frontmatter

Skills
  □ ≥2 個你自己領域的 skill
  □ 至少一個 skill 設定 rag_categories

Eval
  □ golden.yaml 有 12 個 case（4 種類型各 3 個）
  □ eval baseline 表格有三個變體的 6 個 metric
  □ forbidden_phrase_rate (reflection) = 0.00

系統功能
  □ HITL 能 approve / revise / drop
  □ ChannelAdapter Protocol 實作（HTTP adapter 能跑 /api/chat）
  □ KnowledgeStoreAdapter Protocol 實作（Supabase 能用）

分析報告
  □ WEEK1–WEEK7 都有記錄
  □ eval baseline.md 有數字和分析
  □ 能解釋 basic vs selfrag vs reflection 的 trade-off

Demo
  □ 5 分鐘 Demo 腳本練習過
  □ 截圖 / 錄影備份（網路不穩時用）
```

---

## ✏️ 本章任務

1. 完成 4 個替換點（skills / site_rules / KB / Feature Extractor）
2. 跑通 eval，確認三個必過門檻都達成
3. 填寫 `reports/eval_baseline.md`
4. 按照 Demo 腳本練習一次（計時 5 分鐘）
5. 寫完 Capstone README（說明你的領域、如何換成你的設定）

---

## 📝 沒有蠢問題

**Q：我的領域很小眾，抓不到 30 個 chunk 怎麼辦？**

A：30 chunks 是最低要求，你可以：
1. 用多個來源（官方網站 + 論壇 + 文件 + 期刊摘要）
2. 不同粒度的 chunk（大 chunk = 段落，小 chunk = 句子）
3. 如果確實找不到 30 個，在報告裡說明你的資料限制和影響

**Q：eval baseline 的數字比預期差，要怎麼改善？**

A：看哪個 metric 最差：
- `chunk_recall` 差 → 增加 KB、改善 Feature Extractor、調整 fusion 策略
- `clarify_accuracy` 差 → 調整 sufficiency 門檻
- `forbidden_phrase_rate > 0` → 加強 judge prompt 或增加 grounding_check golden cases

**Q：5 分鐘 Demo 太趕了，能要求更多時間嗎？**

A：5 分鐘是建議，實際由課程安排決定。
5 分鐘的目的是逼你「只展示最重要的東西」——
這和真實工作中的 product demo 是一樣的訓練。

---

## 🧠 腦力激盪

> 如果你要把這個 bot 真正上線服務真實使用者，
> 還需要解決哪些問題？
>
> 提示（不需要做，只是思考）：
> - 資料更新：知識庫過期了怎麼辦？定期 re-crawl？
> - 個人化：不同使用者需要不同的回答風格嗎？
> - 多語言：使用者用日文問，知識庫是中文，怎麼處理？
> - 成本控制：如果使用者暴增 100 倍，每月費用是多少？
> - 隱私：使用者的問題會被 OpenAI 儲存嗎？

---

## 🎯 本章里程碑

```
恭喜你完成了整個課程！

你做出了一個：
- 可接 LINE / HTTP / 任何 channel 的 AI 問答 bot（ChannelAdapter Protocol）
- 有多路 embedding 搜尋（multi-seed + RRF fusion）
- 知道自己什麼時候不知道（sufficiency check + clarify）
- 兩段式生成，有自我審查（AnswerContract + JudgeScore + reflect loop）
- 高風險回答等人工確認（HITL interrupt + approve / revise / drop）
- 有量化的 eval 結果（6 個 metric，3 個變體對比）
- 可以在 2 天內換成任何領域（4 個替換點）

這不是玩具——這是一個可以在真實場景使用的架構。

通過門檻：3 個必過指標全達成（chunk_recall ≥ 0.60、clarify_accuracy ≥ 0.75、
forbidden_phrase_rate = 0.00）即為合格（≥60 分）。
Distinction（≥90 分）需要完成加分項目。
```

---

## 📚 繼續學習

完成 Capstone 後，你可以進一步探索：

```
docs/rag-theory/            RAG 的學術背景（論文 + 實作）
docs/ai-agent/specs/        每個功能的設計決策（ADR 格式）
docs/ai-agent/examples/     更多領域的示範（法規、程式教學）
```

準備好把你的 bot 真正「換成你的領域」了嗎？
→ **[Lesson 4：Build Yours](../../Lesson_4_Build_Yours/README.md)**
  逐步引導你完成 4 個替換點、golden case 設計，以及 capstone 提交。

---

上一章 → [Ch 07：多格式 + 人工介入](ch07-multiformat-hitl.md)
回到課程導覽 → [README](README.md)
