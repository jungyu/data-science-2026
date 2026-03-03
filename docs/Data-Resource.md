# 資料科學與 AI 開發資源總覽

> 涵蓋學術資料集、即時 API、台灣本土資源、金融數據及特殊主題資料來源。

---

## 一、網路學術資料

### 1. 機器學習與通用資料集

結構化資料（CSV, JSON），適合回歸、分類與傳統機器學習實驗。

| 資源 | 說明 |
|------|------|
| [Kaggle Datasets](https://www.kaggle.com/datasets) | 全球最大的資料科學競賽平台，數十萬個社群貢獻的真實世界資料集，涵蓋金融、醫療、電商等 |
| [UCI Machine Learning Repository](https://archive.ics.uci.edu/) | 最經典的學術資料庫（如 Iris 鳶尾花資料），格式嚴謹，適合教學與演算法驗證 |
| [OpenML](https://www.openml.org/) | 強調可重現性，將資料集、演算法與實驗結果結合，可直接透過 Python 套件調用 |
| [Google Dataset Search](https://datasetsearch.research.google.com/) | 資料界的 Google 搜尋，從各大學、政府及研究機構中搜尋相關資料集 |

### 2. LLM 與生成式 AI 資料來源（NLP / Text）

用於微調（Fine-tuning）或預訓練（Pre-training）LLM 的資料。

| 資源 | 說明 |
|------|------|
| [Hugging Face Hub — Datasets](https://huggingface.co/datasets) | AI 界的標準入口。包含指令微調（如 Databricks-Dolly、ShareGPT）、多語言語料（Common Crawl、Wikipedia 各語言版本）等 |
| [Papers with Code](https://paperswithcode.com/datasets) | 將最新 AI 論文與使用的資料集串連，可查看 SOTA（當前最佳）模型所用的訓練資料 |
| [LMSYS Chatbot Arena Conversations](https://huggingface.co/datasets/lmsys/chatbot_arena_conversations) | 真實用戶與各種 LLM 互動的對話資料，適合研究模型偏好與對齊（Alignment） |

### 3. 語音與音訊模型資料（Speech / Audio）

針對語音轉文字（ASR）、文字轉語音（TTS）或情緒辨識。

| 資源 | 說明 |
|------|------|
| [Common Voice（Mozilla）](https://commonvoice.mozilla.org/) | 全球最大的開放原始碼多語言語音資料集，包含大量繁體中文語音 |
| [LibriSpeech](https://www.openslr.org/12) | 取自 LibriVox 有聲書，ASR 模型最常用的基準測試集 |
| [AudioSet（Google）](https://research.google.com/audioset/) | 超過 200 萬段 YouTube 片段的標註音訊，涵蓋 632 類音效 |
| [VoxCeleb](https://www.robots.ox.ac.uk/~vgg/data/voxceleb/) | 大型人聲資料集，主要用於說話者辨識（Speaker Recognition） |

### 4. 科學領域與特殊主題

| 資源 | 說明 |
|------|------|
| [NASA Open Data Portal](https://data.nasa.gov/) | 太空、地球科學及衛星遙測影像 |
| [PhysioNet](https://physionet.org/) | 生醫訊號（ECG、EEG）與臨床數據的權威來源 |
| [Registry of Open Data on AWS](https://registry.opendata.aws/) | 託管在 AWS 的大型資料集，包含基因組學（Genomics）、氣象衛星資料等 |

---

## 二、即時 API 平台與 IoT 資源

### 1. 全球即時 API 資料源（Real-time & Tool-ready）

適合開發 SaaS、RAG 或自動化工具，通常提供結構化 JSON 格式。

| 資源 | 說明 |
|------|------|
| [Unified.to](https://unified.to/) | 「統一 API」平台，將數百個 SaaS（CRM、HR、會計系統）整合進單一接口，適合 RAG 工具跨系統資料對接 |
| [Financial Modeling Prep](https://financialmodelingprep.com/) | 高頻率股市、經濟指標與公司財報 API，文檔與測試介面為業界標竿 |
| [Aviationstack](https://aviationstack.com/) | 全球航班即時狀態、機場與航線數據，物聯網追蹤與物流開發首選 |
| [OpenWeatherMap](https://openweathermap.org/) | IoT 專案最常串接的氣象 API，提供精確到分鐘的降水預報與全球氣象雷達資料 |

### 2. 台灣本土 IoT 與政府開放資料

| 資源 | 說明 |
|------|------|
| [民生公共物聯網（CIoT）](https://ci.taiwan.gov.tw/dsp/) | 台灣最完整的 IoT 資料集來源：空氣品質（微型感測器即時數值）、地震／水資源（即時水位、淹水感應器）、電力（台電負載與發電即時統計） |
| [台北市政府資料開放平台](https://data.taipei/) | 台灣各縣市中 API 化最成熟的平台，包含 YouBike 即時站位數、公車動態等 |
| [交通部 TDX 運輸資料流通服務](https://tdx.transportdata.tw/) | 全台所有交通載具（高鐵、台鐵、捷運、公車）的靜態與即時動態 API，開發交通 RAG 的核心來源 |

### 3. 全球科研與 IoT 訓練資料集

用於訓練模型（如異常檢測、節能預測）的歷史資料集。

| 資源 | 說明 |
|------|------|
| [CIC Datasets（Canadian Institute for Cybersecurity）](https://www.unb.ca/cic/datasets/index.html) | 最新 IoT 攻擊與安全資料集，專門用於開發 IoT 網路安全防護模型 |
| [Google Dataset Search — IoT 標籤](https://datasetsearch.research.google.com/) | 搜尋「Smart Home Logs」或「Industrial IoT」可找到智慧家庭設備活動日誌等 |
| [Registry of Open Data on AWS](https://registry.opendata.aws/) | 大量感測器原始數據，特別是地理空間（Sentinel 衛星）與氣候模型 |

---

## 三、股市金融

### 1. 台灣市場（台股、期貨、債券）

| 資源 | 說明 |
|------|------|
| [臺灣證券交易所 OpenAPI](https://openapi.twse.com.tw/) | 每日收盤行情、盤後資訊、上市公司基本資料、董監事持股等。官方來源，JSON 格式，免註冊可測試 |
| [證券櫃檯買賣中心 OpenAPI](https://www.tpex.org.tw/openapi/) | 上櫃、興櫃、創櫃及債券交易資訊 |
| [FinMind 台股數據 API](https://finmind.github.io/) | 開源專案，封裝台股、借券、融資融券等複雜數據，提供友善的 Python SDK（[GitHub](https://github.com/FinMind/FinMind)） |
| [永豐 Shioaji API](https://sinotrade.github.io/) | 即時行情（毫秒級）與自動化交易 SDK，開發者主流之一 |
| [元大證券 API](https://www.yuanta.com.tw/eyuanta/Securities/DigitalArea/ApiOrder) | 即時行情與程式交易下單 API |

### 2. 全球市場與 LLM 整合（Global & Agent-ready）

提供完整 JSON Schema，適合放入 MCP Server 讓 AI Agent 自動調用。

| 資源 | 說明 |
|------|------|
| [Financial Modeling Prep](https://financialmodelingprep.com/) | 「Yahoo Finance 最佳替代品」，含股價與極其詳細的財報（Income Statement、Cash Flow），適合開發會計／審計 AI 或投資研究 RAG |
| [Twelve Data](https://twelvedata.com/) | 整合股市、加密貨幣與外匯，WebSocket 支持強大，適合即時儀表板 |
| [Alpha Vantage](https://www.alphavantage.co/) | 老牌穩定，提供多種技術指標（SMA、RSI 等）的直接計算結果 |

### 3. 總體經濟與研究資料（Macro & Research）

| 資源 | 說明 |
|------|------|
| [FRED（St. Louis Fed）](https://fred.stlouisfed.org/) | 全球最大總體經濟資料庫，含美國與全球 GDP、CPI、利率、就業率等 80 萬個數據系列。Python 套件：`fredapi` |
| [Yahoo Finance（yfinance）](https://github.com/ranaroussi/yfinance) | 非官方 API，透過 `yfinance` 抓取歷史 K 線資料，免費且適合策略回測 |
| [Quandl / Nasdaq Data Link](https://data.nasdaq.com/) | 提供另類數據（Alternative Data）如航運數據、大宗商品庫存，適合深入研究模型 |

---

## 四、其他資源

### 1. 代碼與開發者行為資料（Developer Intelligence）

| 資源 | 說明 |
|------|------|
| [GitHub Archive（GHArchive）](https://www.gharchive.org/) | 記錄 GitHub 上所有事件（Star、Push、Issue），可分析特定技術的流行趨勢或常見 Bug 模式 |
| [Stack Exchange Data Explorer](https://data.stackexchange.com/) | 用 SQL 查詢 Stack Overflow 所有問答，對訓練「懂開發者痛點」的 RAG 系統非常有用 |
| [GHTorrent](https://ghtorrent.org/) | GitHub 鏡像數據，適合研究開源專案的演進邏輯（注意：2019 年後資料有缺口） |

### 2. 商業與法律實體資料（Business & Compliance）

對開發「會計 RAG」或「稅務自動化」至關重要。

| 資源 | 說明 |
|------|------|
| [台灣公司登記資料（經濟部）](https://data.gcis.nat.gov.tw/) | 即時驗證台灣公司統一編號、登記狀態與資本額，自動化會計流程必備校驗源 |
| [OpenCorporates](https://opencorporates.com/) | 全球最大企業資料庫，超過 2 億家公司資料，適合跨境貿易與海外公司背景查詢 |
| [司法院法學資料檢索系統](https://lawsearch.judicial.gov.tw/) | 裁判書開放資料，訓練法律／稅務 AI 判斷爭議案件的權威來源 |

### 3. 非結構化社群資料（Unstructured / Dark Data）

隱藏在互動中的「人類語氣」來源，LLM 訓練的寶貴素材。

| 資源 | 說明 |
|------|------|
| [Pushshift（Reddit Data）](https://pushshift.io/) | 獲取特定技術社群歷史討論的路徑（注意：Reddit 2023 年後限制 API，目前僅限已驗證版主申請存取） |
| Discord 訊息抓取（自建） | 許多現代技術（MCP、Supabase）的精華討論發生在 Discord，可透過自建 Bot 收集感興趣頻道的訊息（需合規），是建立私有知識庫的強大資料來源 |

### 4. 空間與地圖實體（Spatial & Real-world）

| 資源 | 說明 |
|------|------|
| [OpenStreetMap](https://www.openstreetmap.org/) / [Overpass Turbo](https://overpass-turbo.eu/) | 強大的地理資料庫，可過濾出特定地點類型（木材行、五金行、停車場等） |
| [Sentinel Hub](https://www.sentinel-hub.com/) | 歐洲航天局衛星影像，可研究特定區域的地形、綠化程度或森林火災風險 |

### 5. 區塊鏈與鏈上資料（On-chain Data）

| 資源 | 說明 |
|------|------|
| [Dune Analytics](https://dune.com/) | 透過 SQL 查詢區塊鏈數據，可分析全球支付趨勢或特定技術協議的採納率 |
