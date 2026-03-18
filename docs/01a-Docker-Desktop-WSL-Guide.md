# 📦 Docker Desktop 與 WSL 整合使用指南

---

> **🧭 本文件定位**
>
> 這是 [WSL 開發者特訓](01-Environment-WSL-Manual.md) 的 **Docker 專屬補充教材**。
> 主手冊的 Chapter 5（容器化思維）與 Chapter 6（Docker Compose）提供概念總覽，本文件提供完整的安裝、整合、故障排除流程。

---

## 目錄

- [為什麼不在 Ubuntu 裡裝 Docker？](#為什麼不在-ubuntu-裡裝-docker)
- [安裝 Docker Desktop](#安裝-docker-desktop)
- [開啟 WSL Integration](#開啟-wsl-integration)
- [驗證安裝](#驗證安裝)
- [Docker Image 下載過程詳解](#docker-image-下載過程詳解)
- [Docker Compose V2 入門](#docker-compose-v2-入門)
- [日常操作速查](#日常操作速查)
- [故障排除](#故障排除)
  - [殘留舊版 Docker 清除](#殘留舊版-docker-清除)
  - [Cannot connect to the Docker daemon](#cannot-connect-to-the-docker-daemon)
  - [permission denied ... docker daemon socket](#permission-denied)
  - [port is already allocated](#port-is-already-allocated)
  - [Image 下載卡住或很慢](#image-下載卡住或很慢)

---

## 為什麼不在 Ubuntu 裡裝 Docker？

```
❌ 不要在 Ubuntu 裡裝 Docker（sudo apt install docker.io）
✅ 一律用 Docker Desktop + WSL Integration
```

在 WSL 裡用 `apt` 裝 Docker 是**過時的做法**，會導致：

| 問題 | 原因 |
|------|------|
| `docker compose` 指令不存在 | `apt` 裝的是舊版 Docker，不含 Compose V2 plugin |
| `unknown shorthand flag: 'd' in -d` | 同上，`docker compose up -d` 無法解析 |
| daemon 跑不起來 | WSL 內的 systemd/service 機制與 Docker daemon 不相容 |
| 權限混亂 | 需要手動設定群組、socket 權限，容易出錯 |
| 網路異常 | 自建 daemon 的虛擬網路與 WSL2 NAT 容易衝突 |

**Docker Desktop 的做法完全不同**：它在 Windows 端運行 Docker Engine，然後透過 WSL Integration 把 `docker` 和 `docker compose` 指令自動注入你的 Ubuntu — 你不需要在 Linux 裡安裝任何東西。

```
Docker Desktop 架構：

┌─────────────────────────────────────────────┐
│              Windows 11 / 10                │
│                                             │
│  ┌───────────────────┐                      │
│  │  Docker Desktop   │──── Docker Engine    │
│  │  (Windows App)    │──── 管理所有容器     │
│  └────────┬──────────┘                      │
│           │ WSL Integration                 │
│           │ (自動注入 docker CLI)            │
│           ▼                                 │
│  ┌───────────────────┐                      │
│  │   WSL2 Ubuntu     │                      │
│  │                   │                      │
│  │  $ docker version ← 來自 Docker Desktop  │
│  │  $ docker compose ← Compose V2 plugin   │
│  └───────────────────┘                      │
└─────────────────────────────────────────────┘
```

---

## 安裝 Docker Desktop

### 前置條件

- Windows 10 (2004+) 或 Windows 11
- WSL 2 已安裝並可正常使用（見[主手冊 Chapter 0](01-Environment-WSL-Manual.md#chapter-0為什麼要用-wsl)）
- 有 Windows 管理員權限

### 安裝步驟

1. 前往 [Docker Desktop 官方下載頁面](https://www.docker.com/products/docker-desktop/) 下載安裝程式
2. 執行安裝程式，確認勾選 **Use WSL 2 based engine**
3. 安裝完成後，Docker Desktop 會自動啟動
4. 系統匣（右下角）會出現鯨魚圖示 🐳，代表 Docker Engine 正在運行

> 💡 **Docker Desktop 預設會隨 Windows 開機自動啟動。** 如果你不需要，可以在 Settings → General 取消勾選 "Start Docker Desktop when you sign in"。

---

## 開啟 WSL Integration

安裝 Docker Desktop 後，還需要**明確告訴它要整合哪個 WSL 發行版**：

1. 打開 Docker Desktop → **Settings** → **Resources** → **WSL Integration**
2. 確認 "Enable integration with my default WSL distro" 已開啟
3. 在下方列表中，勾選你的 Ubuntu 發行版（例如 `Ubuntu`）
4. 點擊 **Apply & Restart**

```
Docker Desktop Settings 畫面：

Resources → WSL Integration
─────────────────────────────────
☑ Enable integration with my default WSL distro

Enable integration with additional distros:
  ☑ Ubuntu          ← 勾選這個！
  ☐ Ubuntu-22.04
```

設定完成後，重啟 WSL：

```powershell
# 在 PowerShell 中執行
wsl --shutdown
```

然後重新開啟 Ubuntu 終端機。

---

## 驗證安裝

重新進入 Ubuntu 後，依序執行以下指令確認一切正常：

```bash
# 1. 確認 docker 指令存在且來自 Docker Desktop
which docker
# 👉 正常顯示：/usr/bin/docker

# 2. 確認 Docker Engine 版本
docker version
# 👉 應該看到 Client 和 Server 都有版本號
# 👉 如果 Server 那段報錯 → Docker Desktop 沒啟動

# 3. 確認 Compose V2 plugin（這是最關鍵的！）
docker compose version
# 👉 正常顯示：Docker Compose version v2.x.x
# 👉 如果報錯 → 見下方「故障排除」

# 4. 執行測試容器
docker run hello-world
# 👉 看到 "Hello from Docker!" 就代表完全正常！
```

### ✅ 安裝完成判準

- [ ] Docker Desktop 已安裝，系統匣有鯨魚圖示
- [ ] WSL Integration 已勾選你的 Ubuntu
- [ ] `docker compose version` 顯示 `v2.x.x`
- [ ] `docker run hello-world` 執行成功

---

## Docker Image 下載過程詳解

第一次執行 `docker compose up -d` 或 `docker run` 時，你會看到類似這樣的畫面：

```
[+] Running 2/2
 ⠿ db Pulling                                           45.2s
   ⠿ 2d473b07cdd5 Downloading  57MB/163MB               30.1s
   ⠿ a3ed95caeb02 Download complete                      2.3s
   ⠿ 1e2b64fce24c Downloading  12MB/42MB                 15.7s
 ⠿ web Pulling                                          12.5s
   ⠿ e4fff0779e6d Download complete                      5.2s
```

### 這不是卡住！是 Docker 正在下載 Image

Docker Image 是**分層 (Layer)** 結構：

```
一個 postgres:15 Image 的組成：

┌────────────────────────┐
│  PostgreSQL 15 程式     │  ← App Layer (~50MB)
├────────────────────────┤
│  系統工具 & 函式庫      │  ← Lib Layer (~30MB)
├────────────────────────┤
│  Debian 基礎系統        │  ← OS Layer (~80MB)
└────────────────────────┘
                         總計 ≈ 160MB
```

所以你會看到**多條進度條分段下載**，每條是一個 Layer。這是正常行為。

### 第一次下載的常見大小

| Image | 大小 | 用途 |
|-------|------|------|
| `postgres:15` | ~160MB | PostgreSQL 資料庫 |
| `nginx:latest` | ~70MB | Web 伺服器 |
| `supabase/postgres` | ~500MB | Supabase 資料庫（含擴充套件） |
| Playwright | ~1GB | 瀏覽器自動化（含 Chromium） |

> 💡 **第一次會慢，這很正常！** 下載完的 Layer 會快取在本地，之後同一個 Image 或共用相同 Layer 的 Image 會秒速啟動。

### 如何確認下載完成且服務正常？

開另一個終端機視窗，執行：

```bash
# 看容器是否在跑
docker compose ps

# 看即時 log（Ctrl+C 退出）
docker compose logs -f
```

你應該會看到：
- PostgreSQL 的初始化訊息（`database system is ready to accept connections`）
- Nginx 的啟動訊息

---

## Docker Compose V2 入門

### 新舊版本差異

Docker Compose 有兩個版本，現在只需要知道**新版**：

| | 舊版（已淘汰） | 新版（唯一標準） |
|---|---|---|
| **指令** | `docker-compose` (有連字號) | `docker compose` (空格) |
| **技術** | 獨立 Python 程式 | Docker CLI 的 Go plugin |
| **安裝** | 需另外 `pip install` | Docker Desktop 內建 |
| **設定檔** | 需要 `version: "3.x"` | 不需要 `version` 欄位 |

> **如果你在網路上看到 `docker-compose`（有連字號）的範例，請一律改成 `docker compose`（空格）。** 功能完全相同，但用舊版指令可能會在 WSL 環境出錯。

### docker-compose.yml 基本結構

```yaml
# docker-compose.yml（檔名不變，只是不需要 version 欄位了）
services:
  # 資料庫服務
  db:
    image: postgres:15    # 使用的 Docker Image
    environment:          # 環境變數（設定帳號密碼等）
      POSTGRES_USER: student
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: myapp
    ports:
      - "5432:5432"       # 主機 port : 容器 port
    volumes:
      - db_data:/var/lib/postgresql/data  # 持久化儲存

  # Web 伺服器
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    depends_on:           # 啟動順序：先啟動 db
      - db

volumes:
  db_data:                # 命名 volume（資料不會因容器刪除而消失）
```

> **💡 為什麼沒有寫 `version: '3.8'`？**
> Docker Compose V2 已經不需要 `version` 欄位，加了反而會跳出過時警告：
> ```
> WARN[0000] the attribute `version` is obsolete
> ```
> 如果你在網路上看到範例有寫 `version:`，可以安全地刪除那一行。

---

## 日常操作速查

### 基本操作

```bash
# 啟動所有服務（背景執行）
docker compose up -d

# 查看容器狀態
docker compose ps

# 查看即時 log（Ctrl+C 退出觀看，不會停止服務）
docker compose logs -f

# 停止並移除所有容器
docker compose down

# 停止並移除所有容器 + 清除 volume 資料（完全重來）
docker compose down -v
```

### 重建與更新

```bash
# 重新建置（程式碼或設定有改動時）
docker compose up -d --build

# 拉取最新版 Image
docker compose pull

# 拉取後重啟
docker compose pull && docker compose up -d
```

### 單一容器操作

```bash
# 列出所有容器（含已停止的）
docker ps -a

# 進入正在運行的容器
docker exec -it <容器名稱> /bin/bash
# 例如：docker exec -it week03-db-1 /bin/bash

# 停止單一容器
docker stop <容器名稱>

# 刪除單一容器
docker rm <容器名稱>
```

### 清理空間

```bash
# 查看 Docker 佔用的磁碟空間
docker system df

# 清除所有未使用的 Image、容器、網路（釋放空間）
docker system prune

# 連 volume 也一起清（⚠️ 會刪掉資料庫資料！）
docker system prune --volumes
```

---

## 故障排除

<a id="docker-cleanup"></a>
### 殘留舊版 Docker 清除

**症狀**：
- `unknown shorthand flag: 'd' in -d`
- `docker: 'compose' is not a docker command`
- `docker compose version` 報錯

**根本原因**：WSL 裡用 `sudo apt install docker.io` 裝了舊版 Docker，與 Docker Desktop 注入的版本衝突。

**診斷**：

```bash
# 確認 docker 指令來自哪裡
which docker

# 看版本
docker version

# 看 Compose V2 是否可用
docker compose version
```

**修復步驟**：

```bash
# 1. 移除所有殘留的 Docker 套件
sudo apt remove -y docker docker.io docker-ce docker-ce-cli containerd runc 2>/dev/null
sudo apt autoremove -y

# 2. 確認沒有殘留的 binary
which docker
# 如果還有殘留：
# sudo rm -f /usr/bin/docker

# 3. 回到 Docker Desktop
#    Settings → Resources → WSL Integration
#    確認 Ubuntu 有勾選 → Apply & Restart

# 4. 重啟 WSL
# （在 PowerShell 執行）
# wsl --shutdown

# 5. 重新進入 Ubuntu，驗證
docker compose version
# 👉 應該顯示：Docker Compose version v2.x.x
```

---

<a id="cannot-connect-to-the-docker-daemon"></a>
### Cannot connect to the Docker daemon

**症狀**：
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**排除步驟**：
1. **確認 Docker Desktop 有在 Windows 端啟動**：系統匣應該有鯨魚圖示 🐳
2. **確認 WSL Integration 已勾選你的 Ubuntu**：Docker Desktop → Settings → Resources → WSL Integration
3. **重啟**：`wsl --shutdown` 後重新進入 Ubuntu

---

<a id="permission-denied"></a>
### permission denied ... docker daemon socket

**症狀**：
```
permission denied while trying to connect to the Docker daemon socket
```

使用 Docker Desktop 時通常不需要額外設定群組權限。如果遇到：
1. 確認 Docker Desktop 的 WSL Integration 有正確啟用
2. 嘗試重啟 Docker Desktop 和 WSL
3. 如果仍然遇到，確認沒有殘留的舊版 Docker（見[上方清除步驟](#docker-cleanup)）

---

<a id="port-is-already-allocated"></a>
### port is already allocated

**症狀**：
```
bind: address already in use
```

代表你要用的 port 已經被其他程式佔住了。

**診斷**（在 PowerShell 執行）：
```powershell
# 查看誰佔用了 port（以 5432 為例）
netstat -ano | findstr :5432
# 或
Get-NetTCPConnection -LocalPort 5432
```

**解法**：
- 關閉佔用 port 的程式
- 或修改 `docker-compose.yml` 的 port 映射，例如：
  ```yaml
  ports:
    - "5433:5432"    # 主機改用 5433
  ```

---

<a id="image-下載卡住或很慢"></a>
### Image 下載卡住或很慢

**症狀**：`docker compose up -d` 停在 Pulling 很久，進度條不動。

**排除步驟**：

1. **確認網路正常**：
   ```bash
   curl -I https://registry-1.docker.io
   ```

2. **單獨拉取 Image 看詳細進度**：
   ```bash
   docker pull postgres:15
   ```

3. **如果是公司/學校網路**：可能有防火牆限制，嘗試：
   - 切換到手機熱點測試
   - 確認 VPN / 代理沒有干擾（見[主手冊網路排除](01-Environment-WSL-Manual.md#wsl2-localhost-troubleshooting)）

4. **如果持續卡住**：Docker Desktop → Settings → Docker Engine，可以加入鏡像加速源（視你的地區而定）

---

## Docker 資料存放位置

> 這是最多人問的問題：「Docker 的東西到底藏在哪裡？」

### 容器與映像檔

Docker Desktop 把所有資料存在一個虛擬硬碟中：

```
Windows 路徑：
%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx

這是一個大黑盒子（虛擬磁碟），Docker 不建議你直接打開它。
```

### 持久化資料 (Volumes)

`docker-compose.yml` 裡的 `volumes` 設定決定了資料如何持久化：

```yaml
# 命名 Volume（Docker 管理，資料安全）
volumes:
  - db_data:/var/lib/postgresql/data

# Bind Mount（映射到你的目錄，方便讀取）
volumes:
  - ./my-data:/var/lib/postgresql/data
```

| 類型 | 優點 | 適用場景 |
|------|------|----------|
| 命名 Volume | Docker 管理、效能好、不怕路徑問題 | 資料庫、快取 |
| Bind Mount | 可直接在主機讀寫檔案 | 開發時掛載程式碼 |

---

*本文件是 [WSL 開發者特訓](01-Environment-WSL-Manual.md) 的補充教材。*
*版本：1.0 | 最後更新：2026 年 3 月*
