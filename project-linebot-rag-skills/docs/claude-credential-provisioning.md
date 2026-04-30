# Anthropic Claude API 憑證申請指南

最後更新：2026-04-30

本指南說明如何取得 Anthropic Claude API Key，並將本專案切換為 Claude provider。
完成後請回到 [README](../README.md) 繼續啟動流程。

需要取得的憑證：

| 步驟 | 憑證 / 動作 | 來源 |
|------|------------|------|
| 1 | 建立 Anthropic Console 帳號 | console.anthropic.com |
| 2 | 取得 `ANTHROPIC_API_KEY` | Console → API Keys |
| 3 | 設定付款方式與用量上限 | Console → Plans & Billing |
| 4 | 設定 `.env` provider 欄位 | 本地 `.env` |

---

## 開始前準備

請先確認以下帳號已可使用：

1. **Anthropic Console 帳號** — 可登入 [console.anthropic.com](https://console.anthropic.com)（以 Email 或 Google 帳號註冊）
2. **付款方式** — 信用卡或金融卡，用於購買 API 用量

> ⚠️ Anthropic 目前**不提供免費試用額度**，首次使用需先加值（最低 $5）。
>
> ⚠️ API Key 只能放在 `.env` 或伺服器端的 secret store。絕對不能上傳到 git。

---

## `.env` 最終範本

完成所有步驟後，你的 `.env` 相關區塊應該長這樣：

```bash
AI_PROVIDER=claude
EMBEDDING_PROVIDER=openai      # Anthropic 不提供 Embedding API，保留 OpenAI

ANTHROPIC_API_KEY=<步驟 2 複製的值>

ROUTER_MODEL=claude-haiku-4-5-20251001
GENERATOR_MODEL=claude-sonnet-4-6

# Embedding 仍使用 OpenAI（需保留 OPENAI_API_KEY）
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 步驟 1｜建立 Anthropic Console 帳號

1. 前往 [console.anthropic.com](https://console.anthropic.com)
2. 點「**Sign up**」
3. 選擇以 **Email** 或 **Google 帳號**註冊
4. 完成 Email 驗證（若選 Email 方式）
5. 填入姓名與使用用途（個人 / 公司皆可）
6. 同意服務條款後進入 Console 首頁

---

## 步驟 2｜取得 ANTHROPIC_API_KEY

### 2-1 前往 API Keys 頁面

1. 登入 [console.anthropic.com](https://console.anthropic.com)
2. 左側選單點「**API Keys**」
3. 點「**+ Create Key**」

### 2-2 建立 API Key

1. 填入 **Name**（例如 `linebot-rag-local`），方便日後識別用途
2. 點「**Create Key**」
3. 畫面顯示完整 key（格式：`sk-ant-api03-...`）
4. 點「**Copy**」立刻複製，**這是唯一可以看到完整 key 的時機**，關閉後無法再查看

### 填入 `.env`

```bash
ANTHROPIC_API_KEY=<貼上剛才複製的 key>
```

---

## 步驟 3｜設定付款方式與用量上限

### 3-1 加值（首次必做）

Anthropic 採**預付（prepaid）**制，需先充值才能呼叫 API：

1. 左側選單點「**Plans & Billing**」→「**Billing**」
2. 點「**Add credit**」
3. 填入信用卡資訊，選擇加值金額（最低 $5，開發初期 $10 足夠）
4. 完成後「**Credit balance**」欄位會顯示餘額

### 3-2 設定用量上限（強烈建議）

避免餘額快速消耗殆盡，建議設定月用量上限：

1. 左側選單點「**Plans & Billing**」→「**Limits**」
2. 在「**Monthly spend limit**」點「**Set limit**」，輸入月上限（開發期間 $10 即可）
3. 在「**Email alerts**」新增通知：
   - 設定 **80%** 時發送警告信
   - 設定 **100%** 時通知已達上限

---

## 步驟 4｜設定 `.env` provider 欄位

開啟 `.env`，設定以下欄位：

```bash
AI_PROVIDER=claude
EMBEDDING_PROVIDER=openai

ANTHROPIC_API_KEY=sk-ant-api03-...

ROUTER_MODEL=claude-haiku-4-5-20251001
GENERATOR_MODEL=claude-sonnet-4-6
```

### 可選模型一覽

| 模型 | 用途建議 | 速度 | 成本 |
|------|----------|------|------|
| `claude-haiku-4-5-20251001` | Router（意圖分類），輕量快速 | ⚡⚡⚡ | 最低 |
| `claude-sonnet-4-6` | Generator 主力，平衡能力與成本 | ⚡⚡ | 中等 |
| `claude-opus-4-7` | Generator 高品質，複雜推理場景 | ⚡ | 最高 |

> 建議組合：`ROUTER_MODEL=claude-haiku-4-5-20251001` + `GENERATOR_MODEL=claude-sonnet-4-6`
>
> 最新模型清單：[docs.anthropic.com/en/docs/about-claude/models](https://docs.anthropic.com/en/docs/about-claude/models)

### Embedding 注意事項

Anthropic **目前不提供 Embedding API**，RAG 向量化必須使用其他 provider。建議方式：

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
```

或改用 Gemini Embedding（若不想依賴 OpenAI）：

```bash
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=<your-gemini-api-key>
EMBEDDING_MODEL=text-embedding-004
```

---

## 步驟 5｜安裝 Claude SDK

```bash
pip install -e ".[claude]"
```

或直接安裝套件：

```bash
pip install "anthropic>=0.40"
```

---

## 費用估算

### 定價（每百萬 token，僅供參考）

| 模型 | Input | Output |
|------|-------|--------|
| `claude-haiku-4-5-20251001` | $0.80 | $4.00 |
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-opus-4-7` | $15.00 | $75.00 |

> 最新定價：[anthropic.com/pricing](https://www.anthropic.com/pricing)

### 每次 LINE 對話約花費（Haiku + Sonnet 組合）

| 步驟 | 模型 | 約花費 |
|------|------|-------|
| Router 意圖分類 | claude-haiku-4-5-20251001 | ~$0.0002 |
| Generator 回覆生成 | claude-sonnet-4-6 | ~$0.005–0.015 |

$10 加值餘額約可跑 600–1,500 次完整對話，開發測試期間足夠。

---

## Rate Limit 與 Usage Tier 說明

Anthropic 以「Usage Tier」管理配額，新帳號從 **Tier 1** 開始：

| Tier | 累積消費門檻 | RPM（Sonnet） | TPM（Sonnet） |
|------|------------|---------------|---------------|
| Tier 1 | $0（新帳號） | 50 | 40,000 |
| Tier 2 | $40 | 1,000 | 80,000 |
| Tier 3 | $200 | 2,000 | 160,000 |
| Tier 4 | $400 | 4,000 | 400,000 |

> 最新 Tier 表：[docs.anthropic.com/en/api/rate-limits](https://docs.anthropic.com/en/api/rate-limits)

密集測試時若遇到 **429 Too Many Requests**：
- 稍等 60 秒後重試
- 換 `claude-haiku-4-5-20251001` 作為 ROUTER_MODEL，其 RPM 較高
- 累積消費超過門檻後，Tier 會自動升級

---

## 驗證 API Key 可用

安裝 SDK 後，建立測試腳本確認 key 正常：

```python
# test_claude.py
import asyncio, os
import anthropic

async def main():
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        messages=[{"role": "user", "content": "回覆「OK」即可"}],
    )
    print(response.content[0].text)

asyncio.run(main())
```

```bash
ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python test_claude.py
# 期望輸出：OK
```

---

## API Key 管理

### 查看 / 撤銷現有 key

1. 前往 [console.anthropic.com](https://console.anthropic.com) → 左側「**API Keys**」
2. 可看到所有 key 的名稱、建立時間、最後使用時間
3. 點右側「**Disable**」可暫時停用，點「**Delete**」可永久撤銷

### Key 遺失處理

若複製後關閉視窗而未保存，**無法再查看**完整 key。需重新建立並更新 `.env`。

---

## 官方文件參考

- 快速入門：[docs.anthropic.com/en/docs/quickstart](https://docs.anthropic.com/en/docs/quickstart)
- 模型清單：[docs.anthropic.com/en/docs/about-claude/models](https://docs.anthropic.com/en/docs/about-claude/models)
- Messages API 說明：[docs.anthropic.com/en/api/messages](https://docs.anthropic.com/en/api/messages)
- Rate limits：[docs.anthropic.com/en/api/rate-limits](https://docs.anthropic.com/en/api/rate-limits)
- 定價：[anthropic.com/pricing](https://www.anthropic.com/pricing)
- Python SDK：[github.com/anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)
