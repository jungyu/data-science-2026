# 🟢 Supabase 本地開發與 Docker + WSL 實務指南

---

> **🧭 本文件定位**
>
> 這是 [WSL 開發者特訓](01-Environment-WSL-Manual.md) 的 **Supabase 專屬補充教材**。
> 主手冊 Chapter 7 提供 Supabase CLI 的入門概覽，本文件帶你走完從安裝到日常開發的**完整實務流程**。
>
> **前置條件**：你已經完成 [Docker Desktop 與 WSL 整合](01a-Docker-Desktop-WSL-Guide.md)，`docker compose version` 顯示 `v2.x.x`。

---

## 目錄

- [Supabase 到底是什麼？（30 秒版）](#supabase-到底是什麼30-秒版)
- [你的本地開發架構長什麼樣？](#你的本地開發架構長什麼樣)
- [前置安裝：Node.js v20+](#前置安裝nodejs-v20)
- [安裝 Supabase CLI](#安裝-supabase-cli)
- [初始化專案：supabase init](#初始化專案supabase-init)
- [啟動本地服務：supabase start](#啟動本地服務supabase-start)
  - [第一次啟動會很慢（這很正常！）](#第一次啟動會很慢這很正常)
  - [啟動完成後你會拿到什麼？](#啟動完成後你會拿到什麼)
- [連結雲端專案：supabase link](#連結雲端專案supabase-link)
- [Supabase Studio：你的資料庫管理介面](#supabase-studio你的資料庫管理介面)
- [日常開發工作流](#日常開發工作流)
  - [建立資料表（Migration）](#建立資料表migration)
  - [本地 ↔ 雲端同步](#本地--雲端同步)
  - [Seed Data：預填測試資料](#seed-data預填測試資料)
- [supabase start 背後發生了什麼？](#supabase-start-背後發生了什麼)
- [日常操作速查](#日常操作速查)
- [故障排除](#故障排除)
- [本地 vs. 雲端：什麼時候用哪個？](#本地-vs-雲端什麼時候用哪個)

---

## Supabase 到底是什麼？（30 秒版）

```
🧠 大腦體操：餐廳比喻

PostgreSQL = 廚房裡的那口灶（超強、萬用、但你要自己煮）

Supabase   = 整間餐廳
           （灶 + 服務生 + 點餐系統 + 外送平台 + 監控攝影機 都幫你裝好）
```

更具體地說：

```
┌─────────────────────────────────────────────────┐
│                   Supabase                      │
│                                                 │
│   Auth     Storage    Realtime    Edge Functions │
│  (登入)   (檔案)    (即時推播)    (無伺服器函式)  │
│                                                 │
│   PostgREST          Studio         GoTrue      │
│  (自動 API)       (管理介面)      (認證引擎)     │
│                                                 │
│          ┌──────────────────────┐               │
│          │     PostgreSQL 15    │               │
│          │    （真正的資料庫）    │               │
│          └──────────────────────┘               │
└─────────────────────────────────────────────────┘
```

> 💡 **關鍵認知**：Supabase 不是「像 PostgreSQL」的東西，它**就是** PostgreSQL。
> 每個 Supabase 專案底層都是一個完整的 PostgreSQL 資料庫，
> Supabase 只是幫你把周邊服務（Auth、API、管理介面…）全部包好。
>
> 想深入了解兩者的關係，請見 [PostgreSQL vs Supabase](13-Database-Supabase-vs-PostgreSQL.md)。

---

## 你的本地開發架構長什麼樣？

```
你的開發環境（一台電腦裡的三層世界）

┌─────────────────────────────────────────────────────┐
│                    Windows 11/10                    │
│                                                     │
│  ┌────────────────────┐   ┌──────────────────────┐  │
│  │   Docker Desktop   │   │    Chrome 瀏覽器      │  │
│  │   (管理所有容器)    │   │                      │  │
│  └────────┬───────────┘   │  localhost:54323      │  │
│           │ WSL Integration│  (Supabase Studio)   │  │
│           ▼               │                      │  │
│  ┌─────────────────────┐  │  localhost:8080       │  │
│  │    WSL2 Ubuntu      │  │  (你的 Web App)      │  │
│  │                     │  └──────────────────────┘  │
│  │  ~/my-project/      │                            │
│  │  ├── supabase/      │  ← Supabase 設定 & Migration│
│  │  ├── src/           │  ← 你的應用程式碼           │
│  │  └── .env           │  ← API Key（不上 Git！）   │
│  │                     │                            │
│  │  supabase start ──→ 啟動 10+ 個 Docker 容器      │
│  │                     │                            │
│  └─────────────────────┘                            │
└─────────────────────────────────────────────────────┘
```

> **為什麼需要 Docker？**
> `supabase start` 會在背後用 Docker 啟動一整組容器（PostgreSQL、PostgREST、GoTrue、Studio 等），
> 讓你在**完全離線**的情況下也能開發，不需要連到雲端。

---

## 前置安裝：Node.js v20+

Supabase CLI 本身不需要 Node.js，但後續的前端開發（Next.js / React）和 `supabase gen types` 等工具鏈會用到。建議在安裝 Supabase CLI 之前先把 Node.js 準備好。

> **⚠️ 不要用 `sudo apt install nodejs`！**
> Ubuntu 套件庫裡的 Node.js 版本通常很舊（v12 ~ v18），而且升級不方便。
> 使用 **nvm（Node Version Manager）** 可以輕鬆安裝、切換任意版本。

```bash
# 1. 安裝 nvm（Node 版本管理工具）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# 2. 載入 nvm（或重新開啟終端機）
source ~/.bashrc

# 3. 安裝 Node.js v20（目前 LTS 穩定版）
nvm install 20

# 4. 驗證
node -v    # 👉 應該顯示 v20.x.x
npm -v     # 👉 應該顯示 10.x.x
```

> 💡 **nvm 常用指令速查**：
> ```bash
> nvm ls              # 列出已安裝的版本
> nvm install 22      # 安裝 Node.js v22
> nvm use 20          # 切換到 v20
> nvm alias default 20  # 設定預設版本（每次開終端機自動用這個）
> ```

---

## 安裝 Supabase CLI

在 WSL Ubuntu 中，從 GitHub Release 直接下載（不依賴 Node.js）：

```bash
# 建立個人 bin 目錄（放自己安裝的執行檔）
mkdir -p ~/bin
cd /tmp

# 下載最新版 Supabase CLI
curl -L https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz -o supabase.tar.gz

# 解壓縮並安裝
tar -xzf supabase.tar.gz
chmod +x supabase
mv supabase ~/bin/supabase

# 把 ~/bin 加入 PATH（只需要做一次）
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 驗證安裝
supabase --version
# 👉 應該顯示版本號，例如：2.x.x
```

> 💡 **為什麼不用 `npm install -g supabase`？**
> npm 安裝方式需要先有 Node.js，而且有時會遇到版本衝突或權限問題。
> 直接從 GitHub 下載 binary 最乾淨、最不容易出問題。

### 登入 Supabase

```bash
supabase login
```

這會開啟瀏覽器讓你授權。

> **⚠️ WSL 無法自動開啟瀏覽器？**
> 這在 WSL 裡很常見。改用 Access Token 登入：
> 1. 到 [Supabase Dashboard](https://supabase.com/dashboard) → 左下角齒輪 → Access Tokens → Generate New Token
> 2. 執行：`supabase login --token <你的 token>`

---

## 初始化專案：supabase init

```bash
# 進入你的專案目錄
cd ~/my-project

# 初始化 Supabase
supabase init
```

執行後，你的目錄會多出一個 `supabase/` 資料夾：

```
🗂️ 你的專案初始化後長這樣：

my-project/
├── src/                    # 你的應用程式碼（自己建的）
├── .env                    # 真實 API Key（不上 Git！）
├── .env.example            # 空白範本（上 Git 讓別人知道要填什麼）
├── .gitignore              # 包含 .env
└── supabase/               # ← supabase init 自動生成的
    ├── config.toml          # Supabase 本地設定檔
    ├── migrations/          # 資料庫 Schema 變更紀錄
    │   └── (空的，等你建表)
    └── seed.sql             # 預填測試資料的 SQL 腳本
```

### 🧠 大腦體操：config.toml 是什麼？

```
config.toml 就像是一張「本地 Supabase 的設定清單」

它告訴 supabase start 要用：
  - 哪個 PostgreSQL 版本？（db.major_version = 15）
  - Studio 開在哪個 port？（studio.port = 54323）
  - API 開在哪個 port？（api.port = 54321）
  - 要不要啟用 Auth？（auth.enabled = true）
```

> 💡 **通常不需要改** — 預設值就能用。但如果你的 port 被佔了（例如同時跑 Chapter 6 的 compose），可以在這裡換成不同的 port。詳見下方[故障排除：port already in use](#supabase-start-報錯port-already-in-use)。

---

## 啟動本地服務：supabase start

```bash
supabase start
```

### 第一次啟動會很慢（這很正常！）

第一次執行 `supabase start` 時，你會看到類似這樣的畫面：

```
Pulling images ...
 ⠿ supabase/postgres:15.8.1.085       Pulling   120.5s
 ⠿ supabase/gotrue:v2.158.1           Pulling    45.2s
 ⠿ supabase/realtime:v2.30.34         Pulling    38.7s
 ⠿ supabase/storage-api:v1.11.13      Pulling    22.1s
 ⠿ supabase/postgrest:v12.2.3         Pulling    18.3s
 ⠿ supabase/studio:20241029           Pulling    95.4s
 ...
```

```
🧠 這裡發生了什麼？

supabase start 在背後做了這些事：

1. 下載 10+ 個 Docker Image（第一次約 500MB ~ 1GB）
2. 用 Docker Compose 啟動所有容器
3. 初始化 PostgreSQL 資料庫
4. 啟動 PostgREST（自動生成 REST API）
5. 啟動 GoTrue（Auth 認證服務）
6. 啟動 Studio（管理介面）
7. 啟動 Realtime（即時推播）
8. ... 還有更多
```

| 情境 | 預估時間 |
|------|----------|
| 第一次啟動（需下載 Image） | 3-10 分鐘（依網速） |
| 之後啟動（Image 已快取） | 30-60 秒 |
| `supabase stop` → `supabase start` | 30-60 秒 |

> **💡 如何確認不是卡住？**
> 開另一個終端機視窗執行 `docker ps`，你會看到容器一個一個冒出來。

---

### 啟動完成後你會拿到什麼？

啟動成功後，終端機會印出一張表：

```
         API URL: http://127.0.0.1:54321
     GraphQL URL: http://127.0.0.1:54321/graphql/v1
  S3 Storage URL: http://127.0.0.1:54321/storage/v1/s3
          DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
      Studio URL: http://127.0.0.1:54323
    Inbucket URL: http://127.0.0.1:54324
      JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
        anon key: eyJhbG...（很長一串）
service_role key: eyJhbG...（另一串）
   S3 Access Key: ...
   S3 Secret Key: ...
```

```
🧠 大腦體操：這些 URL 分別是什麼？

┌──────────────────────────────────────────────────────────┐
│  http://localhost:54321    API 端點                      │
│  ├── /rest/v1/            REST API（PostgREST 生成）    │
│  ├── /auth/v1/            認證 API（GoTrue）            │
│  └── /storage/v1/         檔案儲存 API                  │
│                                                          │
│  postgresql://...:54322    資料庫連線字串                 │
│  👉 給 psql / ORM / 程式碼用，不是給瀏覽器開的！        │
│                                                          │
│  http://localhost:54323    Supabase Studio 管理介面       │
│  👉 這個才是用 Chrome 打開的！                          │
│                                                          │
│  http://localhost:54324    Inbucket（測試信箱）           │
│  👉 Auth 寄出的驗證信會送到這裡（不是真的寄 email）     │
└──────────────────────────────────────────────────────────┘
```

> **⚠️ 最常搞混的地方：**
> - `54322` 是給程式連的（psql / Prisma / Drizzle），**不能**用瀏覽器開
> - `54323` 是給人看的管理介面，**用 Chrome 開**
> - `54321` 是 API 端點，給你的前端程式呼叫

---

## 連結雲端專案：supabase link

如果你已經在 [Supabase Dashboard](https://supabase.com/dashboard) 建立了雲端專案，可以把本地和雲端連起來：

```bash
# 取得你的 Project Reference ID
# 到 Supabase Dashboard → Settings → General → Reference ID
# 它長這樣：abcdefghijklmnop

supabase link --project-ref <你的-reference-id>
```

連結後，你就可以在本地和雲端之間同步資料庫結構（Schema）。

> **⚠️ `Project ref not found`？**
> 到 Supabase Dashboard 的 `Settings → General` 確認 Reference ID 有沒有複製對。
> 不是專案名稱，是那串英文亂碼。

---

## Supabase Studio：你的資料庫管理介面

啟動 `supabase start` 後，用 Windows 的 Chrome 打開：

```
http://localhost:54323
```

你會看到一個完整的管理介面，可以：

```
Studio 能做什麼？

📊 Table Editor    → 像 Excel 一樣瀏覽和編輯資料
📝 SQL Editor      → 直接寫 SQL 查詢
🔐 Authentication  → 管理使用者和登入設定
📁 Storage         → 上傳和管理檔案
📋 Database        → 查看資料表結構、索引、觸發器
📊 Reports         → 查看資料庫效能指標
```

> **🚨 Chrome 打開 `localhost:54323` 顯示 `ERR_CONNECTION_REFUSED`？**
> 這是 WSL2 網路穿透問題，不是 Supabase 的問題。
> 請回到主手冊的 [localhost 連線故障排除](01-Environment-WSL-Manual.md#wsl2-localhost-troubleshooting) 解決。
> Windows 11 使用者強烈建議啟用[鏡像模式網路](01-Environment-WSL-Manual.md#-推薦方案wsl2-鏡像模式網路-mirrored-mode-networking)。

---

## 日常開發工作流

### 建立資料表（Migration）

在 Supabase 的世界裡，資料庫結構的變更叫做 **Migration**（遷移）。
每一次變更都會產生一個 SQL 檔案，記錄你做了什麼，就像 Git commit 一樣。

```bash
# 建立一個新的 migration 檔案
supabase migration new create_students_table
```

這會在 `supabase/migrations/` 下產生一個新檔案：

```
supabase/migrations/
└── 20260318120000_create_students_table.sql   ← 時間戳記 + 你取的名字
```

編輯這個 SQL 檔案：

```sql
-- supabase/migrations/20260318120000_create_students_table.sql

CREATE TABLE students (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT UNIQUE NOT NULL,
  enrolled_at TIMESTAMPTZ DEFAULT now()
);

-- 啟用 Row Level Security（Supabase 最佳實務）
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
```

然後套用到本地資料庫：

```bash
# 重置本地資料庫並套用所有 migration
supabase db reset
```

> 💡 **也可以用 Studio 建表**：在 Studio 的 Table Editor 用 GUI 建好表後，
> 執行 `supabase db diff -f <名字>` 就能自動把變更轉成 migration 檔案。

---

### 本地 ↔ 雲端同步

```
🗺️ 同步流程圖：

  本地開發                              雲端 (Supabase Cloud)
  ────────                              ──────────────────────
  supabase/migrations/
  ├── 001_create_users.sql
  ├── 002_add_posts.sql               supabase db push
  └── 003_add_comments.sql    ─────────────────────→   雲端資料庫
                                                        (套用 Migration)

  supabase db pull              ←─────────────────────
  (把雲端變更拉回本地)                                   雲端上手動改的東西
```

```bash
# 把本地的 migration 推送到雲端
supabase db push

# 把雲端的資料庫結構拉回本地（如果有人在雲端手動改了東西）
supabase db pull
```

> **⚠️ 最佳實務**：永遠在本地寫 migration → push 到雲端。
> 避免在雲端 Dashboard 手動改結構（會造成本地和雲端不同步）。

---

### Seed Data：預填測試資料

`supabase/seed.sql` 是一個特殊檔案，每次 `supabase db reset` 時會自動執行。
用來預填開發/測試用的假資料：

```sql
-- supabase/seed.sql

INSERT INTO students (name, email) VALUES
  ('小明', 'ming@example.com'),
  ('小華', 'hua@example.com'),
  ('小美', 'mei@example.com');
```

```bash
# 重置資料庫（套用所有 migration + seed.sql）
supabase db reset

# 然後到 Studio 的 Table Editor 就能看到這三筆資料
```

---

## supabase start 背後發生了什麼？

當你執行 `supabase start` 時，背後其實是一個龐大的 Docker Compose 操作：

```bash
# 你可以用這個指令看到所有 Supabase 啟動的容器
docker ps --filter "label=com.supabase.cli.project"
```

```
🧠 大腦體操：supabase start 啟動了哪些容器？

容器名稱                     對應服務              Port     用途
─────────────────────────   ──────────────────   ──────   ──────────────────
supabase_db_...             PostgreSQL 15         54322    資料庫本體
supabase_rest_...           PostgREST             -        自動生成 REST API
supabase_auth_...           GoTrue                -        使用者認證
supabase_realtime_...       Realtime              -        即時推播
supabase_storage_...        Storage API           -        檔案管理
supabase_studio_...         Studio                54323    管理介面（你用 Chrome 開的）
supabase_kong_...           Kong API Gateway      54321    API 入口（統一路由）
supabase_meta_...           postgres-meta         -        資料庫 metadata API
supabase_inbucket_...       Inbucket              54324    測試信箱
supabase_imgproxy_...       imgproxy              -        圖片轉換
supabase_edge_functions_... Deno                  54325    Edge Functions 執行環境
```

> **💡 這就是為什麼 Supabase 需要 Docker Desktop**：
> 一次啟動 10+ 個容器，只有 Docker 能做到這件事。
> 如果你在 WSL 裡用 `apt install docker.io` 裝的舊版 Docker，
> 很可能跑不動這麼多容器（見 [Docker Desktop 指南](01a-Docker-Desktop-WSL-Guide.md)）。

---

## 日常操作速查

### 服務控制

```bash
# 啟動本地 Supabase（啟動所有容器）
supabase start

# 查看服務狀態 & 所有 URL / Key
supabase status

# 停止本地 Supabase（保留資料）
supabase stop

# 停止並清除所有資料（完全重來）
supabase stop --no-backup
```

### 資料庫操作

```bash
# 建立新的 migration
supabase migration new <名字>

# 列出所有 migration
supabase migration list

# 重置本地資料庫（重新套用所有 migration + seed）
supabase db reset

# 從 Studio 手動改的結構生成 migration
supabase db diff -f <名字>

# 用 psql 直接連線到本地資料庫
psql postgresql://postgres:postgres@localhost:54322/postgres
```

### 雲端同步

```bash
# 連結雲端專案
supabase link --project-ref <reference-id>

# 把本地 migration 推到雲端
supabase db push

# 把雲端結構拉回本地
supabase db pull

# 產生 TypeScript 型別定義（搭配前端使用）
supabase gen types typescript --local > src/types/database.ts
```

---

## 故障排除

### `supabase start` 失敗：`failed to connect to Docker daemon`

Docker Desktop 沒啟動，或 WSL Integration 沒勾選。

```bash
# 確認 Docker 正常
docker version
docker compose version

# 如果報錯，回到 Docker Desktop 確認設定
# 見：01a-Docker-Desktop-WSL-Guide.md
```

---

### `supabase start` 卡在 Pulling images

第一次啟動需要下載 ~1GB 的 Image，這很正常。

```bash
# 開另一個終端機，觀察下載進度
docker ps
docker images | grep supabase
```

如果真的卡住不動（超過 15 分鐘沒進度）：
1. 確認網路正常：`curl -I https://registry-1.docker.io`
2. 嘗試手動拉取最大的 Image：`docker pull supabase/postgres:15.8.1.085`
3. 如果是公司/學校網路，可能需要切換到手機熱點

---

### `supabase start` 報錯：port already in use

**症狀**：
```
Bind for 0.0.0.0:54322 failed: port is already allocated
```

這代表 Supabase 預設的 port（`54322`）已經被其他容器或服務佔住了。**不是 Supabase 壞掉，是 port 衝突。**

#### 🔍 Step 1：找出誰佔了 port

```bash
# 看所有正在跑的容器及其 port
docker ps --format "table {{.Names}}\t{{.Ports}}"

# 直接找佔用 54322 的容器
docker ps --filter "publish=54322"

# 也可以從 Linux 端查
sudo ss -ltnp | grep 54322
```

#### 最常見的兩種情境

**情境 A：你自己的 `docker compose` 裡有 PostgreSQL**

你在 Chapter 6 跑了 `docker compose up -d`，那個 compose 裡的 PostgreSQL 可能佔了 `5432` port。雖然不是 `54322`，但如果你之前改過 port 設定就可能撞到。

```bash
# 查看你的 compose 專案狀態
docker compose ps
```

**情境 B：上一次 `supabase start` 沒收乾淨**

`supabase stop` 有時沒完全清掉殘留容器，再次 `supabase start` 就會撞到自己。

#### ⚡ 快速修復：停掉佔用者

```bash
# 停掉佔用 54322 的容器
docker stop $(docker ps -q --filter "publish=54322")

# 如果想連容器一起刪除
docker rm -f $(docker ps -aq --filter "publish=54322")

# 然後重新啟動
supabase start
```

#### 🔧 更穩的解法：改 Supabase 本地 port

如果你打算**同時跑**自己的 `docker compose`（Chapter 6 的 Postgres + Adminer）和 Supabase local stack，
建議直接改 `supabase/config.toml`，讓兩組服務用不同 port，一勞永逸：

```toml
# supabase/config.toml

[api]
port = 64321          # API 端點（預設 54321）

[db]
port = 64322          # PostgreSQL（預設 54322）
shadow_port = 64320   # Migration 用的影子資料庫（預設 54320）
major_version = 15

[studio]
port = 64323          # Studio 管理介面（預設 54323）
```

改完後：

```bash
supabase start
supabase status    # 確認新的 port 有正確生效
```

> 💡 **改完 port 後，連線資訊也會跟著變**：
> - Studio 改開 `http://localhost:64323`
> - 資料庫連線字串改成 `postgresql://postgres:postgres@localhost:64322/postgres`
> - API 端點改成 `http://localhost:64321`

```
🧠 大腦體操：Chapter 6 的 compose 和 Supabase 的 port 分配

Chapter 6（你自己的 compose）     Supabase（改過 port 後）
──────────────────────────       ──────────────────────────
PostgreSQL   → 5432              PostgreSQL   → 64322
Adminer      → 8080              Studio       → 64323
Nginx        → 8088              API          → 64321
                                 Inbucket     → 64324

👉 完全不衝突，可以同時跑！
```

---

### Chrome 打開 `localhost:54323` 顯示 `ERR_CONNECTION_REFUSED`

這不是 Supabase 的問題，是 WSL2 網路穿透問題。

**排除步驟**：
1. 先確認 Supabase 有在跑：`supabase status`
2. 從 WSL 內部測試：`curl -I http://localhost:54323`
3. 如果 WSL 內部能通但 Chrome 不行 → 是網路穿透問題
4. 請回到 [主手冊 localhost 故障排除](01-Environment-WSL-Manual.md#wsl2-localhost-troubleshooting)
5. Windows 11 使用者建議啟用[鏡像模式](01-Environment-WSL-Manual.md#-推薦方案wsl2-鏡像模式網路-mirrored-mode-networking)

---

### `supabase login` 無法開啟瀏覽器

WSL 沒有圖形介面，無法自動開瀏覽器。

```bash
# 改用 Access Token 登入
# 1. 到 https://supabase.com/dashboard → Settings → Access Tokens
# 2. 生成新 Token
supabase login --token <你的 token>
```

---

### `supabase db push` 報錯：remote migration mismatch

本地和雲端的 migration 歷史不一致（通常是有人在雲端 Dashboard 手動改了結構）。

```bash
# 拉取雲端的最新狀態
supabase db pull

# 檢查差異
supabase db diff

# 如果確定以本地為準（⚠️ 會覆蓋雲端）
supabase db push --include-all
```

---

## 本地 vs. 雲端：什麼時候用哪個？

```
🧠 大腦體操：兩個環境的角色分工

┌──────────────────────────┬──────────────────────────┐
│     本地 (supabase start) │     雲端 (Supabase Cloud) │
├──────────────────────────┼──────────────────────────┤
│  ✅ 開發 & 測試           │  ✅ 正式上線 (Production)  │
│  ✅ 寫 migration          │  ✅ 真實使用者登入         │
│  ✅ 試 SQL 不怕弄壞       │  ✅ 對外提供 API          │
│  ✅ 離線也能工作           │  ✅ 自動備份              │
│  ❌ 不要拿來當正式環境     │  ❌ 不要直接改結構        │
└──────────────────────────┴──────────────────────────┘

正確的工作流：

  在本地寫 code + migration
         │
         │  git push（程式碼）
         │  supabase db push（資料庫結構）
         ▼
  雲端自動套用，上線！
```

> **💡 記住這個原則**：
> - **改結構**（建表、改欄位）→ 永遠在本地做，用 migration 管理
> - **改資料**（新增/修改資料）→ 看情況，開發用本地，正式用雲端
> - **改設定**（Auth、RLS 政策）→ 建議寫成 migration，不要只在 Dashboard 點

---

*本文件是 [WSL 開發者特訓](01-Environment-WSL-Manual.md) 的補充教材。*
*相關文件：[Docker Desktop 指南](01a-Docker-Desktop-WSL-Guide.md) | [PostgreSQL vs Supabase](13-Database-Supabase-vs-PostgreSQL.md) | [PostgreSQL 核心架構](14-PostgreSQL-Kernel-Architecture.md)*
*版本：1.0 | 最後更新：2026 年 3 月*
