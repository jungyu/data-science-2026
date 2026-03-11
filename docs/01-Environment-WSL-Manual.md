# 📘 WSL 開發者特訓：從 CLI 到全端開發

---

> **🧭 課程核心哲學：學會「如何查」比「背指令」重要**
>
> 這門課不教死背 `chmod` 的權限參數，而是教：
> **當權限報錯時，該如何用 `man` 手冊或 Google 找到答案。**
>
> 真正的工程師不是人肉字典，而是懂得問對問題的探索者。

---

## 目錄

- [第一階段：喚醒終端機 (The Awakening)](#第一階段喚醒終端機-the-awakening)
  - [Chapter 0：為什麼要用 WSL？](#chapter-0為什麼要用-wsl)
  - [Chapter 1：CLI 的第一課 (Navigation)](#chapter-1cli-的第一課-navigation)
- [第二階段：Linux 的靈魂 (The Essence)](#第二階段linux-的靈魂-the-essence)
  - [Chapter 2：權限與擁有者 (Permissions)](#chapter-2權限與擁有者-permissions)
  - [Chapter 3：管線與過濾 (Pipes & Filters)](#chapter-3管線與過濾-pipes--filters)
- [第三階段：開發者的時光機 (Git)](#第三階段開發者的時光機-git)
  - [Chapter 4：Git 基礎與遠端協作](#chapter-4git-基礎與遠端協作)
- [第四階段：開發者的標準配備 (Docker)](#第四階段開發者的標準配備-docker)
  - [Chapter 5：容器化思維](#chapter-5容器化思維)
  - [Chapter 6：Docker Compose](#chapter-6docker-compose)
- [第五階段：全端開發實戰 (Supabase & Web)](#第五階段全端開發實戰-supabase--web)
  - [Chapter 7：Supabase CLI 與後端整合](#chapter-7supabase-cli-與後端整合)
  - [Chapter 8：畢業專案 — 你的 CLI 助手](#chapter-8畢業專案--你的-cli-助手)
- [🧠 教學小撇步 (Head First Style Tips)](#-教學小撇步-head-first-style-tips)

---

## 第一階段：喚醒終端機 (The Awakening)

> **🎯 階段目標：擺脫滑鼠，感受鍵盤的節奏。**

---

### Chapter 0：為什麼要用 WSL？

#### 🖼️ 視覺化：Windows 與 Linux 的關係

```
┌────────────────────────────────────────────────┐
│               Windows 11 / 10                  │
│                                                │
│   ┌─────────────────────────────────────────┐  │
│   │           WSL 2 (虛擬層)                │  │
│   │                                         │  │
│   │   ┌───────────────────────────────┐     │  │
│   │   │   真正的 Linux 核心 (Kernel)  │     │  │
│   │   │   ─────────────────────────  │     │  │
│   │   │   Ubuntu / Debian / Fedora   │     │  │
│   │   └───────────────────────────────┘     │  │
│   └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

> WSL 不是模擬器，不是虛擬機，而是**內嵌在 Windows 裡的真正 Linux 核心**。  
> 這意味著你可以同時享受 Windows 的應用生態，以及 Linux 的開發環境。

---

#### 🛠️ 任務清單：環境安裝三步驟

| 步驟 | 工具 | 安裝方式 |
|------|------|----------|
| 1 | **WSL 2** | `wsl --install`（PowerShell 系統管理員） |
| 2 | **Windows Terminal** | Microsoft Store 搜尋安裝 |
| 3 | **VS Code** | 官網下載，並安裝 `Remote - WSL` 擴充套件 |

```powershell
# 在 PowerShell (系統管理員) 執行：
wsl --install

# 安裝完成後重新開機，接著設定 Linux 使用者名稱與密碼
```

---

#### 🧠 大腦體操：為什麼不直接用 Windows CMD？

| 比較項目 | PowerShell / CMD | Bash (WSL) |
|----------|-----------------|------------|
| 設計哲學 | 物件導向 | 文字串流（一切皆文字） |
| 套件生態 | NuGet, WinGet | apt, brew, pip |
| 腳本可攜性 | 僅 Windows | macOS / Linux / 雲端伺服器 |
| 開發工具支援 | 部分相容 | 原生支援（Node, Python, Docker） |

> **結論**：雲端伺服器 99% 跑的是 Linux，學 Bash 就是學習**與伺服器溝通的母語**。

---

#### ⚠️ 防呆區 (Wait, what?)

- **看到 `The virtual machine could not be started`？**  
  → 進入 BIOS 確認已啟用「虛擬化技術 (Virtualization Technology)」

- **WSL 版本不是 2？**  
  → 執行 `wsl --set-default-version 2` 更新預設版本

---

### Chapter 1：CLI 的第一課 (Navigation)

#### 🗺️ 檔案系統對應圖

```
Linux (WSL) 路徑              Windows 路徑
─────────────────────────     ─────────────────────
/home/你的名字/           ←→  (WSL 內部，無直接對應)
/mnt/c/Users/你的名字/    ←→  C:\Users\你的名字\
/mnt/c/                   ←→  C:\
/mnt/d/                   ←→  D:\
```

> 💡 **記住這個對應關係！** 這是學生最常混淆的地方。  
> 你的 Windows 桌面在 WSL 裡是：`/mnt/c/Users/你的名字/Desktop/`

---

#### 🛠️ 任務：在 `/mnt/c` 與 `/home` 之間穿梭

```bash
# 查看目前位置
pwd

# 列出所有檔案（含隱藏檔）
ls -la

# 移動到 Windows 的 C 槽
cd /mnt/c

# 回到 Linux 家目錄
cd ~

# 查看檔案內容
cat /etc/os-release
```

---

#### 🔑 關鍵指令速查表

| 指令 | 功能 | 範例 |
|------|------|------|
| `pwd` | 顯示目前路徑 | `pwd` |
| `ls -la` | 列出所有檔案（含詳細資訊） | `ls -la ~/projects` |
| `cd` | 切換目錄 | `cd /mnt/c/Users` |
| `cat` | 顯示檔案內容 | `cat README.md` |
| `touch` | 建立空白檔案 | `touch secret.txt` |
| `mkdir` | 建立目錄 | `mkdir -p .hidden/notes` |
| `rm` | 刪除檔案 | `rm secret.txt` |

---

#### 🎮 實戰練習：秘密筆記本任務

```bash
# 1. 建立一個隱藏目錄（以 . 開頭的目錄會被隱藏）
mkdir ~/.secret_vault

# 2. 建立秘密筆記本
touch ~/.secret_vault/my_secret.txt

# 3. 寫入內容
echo "這是我的秘密：我其實很怕 Permission Denied" > ~/.secret_vault/my_secret.txt

# 4. 確認它存在（注意要用 ls -la 才看得到隱藏目錄）
ls -la ~/

# 5. 讀取內容
cat ~/.secret_vault/my_secret.txt

# 6. 刪除它（任務完成！）
rm -rf ~/.secret_vault
```

---

#### 🕹️ 不插電時間：指令迷宮遊戲

> 在學習 CLI 之前，先在**紙上**畫出以下目錄結構，並回答問題：

```
/home/student/
├── projects/
│   ├── website/
│   │   └── index.html
│   └── scripts/
│       └── backup.sh
├── documents/
│   └── notes.txt
└── .hidden/
    └── secret.txt
```

**練習題**（不碰電腦，只用腦袋回答）：

1. 你在 `/home/student/projects/website/`，輸入 `cd ..` 後在哪裡？
2. 你在 `/home/student/documents/`，如何一步到達 `/home/student/projects/scripts/`？
3. 從任何位置輸入 `cd ~`，你會到哪裡？

---

## 第二階段：Linux 的靈魂 (The Essence)

> **🎯 階段目標：理解「一切皆檔案」的哲學。**

---

### Chapter 2：權限與擁有者 (Permissions)

#### 🖼️ 視覺化：rwx 數字解碼圖

```
ls -la 的輸出範例：
-rwxr-xr-- 1 aaron staff 1024 Mar 01 10:00 script.sh
 │││││││││
 ││││││││└─ 其他人 (Others)：r-- = 4 = 只能讀
 │││││││└── 其他人執行位
 ││││││└─── 群組 (Group)：r-x = 5 = 讀和執行
 │││││└──── 群組寫入位
 ││││└───── 群組讀取位
 │││└────── 擁有者 (Owner)：rwx = 7 = 全部權限
 ││└─────── 擁有者執行位
 │└──────── 擁有者寫入位
 └───────── 擁有者讀取位

權限數字對應：
  r (讀取) = 4
  w (寫入) = 2
  x (執行) = 1
  ─────────────
  rwx = 4+2+1 = 7
  r-x = 4+0+1 = 5
  r-- = 4+0+0 = 4
```

---

#### 🛠️ 任務：享受被拒絕的挫折感

```bash
# 嘗試修改系統檔案（你會被拒絕，這很正常！）
echo "hack" > /etc/hosts

# 你將看到：
# -bash: /etc/hosts: Permission denied

# 用 sudo 才能修改（但要非常小心！）
sudo nano /etc/hosts

# 查看自己的身份
whoami
id

# 修改一個自己建立的檔案權限
touch test.sh
chmod 755 test.sh   # 設定為 rwxr-xr-x
ls -la test.sh
```

> **💡 學習重點**：`Permission Denied` 不是錯誤，是**安全機制**。  
> 遇到它，先問自己：「我是正確的使用者嗎？」「我真的有必要用 `sudo` 嗎？」

---

#### ⚠️ 防呆區 (Wait, what?)

- **`sudo: command not found`？**  
  → 某些最小化安裝的 Linux 沒有 sudo，執行 `su root` 切換到 root 使用者

- **`chmod: invalid mode`？**  
  → 確認你輸入的是 3 位數字（例如 `755`，不是 `75`）

---

### Chapter 3：管線與過濾 (Pipes & Filters)

#### 🧠 大腦體操：廚房水管比喻

```
原始資料（水源）
      │
      ▼
  cat log.txt          ← 打開水龍頭（輸出全部資料）
      │
      │  ← 這是管線 |（資料流過這裡）
      ▼
  grep "ERROR"         ← 過濾器（只讓含 ERROR 的通過）
      │
      ▼
  sort                 ← 第二個過濾器（排序）
      │
      ▼
  > errors.txt         ← 儲水桶（輸出到檔案）
```

---

#### 🛠️ 任務：在一萬行 log 中找出錯誤

```bash
# 先產生一個假的 log 檔案來練習
cat /var/log/syslog | head -100

# 最基本的：grep 搜尋
grep "ERROR" /var/log/syslog

# 搭配管線，同時計算有幾行 ERROR
grep "ERROR" /var/log/syslog | wc -l

# 搜尋並只顯示前 10 筆
grep "ERROR" /var/log/syslog | head -10

# 輸出到檔案（覆蓋）
grep "ERROR" /var/log/syslog > errors_only.txt

# 輸出到檔案（追加，不覆蓋）
grep "ERROR" /var/log/syslog >> all_errors.txt

# 組合技：找錯誤、排序、去重複、存檔
cat /var/log/syslog | grep "ERROR" | sort | uniq > unique_errors.txt
```

---

#### 🔑 關鍵指令速查表

| 指令 | 功能 | 範例 |
|------|------|------|
| `grep` | 搜尋文字 | `grep "ERROR" log.txt` |
| `\|` | 管線，串接指令 | `cat file \| grep "key"` |
| `>` | 輸出到檔案（覆蓋） | `ls > list.txt` |
| `>>` | 輸出到檔案（追加） | `echo "新內容" >> log.txt` |
| `wc -l` | 計算行數 | `grep "ERROR" log \| wc -l` |
| `sort` | 排序 | `cat names.txt \| sort` |
| `uniq` | 去除重複行 | `sort names.txt \| uniq` |
| `head -n` | 顯示前 n 行 | `head -20 log.txt` |
| `tail -n` | 顯示後 n 行 | `tail -50 log.txt` |

---

## 第三階段：開發者的時光機 (Git)

> **🎯 階段目標：別再用 `final_v1`, `final_v2` 命名檔案了。**

---

### Chapter 4：Git 基礎與遠端協作

#### 🖼️ 視覺化：本地庫、暫存區、遠端倉庫的三角關係

```
                    ┌──────────────────┐
                    │   GitHub 遠端    │
                    │  (Remote Repo)   │
                    └────────┬─────────┘
                             │  ↑
                    git pull │  │ git push
                             │  │
┌──────────────────────────────────────────┐
│                本地端 (Local)            │
│                                          │
│  ┌──────────┐   git add   ┌───────────┐  │
│  │ 工作目錄 │ ──────────→ │  暫存區   │  │
│  │(Working  │             │ (Staging  │  │
│  │  Tree)   │ ←────────── │   Area)   │  │
│  └──────────┘  git restore└─────┬─────┘  │
│                                 │        │
│                          git commit      │
│                                 ↓        │
│                         ┌─────────────┐  │
│                         │  本地倉庫   │  │
│                         │ (Local Repo)│  │
│                         └─────────────┘  │
└──────────────────────────────────────────┘
```

---

#### 🛠️ 任務：將 CLI 練習筆記推送到 GitHub

```bash
# 初始化一個 Git 倉庫
mkdir cli-notes && cd cli-notes
git init

# 設定你的身份（首次使用必做）
git config --global user.name "你的名字"
git config --global user.email "your@email.com"

# 建立你的練習筆記
echo "# CLI 練習筆記" > README.md
echo "## 今天學到的指令" >> README.md
echo "- pwd：顯示目前路徑" >> README.md

# 將檔案加入暫存區
git add README.md
# 或加入所有改動
git add .

# 提交 commit（附上有意義的訊息）
git commit -m "feat: 新增 CLI 基礎指令筆記"

# 連結到 GitHub 遠端倉庫
git remote add origin https://github.com/你的帳號/cli-notes.git

# 推送到 GitHub
git push -u origin main
```

---

#### 🔑 Git 常用指令速查表

| 指令 | 功能 |
|------|------|
| `git init` | 初始化倉庫 |
| `git status` | 查看目前狀態 |
| `git add <file>` | 加入暫存區 |
| `git commit -m "msg"` | 提交 |
| `git log --oneline` | 查看提交歷史 |
| `git push` | 推送到遠端 |
| `git pull` | 拉取遠端更新 |
| `git branch` | 查看分支 |
| `git checkout -b <branch>` | 建立並切換分支 |

---

#### 🧱 防呆建議

> 如果你 `git push` 失敗，**不要慌**，讀最後那幾行錯誤訊息。

常見錯誤與解法：

```bash
# 錯誤：remote: Support for password authentication was removed
# 解法：使用 Personal Access Token (PAT) 代替密碼
# 到 GitHub → Settings → Developer settings → Personal access tokens

# 錯誤：error: failed to push some refs
# 解法：先 pull 再 push
git pull origin main --rebase
git push origin main

# 錯誤：nothing to commit, working tree clean
# 這不是錯誤！代表你的檔案已經是最新狀態 ✅
```

---

## 第四階段：開發者的標準配備 (Docker)

> **🎯 階段目標：解決「在我電腦上可以跑，在你那裡不行」的世紀難題。**

---

### Chapter 5：容器化思維

#### 🖼️ 視覺化：貨櫃船 vs. 虛擬機

```
虛擬機 (VM)                      Docker 容器
──────────────────               ──────────────────
┌────────────────────┐           ┌────────────────────┐
│     應用程式 A     │           │     應用程式 A     │
├────────────────────┤           ├────────────────────┤
│   完整 OS 副本     │           │  共用 Host OS 核心  │
│  （幾個 GB！）     │           │   （只有 MB！）    │
├────────────────────┤           └────────────────────┘
│   虛擬硬體層       │           ┌────────────────────┐
│   Hypervisor       │           │     應用程式 B     │
└────────────────────┘           ├────────────────────┤
                                 │  共用 Host OS 核心  │
                                 └────────────────────┘
                                         │
                                 ┌───────────────────┐
                                 │   Host OS (Linux) │
                                 └───────────────────┘
```

> **為什麼 Docker 輕？** 因為容器不需要完整的作業系統副本，只包含應用程式本身和它的依賴。就像**標準化貨櫃**，不管裝什麼貨，都能放到任何一艘船上。

---

#### 🛠️ 任務：啟動 Nginx 網頁伺服器

```bash
# 安裝 Docker（在 WSL Ubuntu 內）
sudo apt update
sudo apt install docker.io -y
sudo systemctl start docker
sudo usermod -aG docker $USER

# 重新登入後，測試 Docker 是否正常
docker --version
docker run hello-world

# 啟動 Nginx 伺服器
docker run -d -p 8080:80 --name my-nginx nginx

# 確認容器正在運行
docker ps

# 在 Windows 瀏覽器輸入 http://localhost:8080
# 你應該會看到 Nginx 歡迎頁面！ 🎉

# 停止並刪除容器
docker stop my-nginx
docker rm my-nginx
```

---

#### ⚠️ 防呆區 (Wait, what?)

- **`Cannot connect to the Docker daemon`？**  
  → 執行 `sudo service docker start` 啟動 Docker 服務

- **`port is already allocated`？**  
  → 換一個 port：`docker run -d -p 8081:80 nginx`

---

### Chapter 6：Docker Compose

#### 🛠️ 任務：一鍵啟動資料庫與應用程式

```yaml
# 建立 docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 資料庫
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: student
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: myapp
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  # 簡單的 Web 應用程式
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    depends_on:
      - db

volumes:
  db_data:
```

```bash
# 一鍵啟動所有服務
docker compose up -d

# 查看所有容器狀態
docker compose ps

# 查看 log
docker compose logs -f

# 一鍵關閉所有服務
docker compose down
```

---

## 第五階段：全端開發實戰 (Supabase & Web)

> **🎯 階段目標：用 CLI 串接真實世界的雲端資料庫。**

---

### Chapter 7：Supabase CLI 與後端整合

#### 🛠️ 任務：安裝 Supabase CLI 並連線雲端

```bash
# 方法一：使用 npm 安裝
npm install -g supabase

# 方法二：使用官方安裝腳本（推薦）
curl -fsSL https://supabase.com/install.sh | sh

# 確認安裝成功
supabase --version

# 登入 Supabase（會開啟瀏覽器驗證）
supabase login

# 在專案目錄初始化
mkdir my-supabase-project && cd my-supabase-project
supabase init

# 連結到你的雲端專案
supabase link --project-ref your-project-id

# 查看資料庫狀態
supabase status
```

---

#### 🔗 整合：本地開發 + 雲端佈署架構

```
開發環境 (WSL)
─────────────────────────────────────────
┌─────────────────────────────────────┐
│  你的應用程式 (Next.js / React)     │
│                                     │
│  開發時 ─→ Docker 本地 Postgres     │
│  佈署時 ─→ Supabase 雲端資料庫      │
└─────────────────────────────────────┘
         │
         │ supabase db push (同步 Schema)
         ▼
┌─────────────────────────────────────┐
│         Supabase Cloud              │
│   (PostgreSQL + Auth + Storage)     │
└─────────────────────────────────────┘
```

```bash
# 啟動本地 Supabase（包含完整服務）
supabase start

# 本地資料庫 URL 會顯示在終端機
# postgresql://postgres:postgres@localhost:54322/postgres

# 將本地 Schema 推送到雲端
supabase db push

# 停止本地服務
supabase stop
```

---

### Chapter 8：畢業專案 — 你的 CLI 助手

#### 🎓 實戰任務：自動備份 Shell Script

建立一個 `backup.sh` 腳本，自動備份重要檔案：

```bash
#!/bin/bash
# ================================================
# backup.sh - 自動備份並上傳到 Supabase Storage
# 作者：[你的名字]
# 日期：$(date +%Y-%m-%d)
# ================================================

# === 設定區 ===
BACKUP_DIR="$HOME/backups"
SOURCE_DIR="$HOME/projects"
SUPABASE_URL="https://你的專案.supabase.co"
SUPABASE_BUCKET="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${TIMESTAMP}.tar.gz"

# === 顏色設定 ===
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# === 函式定義 ===
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# === 主程式 ===
log_info "開始備份程序..."

# 1. 建立備份目錄
mkdir -p "$BACKUP_DIR"
log_info "備份目錄：$BACKUP_DIR"

# 2. 壓縮檔案
log_info "正在壓縮 $SOURCE_DIR..."
if tar -czf "$BACKUP_DIR/$BACKUP_FILE" "$SOURCE_DIR" 2>/dev/null; then
    log_info "壓縮完成：$BACKUP_FILE"
else
    log_error "壓縮失敗！"
    exit 1
fi

# 3. 顯示備份大小
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
log_info "備份大小：$BACKUP_SIZE"

# 4. 上傳到 Supabase Storage（需要 curl 和 API Key）
if [ -n "$SUPABASE_SERVICE_KEY" ]; then
    log_info "上傳到 Supabase..."
    curl -X POST \
        "${SUPABASE_URL}/storage/v1/object/${SUPABASE_BUCKET}/${BACKUP_FILE}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
        -H "Content-Type: application/gzip" \
        --data-binary "@${BACKUP_DIR}/${BACKUP_FILE}"
    log_info "上傳完成！✅"
else
    log_warn "未設定 SUPABASE_SERVICE_KEY，跳過上傳步驟"
fi

# 5. 清理 7 天前的舊備份
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
log_info "已清理 7 天前的舊備份"

log_info "備份程序完成！🎉"
```

```bash
# 讓腳本可執行
chmod +x backup.sh

# 執行備份
./backup.sh

# 設定排程（每天凌晨 2 點自動備份）
crontab -e
# 加入以下這行：
# 0 2 * * * /home/你的名字/backup.sh >> /home/你的名字/backup.log 2>&1
```

---

## 🧠 教學小撇步 (Head First Style Tips)

---

### 撇步 1：防呆區 (Wait, what?) 設計原則

> 每章節末尾都應設置**常見錯誤集中區**，讓學生在卡關時有地方查。

**範例格式**：

| 你看到的錯誤 | 原因 | 解法 |
|-------------|------|------|
| `command not found` | 套件未安裝，或未加入 PATH | `sudo apt install <套件名>` |
| `Permission denied` | 權限不足 | 確認是否需要 `sudo` |
| `No such file or directory` | 路徑錯誤 | 用 `ls` 確認路徑是否正確 |
| `Connection refused` | 服務未啟動 | 確認 Docker / 服務是否在運行 |

---

### 撇步 2：視覺圖卡設計建議

> 以下是本課程**最容易混淆的三個概念**，務必製作圖卡：

#### 圖卡 A：WSL 檔案系統對應

```
📁 Windows Explorer          🐧 WSL Terminal
──────────────────           ──────────────────
C:\                    ↔     /mnt/c/
C:\Users\Aaron\        ↔     /mnt/c/Users/Aaron/
C:\Users\Aaron\Desktop ↔     /mnt/c/Users/Aaron/Desktop
                             /home/aaron/          ← WSL 專屬家目錄
```

#### 圖卡 B：Git 三區域概念

```
未追蹤的檔案
     │
     │ git add
     ▼
  暫存區 (Staging)
     │
     │ git commit
     ▼
  本地倉庫 (Local)
     │
     │ git push
     ▼
  遠端倉庫 (GitHub)
```

#### 圖卡 C：Docker 生命週期

```
docker pull    →  映像檔 (Image)
                      │
             docker run│
                       ▼
                  容器 (Container)  ←→ 運行中的程式
                      │
           docker stop │
                       ▼
                  已停止的容器
                      │
            docker rm  │
                       ▼
                    (消失)
```

---

### 撇步 3：不插電時間設計建議

> 動手前先動腦，效果加倍！

| 章節 | 不插電活動 |
|------|----------|
| Chapter 1 | 在紙上畫目錄樹，練習路徑跳轉 |
| Chapter 2 | 用便利貼模擬 rwx 權限，3 人一組（擁有者 / 群組 / 其他人）輪流「進入房間」 |
| Chapter 3 | 用人力模擬管線：第一個人朗讀全文，第二個人只轉述含關鍵字的句子 |
| Chapter 4 | 畫出 Git 三角關係，並用箭頭標出每個 git 指令的方向 |
| Chapter 5 | 討論：如果你是一個 Docker 容器，你帶了哪些「必需品」上船？ |

---

### 撇步 4：如何「查」而非「背」— 工具清單

```bash
# 1. 查指令用法（最原始的方式）
man grep
man chmod

# 2. 快速查參數說明
grep --help
chmod --help

# 3. TL;DR 版（安裝 tldr 工具）
sudo apt install tldr
tldr grep
tldr git

# 4. 線上資源
# https://explainshell.com   ← 貼入任何指令，逐字解釋
# https://devhints.io        ← 各種工具的速查表 (Cheatsheet)
# https://stackoverflow.com  ← 工程師的聖地
```

---

## 📋 課程進度追蹤表

| 章節 | 主題 | 核心技能 | 完成 |
|------|------|----------|------|
| Chapter 0 | 為什麼要用 WSL？ | 環境安裝 | ☐ |
| Chapter 1 | CLI Navigation | pwd, ls, cd, cat | ☐ |
| Chapter 2 | 權限與擁有者 | chmod, sudo | ☐ |
| Chapter 3 | 管線與過濾 | grep, pipe, redirect | ☐ |
| Chapter 4 | Git 基礎 | add, commit, push | ☐ |
| Chapter 5 | 容器化思維 | docker run, ps | ☐ |
| Chapter 6 | Docker Compose | compose up/down | ☐ |
| Chapter 7 | Supabase CLI | 雲端資料庫連線 | ☐ |
| Chapter 8 | 畢業專案 | Shell Script 實戰 | ☐ |

---

*本手冊採用 Head First 教學風格設計，強調視覺化學習、動手實作與錯誤友善。*  
*版本：1.0 | 最後更新：2026 年 3 月*