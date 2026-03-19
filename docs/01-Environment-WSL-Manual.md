# 📘 WSL 開發者特訓：從 CLI 到全端開發

---

> **🧭 課程核心哲學：學會「如何查」比「背指令」重要**
>
> 這門課不教死背 `chmod` 的權限參數，而是教：
> **當權限報錯時，該如何用 `man` 手冊或 Google 找到答案。**
>
> 真正的工程師不是人肉字典，而是懂得問對問題的探索者。

---

---

## 🎯 你的學習地圖：打造專屬地基

在接下來的幾章中，我們將一步步引導你建立起專業的開發環境。這份手冊的最終目標是帶領你完成本週的畢業挑戰：

**[🏆 直接跳轉到本週畢業作業：打造地基](#week03-assignment) (建議學完 Chapter 1~8 再開始)**

### 你將會逐步解鎖的「裝備」：
- **Chapter 1 & 4**：解鎖 `README.md` (環境紀錄與 Git 協作)
- **Chapter 6**：解鎖 `docker-compose.yml` (一鍵啟動資料庫)
- **Chapter 8**：解鎖 `config.json` 與 `.env` (資安與配置)

讓我們開始這場從零到一的特訓吧！

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
- [第四階段：開發者的標準配備 (Docker)](#第四階段開發者的標準配備-docker) → 📖 [完整 Docker 指南](01a-Docker-Desktop-WSL-Guide.md)
  - [Chapter 5：容器化思維](#chapter-5容器化思維)
  - [Chapter 6：Docker Compose](#chapter-6docker-compose)
- [第五階段：全端開發實戰 (Supabase & Web)](#第五階段全端開發實戰-supabase--web) → 📖 [完整 Supabase 指南](01b-Supabase-Local-Dev-Guide.md)
  - [Chapter 7：Supabase CLI 與後端整合](#chapter-7supabase-cli-與後端整合)
  - [Chapter 8：開發者的護身符 (設定檔與資安)](#chapter-8開發者的護身符-設定檔與資安)
- [🧭 最短排錯流程圖](#-最短排錯流程圖)
  - [🌐 Windows 瀏覽器無法連到 WSL2 容器服務](#wsl2-localhost-troubleshooting)
  - [🪞 WSL2 鏡像模式網路](#-推薦方案wsl2-鏡像模式網路-mirrored-mode-networking)
- [🧠 教學小撇步 (Head First Style Tips)](#-教學小撇步-head-first-style-tips)
- [🧹 附錄：WSL 完整重置與重新安裝指南](#wsl-reset-reinstall)

---

## 第一階段：喚醒終端機 (The Awakening)

> **🎯 階段目標：擺脫滑鼠，感受鍵盤的節奏。**

---

### Chapter 0：為什麼要用 WSL？

#### ⏱️ 章節資訊
- 預估時間：20-30 分鐘
- 前置條件：Windows 10/11、可使用系統管理員權限的 PowerShell、穩定網路

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

> WSL 2 對開發者來說幾乎是原生 Linux 體驗，底層由 Windows 啟動的**輕量虛擬機**承載 Linux 核心。  
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

#### 💡 進階提示：如果預設安裝了 Alpine Linux？（如何更換為 Ubuntu）

有時 `wsl --install` 可能會預設安裝輕量化的 Alpine Linux，但本課程建議使用系統支援度最廣的 **Ubuntu**。

1. **查看目前可安裝的版本**  
   在 Windows 的 PowerShell 或 CMD 中輸入：
   ```powershell
   wsl --list --online
   ```

2. **安裝 Ubuntu**  
   執行安裝指令（預設安裝最新 LTS 版本）：
   ```powershell
   wsl --install -d Ubuntu
   ```
   *安裝時會彈出新視窗要求設定 Username 和 Password，請務必記住！*

3. **切換預設發行版**  
   如果你希望以後輸入 `wsl` 就直接進入 Ubuntu，請執行：
   ```powershell
   wsl --set-default Ubuntu
   ```

4. **移除舊的 Alpine (選填)**  
   若不再需要 Alpine（會刪除內部所有檔案）：
   ```powershell
   wsl --unregister Alpine
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

- **遇到 Windows 10 未升級導致沒有 WSL？**  
  → **先決條件：**您必須執行 Windows 10 版本 2004 和更新版本（組建 19041 和更新版本）或 Windows 11，才能使用 `wsl --install` 等相關命令。如果您使用的是舊版，請參閱 [微軟手動安裝頁面](https://learn.microsoft.com/zh-tw/windows/wsl/install-manual)。

- **遇到 Windows 登入的使用者權限-不具系統管理能力？**  
  → 往下看 [補充說明：Windows 權限與系統管理員](#windows-admin-rights)。

- **看到 `The virtual machine could not be started`？**  
  → 進入 BIOS 確認已啟用「虛擬化技術 (Virtualization Technology)」

- **WSL 版本不是 2？**  
  → 執行 `wsl --set-default-version 2` 更新預設版本

#### ✅ 完成判準
- 你可以在 Windows 終端機成功執行 `wsl` 進入 Ubuntu。
- 你知道自己的 Linux 使用者名稱，且可用 `whoami` 驗證。
- 你理解 WSL 與 Windows 的角色分工，知道何時在 PowerShell、何時在 Ubuntu 操作。

---

### Chapter 1：CLI 的第一課 (Navigation)

#### ⏱️ 章節資訊
- 預估時間：25 分鐘
- 前置條件：已完成 Chapter 0，能進入 Ubuntu 終端機

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

#### ✅ 完成判準
- 你可以不用複製貼上，自行完成 `pwd`、`ls -la`、`cd`、`cat` 的基本操作。
- 你能清楚說出 `/home/...` 與 `/mnt/c/...` 的差異。
- 你能獨立建立並刪除一個隱藏資料夾與檔案。

---

## 第二階段：Linux 的靈魂 (The Essence)

> **🎯 階段目標：理解「一切皆檔案」的哲學。**

---

### Chapter 2：權限與擁有者 (Permissions)

#### ⏱️ 章節資訊
- 預估時間：20 分鐘
- 前置條件：已理解 `pwd`、`ls`、`cd` 與家目錄 `~`

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

#### 🔐 `sudo` 使用邊界（先講清楚再用）

在初學階段，`sudo` 的確可以減少撞牆，但請遵守這三條：
1. **可以用 `sudo` 的時機**：安裝套件、啟動系統服務、修改 `/etc` 等系統層設定。
2. **不要用 `sudo` 的時機**：編輯自己的專案檔案（`~/` 下），避免把檔案擁有者改成 root。
3. **避免長時間 root shell**：不建議用 `sudo su` 做日常開發，改用「單行命令 + sudo」。

---

#### 🛠️ 任務：享受被拒絕的挫折感

```bash
# 嘗試在系統目錄建立檔案（你會被拒絕，這很正常！）
touch /usr/local/share/permission-lab.txt

# 你將看到：
# touch: cannot touch '/usr/local/share/permission-lab.txt': Permission denied

# 這一步使用 sudo，因為你正在寫入系統目錄（/usr/local/share）
sudo touch /usr/local/share/permission-lab.txt
sudo rm /usr/local/share/permission-lab.txt

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
  → 先確認你是否在 Ubuntu：`cat /etc/os-release`。  
  → 若是精簡版 Linux，請找助教協助補裝 `sudo`；不建議改成長期使用 root 進行開發。

- **`chmod: invalid mode`？**  
  → 確認你輸入的是 3 位數字（例如 `755`，不是 `75`）

#### ✅ 完成判準
- 你能讀懂 `-rwxr-xr--` 這類權限字串。
- 你知道何時應該用 `sudo`、何時不該用 `sudo`。
- 你可以用 `chmod 755` 成功改變測試檔案權限並驗證結果。

---

### Chapter 3：管線與過濾 (Pipes & Filters)

#### ⏱️ 章節資訊
- 預估時間：25 分鐘
- 前置條件：已能操作文字檔案並執行基本 CLI 指令

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
# 先產生一個可重現的練習 log（避免不同系統路徑差異）
cat > app.log <<'EOF'
INFO Server started
ERROR DB connection failed
INFO Retry request
ERROR Timeout while calling API
WARN Disk usage high
ERROR DB connection failed
EOF

# 最基本的：grep 搜尋
grep "ERROR" app.log

# 搭配管線，同時計算有幾行 ERROR
grep "ERROR" app.log | wc -l

# 搜尋並只顯示前 10 筆
grep "ERROR" app.log | head -10

# 輸出到檔案（覆蓋）
grep "ERROR" app.log > errors_only.txt

# 輸出到檔案（追加，不覆蓋）
grep "ERROR" app.log >> all_errors.txt

# 組合技：找錯誤、排序、去重複、存檔
grep "ERROR" app.log | sort | uniq > unique_errors.txt

# （選修）如果你的系統有 /var/log/syslog，也可這樣練習：
# grep "ERROR" /var/log/syslog | head -10
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

#### ✅ 完成判準
- 你可以用 `grep` 找到指定關鍵字並限制輸出筆數。
- 你可以用 `|`, `>`, `>>` 串接與保存結果。
- 你可以產生 `unique_errors.txt` 並解釋為什麼要先 `sort` 再 `uniq`。

---

## 第三階段：開發者的時光機 (Git)

> **🎯 階段目標：別再用 `final_v1`, `final_v2` 命名檔案了。**

---

### Chapter 4：Git 基礎與遠端協作

#### ⏱️ 章節資訊
- 預估時間：40 分鐘
- 前置條件：已完成 Chapter 1、已註冊 GitHub 帳號、可連網

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

#### 🔐 第一步：設定 SSH Key 與 GitHub 連線

在 WSL2 (Ubuntu) 環境下，最推薦的做法是使用 SSH Key。這能讓您在 `git clone` 或 `git push` 時不需要每次都輸入長長的密碼，既安全又方便。

請按照以下三個簡單步驟操作：

##### 1. 產生您的專屬金鑰 (SSH Key)
在您的 Ubuntu 終端機輸入這行指令：
```bash
ssh-keygen -t ed25519 -C "您的 GitHub 註冊信箱"
```
> **注意**：系統會問您要存在哪或是否輸入密碼（Passphrase），直接連按 3 下 **Enter** 即可（保持預設路徑且不設密碼）。

##### 2. 複製公鑰內容
產生完成後，您需要把「公鑰」的內容複製起來交給 GitHub。請執行：
```bash
cat ~/.ssh/id_ed25519.pub
```
畫面上會出現一串以 `ssh-ed25519` 開頭、您的信箱結尾的長字串。請完整選取並複製它。

##### 3. 將金鑰新增至 GitHub 網頁
1. 登入您的 GitHub 官網。
2. 點擊右上角個人頭像 -> **Settings**。
3. 在左側選單找到 **SSH and GPG keys**。
4. 點擊右上角的綠色按鈕 **New SSH key**。
5. **Title**: 隨便取個名字（例如：`My-WSL-PC`）。
6. **Key**: 把剛剛複製的那串內容貼進去。
7. 按下 **Add SSH key**，完成！

##### ✅ 測試是否成功
回到 Ubuntu 終端機，輸入這行指令測試連線：
```bash
ssh -T git@github.com
```
如果是第一次連線，會問你：*Are you sure you want to continue connecting (yes/no/[fingerprint])?*  
請輸入 **yes** 並按 **Enter**。

如果看到 `"Hi [您的帳號]! You've successfully authenticated..."`，就代表您已經成功「登入」GitHub 了！

---

#### 🛠️ 第二步：從 GitHub 複製專案與基礎操作

在真實的開發流程中，我們通常會**先在 GitHub 網頁上建立好一個 Repository (專案倉庫)**，然後再把它「複製 (Clone)」到我們的電腦上。

**前置作業：** 請先到 GitHub 網頁上點擊 `New repository`，建立一個名為 `cli-notes` 的專案（不要勾選 Add a README file），並複製它的 SSH 網址。

> 💡 **實戰小技巧：複製專案時的選擇**  
> 以後在 GitHub 點擊綠色的 "Code" 按鈕複製網址時，請記得切換到 **SSH** 分頁（網址會是 `git@github.com:使用者名稱/專案名.git`），這樣才不會被要求輸入密碼。

```bash
# 1. 將 GitHub 上的專案複製 (Clone) 到本地端
git clone git@github.com:你的帳號/cli-notes.git

# 進入專案資料夾
cd cli-notes

# 2. 設定你的身份（首次使用必做）
# 💡 注意：即使剛剛設定了 SSH 金鑰，這裡還是「必須」設定的！
# SSH 金鑰是為了「連線免密碼」，而這裡的設定是為了「在每筆 Commit 紀錄你是誰」。
git config --global user.name "你的名字"
git config --global user.email "your@email.com"

# 3. 建立你的練習筆記
echo "# CLI 練習筆記" > README.md
echo "## 今天學到的指令" >> README.md
echo "- pwd：顯示目前路徑" >> README.md

# 4. 將檔案加入暫存區
git add README.md
# 或加入所有改動
git add .

# 5. 提交 commit（附上有意義的訊息）
git commit -m "feat: 新增 CLI 基礎指令筆記"

# 6. 首次推送到 GitHub（明確指定 main，避免 upstream / 分支名卡關）
git branch -M main
git push -u origin main
```

---

#### 🔑 Git 常用指令速查表

| 指令 | 功能 |
|------|------|
| `git clone` | 複製遠端倉庫到本地 |
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

> 如果你 `git push` 或連線 GitHub 失敗，**不要慌**，讀最後那幾行錯誤訊息。
> 詳細清單請看後方附錄：[Git 常見錯誤與解法](#git-common-errors)。

#### ✅ 完成判準
- 你能完成一次 `clone -> add -> commit -> push` 流程。
- 你可以用 `git status` 說明目前在 working tree / staging 的狀態。
- 你知道首次推送時應使用 `git push -u origin main`。

---

## 第四階段：開發者的標準配備 (Docker)

> **🎯 階段目標：解決「在我電腦上可以跑，在你那裡不行」的世紀難題。**

---

### Chapter 5：容器化思維

#### ⏱️ 章節資訊
- 預估時間：35 分鐘
- 前置條件：已完成 Chapter 0、可在 WSL 中使用 `sudo`、有 Windows 管理員權限（安裝 Docker Desktop 需要）

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

#### 🛠️ 任務：安裝 Docker Desktop 並驗證

> **🚨 關鍵觀念：WSL 時代的 Docker 正確安裝方式**
>
> ```
> ❌ 不要在 Ubuntu 裡裝 Docker（sudo apt install docker.io）
> ✅ 一律用 Docker Desktop + WSL Integration
> ```
>
> 在 WSL 裡用 `apt` 裝 Docker 會導致：daemon 跑不起來、沒有 Compose V2 plugin、權限混亂、網路異常。
> **Docker Desktop 會自動把完整的 `docker` 和 `docker compose` 指令注入 WSL，不需要你在 Linux 裡安裝任何東西。**

**請依照 [Docker Desktop 與 WSL 整合使用指南](01a-Docker-Desktop-WSL-Guide.md) 完成以下步驟：**

1. [安裝 Docker Desktop](01a-Docker-Desktop-WSL-Guide.md#安裝-docker-desktop)（在 Windows 端，[官方下載頁面](https://www.docker.com/products/docker-desktop/)）
2. [開啟 WSL Integration](01a-Docker-Desktop-WSL-Guide.md#開啟-wsl-integration)（Docker Desktop → Settings → Resources → WSL Integration → 勾選 Ubuntu）
3. [驗證安裝](01a-Docker-Desktop-WSL-Guide.md#驗證安裝)（在 WSL 中執行 `docker compose version` 確認看到 `v2.x.x`）

安裝驗證完成後，試跑你的第一個容器：

```bash
# 執行官方測試容器，看到 "Hello from Docker!" 就代表成功！
docker run hello-world

# 啟動 Playwright 自動化測試環境（微軟官方容器，內建瀏覽器驅動）
docker run -d --name my-playwright-env mcr.microsoft.com/playwright:v1.40.0-jammy tail -f /dev/null

# 確認容器正在運行
docker ps

# 進入容器內部逛逛（這就是你未來的 Automation 執行基地）
docker exec -it my-playwright-env /bin/bash
# (逛完後輸入 exit 退出)

# 停止並刪除容器
docker stop my-playwright-env && docker rm my-playwright-env
```

---

#### ⚠️ 防呆區 (Wait, what?)

<a id="docker-cleanup"></a>
> 完整的故障排除流程請見 [Docker Desktop 故障排除](01a-Docker-Desktop-WSL-Guide.md#故障排除)，以下是快速摘要：

- **`unknown shorthand flag: 'd' in -d` 或 `'compose' is not a docker command`？**
  → WSL 裡殘留了舊版 Docker。請照 [清除步驟](01a-Docker-Desktop-WSL-Guide.md#殘留舊版-docker-清除) 移除後重啟。

- **`Cannot connect to the Docker daemon`？**
  → 確認 Docker Desktop 有在 Windows 端啟動（系統匣有鯨魚圖示 🐳），且 WSL Integration 已勾選。

- **`permission denied ... docker daemon socket`？**
  → 使用 Docker Desktop 時不需要設定群組權限，重啟 Docker Desktop 和 WSL 即可。

- **`port is already allocated`？**
  → 換一個 port，例如 `-p 8081:8080`。

#### ✅ 完成判準
- Docker Desktop 已安裝，且 WSL Integration 已啟用。
- 在 WSL 中執行 `docker compose version` 可以看到 `v2.x.x`。
- 你可以成功執行 `docker run hello-world`。
- 你可以使用 `docker ps`、`docker exec`、`docker stop`、`docker rm` 完成容器生命週期操作。

---

### Chapter 6：Docker Compose

#### ⏱️ 章節資訊
- 預估時間：30 分鐘
- 前置條件：Chapter 5 完成，`docker run hello-world` 可成功

#### 🌉 觀念橋樑：從單一容器到 Docker Compose

剛剛我們學會了用 `docker run` 啟動**一個** Nginx 容器（一個貨櫃）。但現實世界中，一個網站通常不會只有網頁伺服器，它還需要**資料庫（PostgreSQL）**、**後端 API（Node.js / Python）**甚至**快取（Redis）**。

如果每次都要手動輸入很長的指令去啟動三、四個容器，不僅容易打錯參數，還很難建立它們之間的網路連線（讓後端能連到資料庫）。

**這時候 Docker Compose 就來拯救我們了！**  
它就像是一張「**貨物配置清單（YAML 檔）**」，我們只要把需要哪些容器、密碼是什麼、開哪個 Port 寫在清單上，就能「**一鍵叫出所有貨櫃，並自動把它們連好網路**」。

---

#### 🛠️ 任務：一鍵啟動資料庫環境 (Docker Compose)

> **💡 這份 compose 只負責本章練習**
> - `nginx`：驗證 Windows 瀏覽器可以連到 WSL 內的容器服務（後續所有開發的基礎）
> - `crawler`：練習容器化 Playwright 爬蟲
>
> 完整的 `qdrant + mcp-server` 架構放在 [`_project-fullstack/`](../_project-fullstack/)，最終專案直接用那份，不需要在這裡堆服務。
>
> 資料庫（PostgreSQL）由 Chapter 7 的 `supabase start` 負責，也不需要放進這份 compose。

---

**📝 預備知識：用 Nano 編輯檔案**  
在接下來的任務裡，我們需要新增或編輯設定檔。Linux 內建最親民的文字編輯器叫做 **Nano**。
基本操作只有四步：
1. **輸入與貼上：** 打開檔案後，你可以直接打字。如果是從網頁複製的文字，對著 Terminal **點擊滑鼠右鍵** 就能貼上。
   - **💡 為什麼不是 Ctrl+V？** 在 Linux 終端機裡，`Ctrl+C` 是用來「中斷/強制停止程式」的，如果直接按 `Ctrl+V` 則可能打出怪字元。因此，微軟的 Windows Terminal 預設將複製與貼上的快捷鍵設定為 `Ctrl+Shift+C` 與 `Ctrl+Shift+V` 以避免衝突！
   - **⚙️ 如何確認/修改 Terminal 快捷鍵：**
     點擊 Windows Terminal 最上方標籤列右側的 `下拉式選單 (˅)` → `設定 (Settings)` → 點擊左側 `互動 (Interaction)`，勾選「**使用 Ctrl+Shift+C/V 做為複製/貼上**」來啟用快捷鍵。
2. **存檔準備：** 按 `Ctrl + O` (這是英文字母 O，不是零)。
3. **確認檔名：** 螢幕下方會問你檔名對不對？按下 `Enter` 確認。
4. **離開編輯：** 按 `Ctrl + X` 關閉檔案並回到終端機。

有了這些基本功，就可以來建立我們的第一張設定清單了！

```bash
# 1. 依照作業規範建立資料夾結構
mkdir -p week03/html && cd week03

# 2. 建立一個簡單的首頁（用來測試 Nginx 是否正常）
cat > html/index.html << 'EOF'
<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>week03 local stack</title></head>
<body>
  <h1>Docker Compose 啟動成功 🎉</h1>
  <p>Nginx 正常運作。接下來可以打開 <a href="http://localhost:6333/dashboard">Qdrant Dashboard</a> 確認向量資料庫。</p>
</body>
</html>
EOF

# 3. 開啟 Nano 準備撰寫 yaml 設定檔
nano docker-compose.yml
```

**(進入 Nano 編輯畫面後，右鍵貼上以下內容，然後 Ctrl+O -> Enter -> Ctrl+X 存檔離開！)**

```yaml
# docker-compose.yml
# 完整專案模板請見 _project-fullstack/docker-compose.yml
name: week03-stack

services:
  # 靜態網頁伺服器：驗證 Windows 瀏覽器可以連到 WSL 內的容器服務
  nginx:
    image: nginx:alpine
    container_name: week03-nginx
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro

  # Playwright 爬蟲：練習容器化爬蟲，之後接上向量資料庫
  crawler:
    build: ./crawler          # 基於 mcr.microsoft.com/playwright/python
    container_name: week03-crawler
    restart: unless-stopped
    ports:
      - "3001:3001"
```

> **💡 這份 compose 只做兩件事**：驗證 localhost 穿透（nginx）、練習容器化爬蟲（crawler）。完整的 qdrant + mcp-server 架構在 [`_project-fullstack/`](../_project-fullstack/) 中，做最終專案時直接用那份。
>
> 為什麼沒有寫 `version: '3.8'`？Docker Compose V2 已不需要此欄位，加了會出現 `WARN the attribute 'version' is obsolete` 警告。

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

> **⚠️ 如果你看到 `docker: 'compose' is not a docker command` 或 `unknown shorthand flag: 'd' in -d`？**
> 這代表你的 Docker 環境不完整。**請不要改用舊版 `docker-compose` 指令**（那是已淘汰的做法）。
> 請回到 [Chapter 5 防呆區](#docker-cleanup) 按照步驟清除殘留 Docker，確認使用 Docker Desktop + WSL Integration。

> 📖 **想深入了解？** 更多 Compose 日常操作指令、Image 下載過程說明、資料存放位置等，請參考 [Docker Desktop 與 WSL 整合使用指南](01a-Docker-Desktop-WSL-Guide.md)。

---

#### 🌐 驗證：用 Windows 瀏覽器連到 WSL 容器服務

啟動 Compose 後，最重要的一步是**確認 Windows 的 Chrome 能連到 WSL 內的服務**。
這是後續所有開發工作的基礎（包括 Chapter 7 的 Supabase Studio）。

```bash
# 先確認容器確實在跑，且 port 有正確映射
docker compose ps
# 你應該看到類似：
# NAME           ... STATE     PORTS
# ds-nginx           running   0.0.0.0:8080->80/tcp
# ds-crawler         running   0.0.0.0:3001->3001/tcp
```

**打開 Windows 的 Chrome，驗證 Nginx：**

| 服務 | 網址 | 你應該看到 |
|------|------|-----------|
| Nginx | `http://localhost:8080` | 你寫的 HTML 頁面（「Docker Compose 啟動成功」） |

> **💡 crawler 還沒有 Web UI**，目前只是確認容器有跑起來。之後 Stage 2 解鎖 Qdrant 後，爬蟲抓到的內容才會有地方存。

> **🚨 如果看到 `ERR_CONNECTION_REFUSED` 或頁面載入不出來？**
> 這是 WSL2 初學者最常卡關的地方！請依照後方的 [🌐 補充：Windows 瀏覽器無法連到 WSL2 容器服務](#wsl2-localhost-troubleshooting) 逐步排除。

---

#### ⚠️ 防呆區 (Wait, what?)

- **Chrome 打開 `localhost:8080` 顯示 `ERR_CONNECTION_REFUSED`？**
  → 這是網路穿透問題，不是 Docker 壞掉！請跳到後方 [localhost 連線故障排除](#wsl2-localhost-troubleshooting)。

- **Chrome 一直轉圈 (Loading) 最後逾時？**
  → 可能是防火牆攔截，請跳到後方 [防火牆排除](#wsl2-localhost-troubleshooting)。

- **`docker compose up -d` 報錯 `unable to prepare context: path "./crawler" not found`？**
  → `./crawler` 目錄還不存在。建立一個佔位 Dockerfile 讓 compose 可以正常啟動：
  ```bash
  mkdir -p ~/week03/crawler
  cat > ~/week03/crawler/Dockerfile << 'EOF'
  FROM mcr.microsoft.com/playwright/python:v1.49.0-noble
  WORKDIR /app
  CMD ["sleep", "infinity"]
  EOF
  docker compose up -d
  ```
  爬蟲章節會再替換這個 Dockerfile 為正式版本。

#### ✅ 完成判準
- 你可以從 `docker-compose.yml` 一鍵啟動並關閉多容器環境。
- 你可以用 `docker compose ps` 與 `docker compose logs -f` 檢查服務狀態。
- **你可以在 Chrome 打開 `http://localhost:8080` 看到你寫的 HTML 頁面。**
- 你理解 Compose 相對於手動 `docker run` 的優勢，以及服務會隨課程逐步解鎖的設計邏輯。

> **💡 這份 compose 之後還會用到**
> Chapter 7 起你會加入 Supabase（用 `supabase start` 獨立啟動），最終專案再把 API 服務也加進這份 compose。這個檔案不是練習完就丟掉的——它是你專案基礎設施的起點。

---

## 第五階段：全端開發實戰 (Supabase & Web)

> **🎯 階段目標：用 CLI 串接真實世界的雲端資料庫。**

---

### Chapter 7：Supabase CLI 與後端整合

> 📖 **完整教學**：本章提供入門概覽。完整的安裝流程、日常開發工作流、Migration 管理、故障排除，請見 [Supabase 本地開發與 Docker + WSL 實務指南](01b-Supabase-Local-Dev-Guide.md)。

> **💡 Supabase 和你的 docker-compose.yml 是並行的，不衝突**
> `supabase start` 會在背後自己跑一套 Docker 容器（PostgreSQL、Studio、Auth...），和你在 Chapter 6 建的 `docker-compose.yml` 是**完全獨立的兩套服務**。開發時兩個都跑，互不干擾：
> ```
> supabase start          # 負責：資料庫、Auth、Studio（:54323）
> docker compose up -d    # 負責：Qdrant（:6333）、Nginx（:8080）
> ```
> 你的 API 之後會同時連這兩套（Supabase 提供 DB + Auth，Qdrant 提供向量搜尋）。

#### ⏱️ 章節資訊
- 預估時間：35 分鐘
- 前置條件：Docker Desktop 已安裝且 WSL Integration 已啟用（見 Chapter 5）、已建立 Supabase 帳號

#### 🛠️ 任務：安裝 Supabase CLI 並連線雲端

```bash
# 0. 前置檢查：Supabase 本地服務依賴 Docker
docker --version
docker ps >/dev/null

# 安裝 Supabase CLI（從 GitHub Release 直接下載，不依賴 Node.js）
mkdir -p ~/bin
cd /tmp
curl -L https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz -o supabase.tar.gz
tar -xzf supabase.tar.gz
chmod +x supabase
mv supabase ~/bin/supabase
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 確認安裝成功
supabase --version

# 登入 Supabase（會開啟瀏覽器驗證）
supabase login

# 在你的作業 Repo 目錄初始化（範例：cli-notes/week03）
cd ~/cli-notes
mkdir -p week03
cd week03
supabase init

# 💡 初始化後，你的目錄會長這樣：
# week03/
# ├── docker-compose.yml   # Qdrant + Nginx（專案基礎設施，之後會繼續擴充）
# ├── config.json          # 你的 JSON 練習檔
# ├── .env.example         # 變數範本
# └── supabase/            # 自動生成的 Supabase 控制中心
#     ├── config.toml
#     ├── migrations/
#     └── seed.sql

# 連結到你的雲端專案
supabase link --project-ref your-project-id

# 查看資料庫狀態
supabase status
```

#### ⚠️ 防呆區 (Wait, what?)

- **`supabase login` 無法開啟瀏覽器？**
  → 可改用 Access Token：`supabase login --token <your-token>`。

- **`failed to connect to Docker daemon`？**
  → 先確認 Docker Desktop 有在 Windows 端啟動（系統匣應該有鯨魚圖示），且 WSL Integration 已勾選你的 Ubuntu（見 [Chapter 5](#chapter-5容器化思維)）。確認後重跑 `supabase start`。

- **`Project ref not found`？**
  → 到 Supabase 專案 Dashboard 的 `Settings -> General` 複製正確 `Reference ID`。

- **Chrome 打開 `localhost:54323` (Supabase Studio) 顯示 `ERR_CONNECTION_REFUSED`？**
  → 這是 Chapter 6 就需要解決的 WSL2 網路穿透問題。請回到 [🌐 localhost 連線故障排除](#wsl2-localhost-troubleshooting) 完成排除。
  → 如果你用的是 Windows 11，最推薦直接啟用 [鏡像模式網路](#wsl2-localhost-troubleshooting) 一次解決。

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
# 注意：這是給 psql / ORM / 程式碼用的連線字串，不是給瀏覽器開的網址。

# 若要用 Windows 瀏覽器檢視 PostgreSQL 的網頁管理介面，請開：
# http://localhost:54323   (Supabase Studio)

# 將本地 Schema 推送到雲端
supabase db push

# 停止本地服務
supabase stop
```

#### ✅ 完成判準
- 你可以完成 `supabase init`、`supabase link`、`supabase start` 基本流程。
- 你知道 `postgresql://...` 是連線字串，瀏覽器要看的是 `http://localhost:54323`。
- 你可以描述「本地開發」與「雲端 Supabase」在流程中的分工。

---

### Chapter 8：開發者的護身符 (設定檔與資安)

#### ⏱️ 章節資訊
- 預估時間：20 分鐘
- 前置條件：已完成 Chapter 4 與 Chapter 7 的基本操作

#### 📝 觀念 1：JSON 資料建模 (Configuration)
在現代全端開發中，**JSON** 是最常見的資料交換與設定格式。它就像是 Python 的字典或 JavaScript 的物件。

**範例格式 (`config.json`)：**
```json
{
  "project_name": "My Supabase App",
  "region": "ap-northeast-1",
  "features": [
    "auth",
    "database",
    "storage"
  ]
}
```
> **⚠️ 格式防呆：**
> 1. JSON 的字串和鍵名**都必須使用雙引號 (`"`)**，不能用單引號。
> 2. 最後一個屬性後面**絕對不能有逗號 (`,`)**。這也是最常見的語法錯誤！

#### 🛡️ 觀念 2：環境變數與 .gitignore
在開發 Supabase 或串接其他第三方服務時，你一定會拿到「API Key」或資料庫密碼。
**絕對不要把這把鑰匙直接寫在程式碼中，更不要被 `git push` 上傳到 GitHub！** (否則不僅是資安外洩，有些服務甚至會把你帳號停權)。

**開發業界標準實務 (3+1 步防護)：**
1. **建立 `.env` 檔案（真正的鑰匙）：**
   此檔案會存放真實密碼，而且**只會存在你的本機**。
2. **建立 `.env.example` 檔案（空鑰匙盒）：**
   隨專案上傳給其他人看，讓他們知道需要填入哪些變數，但裡面**不能填寫真實密碼**。
3. **建立 `.gitignore` 檔案（海關黑名單）：**
   明確告訴 Git：「永遠不要追蹤 `.env` 檔案」。

```bash
# 在你即將推送到 GitHub 的專案目錄中操作 (例如 week03/)

# 1. 產生真實環境變數檔 (放真 Key)
# 建議用編輯器手動輸入，避免把金鑰留在 shell history
nano .env
# 填入：SUPABASE_API_KEY="eyJhbG..."

# 2. 產生範本檔 (讓看 Repo 的人知道要填這欄)
nano .env.example
# 填入：SUPABASE_API_KEY=""

# 3. 把 .env 列入 Git 黑名單！！！
echo ".env" >> .gitignore

# 此時如果做 git add .
# Git 就會自動忽略 .env！恭喜你已經擁有了真正的資安觀念。

# 4. 如果你曾經誤加過 .env，立刻取消追蹤（不刪本機檔案）
git rm --cached .env
```

#### ✅ 完成判準
- 你能建立格式正確的 `config.json`。
- 你能建立 `.env` 與 `.env.example`，並確保真實金鑰不進版控。
- 你能說明為什麼 `.gitignore` 是資安基本習慣。

---

## 🧭 最短排錯流程圖

卡住時請先走這 6 步，不要直接重灌：

1. **看最後一行錯誤訊息**：先抓關鍵字（`permission denied`、`command not found`、`connection refused`、`publickey`）。
2. **確認你在哪裡**：`pwd`、`whoami`、`ls`，確認目錄和使用者是否正確。
3. **確認工具有安裝**：`git --version`、`docker --version`、`supabase --version`。
4. **確認服務有啟動**：`docker ps`、`supabase status`（Docker 不通？確認 Docker Desktop 有在 Windows 端啟動）。
5. **確認網路與認證**：`ssh -T git@github.com`、重看 token / key / 權限設定。
6. **最後才做重置動作**：保留錯誤訊息截圖，帶著訊息請助教協助。

快速對照：
- `command not found`：通常是沒安裝或 PATH 問題。
- `Permission denied`：先判斷是否系統層操作，再決定是否加 `sudo`。
- `Connection refused`：服務沒啟動或 port 不對。
- `ERR_CONNECTION_REFUSED`（Chrome）：WSL2 網路穿透問題，見 [localhost 連線故障排除](#wsl2-localhost-troubleshooting)。
- `Connection timeout`（curl / git）：防火牆或 MTU 問題，見 [網路故障排除](#wsl2-localhost-troubleshooting)。
- `failed to push some refs`：先 `git pull --rebase` 再 `git push`。

<a id="wsl2-localhost-troubleshooting"></a>
#### 🌐 補充：Windows 瀏覽器無法連到 WSL2 容器服務（localhost 不通）

> **💡 為什麼這很重要？**
> 在本課程中，Docker Compose (Chapter 6) 的 Nginx 要用 `localhost:8080` 驗證網頁、Supabase Studio (Chapter 7) 要用 `localhost:54323` 操作資料庫 — 如果 Windows 瀏覽器連不到 WSL2 的服務，後面所有章節都會卡住。

WSL2 內部跑的容器服務，要讓 Windows 的 Chrome 能透過 `localhost` 連到，必須經過一層**網路穿透**。以下是最完整的排除流程：

```
Windows Chrome                WSL2 Ubuntu
─────────────                ──────────────
http://localhost:8080  ──?──→  Docker Nginx (port 80)
http://localhost:54323 ──?──→  Supabase Studio
                        ↑
                   這一段可能斷掉！
                   原因：防火牆 / NAT 模式 / port 衝突
```

**🔍 第 0 步：先確認容器有在跑（排除 Docker 本身問題）**

```bash
# 在 WSL 內執行
docker compose ps
# 確認 STATE 是 running，且 PORTS 欄位有顯示 0.0.0.0:8080->80/tcp

# 從 WSL 內部測試服務是否正常
curl -I http://localhost:8080
# 如果這裡就失敗 → 是 Docker 問題，不是網路穿透問題
# 如果這裡成功但 Chrome 打不開 → 繼續往下排除
```

**1. Windows 防火牆攔截 WSL2 流量（最常見！）**

Windows Defender 防火牆可能將 WSL2 的虛擬網卡視為「公用網路」，**同時攔截進出兩個方向的流量**：
- **出站攔截**：WSL 內 `curl`、`git push` 逾時
- **入站攔截**：Windows Chrome 連 `localhost` 被拒絕（`ERR_CONNECTION_REFUSED`）

```
測試方法：
1. 暫時關閉 Windows Defender 防火牆
   （Windows 設定 → 隱私權與安全性 → Windows 安全性 → 防火牆與網路保護）
2. 在 Chrome 重新打開 http://localhost:8080（Nginx）
3. 如果這時通了 → 確認是防火牆的問題，請執行下方指令永久修復
```

- **解決方法**：在 PowerShell (管理員) 執行以下指令：
  ```powershell
  # 方法 A：允許 WSL 虛擬網卡的所有流量（最簡單）
  New-NetFirewallRule -DisplayName "WSL2 Inbound" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
  New-NetFirewallRule -DisplayName "WSL2 Outbound" -Direction Outbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
  ```

  ```powershell
  # 方法 B：如果方法 A 報錯「找不到 vEthernet (WSL)」，改用以下指令
  # （先查看你的 WSL 虛擬網卡實際名稱）
  Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*Hyper-V*" }
  # 用查到的名稱替換下方的 InterfaceAlias
  ```

  ```powershell
  # 方法 C：如果你使用 Windows 11 22H2+ 且啟用了鏡像模式（見下方），
  # 需要額外設定 Hyper-V 防火牆：
  Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
  ```

> **⚠️ 第三方防毒軟體注意**：Trend Micro, FortiClient, ESET, Kaspersky, Norton 等防毒軟體有自己的防火牆，即使關閉 Windows Defender 防火牆也可能持續攔截。請在這些軟體中也檢查是否有阻擋 WSL 相關的規則。

**2. Windows 上有其他程式佔用了相同 port**

```powershell
# 在 PowerShell 中檢查誰佔用了 8080 port
netstat -ano | findstr :8080
# 或
Get-NetTCPConnection -LocalPort 8080
```

如果有其他程式佔用，選擇其中一個解法：
- 關閉佔用 port 的程式
- 修改 `docker-compose.yml` 的 port 映射（例如改成 `"8081:80"`），然後 Chrome 改連 `localhost:8081`

**3. MTU (最大傳輸單元) 設定過大**

如果你身處的網路環境（例如某些公司 VPN、校園網或是特定路由器）對封包大小有限制，WSL2 預設的 MTU (1500) 可能過大，導致小封包 (Ping) 能過，但建立連線的大封包 (TCP) 被丟棄。

- **嘗試修改 MTU**（在 WSL 內執行）：
  ```bash
  sudo ip link set dev eth0 mtu 1400
  ```
  修改後再試一次 `curl https://github.com`，如果通了，就是 MTU 的問題。

> **💡 注意**：MTU 修改在 WSL 重啟後會失效。如果確認是 MTU 問題，可在 `~/.bashrc` 末尾加入：
> ```bash
> sudo ip link set dev eth0 mtu 1400 2>/dev/null
> ```
> 這樣每次開啟終端機就會自動套用。

**4. 代理伺服器 (Proxy) 或網路加速器衝突**

如果你在 Windows 上有開啟任何代理工具（如系統代理、VPN 或遊戲加速器），它們常會攔截 WSL2 的流量卻處理失敗。

- **檢查**：確保 Windows 代理設定中，沒有干擾到 WSL2 的虛擬橋接。
- **測試**：暫時關閉所有代理 / VPN / 加速器，再試一次。

**5. WSL2 的 localhost 轉發機制故障（重啟大法）**

WSL2 預設的 NAT 模式有一個自動的 localhost 轉發機制，但它偶爾會「卡住」。最快的修復方式：

```powershell
# 在 PowerShell 中徹底重啟 WSL
wsl --shutdown
```

然後重新開啟 Ubuntu，重新 `docker compose up -d`，再試 Chrome。

---

#### 🪞 推薦方案：WSL2 鏡像模式網路 (Mirrored Mode Networking)

> **適用版本**：Windows 11 22H2 以上
>
> **💡 如果你正在使用 Windows 11，強烈建議直接啟用鏡像模式**，它能從根本上解決上面大部分的 localhost 連線問題。

WSL2 預設使用 **NAT 模式**，Windows 和 WSL 之間隔了一層虛擬 NAT 閘道，localhost 的穿透靠的是一個不太穩定的自動轉發機制。**鏡像模式**則是將 Windows 的網路介面直接「鏡像」到 Linux，讓兩邊共享同一套網路堆疊：

```
NAT 模式（預設，容易出問題）：
Windows ──NAT閘道──→ WSL2 VM（獨立 IP）
  ↑ localhost 轉發可能斷掉

鏡像模式（推薦）：
Windows ←──共享網路介面──→ WSL2
  ↑ localhost 直接互通，不需要轉發
```

**鏡像模式的優點**：
- **localhost 直接互通**：Chrome 連 `localhost:8080`（Nginx）、`localhost:54323`（Supabase Studio）不再經過 NAT 轉發，穩定度大幅提升
- **改善 VPN 相容性**：傳統 NAT 模式下 VPN 常與 WSL2 衝突，鏡像模式能大幅緩解
- **IPv6 支援**：原生支援 IPv6 網路
- **LAN 直連**：區域網路內其他設備可直接連入 WSL2 的服務
- **多播 (Multicast) 支援**

**啟用方式**：

1. 在 Windows 使用者目錄下建立或編輯 `.wslconfig` 檔案：
   ```powershell
   # 在 PowerShell 中執行
   notepad "$env:USERPROFILE\.wslconfig"
   ```

2. 加入以下設定：
   ```ini
   [wsl2]
   networkingMode=mirrored
   dnsTunneling=true
   autoProxy=true
   ```
   > **設定說明**：
   > - `networkingMode=mirrored`：啟用鏡像模式，Windows 與 WSL 共享網路介面
   > - `dnsTunneling=true`：透過虛擬化處理 DNS 請求，改善 VPN 環境下的 DNS 解析（Windows 11 22H2+ 預設已開啟）
   > - `autoProxy=true`：自動將 Windows 的代理伺服器設定同步到 WSL，不需要手動設定 `http_proxy` 等環境變數

3. 重新啟動 WSL：
   ```powershell
   wsl --shutdown
   ```

4. 重新開啟 Ubuntu 終端機，驗證網路：
   ```bash
   # 測試對外連線
   curl -I https://www.google.com

   # 啟動 Docker 服務後，測試 localhost 穿透
   # (如果你的 docker compose 還在跑)
   curl -I http://localhost:8080
   ```

5. 回到 Windows Chrome，打開 `http://localhost:8080`（Nginx），應該能順利看到頁面。

**⚠️ 啟用鏡像模式後仍需注意**：
- 如果區域網路內其他設備要連入你的 WSL 服務，需額外設定 Hyper-V 防火牆：
  ```powershell
  # 在 PowerShell (管理員) 執行
  Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
  ```
  或僅開放特定 port（更安全）：
  ```powershell
  New-NetFirewallHyperVRule -Name "WSL-Web" -DisplayName "WSL Web Services" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol TCP -LocalPorts 8080,3001,6333,54321,54322,54323
  ```
- Windows 10 不支援鏡像模式，請使用前面的防火牆修復方法
- 如果你有用到 `ip addr` 取得 WSL IP 的腳本，鏡像模式下 IP 會與 Windows 相同，可能需要調整

> 📖 **參考資料**：[微軟官方文件 — WSL 鏡像模式網路](https://learn.microsoft.com/zh-tw/windows/wsl/networking#mirrored-mode-networking)

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
| Chapter 8 | 配置與資安 | JSON, .env, .gitignore | ☐ |

---

<a id="week03-assignment"></a>
## 🎓 畢業考：本週作業 (打造地基)

各位同學好！這一週我們從純軟體開發跨入了「系統環境」的領域。這些工具（WSL, Docker, Supabase）是現代全端工程師與資料科學家的標準配備。

這週的作業目的不是要考倒你，而是要幫你建立起屬於自己的雲端開發工作台。請依照以下說明，將所有成果整理至你的 GitHub 倉庫 (Repository) 中。

### 📁 本週目錄結構
請在你的 Repo 根目錄下建立一個 `[學習週別]` 資料夾 (例如 `week03`)，結構如下：

```text
/ (Repo Root)
└── [學習週別]/
    ├── README.md            # 本週學習心得與任務檢核（必填！）
    ├── docker-compose.yml   # Qdrant + Nginx（專案基礎設施）
    ├── config.json          # 專案配置練習檔
    └── .env.example         # 變數範本（保護秘密的示範）
```

### 🎯 任務詳細說明

#### 1. WSL 與 Docker 環境解鎖 🛠️
在 `[學習週別]/README.md` 中，請用幾句話記錄你的安裝心得：
- 你在安裝 WSL 或 Docker 時有遇到什麼「驚喜（Bug）」嗎？你是如何解決的？
- 請在 `[學習週別]/` 下放 Chapter 6 的 `docker-compose.yml`（Qdrant + Nginx），確保你能一鍵啟動並用瀏覽器驗證兩個服務。

#### 2. Supabase 雲端專案初始化 ☁️
請到 [Supabase 官方網站](https://supabase.com/)建立一個新專案，並：
- 在 `[學習週別]/README.md` 中貼上你的 **Project URL**（不需要貼 API Key，資安第一！）。
- 練習建立一個簡單的資料表（例如：`students` 或 `tasks`）。

#### 3. JSON 資料建模練習 📂
建立一個 `[學習週別]/config.json` 檔案，用 JSON 格式描述你的 Supabase 專案資訊：
- 包含 `project_name`、`region`、`features` (用 Array 列表) 等欄位。
- 注意：確認你的 JSON 格式正確，不要漏掉任何一個雙引號或逗號。

#### 4. Git 提交與資安習慣（重點！核心評分項） 🛡️
這是這週最重要的習慣練習：
- **不要把 API Key 傳上 GitHub：**
  - 建立一個 `.env` 存真正的 Key。
  - 建立一個 `.env.example` 存「空白的欄位」方便同學參考。
  - **把 `.env` 加到根目錄的 `.gitignore`。**
- **Commit Message：**
  - 請練習用 `feat:` 或 `docs:` 開頭來寫你的提交訊息。
  - *範例：* `git commit -m "feat: 完成 [學習週別] Supabase 初始設定與 JSON 練習"`

### 📝 學習日誌檢核表
請將以下內容拷貝並貼在 `[學習週別]/README.md` 檔案中，並自行打勾確認：

```markdown
### [學習週別] 任務完成清單
- [ ] WSL 2 環境運作正常
- [ ] Docker 能成功啟動 `docker-compose.yml` 中的服務
- [ ] Supabase 雲端專案已建立
- [ ] 成功編輯 `config.json` 且格式正確
- [ ] 已設定 `.gitignore` 保護敏感資訊
```

> **💡 悄悄話**
> 如果你在執行 `git push` 的時候看到一堆紅色錯誤，先別緊張！看最後兩行，Git 通常會告訴你該怎麼做。如果真的卡住了，把錯誤碼丟到我們的討論區，我們會一起解決它。
> 
> 「概念（Why）→ 實作（Do）→ 提交（Ship）」，讓我們一起把這週的進度 Ship 掉吧！

- 截止時間：下週上課前 
- 繳交地點：你自己的 GitHub 倉庫 `[學習週別]` 資料夾

---

<a id="git-common-errors"></a>
## 🔧 附錄：Git 常見錯誤與解法

### 1. `ssh: connect to host github.com port 22: Connection timed out`

**可能原因：** 你所在的網路（學校/公司）封鎖了 SSH 22 port。  
**解法：**
1. 改用 HTTPS 網址進行 clone / push。
2. 或讓 SSH 走 443 port，在 `~/.ssh/config` 新增：

```sshconfig
Host github.com
    Hostname ssh.github.com
    Port 443
    User git
```

3. 重新測試連線：

```bash
ssh -T git@github.com
```

### 2. `403 Forbidden` 或 `Permission denied (publickey)`

**可能原因：** GitHub 拒絕存取（身分驗證或授權不足）。  
**解法：**
1. 執行 `ssh -T git@github.com`，確認 SSH 公鑰已正確綁定。
2. 若你使用 HTTPS，請確認 PAT 權杖權限包含 repo 存取。
3. 確認你對該 repository 具備 Write 權限。

### 3. 重複執行 `ssh-keygen`，導致舊金鑰失效

**現象：** 原本可用，重新產生金鑰後突然無法 push。  
**解法：**
1. 重新取得新公鑰：

```bash
cat ~/.ssh/id_ed25519.pub
```

2. 到 GitHub `Settings -> SSH and GPG keys`。
3. 刪除舊金鑰，新增剛複製的新公鑰。
4. 再次測試：

```bash
ssh -T git@github.com
```

### 4. `remote: Support for password authentication was removed`

**原因：** GitHub 已不支援帳號密碼直接推送。  
**解法：**
1. 使用 SSH（推薦）。
2. 若走 HTTPS，改用 PAT（Personal Access Token）。  
   路徑：GitHub `Settings -> Developer settings -> Personal access tokens`。

### 5. `error: failed to push some refs`

**可能原因：** 遠端分支有新提交，本地落後。  
**解法：**

```bash
git pull origin main --rebase
git push origin main
```

### 6. `nothing to commit, working tree clean`

這不是錯誤，代表目前沒有未提交變更。  
若你以為有改檔，先執行 `git status` 與 `git diff` 確認。

---

<a id="windows-admin-rights"></a>
## 🔑 補充說明：Windows 權限與系統管理員

如果在環境安裝與執行過程中，遇到 **Windows 登入的使用者權限-不具系統管理能力**，請參考以下的處理方式與觀念：

### 1. 一般情況：取得 Administrator 權限

如果你的帳號已經是管理員群組，只需要 **提升權限 (Run as Administrator)**。

- **方法 1：右鍵提升**
  在程式 (如 PowerShell, Windows Terminal, CMD) 上**右鍵**，選「**以系統管理員身分執行**」。
- **方法 2：開始功能表**
  搜尋 `powershell`，然後**右鍵** → **以系統管理員身分執行**。

### 2. 檢查自己是不是 Administrator

在 PowerShell 或 CMD 輸入：
```powershell
whoami /groups
```
如果看到 `BUILTIN\Administrators`，代表你是管理員。

### 3. 不建議：啟用 Windows 隱藏的 Administrator 帳號（除非 IT 要求）

這個帳號權限非常高，課程一般情境不需要。  
若你的電腦是學校/公司管理裝置，請優先找 IT 或助教協助，不要自行長期啟用。

### 4. 不建議在課程中使用 SYSTEM 權限

`SYSTEM` 主要給系統維運與除錯用途，不是一般開發流程的一部分。  
對本課程而言，通常只需要「臨時 Administrator + WSL 內單次 sudo」就足夠。

### 5. Windows 權限層級（由低到高）

```text
User
 ↓
Administrator
 ↓
SYSTEM
 ↓
TrustedInstaller
```
*(最高其實是 TrustedInstaller，但通常只有 Windows Update 使用。)*

### 6. Windows + WSL 開發者實務權限組合

如果在做 Docker、WSL、AI agent、Playwright、Supabase 等開發，建議模式是：

`Windows 一般帳號 + 必要時以 Administrator 啟動 PowerShell + WSL 一般使用者（需要時單次 sudo）`

而不是長時間使用 root 或 SYSTEM。
架構建議如下：
```text
Windows User
   └─ Windows PowerShell (Run as Administrator, 僅安裝階段)
        └─ WSL User (日常開發)
             └─ sudo <單次系統命令>
```

---

<a id="wsl-reset-reinstall"></a>
## 🧹 附錄：WSL 完整重置與重新安裝指南

> **💡 什麼時候該重裝 WSL？**
> 如果你的 WSL 環境已經「不可理解」— 例如 Docker daemon 怎麼都啟動不了、套件衝突解不掉、`apt` 壞掉、或開發環境被各種實驗汙染到難以復原 — **重裝是正確的選擇，不是失敗**。
>
> 這在玩 Docker / AI / PostgreSQL / Supabase 等複雜開發環境時非常常見。以下是一個**乾淨、可重現的完整流程**。

---

### 第 1 步：確認目前 WSL 狀態

先在 **PowerShell** 列出所有已安裝的子系統：

```powershell
wsl -l -v
```

你會看到類似：

```
NAME      STATE           VERSION
Ubuntu    Running         2
```

---

### 第 2 步：備份資料（⚠️ 非常重要！）

> **🚨 一旦移除 = 整個 Linux 檔案系統刪光（包括 `/home` 下的所有檔案、資料庫、Docker volume、設定檔）。**

如果你有重要的東西要保留：

```powershell
# 匯出整個 Ubuntu 為備份檔（可能需要幾分鐘）
wsl --export Ubuntu ubuntu-backup.tar
```

> 💡 **備份存放位置**：這個 `.tar` 檔案會儲存在你執行指令時的當前目錄（通常是 `C:\Users\你的名字\`）。
> 你也可以指定完整路徑，例如 `wsl --export Ubuntu D:\Backups\ubuntu-backup.tar`。

---

### 第 3 步：停止 WSL

```powershell
wsl --shutdown
```

---

### 第 4 步：徹底移除 Ubuntu 子系統

```powershell
wsl --unregister Ubuntu
```

這一步會：
- 刪掉整個 Linux 檔案系統（`/home`、`/etc`、所有安裝的套件）
- 清空 Docker 映像檔、容器、volume
- 清空資料庫資料、開發設定
- 回到「完全沒裝」的狀態

---

### 第 5 步：（選做）清理殘留快取

有時候會殘留 cache 或損壞的 layer，建議做：

```powershell
# 確認是否還有殘留的發行版
wsl --list --online

# 刪除 Microsoft Store 的下載快取（選做，有時能修復奇怪 bug）
Remove-Item "$env:LOCALAPPDATA\Packages\Canonical*" -Recurse -Force
```

> 💡 如果你之前有遇到 Docker 網路異常、Mount 失敗、或其他怪異 bug，這步清理特別有幫助。

---

### 第 6 步：重新安裝 Ubuntu

```powershell
# 方法 1（推薦）：安裝預設最新版 Ubuntu
wsl --install -d Ubuntu

# 方法 2：指定特定版本（例如 22.04 LTS）
wsl --install -d Ubuntu-22.04
```

安裝後會自動開啟 Ubuntu 視窗，要求設定：
- **Username**：你的 Linux 使用者名稱
- **Password**：你的 Linux 密碼（輸入時不會顯示字元，這是正常的）

> ⚠️ **請務必記住這組帳號密碼！** 之後 `sudo` 指令會用到。

---

### 第 7 步：基本初始化

進入新的 Ubuntu 後，先更新系統套件：

```bash
sudo apt update && sudo apt upgrade -y
```

---

### 第 8 步：重建開發環境（建議安裝清單）

如果你是本課程的學生（Docker + Supabase + AI + 全端開發），重建時建議依序安裝：

```bash
# 基本開發工具
sudo apt install -y build-essential git curl unzip

# Python
sudo apt install -y python3 python3-pip

# Node.js v20+（使用 nvm 管理版本，比直接 apt install 更彈性）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20
node -v   # 應該顯示 v20.x.x
npm -v    # 應該顯示 10.x.x
```

**Docker**：

> ```
> ❌ 不要在 Ubuntu 裡裝 Docker（sudo apt install docker.io）
> ✅ 一律用 Docker Desktop + WSL Integration
> ```

Docker **不需要在 WSL 內安裝**。請在 Windows 端安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，然後進入 `Settings → Resources → WSL Integration`，勾選你的 Ubuntu 發行版即可。Docker Desktop 會自動把 `docker` 和 `docker compose` 指令注入 WSL。

詳細步驟請參考 [Chapter 5：容器化思維](#chapter-5容器化思維)。

---

### ⚠️ 重建後的常見注意事項

#### 1. Docker 整合方式
- **唯一正確做法**：使用 Docker Desktop + WSL Integration
- **不要在 Ubuntu 裡裝 Docker**（`sudo apt install docker.io` 是錯的）— 會導致沒有 Compose V2、daemon 跑不起來、權限混亂等問題
- 重裝 WSL 後，只需回到 Docker Desktop → Settings → Resources → WSL Integration，重新勾選新的 Ubuntu 即可

#### 2. PostgreSQL / Supabase
重裝後所有資料庫資料會清空，包括：
- Port 映射設定
- Volume 資料
- 使用者權限

> 這其實是好事 — 等於你拿到一個乾淨的環境重新開始，不會被舊的設定汙染。

#### 3. 檔案系統效能（重要！）
你的程式碼**一定要放在 Linux 檔案系統內**：

```
✅ 正確：/home/你的名字/projects/
❌ 錯誤：/mnt/c/Users/你的名字/projects/
```

放在 `/mnt/c/` 下的檔案會因為跨檔案系統存取而**嚴重拖慢**編譯速度、Docker build、`git` 操作等。

---

### 🔥 進階：建立可快速重建的「乾淨基底映像」

如果你之後會常做重裝（或想在不同電腦快速複製環境），可以在設定好基本開發環境後，匯出一份「乾淨基底」：

```powershell
# 設定好基本環境後，匯出為基底映像
wsl --export Ubuntu clean-base.tar
```

之後可以用這個基底**秒級重建**環境：

```powershell
# 匯入為新的發行版（可取不同名字，多套並存）
wsl --import UbuntuDev C:\WSL\UbuntuDev clean-base.tar

# 啟動
wsl -d UbuntuDev
```

> 💡 **這招超實用！** 你可以維護多個用途不同的環境（開發用、實驗用、乾淨測試用），壞了隨時從基底重建。

---

### 📋 最短版速查（給熟手用）

```powershell
wsl --shutdown
wsl --unregister Ubuntu
wsl --install -d Ubuntu
# → 設定帳號密碼 → sudo apt update && sudo apt upgrade -y → 完成
```

---

*本手冊採用 Head First 教學風格設計，強調視覺化學習、動手實作與錯誤友善。*
*版本：1.0 | 最後更新：2026 年 3 月*
