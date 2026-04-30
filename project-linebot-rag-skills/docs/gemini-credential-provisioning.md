# Google Gemini 憑證申請指南

最後更新：2026-04-30

本指南說明如何取得 Google Gemini API Key，並將本專案切換為 Gemini provider。
完成後請回到 [README](../README.md) 繼續啟動流程。

需要取得的憑證：

| 步驟 | 憑證 / 動作 | 來源 |
|------|------------|------|
| 1 | 建立 / 確認 Google 帳號 | myaccount.google.com |
| 2 | 取得 `GEMINI_API_KEY` | Google AI Studio → API keys |
| 3 | 選擇模型世代並設定 `.env` | 本地 `.env` |
| 4（選用）| 連結 Google Cloud Project 提高配額 | console.cloud.google.com |

---

## 開始前準備

請先確認以下帳號已可使用：

1. **Google 帳號** — 可登入 [Google AI Studio](https://aistudio.google.com)
2. （選用）**Google Cloud 帳號** — 若需要高流量或商業部署，需連結有啟用計費的 Cloud Project

> ⚠️ API Key 只能放在 `.env` 或伺服器端的 secret store。絕對不能上傳到 git。

---

## `.env` 最終範本

### 穩定版（生產環境 / 預設推薦）

```bash
AI_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini

GEMINI_API_KEY=<步驟 2 複製的值>

ROUTER_MODEL=gemini-2.5-flash
GENERATOR_MODEL=gemini-2.5-pro
EMBEDDING_MODEL=gemini-embedding-2
```

### 試驗版 3.1（Preview — 功能最新，API 行為可能變動）

```bash
AI_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini

GEMINI_API_KEY=<步驟 2 複製的值>

ROUTER_MODEL=gemini-3.1-flash-lite-preview
GENERATOR_MODEL=gemini-3.1-pro-preview
EMBEDDING_MODEL=gemini-embedding-2-preview
```

> 若只想用 Gemini 做 LLM、保留 OpenAI 做 embedding，可設定：
> ```bash
> AI_PROVIDER=gemini
> EMBEDDING_PROVIDER=openai   # 保留 OPENAI_API_KEY
> ```

---

## 步驟 1｜確認 Google 帳號

前往 [myaccount.google.com](https://myaccount.google.com) 確認已登入。
若沒有 Google 帳號，點右上角「建立帳戶」免費申請。

---

## 步驟 2｜取得 GEMINI_API_KEY

### 2-1 前往 Google AI Studio

1. 前往 [aistudio.google.com](https://aistudio.google.com)
2. 若是首次登入，同意服務條款

### 2-2 建立 API Key

1. 點左側選單或上方的「**Get API key**」
2. 點「**Create API key**」
3. 選擇**建立方式**：

   | 選項 | 適用情境 |
   |------|----------|
   | **Create API key in new project** | 沒有 Google Cloud 帳號，快速取得免費額度用 |
   | **Create API key in existing project** | 已有 Google Cloud Project，可使用付費配額 |

   開發初期選「**Create API key in new project**」即可，AI Studio 會自動建立一個 Google Cloud Project。

4. 點「**Create**」，畫面會顯示新建立的 API Key（格式：`AIzaSy...`）
5. 點「**Copy**」立刻複製，頁面關閉後仍可在 API keys 列表中重新複製

### 填入 `.env`

```bash
GEMINI_API_KEY=<貼上剛才複製的 key>
```

---

## 步驟 3｜選擇模型世代並設定 `.env`

### 可用模型一覽

以下模型清單來自 2026-04-30 的 API 實測查詢（`GET /v1beta/models`）。

#### LLM 模型

| 模型 | 世代 | 穩定性 | 用途建議 |
|------|------|--------|----------|
| `gemini-2.5-flash` | 2.5 | ✅ 穩定版 | Router — 低延遲意圖分類 |
| `gemini-2.5-pro` | 2.5 | ✅ 穩定版 | Generator — 高品質回覆生成 |
| `gemini-2.0-flash` | 2.0 | ✅ 穩定版 | 輕量替代，成本最低 |
| `gemini-2.0-flash-lite` | 2.0 | ✅ 穩定版 | 極高 RPM，適合壓測 |
| `gemini-3.1-flash-lite-preview` | 3.1 | ⚠️ Preview | Router 試驗 — 最新輕量模型 |
| `gemini-3.1-pro-preview` | 3.1 | ⚠️ Preview | Generator 試驗 — 最新高品質模型 |

#### Embedding 模型

| 模型 | 穩定性 | 說明 |
|------|--------|------|
| `gemini-embedding-2` | ✅ 穩定版 | 生產環境推薦 |
| `gemini-embedding-2-preview` | ⚠️ Preview | 最新版本，可能有更好的向量品質 |
| `gemini-embedding-001` | ✅ 穩定版 | 舊版，不建議新專案使用 |

> ⚠️ 注意：`text-embedding-004` 並非 Gemini embedding 系列命名，**此名稱不存在**。
> Gemini embedding 模型命名皆為 `gemini-embedding-*`。

---

### 模型選擇策略

#### 穩定版 vs Preview — 如何取捨？

| 考量 | 穩定版（2.5） | Preview（3.1） |
|------|--------------|----------------|
| API 穩定性 | 高，不會突然改變行為 | 可能在無通知的情況下調整 |
| 功能完整度 | 完整 | 部分功能仍在測試 |
| 效能 | 已知且有 benchmark | 理論上較新，但尚無公開數據 |
| 費率 | 明確 | Preview 期間通常有優惠或免費 |
| 建議場景 | **生產環境、需要可預期行為** | **開發探索、願意接受不穩定** |

#### Router 與 Generator 的不同考量

**Router（意圖分類）** 的輸出必須是合法 JSON，對模型的**指令遵循能力**要求高、對推理深度要求低：
- 優先選 **Flash 系列**（速度快、成本低、每日可跑大量測試）
- 穩定版推薦：`gemini-2.5-flash`
- 試驗版推薦：`gemini-3.1-flash-lite-preview`

**Generator（回覆生成）** 需要根據 RAG 內容、skill prompt、情緒狀態生成自然語言，對**推理品質**要求高：
- 優先選 **Pro 系列**（推理能力更強）
- 穩定版推薦：`gemini-2.5-pro`
- 試驗版推薦：`gemini-3.1-pro-preview`

#### 建議的漸進切換路徑

```
起點（保守）：2.5-flash / 2.5-pro / gemini-embedding-2
       ↓ 觀察 Router JSON 解析成功率是否提升
       ↓
Step 1：Router 換 3.1-flash-lite-preview，Generator 維持 2.5-pro
       ↓ 觀察回覆品質與 RAG 引用準確度
       ↓
Step 2：Generator 換 3.1-pro-preview
       ↓ 觀察 embedding 檢索的召回率
       ↓
Step 3：Embedding 換 gemini-embedding-2-preview
```

每步之間建議觀察至少 50 次真實對話，再決定是否往下推進。

#### 查詢目前帳號可用模型

隨時用此指令核對最新清單（不同帳號的 preview 存取權可能不同）：

```bash
GEMINI_API_KEY=$(grep '^GEMINI_API_KEY=' .env | cut -d= -f2-) && \
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY" \
  | python3 -m json.tool | grep '"name"'
```

---

## 步驟 4｜安裝 Gemini SDK

```bash
pip install -e ".[gemini]"
```

或直接安裝套件：

```bash
pip install "google-genai>=1.0"
```

---

## 步驟 5（選用）｜連結 Google Cloud Project 提高配額

免費額度的 RPM（每分鐘請求數）與 TPD（每日 token 數）較低，密集測試或上線後建議升級：

1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 建立或選取一個 Project
3. 啟用「**Generative Language API**」：
   - 搜尋列輸入 `Generative Language API` → 點「**啟用**」
4. 前往「**帳單**」→ 連結付款帳戶（需填信用卡，但有 $300 免費額度新帳號）
5. 回到 [AI Studio](https://aistudio.google.com) → Get API key → 選「**Create API key in existing project**」，選剛才的 Project → 重新建立 key

啟用計費後，配額限制大幅提高（Pay-as-you-go）。

---

## 費用估算

### 免費額度（請以官方為準）

| 模型 | 免費 RPM | 備註 |
|------|----------|------|
| `gemini-2.5-flash` | 10 | 穩定版主力 |
| `gemini-2.0-flash` | 15 | 成本最低選項 |
| `gemini-2.0-flash-lite` | 30 | 壓測首選 |
| `gemini-3.1-flash-lite-preview` | 視 Preview 配額而定 | 可能暫時免費 |
| `gemini-3.1-pro-preview` | 視 Preview 配額而定 | 可能暫時免費 |
| `gemini-embedding-2` | 1,500 | — |

### 付費費率（每 100 萬 token，僅供參考）

| 模型 | Input | Output |
|------|-------|--------|
| `gemini-2.5-flash` | ~$0.15 | ~$0.60 |
| `gemini-2.5-pro` | ~$1.25 | ~$10.00 |
| `gemini-2.0-flash` | ~$0.075 | ~$0.30 |
| `gemini-embedding-2` | 免費 | — |

> 最新定價：[ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)

每次 LINE 對話約花費（穩定版 2.5-flash + 2.5-pro 組合）：

| 步驟 | 模型 | 約花費 |
|------|------|-------|
| Router 意圖分類 | gemini-2.5-flash | < $0.0002 |
| Generator 回覆生成 | gemini-2.5-pro | ~$0.005–0.02 |
| Embeddings（RAG） | gemini-embedding-2 | 幾乎免費 |

---

## Rate Limit 注意事項

免費帳號遇到 **429 Too Many Requests** 時：

- 稍等 60 秒後重試
- Router 改用 `gemini-2.0-flash-lite`（免費 RPM 最高）
- Preview 模型的配額可能比穩定版更嚴格，遇到 429 可暫時降回 2.5 穩定版
- 密集壓測時建議連結有計費的 Cloud Project

---

## 驗證 API Key 與模型可用

安裝 SDK 後，執行以下腳本確認 key 與指定模型都正常：

```python
# test_gemini.py
import asyncio, os
from google import genai

async def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("GENERATOR_MODEL", "gemini-2.5-flash")
    r = await client.aio.models.generate_content(
        model=model,
        contents="回覆「OK」即可",
    )
    print(f"model={model}  response={r.text}")

asyncio.run(main())
```

```bash
# 穩定版測試
GEMINI_API_KEY=AIzaSy... GENERATOR_MODEL=gemini-2.5-flash \
  .venv/bin/python test_gemini.py

# 3.1 preview 測試
GEMINI_API_KEY=AIzaSy... GENERATOR_MODEL=gemini-3.1-pro-preview \
  .venv/bin/python test_gemini.py
```

---

## API Key 管理

### 查看 / 刪除現有 key

1. 前往 [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. 可看到所有已建立的 key 及其所屬 Project
3. 點「**刪除**」可撤銷 key

### 設定 API Key 限制（選用）

若想限制 key 只能從特定 IP 或 HTTP referrer 使用：

1. 前往 [Google Cloud Console](https://console.cloud.google.com) → API & Services → Credentials
2. 找到對應的 API Key → 點「**編輯**」
3. 在「Application restrictions」設定 IP 白名單或 HTTP referrer

---

## 官方文件參考

- Gemini API 快速入門：[ai.google.dev/gemini-api/docs/quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
- 模型清單：[ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)
- Embedding 使用說明：[ai.google.dev/gemini-api/docs/embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- 定價：[ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Rate limits：[ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- google-genai SDK（Python）：[github.com/googleapis/python-genai](https://github.com/googleapis/python-genai)
