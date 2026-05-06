# Ch 00：環境設定

> **本章目標**：讓所有工具在你的機器上跑起來，在第一行業務邏輯之前確認環境可用。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ pytest 全綠                                          ║
║  ✅ 本地服務在 http://localhost:8000 回應 {"status":"ok"} ║
║  ✅ curl /api/chat 能收到 bot 回應（HTTP channel）       ║
║  ⬜ ngrok + LINE webhook（選做，Ch06 再接也可以）         ║
╚══════════════════════════════════════════════════════════╝
```

---

## 0-1  你需要準備的帳號

在開始之前，先把這些帳號開好。沒有它們，後面的步驟會一直卡住。

| 服務 | 用途 | 免費方案夠用？ |
|------|------|--------------|
| OpenAI / Claude / Gemini（任一）| LLM + Embedding | ✅（API free tier 或小額付費）|
| [Supabase](https://supabase.com) | PostgreSQL + pgvector | ✅（免費方案 500 MB）|
| [LINE Developers](https://developers.line.biz) | LINE Bot channel | 選填（完全免費）|
| [ngrok](https://ngrok.com) | 本地服務 → 公開 URL | 選填（LINE 才需要）|

> 💡 **從 Ch01 到 Ch07 都可以只用 HTTP channel**
>
> `/api/chat` endpoint 完整模擬所有 graph 功能，不需要 LINE 帳號。
> 想接 LINE 的話，Ch06 才需要設定 ngrok + webhook；
> 想接 Telegram 或自架 Web 前端，見 [Lesson 4 Ch04](../Lesson_4_Build_Yours/ch04-channel.md)。

---

## 0-2  Clone + 安裝依賴

```bash
# Clone
git clone <你的 fork URL>
cd project-linebot-rag-skills

# 建立虛擬環境（建議用 venv，不要用 conda）
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 安裝依賴（包含開發工具）
python -m pip install -e ".[dev]"
```

> ⚠️ **為什麼用 `python -m pip` 而不是直接 `pip`？**
>
> 確保你用的 pip 屬於你剛建的 venv，而不是系統的 pip。
> 在某些系統上直接用 `pip` 會把套件裝到全域，產生版本衝突。

---

## 0-3  設定 `.env`

```bash
cp .env.example .env
```

打開 `.env`，至少填這幾行：

```bash
# ── AI Provider（三選一）──────────────────────────────────
OPENAI_API_KEY=sk-...                    # OpenAI
# ANTHROPIC_API_KEY=sk-ant-...           # Claude（改前綴取消註解）
# GEMINI_API_KEY=AIza...                 # Gemini

# ── Supabase ─────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...   # Settings → API → service_role（不是 anon key）

# ── LINE Bot（暫時可留空，Ch06 再填）────────────────────
LINE_CHANNEL_ACCESS_TOKEN=
LINE_CHANNEL_SECRET=

# ── 應用設定 ─────────────────────────────────────────────
LOG_LEVEL=INFO
GRAPH_VARIANT=selfrag                    # basic | selfrag | reflection
```

---

## 0-4  建立 Supabase 資料表

```bash
# 執行 schema migration
bash scripts/apply_supabase_sql.sh
```

這個指令執行 `supabase/schema.sql`，建立：
- `private_knowledge`（chunks + embeddings）
- `private_knowledge_meta`（metadata）
- `messages`（對話記錄）

驗證：

```bash
# 看 psql 連線是否成功
python -c "from app.storage.supabase_client import get_supabase_client; print('OK')"
```

---

## 0-5  跑測試

```bash
pytest
```

**預期輸出**：

```
============================= test session starts ==============================
collected 42 items

tests/test_ai_providers.py ......
tests/test_router.py ....
...（中間省略）
============================== 42 passed in 8.3s ==============================
```

> ⚠️ **如果有測試失敗**
>
> 最常見的原因：
>
> 1. `.env` 沒設定 → `KeyError: 'OPENAI_API_KEY'`
>    → 確認 `.env` 已複製並填好
>
> 2. Supabase 連線失敗 → `ConnectionRefusedError`
>    → 確認 `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` 正確（不是 anon key）
>
> 3. 依賴版本衝突 → `ImportError`
>    → 試試 `python -m pip install -e ".[dev]" --upgrade`

---

## 0-6  啟動本地服務

```bash
./scripts/run_local.sh
```

另開一個 terminal，確認服務活著：

```bash
curl http://localhost:8000/health
# 應該回傳：{"status":"ok"}
```

---

## 0-7  LINE Webhook 設定（選做）

如果你已經建好 LINE Developer 帳號：

### Step 1：啟動 ngrok

```bash
ngrok http 8000
```

複製輸出的 `https://xxxx.ngrok-free.app` URL。

### Step 2：填入 `.env`

```bash
LINE_CHANNEL_ACCESS_TOKEN=<你的 token>
LINE_CHANNEL_SECRET=<你的 secret>
```

重啟服務：`./scripts/run_local.sh`

### Step 3：設定 LINE webhook

在 LINE Developers Console：
- Webhook URL：`https://xxxx.ngrok-free.app/webhook`
- 點「Verify」→ 應該看到 `200 OK`

### Step 4：傳送測試訊息

用你的 LINE app 加 bot 為好友，傳送「你好」。
服務 log 應該出現：

```
INFO     處理訊息: 你好（來自 U_xxx）
INFO     routing → general_chat
INFO     graph 執行完成，推送 1 則訊息
```

---

## 📝 沒有蠢問題

**Q：為什麼用 Supabase，不用本地 SQLite？**

A：Supabase 提供 `pgvector` extension，讓 PostgreSQL 可以做向量相似度搜尋。
本課 Ch06 會加入 `sqlite-vec` 作為離線替代，你到時候可以切換。
現在先用 Supabase 跑起來，理解架構再優化。

**Q：一定要 LINE Bot 嗎？我能不能只用 REST API？**

A：可以。Ch01 後你就能用 `/api/chat` endpoint 測試整個 graph。
LINE 只是「前端介面」，跟 graph 邏輯無關。

**Q：API 費用大概多少？**

A：整個 8 週課程（包含多次 eval run）約 **$5–15 USD**。
Ch05 會教你怎麼追蹤每次 query 的成本。

---

## 🎯 本章里程碑

```bash
pytest                          # ✅ 全綠
curl localhost:8000/health      # ✅ {"status":"ok"}

# 驗證 HTTP channel 能用
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "user_id": "test_001"}' \
  | python -m json.tool          # ✅ 看到 messages 欄位
```

完成後進 [Ch 01 → Graph 起步](ch01-graph-basics.md)。
