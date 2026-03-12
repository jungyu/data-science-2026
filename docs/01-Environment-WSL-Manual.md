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
- [第四階段：開發者的標準配備 (Docker)](#第四階段開發者的標準配備-docker)
  - [Chapter 5：容器化思維](#chapter-5容器化思維)
  - [Chapter 6：Docker Compose](#chapter-6docker-compose)
- [第五階段：全端開發實戰 (Supabase & Web)](#第五階段全端開發實戰-supabase--web)
  - [Chapter 7：Supabase CLI 與後端整合](#chapter-7supabase-cli-與後端整合)
  - [Chapter 8：開發者的護身符 (設定檔與資安)](#chapter-8開發者的護身符-設定檔與資安)
- [🧭 最短排錯流程圖](#-最短排錯流程圖)
- [🧠 教學小撇步 (Head First Style Tips)](#-教學小撇步-head-first-style-tips)

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
- 前置條件：已完成 Chapter 0、可在 WSL 中使用 `sudo`

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

#### 🛠️ 任務：啟動 Playwright 自動化爬蟲環境

```bash
# 安裝 Docker（系統套件安裝需要 sudo）
sudo apt update
sudo apt install docker.io -y

# 啟動 Docker 服務（系統服務操作需要 sudo）
sudo service docker start

# 讓一般使用者可直接執行 docker（一次性設定）
sudo usermod -aG docker $USER
# 💡 指令拆解：
# usermod: 修改使用者帳號屬性的指令
# -aG docker: `-a` (append 附加) 和 `-G` (Group 群組)，意思是「附加到 docker 這個群組中」
# $USER: 這是一個系統環境變數，代表「當前登入的使用者名稱」(例如 aaron)
# 整句白話文：「把現在的我，加入到可以管理 docker 的群組裡，讓我之後能操作它。」

# 套用新群組（或重新開啟終端機）
newgrp docker

docker --version
# 執行官方的測試用迷你容器，如果你看到 "Hello from Docker!"
# 就代表 Docker 引擎的心跳正常，安裝大成功！
docker run hello-world

# 啟動自動化測試與爬蟲環境 (Playwright)
# 這裡我們下載並執行微軟官方提供的 Playwright 容器（內建瀏覽器驅動）
# 注意：這個範例是「啟動可進入的開發容器」，不是啟動 Web 服務；8080 映射可先省略
docker run -d --name my-playwright-env mcr.microsoft.com/playwright:v1.40.0-jammy tail -f /dev/null

# 確認容器正在運行
docker ps

# 進入容器內部逛逛 (這就是你未來的 MCP Server / Automation 執行基地)
docker exec -it my-playwright-env /bin/bash
# (逛完後輸入 exit 退出)

# 停止並刪除容器
docker stop my-playwright-env
docker rm my-playwright-env
```

> **🏠 深度探索：Docker 創造的東西到底存在哪？**
>
> 這是最多人問的問題！既然我沒看到檔案夾，那 Docker 把資料藏哪了？
> 1. **容器與映像檔**：它們存放在一個由 Docker 管理的「虛擬硬碟」中。在 Windows WSL 中，這個檔案通常藏在 `%LOCALAPPDATA%/Docker/wsl/data/ext4.vhdx`。這是一個大黑盒子，為了效能，Docker 不建議你直接去翻它。
> 2. **持久化的資料 (Volumes)**：我們在 `docker-compose.yml` 寫的 `volumes`。如果你想要檔案直接「掉」在你的 Windows 資料夾裡方便你讀取，那就要用 **Bind Mount (路徑映射)**，把 Linux 某個路徑與 Windows 目錄連起來。我們在後續專案會用到！

---

#### ⚠️ 防呆區 (Wait, what?)

- **`Cannot connect to the Docker daemon` 或遇到 `System has not been booted with systemd` 錯誤？**  
  如果是前者，通常執行 `sudo service docker start` 就能啟動。  
  *(💡 觀念補充：`systemctl` 是 Ubuntu 現代的背景服務系統 (systemd)，而 WSL 早期沒啟用它。)*  

  **🚀 進階解法：在 WSL (Ubuntu 24.04.4 LTS) 中徹底啟用 systemd**  
  現在的 WSL 已經原生支援 systemd，強烈建議啟用它，這樣才能正常使用 `systemctl`！  
  1. 編輯設定檔：  
     ```bash
     sudo nano /etc/wsl.conf
     ```
  2. 貼上這兩行設定，然後存檔離開 (`Ctrl+O`, `Enter`, `Ctrl+X`)：  
     ```ini
     [boot]
     systemd=true
     ```
  3. 回到 **Windows PowerShell (系統管理員)**，徹底關閉 WSL：  
     ```powershell
     wsl --shutdown
     ```
  4. 重新開啟你的 Ubuntu 終端機，這時 `sudo systemctl start docker` 就能完美運作了！

- **`permission denied while trying to connect to the Docker daemon socket`？**  
  → 代表目前使用者尚未套用 `docker` 群組。  
  → 先執行 `groups` 檢查是否包含 `docker`。若沒有，重新開終端機或執行 `newgrp docker`。
  → 在你確認群組生效前，可以暫時對單一命令加 `sudo`，但不要養成「所有 docker 都加 sudo」的習慣。

- **`port is already allocated`？**  
  → 這通常發生在你真的有映射 port 的情境，換一個 port：`docker run -d -p 8081:8080 --name my-playwright-env mcr.microsoft.com/playwright:v1.40.0-jammy tail -f /dev/null`

#### ✅ 完成判準
- 你可以啟動 Docker 服務並成功執行 `docker run hello-world`。
- 你可以使用 `docker ps`、`docker exec`、`docker stop`、`docker rm` 完成容器生命週期操作。
- 你知道 `permission denied ... docker daemon socket` 通常是群組權限未生效造成。

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

> **💡 為什麼範例用 Postgres 而不是 Supabase？**  
> 這是個好問題！**Supabase 的核心其實就是 PostgreSQL。**  
> 在 Chapter 6 我們先學習如何用 Docker 啟動一個「原味」的資料庫（像是在學開手排車）；到了 Chapter 7，我們會改用 Supabase（像是開自動駕駛的特斯拉），它會幫我們把資料庫、API、權限管理全部打包好。學會本章，你才能理解 Supabase 底部是在運作什麼。

> **💡 為什麼教材會搭配 Nginx？**  
> `postgresql://postgres:postgres@localhost:54322/postgres` 這種是「資料庫連線字串」，給程式或 CLI 用，不是瀏覽器網址。  
> 課程先放一個 Web 入口（Nginx）是為了讓你確認：**Windows 瀏覽器可以透過 `localhost` 連到 WSL 內的容器服務**。  
> 到 Chapter 7 的 Supabase 階段，真正用來檢視 PostgreSQL 的網頁管理介面會是 **Supabase Studio (`http://localhost:54323`)**。

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
# 1. 依照作業規範建立資料夾並進入 (例如 week03)
mkdir week03 && cd week03

# 2. 開啟 Nano 準備撰寫 yaml 設定檔
nano docker-compose.yml
```

**(進入 Nano 編輯畫面後，右鍵貼上以下內容，然後 Ctrl+O -> Enter -> Ctrl+X 存檔離開！)**

```yaml
# 建立 docker-compose.yml
version: '3.8'

services:
  # 資料庫服務 (Supabase 的核心就是它！)
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

> 如果你看到 `docker: 'compose' is not a docker command`，請改用舊版指令：`docker-compose up -d` / `docker-compose down`。

#### ✅ 完成判準
- 你可以從 `docker-compose.yml` 一鍵啟動並關閉多容器環境。
- 你可以用 `docker compose ps` 與 `docker compose logs -f` 檢查服務狀態。
- 你理解 Compose 相對於手動 `docker run` 的優勢。

---

## 第五階段：全端開發實戰 (Supabase & Web)

> **🎯 階段目標：用 CLI 串接真實世界的雲端資料庫。**

---

### Chapter 7：Supabase CLI 與後端整合

#### ⏱️ 章節資訊
- 預估時間：35 分鐘
- 前置條件：Docker daemon 可運作、已建立 Supabase 帳號

#### 🛠️ 任務：安裝 Supabase CLI 並連線雲端

```bash
# 0. 前置檢查：Supabase 本地服務依賴 Docker
docker --version
docker ps >/dev/null

# 方法一：使用 npm 安裝（需要先有 Node.js）
npm install -g supabase

# 方法二：使用官方安裝腳本（不依賴 Node.js，二選一）
curl -fsSL https://supabase.com/install.sh | sh

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
# ├── docker-compose.yml   # 你的 Docker 練習設定檔
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
  → 先確認 Docker 有啟動：`sudo service docker start`，再重跑 `supabase start`。

- **`Project ref not found`？**  
  → 到 Supabase 專案 Dashboard 的 `Settings -> General` 複製正確 `Reference ID`。

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
4. **確認服務有啟動**：`docker ps`、`supabase status`（必要時 `sudo service docker start`）。
5. **確認網路與認證**：`ssh -T git@github.com`、重看 token / key / 權限設定。
6. **最後才做重置動作**：保留錯誤訊息截圖，帶著訊息請助教協助。

快速對照：
- `command not found`：通常是沒安裝或 PATH 問題。
- `Permission denied`：先判斷是否系統層操作，再決定是否加 `sudo`。
- `Connection refused`：服務沒啟動或 port 不對。
- `failed to push some refs`：先 `git pull --rebase` 再 `git push`。

#### 🌐 補充：WSL2 網路連線故障排除（Connection Timeout）

如果你發現 `ping` 正常，但 `curl` 或 `git push` 時常遇到逾時，這類問題在 WSL2 通常由以下三個原因引起，建議依序排除：

**1. Windows 防火牆攔截 (最常見)**
Windows 防火牆有時會將 WSL2 的虛擬網卡視為「公用網路」而阻擋其發出的 TCP 443 (HTTPS) 或 22 (SSH) 請求。

- **測試方法**：暫時關閉 Windows Defender 防火牆，看 `curl` 是否恢復正常。
- **解決方法**：如果關閉後就通了，請在 PowerShell (管理員) 執行以下指令開放權限：
  ```powershell
  New-NetFirewallRule -DisplayName "WSL2 Network Access" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
  ```

**2. MTU (最大傳輸單元) 設定過大**
如果你身處的網路環境（例如某些公司 VPN、校園網或是特定路由器）對封包大小有限制，WSL2 預設的 MTU (1500) 可能過大，導致小封包 (Ping) 能過，但建立連線的大封包 (TCP) 被丟棄。

- **嘗試修改 MTU**（在 WSL 內執行）：
  ```bash
  sudo ip link set dev eth0 mtu 1400
  ```
  修改後再試一次 `curl https://github.com`，如果通了，就是 MTU 的問題。

**3. 代理伺服器 (Proxy) 或網路加速器衝突**
如果你在 Windows 上有開啟任何代理工具（如系統代理、VPN 或遊戲加速器），它們常會攔截 WSL2 的流量卻處理失敗。

- **檢查**：確保 Windows 代理設定中，沒有干擾到 WSL2 的虛擬橋接。

> **💡 建議下一步操作**
> 既然你已經測試過 IP 連線也會超時，我建議你優先嘗試調整 MTU：
> 1. 在 WSL 終端機輸入：`sudo ip link set dev eth0 mtu 1350`
> 2. 立即執行：`curl -I https://www.google.com`
>
> 如果 MTU 調整後依然無效，請確認你的筆電是否有安裝任何第三方防毒軟體或網路過濾軟體（如 Trend Micro, FortiClient 等），這些軟體經常與 WSL2 的虛擬交換器（vSwitch）八字不合。


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
    ├── docker-compose.yml   # 你的 Docker 練習設定檔
    ├── config.json          # 專案配置練習檔
    └── .env.example         # 變數範本（保護秘密的示範）
```

### 🎯 任務詳細說明

#### 1. WSL 與 Docker 環境解鎖 🛠️
在 `[學習週別]/README.md` 中，請用幾句話記錄你的安裝心得：
- 你在安裝 WSL 或 Docker 時有遇到什麼「驚喜（Bug）」嗎？你是如何解決的？
- 請在 `[學習週別]/` 下放一個 `docker-compose.yml`（可以是我們課堂練習的 Nginx 或簡單資料庫版本），確保你能一鍵啟動環境。

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

*本手冊採用 Head First 教學風格設計，強調視覺化學習、動手實作與錯誤友善。*  
*版本：1.0 | 最後更新：2026 年 3 月*
