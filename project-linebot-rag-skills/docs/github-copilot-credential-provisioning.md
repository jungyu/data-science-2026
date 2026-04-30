# GitHub Copilot / GitHub Models API 憑證申請指南

最後更新：2026-04-30

本指南說明如何取得 GitHub 的 AI API 存取憑證，並將本專案切換為 `github_copilot` provider。  
完成後請回到 [README](../README.md) 繼續啟動流程。

本文涵蓋兩條路徑，二擇一即可：

| 路徑 | 需求 | Base URL | 免費額度 |
|------|------|----------|----------|
| **A｜GitHub Models**（建議新手） | 任何 GitHub 帳號 | `https://models.inference.ai.azure.com` | 有（Rate limited） |
| **B｜GitHub Copilot API** | Copilot Individual / Business / Enterprise 訂閱 | `https://api.githubcopilot.com` | 包含在訂閱費內 |

> 兩者都使用 OpenAI 相容的 Chat Completions API，本專案的 `OpenAIChatLLM` 可直接對應。

---

## 開始前準備

1. **GitHub 帳號** — 可登入 [github.com](https://github.com)
2. **路徑 B 額外需求**：已啟用 GitHub Copilot 訂閱（Individual $10/月 或由組織授權的 Business / Enterprise）

> ⚠️ Token 只能放在 `.env` 或伺服器端的 secret store。絕對不能上傳到 git。

---

## `.env` 最終範本

### 路徑 A｜GitHub Models

```bash
AI_PROVIDER=github_copilot
EMBEDDING_PROVIDER=openai          # GitHub Models 不提供 Embedding API

GITHUB_COPILOT_TOKEN=<步驟 A-2 複製的 PAT>
GITHUB_COPILOT_BASE_URL=https://models.inference.ai.azure.com

ROUTER_MODEL=gpt-4o-mini
GENERATOR_MODEL=gpt-4o

# Embedding 仍使用 OpenAI
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
```

### 路徑 B｜GitHub Copilot API

```bash
AI_PROVIDER=github_copilot
EMBEDDING_PROVIDER=openai

GITHUB_COPILOT_TOKEN=<步驟 B-2 取得的 token>
GITHUB_COPILOT_BASE_URL=https://api.githubcopilot.com

ROUTER_MODEL=gpt-4o-mini
GENERATOR_MODEL=gpt-4o

OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 路徑 A｜GitHub Models（免費，推薦快速試用）

GitHub Models 是 GitHub 提供的 AI 模型試驗平台，使用一般 GitHub 帳號即可存取，支援多款 OpenAI、Meta、Mistral 等模型。

### A-1 確認 GitHub Models 存取權

1. 前往 [github.com/marketplace/models](https://github.com/marketplace/models)
2. 點任意模型（例如 `gpt-4o`）→ 確認可以看到「**Playground**」頁面
3. 若出現等待清單（waitlist）提示，點「**Join waitlist**」，通常數小時內核准

### A-2 建立 Personal Access Token（PAT）

GitHub Models 只需要一個有效的 GitHub 登入身份，不需要特定 scope：

1. 前往 [github.com/settings/tokens](https://github.com/settings/tokens)
2. 點「**Generate new token**」→「**Generate new token (classic)**」
3. 填入：
   - **Note**：`linebot-rag-github-models`
   - **Expiration**：選 90 days（或 No expiration，視需求）
   - **Scopes**：可全部不勾，僅需登入身份即可存取 public models
4. 點「**Generate token**」
5. 立刻複製（格式：`ghp_...`），頁面關閉後無法再查看

### 填入 `.env`

```bash
GITHUB_COPILOT_TOKEN=ghp_...
GITHUB_COPILOT_BASE_URL=https://models.inference.ai.azure.com
```

---

## 路徑 B｜GitHub Copilot API（訂閱用戶）

GitHub Copilot API 讓 Copilot 訂閱用戶以程式方式使用與 Copilot 相同的模型後端。

### B-1 確認 Copilot 訂閱狀態

1. 前往 [github.com/settings/copilot](https://github.com/settings/copilot)
2. 確認顯示「**Active**」訂閱狀態
3. 若尚未訂閱，可選擇：
   - **Individual**：$10/月，個人使用（[立即訂閱](https://github.com/github-copilot/signup)）
   - **Business**：由組織管理員授權（$19/用戶/月）

### B-2 取得 Copilot API Token

Copilot API 使用動態短效 token，需透過 GitHub OAuth 設備授權流程取得。最簡單的方式是使用 **GitHub CLI**：

```bash
# 安裝 GitHub CLI（若尚未安裝）
# macOS
brew install gh

# 登入（若尚未登入）
gh auth login

# 取得含 Copilot 權限的 token
gh auth token
```

複製輸出的 token（格式：`gho_...` 或 `ghp_...`）。

> **若不使用 GitHub CLI**，也可透過以下步驟手動取得：
>
> 1. 建立 GitHub OAuth App：前往 [github.com/settings/applications/new](https://github.com/settings/applications/new)
> 2. 使用 Device Flow 取得用戶授權 token（需呼叫 `https://github.com/login/device/code`）
> 3. 詳見官方文件：[docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow)

### 填入 `.env`

```bash
GITHUB_COPILOT_TOKEN=<gh auth token 輸出的值>
GITHUB_COPILOT_BASE_URL=https://api.githubcopilot.com
```

---

## 步驟 4｜設定模型

### GitHub Models 可用模型（部分）

| 模型識別碼 | 用途建議 |
|-----------|----------|
| `gpt-4o-mini` | Router（輕量、快速） |
| `gpt-4o` | Generator（高品質） |
| `Phi-4` | 輕量推理，低延遲 |
| `Llama-3.3-70B-Instruct` | 開源替代方案 |
| `Mistral-Large-2411` | 多語言能力強 |

> 完整模型清單：[github.com/marketplace/models](https://github.com/marketplace/models)

### GitHub Copilot API 可用模型（部分）

| 模型識別碼 | 說明 |
|-----------|------|
| `gpt-4o` | OpenAI GPT-4o |
| `gpt-4o-mini` | 輕量版 GPT-4o |
| `claude-3.5-sonnet` | Anthropic Sonnet（部分方案） |
| `o3-mini` | OpenAI 推理模型 |

> 可用模型視訂閱方案與地區而異，建議呼叫 `GET https://api.githubcopilot.com/models` 查詢目前可用清單。

### Embedding 注意事項

GitHub Models 與 Copilot API 目前**不提供 Embedding API**，須保留 OpenAI 或 Gemini 作為 embedding provider：

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 費用與用量限制

### 路徑 A｜GitHub Models 免費配額

| 等級 | RPM | 每日請求上限 | Token/請求上限 |
|------|-----|-------------|----------------|
| 低速（免費） | 15 | 150 | 8,000 |
| 高速（免費） | 10 | 50 | 8,000 |

> 免費配額僅供試驗用途，正式上線請換用 Azure OpenAI 或其他 provider。

### 路徑 B｜GitHub Copilot API

包含在訂閱費內，不額外計費，但有以下使用原則：
- 僅限訂閱用戶本人使用（不可轉讓或供多人共用）
- 仍受合理使用限制（Responsible Use Policy）

---

## 驗證 API 可用

安裝好依賴後，建立測試腳本確認 token 和 base URL 正常：

```python
# test_github_copilot.py
import asyncio, os
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
        api_key=os.environ["GITHUB_COPILOT_TOKEN"],
        base_url=os.environ.get(
            "GITHUB_COPILOT_BASE_URL",
            "https://models.inference.ai.azure.com",
        ),
    )
    response = await client.chat.completions.create(
        model=os.environ.get("ROUTER_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": "回覆「OK」即可"}],
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

```bash
GITHUB_COPILOT_TOKEN=ghp_... \
GITHUB_COPILOT_BASE_URL=https://models.inference.ai.azure.com \
ROUTER_MODEL=gpt-4o-mini \
.venv/bin/python test_github_copilot.py
# 期望輸出：OK
```

---

## Token 管理

### 查看 / 撤銷 PAT（路徑 A）

1. 前往 [github.com/settings/tokens](https://github.com/settings/tokens)
2. 找到對應 token → 點「**Delete**」撤銷

### Token 到期後重新取得（路徑 B）

GitHub Copilot token 有效期限較短，到期後重新執行：

```bash
gh auth refresh
gh auth token
```

更新 `.env` 的 `GITHUB_COPILOT_TOKEN` 即可。

---

## 官方文件參考

- GitHub Models 快速入門：[docs.github.com/en/github-models/prototyping-with-ai-models](https://docs.github.com/en/github-models/prototyping-with-ai-models)
- GitHub Models 模型清單：[github.com/marketplace/models](https://github.com/marketplace/models)
- GitHub Copilot 訂閱：[github.com/features/copilot](https://github.com/features/copilot)
- GitHub Copilot API 文件：[docs.github.com/en/copilot/building-copilot-extensions/building-a-copilot-agent-for-your-copilot-extension/using-copilots-llm-for-your-agent](https://docs.github.com/en/copilot/building-copilot-extensions/building-a-copilot-agent-for-your-copilot-extension/using-copilots-llm-for-your-agent)
- GitHub OAuth Device Flow：[docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow)
- GitHub CLI 安裝：[cli.github.com](https://cli.github.com)
