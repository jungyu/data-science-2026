# ADR-001：以 LINE Bot 作為個人 AI 主介面

## 狀態

已採納

## 背景

使用者已長期使用 LINE 作為主要通訊工具。若另建 Web App，每次使用都需切換介面，降低實際使用頻率。LINE 對話框本身即是低摩擦的輸入環境，適合碎片化的技術問答、情緒校準與知識查詢。

## 決策

以 LINE Messaging API 作為主要對話介面。FastAPI 接收 webhook 事件後非同步處理，透過 LINE Push API 回覆。

### 實作細節

- 帳號管理（自動回覆、歡迎訊息）在 [LINE Official Account Manager](https://manager.line.biz) 設定
- Messaging API 憑證（Channel Secret、Channel Access Token）在 [LINE Developers Console](https://developers.line.biz/console/) 取得
- 每則訊息的處理（Router → RAG → Generator）在背景 task 執行，確保 webhook 在 5 秒內回應 200
- Webhook URL 格式：`https://<host>/api/line/webhook`
- 本地開發使用 ngrok 暴露 webhook，免費帳號每次重啟 URL 都會改變，需重新更新 Developers Console

### 免費方案限制

LINE 官方帳號免費方案每月可發送 **200 則 Push Message**，超出後需付費。個人私用場景通常不會觸及上限。

## 後果

### 正面

- 最低日常使用成本，使用者不需額外開啟任何 App
- 自然適合短句、碎片化查詢
- 未來可擴充語音轉文字（STT）、圖片 OCR 等功能

### 負面

- Webhook 有 5 秒回應限制，長任務須非同步處理
- 輸出長度受 LINE 訊息氣泡限制，複雜回覆需分段
- 免費方案 Push Message 有月上限，大量使用需升級
- ngrok 免費帳號 URL 不固定，開發時每次重啟都要更新 webhook 設定
