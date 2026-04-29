# Webhook Tunnel 指南

本地開發時，LINE 的 Webhook 需要一個公開的 HTTPS URL 才能打到你的電腦。這份文件說明為何需要 tunnel、ngrok 的安裝與使用，以及正式上線後改用 GCP 的部署方式。

---

## 目錄

1. [為什麼需要 Tunnel](#1-為什麼需要-tunnel)
2. [ngrok 原理](#2-ngrok-原理)
3. [ngrok 安裝與設定](#3-ngrok-安裝與設定)
4. [ngrok 基本使用](#4-ngrok-基本使用)
5. [ngrok Web Inspector（除錯工具）](#5-ngrok-web-inspector除錯工具)
6. [ngrok 免費方案限制](#6-ngrok-免費方案限制)
7. [其他 Tunnel 替代方案](#7-其他-tunnel-替代方案)
8. [正式環境：部署到 GCP Cloud Run](#8-正式環境部署到-gcp-cloud-run)

---

## 1. 為什麼需要 Tunnel

LINE 的 Webhook 機制是：當用戶傳訊息時，LINE server 主動向你設定的 URL 發送 HTTP POST 請求。這個 URL 必須滿足兩個條件：

1. **公開可存取**：LINE server 在網際網路上，必須能打到你的 server
2. **HTTPS**：LINE 不接受純 HTTP 的 Webhook URL

本地開發的 FastAPI App 跑在 `http://127.0.0.1:8000`，只有你自己的電腦能連，LINE server 無法直接存取。Tunnel 服務的作用就是在公網建立一個 HTTPS URL，將流量代理到你本機的 port。

```
LINE server
    ↓  HTTPS POST
ngrok cloud（公開 HTTPS URL）
    ↓  HTTP（透過加密 tunnel）
你的電腦 127.0.0.1:8000
    ↓
FastAPI App
```

---

## 2. ngrok 原理

ngrok 由兩個部分組成：

**ngrok agent（本地端）**

在你的電腦執行 `ngrok http 8000` 後，agent 會：

1. 與 ngrok cloud 建立一條長連線（outbound TCP，不需要對外開放 port）
2. 向 ngrok cloud 申請一個公開 HTTPS URL（例如 `https://xxxx.ngrok-free.app`）
3. 所有打到該 URL 的請求，都透過這條長連線轉發到 `localhost:8000`

**ngrok cloud（公網端）**

- 持有公開 IP 與 HTTPS 憑證
- 接收來自 LINE server 的請求
- 轉發到對應的 agent 連線

整個流程中，你的電腦不需要設定防火牆規則或開放 port，因為連線是由 agent 主動向外建立的。

```
[ngrok agent] ──outbound TCP──▶ [ngrok cloud] ◀──HTTPS──  [LINE server]
      │                                │
  localhost:8000                  轉發請求
      │
  FastAPI App
```

---

## 3. ngrok 安裝與設定

### 安裝

**macOS（Homebrew）**

```bash
brew install ngrok/ngrok/ngrok
```

**直接下載**

前往 [ngrok.com/download](https://ngrok.com/download)，選對應平台下載，解壓縮後將 `ngrok` 執行檔移至 `PATH` 內：

```bash
sudo mv ngrok /usr/local/bin/
```

**確認安裝成功**

```bash
ngrok version
# ngrok version 3.x.x
```

### 建立帳號並取得 Auth Token

免費方案需要登入帳號（否則 tunnel 有時間限制且不穩定）：

1. 前往 [dashboard.ngrok.com](https://dashboard.ngrok.com) 註冊免費帳號
2. 登入後，左側選「**Your Authtoken**」
3. 複製 token，執行：

```bash
ngrok config add-authtoken <你的-auth-token>
```

token 會儲存到 `~/.config/ngrok/ngrok.yml`，之後不需要重複設定。

---

## 4. ngrok 基本使用

### 啟動 Tunnel

確認 FastAPI App 已在執行（`./scripts/run_local.sh`），再另開一個 terminal：

```bash
ngrok http 8000
```

成功後會看到類似輸出：

```
Session Status     online
Account            your@email.com (Plan: Free)
Version            3.x.x
Region             Asia Pacific (ap)
Web Interface      http://127.0.0.1:4040
Forwarding         https://ab12-34-56-78-90.ngrok-free.app -> http://localhost:8000

Connections        ttl     opn     rt1     rt5     p50     p90
                   0       0       0.00    0.00    0.00    0.00
```

**關鍵資訊：**

| 欄位 | 說明 |
|------|------|
| `Forwarding` | 左邊是公開 HTTPS URL，右邊是本地 App |
| `Web Interface` | ngrok 的本地 Inspector UI，可查看所有請求 |
| `Session Status` | `online` 表示 tunnel 正常運作 |

### 更新 LINE Webhook URL

複製 `https://ab12-34-56-78-90.ngrok-free.app`，前往 LINE Developers Console：

1. Messaging API → Webhook URL 填入：
   ```
   https://ab12-34-56-78-90.ngrok-free.app/api/line/webhook
   ```
2. 點「**Update**」→ 開啟「**Use webhook**」→ 點「**Verify**」

Verify 成功後，傳訊息給 bot 即可測試。

### 驗證 Tunnel 是否正常

```bash
curl https://ab12-34-56-78-90.ngrok-free.app/health
# 期望：{"status":"ok"}
```

---

## 5. ngrok Web Inspector（除錯工具）

ngrok 附帶一個本地 Web UI，可以查看所有經過 tunnel 的請求與回應：

```
http://127.0.0.1:4040
```

在瀏覽器開啟後可以看到：

- 每一筆進來的 HTTP 請求（method、path、headers、body）
- App 的回應（status code、body）
- 可以「**Replay**」重新送出任一請求（不需要重新傳 LINE 訊息）

**常用場景：**

- 確認 LINE 有沒有真的送出 webhook（看有沒有 `POST /api/line/webhook`）
- 查看 LINE 傳來的 payload 格式
- Replay 測試，不需要一直打 LINE 傳訊息

---

## 6. ngrok 免費方案限制

| 限制項目 | 免費方案 |
|---------|---------|
| HTTPS 公開 URL | 每次重啟都會變（非固定域名） |
| 同時執行的 tunnel 數量 | 1 個 |
| 每分鐘請求數（RPM） | 40 |
| Tunnel 連線時長 | 無限制（需保持 terminal 開啟） |
| 自訂域名 | 不支援（需付費） |

**免費方案最大的不便**：每次重啟 ngrok，URL 都會改變，必須重新更新 LINE Developers Console 的 Webhook URL。

如果需要固定 URL 但不想付費給 ngrok，可考慮 [Cloudflare Tunnel](#7-其他-tunnel-替代方案)。

---

## 7.其他 Tunnel 替代方案

### Cloudflare Tunnel（推薦免費替代）

Cloudflare Tunnel 提供**免費固定域名**，比 ngrok 免費方案更適合持續開發：

**安裝（macOS）：**

```bash
brew install cloudflared
```

**登入並建立 tunnel：**

```bash
cloudflared tunnel login
cloudflared tunnel create linebot-dev
cloudflared tunnel route dns linebot-dev webhook.你的域名.com
```

**啟動：**

```bash
cloudflared tunnel run --url http://localhost:8000 linebot-dev
```

LINE Webhook URL 設為 `https://webhook.你的域名.com/api/line/webhook`，重啟後 URL 不會改變。

> 需要有自己的域名並且 DNS 已交由 Cloudflare 管理。

---

### localhost.run（免安裝）

不需要安裝任何工具，只用 SSH：

```bash
ssh -R 80:localhost:8000 localhost.run
```

URL 每次不固定，適合臨時測試。

---

## 8. 正式環境：部署到 GCP Cloud Run

正式上線後，不再需要 ngrok。LINE Webhook 直接打到 GCP 上的穩定 HTTPS URL。推薦使用 **Cloud Run**（無伺服器容器，按需付費，自動 HTTPS）。

### 前置需求

- 已安裝 [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)（`gcloud`）
- 已建立 GCP Project 並啟用計費
- 已安裝 Docker

```bash
gcloud auth login
gcloud config set project <your-gcp-project-id>
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### 建立 Dockerfile

在專案根目錄建立 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

COPY app/ ./app/
COPY skills/ ./skills/

ENV PORT=8080
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

> Cloud Run 預設使用 port 8080，`$PORT` 環境變數由 Cloud Run 注入。

### 建立 `.dockerignore`

```
.venv/
.env
__pycache__/
*.pyc
tests/
docs/
scripts/
supabase/
.git/
```

### 建置並推送 Image

```bash
# 設定 Artifact Registry（只需執行一次）
gcloud artifacts repositories create linebot-rag \
  --repository-format=docker \
  --location=asia-east1

# 建置 image
gcloud builds submit \
  --tag asia-east1-docker.pkg.dev/<project-id>/linebot-rag/app:latest

# 或本機 build 後推送
docker build -t asia-east1-docker.pkg.dev/<project-id>/linebot-rag/app:latest .
docker push asia-east1-docker.pkg.dev/<project-id>/linebot-rag/app:latest
```

### 部署到 Cloud Run

```bash
gcloud run deploy linebot-rag-app \
  --image asia-east1-docker.pkg.dev/<project-id>/linebot-rag/app:latest \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "LINE_CHANNEL_SECRET=...,LINE_CHANNEL_ACCESS_TOKEN=...,OPENAI_API_KEY=...,SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=..."
```

> **建議**：不要在 `--set-env-vars` 直接貼 secret 值。改用 [Secret Manager](https://cloud.google.com/secret-manager) 管理憑證：
>
> ```bash
> gcloud secrets create LINE_CHANNEL_SECRET --data-file=- <<< "你的值"
> gcloud run deploy ... --set-secrets "LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest"
> ```

### 取得 Cloud Run URL

部署完成後，`gcloud` 會印出：

```
Service URL: https://linebot-rag-app-xxxxxxxxxx-de.a.run.app
```

這就是你的穩定 HTTPS URL。設定 LINE Webhook URL 為：

```
https://linebot-rag-app-xxxxxxxxxx-de.a.run.app/api/line/webhook
```

不再需要 ngrok，URL 永遠不會改變。

### Cloud Run 費用估算

Cloud Run 按實際用量計費，個人 bot 費用極低：

| 項目 | 免費額度（每月） | 超出後 |
|------|----------------|--------|
| 請求數 | 200 萬次 | $0.40 / 百萬次 |
| CPU（vCPU-秒） | 180,000 vCPU-秒 | $0.00002400 / vCPU-秒 |
| 記憶體（GiB-秒） | 360,000 GiB-秒 | $0.00000250 / GiB-秒 |

一般個人 LINE Bot 每月幾乎都在免費額度內，幾乎不產生費用。

### 本地開發 vs 正式環境對照

| 項目 | 本地開發（ngrok） | 正式環境（GCP Cloud Run） |
|------|-----------------|------------------------|
| HTTPS URL | 每次重啟改變 | 固定不變 |
| 費用 | 免費 | 幾乎免費（免費額度內） |
| 啟動速度 | 即時 | 首次冷啟動約 2–5 秒 |
| 環境變數管理 | `.env` 檔案 | Secret Manager |
| Log 查看 | terminal | Cloud Logging |
| 適合情境 | 開發、除錯 | 持續運行的正式服務 |
