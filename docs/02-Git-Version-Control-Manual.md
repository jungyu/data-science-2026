# Git 深入淺出手冊 🎯

> **像翻閱相簿一樣管理你的程式碼**
> 每個 commit 都是一張快照，每個分支都是一條時間線

---

## 📚 目錄

- [第一章：Git 是什麼？](#第一章git-是什麼)
- [第二章：日常必備指令](#第二章日常必備指令)
- [第三章：分支的藝術](#第三章分支的藝術)
- [第四章：合併與衝突](#第四章合併與衝突)
- [第五章：時光旅行](#第五章時光旅行)
- [第六章：協作工作流](#第六章協作工作流)
- [第七章：救命錦囊](#第七章救命錦囊)
- [附錄：速查表](#附錄速查表)

---

## 第一章：Git 是什麼？

### 🤔 想像一下

你在寫小說，每寫完一章就**存檔**一次。某天你想回去看第三章的初稿，或者想知道第五章改了什麼——Git 就是這個存檔系統的專業版！

### Git 的三個工作區域

```text
工作目錄 (Working Directory)     你正在編輯的檔案
    ↓ git add
暫存區 (Staging Area)           準備要拍照的檔案
    ↓ git commit
本地倉庫 (Local Repository)     已經拍好的照片
    ↓ git push
遠端倉庫 (Remote Repository)    雲端相簿
```

**記住這個口訣**：
改檔案 → `add` 進暫存區 → `commit` 拍快照 → `push` 上雲端

---

## 第二章：日常必備指令

### 🎬 場景一：開始新專案

```bash
# 方法 1：從零開始
mkdir my-project
cd my-project
git init                    # 初始化 Git 倉庫

# 方法 2：下載現有專案
git clone https://github.com/user/repo.git
cd repo
```

**💡 小技巧**：`git clone` 會自動幫你設定好遠端連線，連 `git init` 都省了！

---

### 🔐 認證機制：SSH vs HTTPS

當你要把程式碼推送到 GitHub 時，Git 需要確認你的身份。

#### 1. HTTPS（預設，需 Token）
網址以 `https://` 開頭。優點是簡單，缺點是每次（或一段時間後）都需要輸入 **Personal Access Token (PAT)**，且 Token 會過期。

#### 2. SSH（專業推薦，免密碼） ⭐
網址以 `git@github.com` 開頭。設定一次金鑰後，就能永久免密碼安全推送。

---

### 🛠️ SSH Key 設定三部曲（以 WSL/Linux 為例）

##### 第一步：產生金鑰 (SSH Key)
在終端機輸入：
```bash
ssh-keygen -t ed25519 -C "您的註冊信箱"
```
> **提示**：看到詢問路徑或密碼，直接連按 3 次 **Enter** 即可（保持預設預設是不設密碼）。

##### 第二步：複製公鑰內容
執行以下指令並複製輸出的長字串：
```bash
cat ~/.ssh/id_ed25519.pub
```

##### 第三步：交給 GitHub
1. 登入 GitHub -> **Settings** -> **SSH and GPG keys**。
2. 點擊 **New SSH key**。
3. 把內容貼進 **Key** 欄位，完成！

##### ✅ 驗證連線
```bash
ssh -T git@github.com
```
看到 `"Hi [您的帳號]! You've successfully authenticated..."` 就成功了！

---


### 📸 場景二：保存你的工作

```bash
# 1. 看看改了什麼
git status                  # 查看狀態（最常用！）
git diff                    # 看詳細改動

# 2. 選擇要保存的檔案
git add index.html          # 加入單一檔案
git add .                   # 加入所有檔案（小心！）
git add *.js                # 加入所有 JS 檔案
git add src/                # 加入整個目錄

# 3. 拍快照（commit）
git commit -m "feat: add login page"

# 4. 上傳到雲端
git push origin main
```

**⚠️ 警告**：`git add .` 會加入所有檔案，包括你可能不想 commit 的！
**解決方案**：使用 `.gitignore` 排除不需要的檔案

### 🔍 場景三：查看歷史

```bash
# 看提交記錄
git log                     # 詳細記錄
git log --oneline          # 一行一筆，清爽！
git log --graph --oneline  # 圖形化顯示分支

# 看特定檔案的歷史
git log -- index.html

# 看誰改了這一行？
git blame index.html
```

**🎯 實用範例**：

```bash
# 找出最近 5 筆 commit
git log -5 --oneline

# 找出特定作者的 commit
git log --author="Aaron"

# 找出包含特定關鍵字的 commit
git log --grep="fix bug"
```

### 🔄 場景四：同步最新內容

```bash
# 下載最新內容但不合併
git fetch origin

# 下載並自動合併
git pull origin main

# 建議寫法（避免衝突）
git fetch origin
git merge origin/main
```

**💡 fetch vs pull 的差異**：

- `fetch`：下載最新內容到本地，但不影響你的工作目錄（安全）
- `pull`：下載並立即合併（快速但可能產生衝突）

---

## 第三章：分支的藝術

### 🌳 分支是什麼？

想像你在寫小說：

- **main 分支**：正式出版的版本
- **feature 分支**：實驗性的新章節
- **hotfix 分支**：緊急修正錯字

每個分支都是**獨立的時間線**，你可以在分支上自由實驗，不會影響主線！

### 基本分支操作

```bash
# 查看所有分支
git branch                  # 本地分支
git branch -a              # 包含遠端分支
git branch -r              # 只看遠端分支

# 創建新分支
git branch feature/login   # 創建但不切換
git checkout -b feature/login  # 創建並切換（常用！）
git switch -c feature/login    # 新語法，更直觀

# 切換分支
git checkout main          # 舊語法
git switch main           # 新語法（推薦）

# 刪除分支
git branch -d feature/login    # 安全刪除（已合併）
git branch -D feature/login    # 強制刪除（小心！）

# 刪除遠端分支
git push origin --delete feature/login
```

### 🎨 分支命名策略

```text
功能開發：  feature/user-authentication
            feature/shopping-cart

錯誤修復：  fix/login-button-crash
            fix/memory-leak

緊急修復：  hotfix/security-patch
            hotfix/production-bug

實驗性：    experiment/new-ui
            experiment/performance-test
```

**命名原則**：類型/簡短描述（使用小寫和連字號）

### 📐 常見分支策略

#### 策略 1：GitHub Flow（簡單專案）

```text
main ────────────────────────────
      \           /       \
       feature-1 /         feature-2
```

**規則**：

1. `main` 永遠是可部署的
2. 新功能從 `main` 開分支
3. 完成後發 Pull Request
4. 審查通過後合併回 `main`

#### 策略 2：Git Flow（大型專案）

```text
main ────────────v1.0─────v1.1───
      \           ↑
develop ─────────┼────────────────
         \      /  \
          feature  hotfix
```

**規則**：

- `main`：正式發布版本
- `develop`：開發主線
- `feature/*`：功能分支
- `release/*`：發布準備
- `hotfix/*`：緊急修復

#### 策略 3：實用混合策略（推薦）

```bash
# 長期分支
main              # 生產環境
develop           # 開發環境

# 短期分支
feature/*         # 功能開發（從 develop 分出）
fix/*            # 錯誤修復
hotfix/*         # 緊急修復（從 main 分出）
```

---

## 第四章：合併與衝突

### 🤝 場景一：順利合併

```bash
# 1. 切換到目標分支
git switch main

# 2. 合併功能分支
git merge feature/login

# 3. 推送到遠端
git push origin main
```

**結果**：所有改動自動合併，沒有衝突 ✨

### 💥 場景二：遇到衝突了

```bash
$ git merge feature/login
Auto-merging index.html
CONFLICT (content): Merge conflict in index.html
Automatic merge failed; fix conflicts and then commit the result.
```

**不要慌！** 這只是 Git 在說：「同一個地方有兩種改法，你決定要哪一個。」

### 🔧 解決衝突的步驟

#### 步驟 1：找出衝突檔案

```bash
git status
# Unmerged paths:
#   both modified:   index.html
```

#### 步驟 2：打開檔案，看到這樣的標記

```html
<<<<<<< HEAD
<h1>歡迎來到我的網站</h1>
=======
<h1>Welcome to My Site</h1>
>>>>>>> feature/login
```

**解讀**：

- `<<<<<<< HEAD`：目前分支的內容
- `=======`：分隔線
- `>>>>>>> feature/login`：要合併進來的內容

#### 步驟 3：決定要保留什麼

**選項 A**：保留目前分支

```html
<h1>歡迎來到我的網站</h1>
```

**選項 B**：保留新分支

```html
<h1>Welcome to My Site</h1>
```

**選項 C**：兩者都要

```html
<h1>歡迎來到我的網站 | Welcome to My Site</h1>
```

**選項 D**：全部改寫

```html
<h1 data-i18n="welcome">歡迎來到我的網站</h1>
```

#### 步驟 4：移除衝突標記

```html
<!-- 移除這些標記 -->
<<<<<<< HEAD
=======
>>>>>>> feature/login

<!-- 只保留你要的內容 -->
<h1>歡迎來到我的網站 | Welcome to My Site</h1>
```

#### 步驟 5：完成合併

```bash
# 1. 加入解決後的檔案
git add index.html

# 2. 完成合併 commit
git commit -m "Merge feature/login: resolve conflicts in index.html"

# 3. 推送
git push origin main
```

### 🎯 避免衝突的技巧

**技巧 1：經常同步**

```bash
# 開始工作前
git pull origin main

# 工作中每隔幾小時
git fetch origin
git merge origin/main
```

**技巧 2：小步提交**

```bash
# ❌ 不好：改了 10 個檔案才 commit
git add .
git commit -m "various changes"

# ✅ 好：改一個功能就 commit
git add login.js
git commit -m "feat: add login validation"
git add styles.css
git commit -m "style: update login button"
```

**技巧 3：清楚的分工**

- 團隊成員各自負責不同的檔案
- 如果必須改同一個檔案，先溝通好負責的區域

### 🛠️ 進階合併技巧

#### 使用 rebase 保持歷史乾淨

```bash
# 一般合併（會產生合併 commit）
git merge feature/login

# Rebase（歷史會是一直線）
git rebase main

# ⚠️ 注意：只在自己的分支上用 rebase！
```

**merge vs rebase 比較**：

```
# merge 結果（有分叉）
main ────A────C────E──
          \        /
feature    B────D/

# rebase 結果（一直線）
main ────A────C────E────B'────D'
```

**原則**：公開分支用 merge，私人分支用 rebase

---

## 第五章：時光旅行

### ⏪ 場景一：我想看之前的版本

```bash
# 看某個 commit 的內容
git show abc123

# 切換到某個 commit（唯讀）
git checkout abc123

# 回到現在
git switch main
```

### 🔙 場景二：我想回到過去

#### 情況 A：還沒 push，只在本地

```bash
# 取消最後一次 commit（保留改動）
git reset --soft HEAD~1

# 取消最後一次 commit（丟棄改動）⚠️
git reset --hard HEAD~1

# 取消最近 3 次 commit
git reset --hard HEAD~3
```

**⚠️ 警告**：`--hard` 會永久刪除改動！

#### 情況 B：已經 push 到遠端

```bash
# ❌ 不要用 reset！會破壞別人的 git 歷史

# ✅ 使用 revert（創建一個新的反向 commit）
git revert abc123
git push origin main
```

**為什麼？** revert 不會改寫歷史，對團隊協作更安全！

### 📝 場景三：修改 commit 訊息

```bash
# 修改最後一次 commit 的訊息
git commit --amend -m "fix: correct typo in login page"

# 如果已經 push 了
git push --force origin main  # ⚠️ 小心使用！
```

### 💎 場景四：把多個 commit 壓縮成一個

```bash
# 互動式 rebase
git rebase -i HEAD~3

# 在編輯器中會看到：
# pick abc123 feat: add feature 1
# pick def456 feat: add feature 2
# pick ghi789 feat: add feature 3

# 改成：
# pick abc123 feat: add feature 1
# squash def456 feat: add feature 2
# squash ghi789 feat: add feature 3

# 儲存後，3 個 commit 變成 1 個！
```

### 🚨 救命用法

#### 救命 1：我不小心刪除了檔案

```bash
# 恢復單一檔案
git checkout HEAD -- index.html

# 恢復整個目錄
git checkout HEAD -- src/

# 恢復所有檔案
git checkout HEAD -- .
```

#### 救命 2：我不小心改壞了，想全部重來

```bash
# 放棄所有未 commit 的改動 ⚠️
git reset --hard HEAD

# 放棄所有改動，包括暫存區 ⚠️
git reset --hard
git clean -fd
```

#### 救命 3：找回被刪除的 commit

```bash
# 查看所有操作記錄
git reflog

# 輸出類似：
# abc123 HEAD@{0}: reset: moving to HEAD~1
# def456 HEAD@{1}: commit: feat: add login  ← 想找回這個！

# 恢復到該 commit
git reset --hard def456
```

---

## 第六章：協作工作流

### 👥 Pull Request (PR) 工作流

#### 步驟 1：創建功能分支

```bash
git switch -c feature/user-profile
# 進行開發...
git add .
git commit -m "feat: add user profile page"
git push origin feature/user-profile
```

#### 步驟 2：在 GitHub 上創建 PR

1. 去 GitHub 網站
2. 點擊 "Compare & pull request"
3. 填寫 PR 描述（說明改了什麼、為什麼）
4. 指定審查者

#### 步驟 3：審查與修改

```bash
# 如果審查者要求修改
git add .
git commit -m "fix: address review comments"
git push origin feature/user-profile

# PR 會自動更新！
```

#### 步驟 4：合併 PR

```bash
# 在 GitHub 上點擊 "Merge pull request"

# 然後在本地：
git switch main
git pull origin main
git branch -d feature/user-profile
```

### 🔄 同步 Fork 的專案

```bash
# 1. 添加上游倉庫
git remote add upstream https://github.com/original/repo.git

# 2. 獲取上游更新
git fetch upstream

# 3. 合併到你的 main
git switch main
git merge upstream/main

# 4. 推送到你的 fork
git push origin main
```

### 👀 審查他人的 PR

```bash
# 1. 下載 PR 分支
git fetch origin pull/123/head:pr-123
git switch pr-123

# 2. 測試功能

# 3. 留下評論（在 GitHub 上）

# 4. 切回自己的分支
git switch main
```

---

## 第七章：救命錦囊

### 🆘 常見問題與解決方案

#### 問題 1：我在錯誤的分支上 commit 了

```bash
# 假設你在 main，但應該在 feature
# 1. 記下 commit 的 hash
git log --oneline -1  # abc123

# 2. 切換到正確的分支
git switch feature

# 3. 把 commit 移過來
git cherry-pick abc123

# 4. 回到 main，移除那個 commit
git switch main
git reset --hard HEAD~1
```

#### 問題 2：我想暫時保存改動，切換到其他分支

```bash
# 1. 保存當前改動
git stash save "working on login feature"

# 2. 切換分支處理其他事情
git switch hotfix/urgent-bug
# ... 修復 bug ...

# 3. 回來繼續原本的工作
git switch feature/login
git stash pop

# 查看所有 stash
git stash list

# 套用特定的 stash
git stash apply stash@{1}
```

#### 問題 3：我想只合併某個 commit

```bash
# 從其他分支挑選特定 commit
git cherry-pick abc123

# 挑選多個 commit
git cherry-pick abc123 def456 ghi789
```

#### 問題 4：我的 git 歷史太亂了

```bash
# 互動式 rebase 整理歷史
git rebase -i HEAD~5

# 可以做的事：
# pick   - 保留這個 commit
# reword - 修改 commit 訊息
# edit   - 修改 commit 內容
# squash - 合併到前一個 commit
# drop   - 刪除這個 commit
```

#### 問題 5：如何找出是哪個 commit 引入了 bug？

```bash
# 使用 git bisect 二分搜尋
git bisect start
git bisect bad                 # 目前版本有 bug
git bisect good v1.0          # 這個版本是好的

# Git 會自動切換到中間的 commit
# 測試後標記：
git bisect good   # 這個版本沒問題
# 或
git bisect bad    # 這個版本有問題

# 重複直到找出問題的 commit
git bisect reset  # 完成後回到原本的分支
```

### 🔐 安全操作原則

**黃金法則**：

1. **推送前先拉取**：`git pull` 再 `git push`
2. **本地先測試**：確認能運行才 push
3. **小步前進**：頻繁 commit，容易回退
4. **保護主分支**：在分支上開發，PR 合併
5. **不改寫公開歷史**：避免 `--force` push

**⚠️ 危險操作清單**：

```bash
# 這些操作要特別小心！
git reset --hard      # 會丟失未 commit 的改動
git clean -fd         # 會刪除未追蹤的檔案
git push --force      # 會覆蓋遠端歷史
git rebase           # 在公開分支上用會出問題
```

---

## 附錄：速查表

### 📋 常用指令速查

#### 設定與初始化

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git init
git clone <url>
```

#### 基本操作

```bash
git status              # 查看狀態 ⭐ 最常用
git add <file>         # 加入暫存區
git add .              # 加入所有改動
git commit -m "msg"    # 提交
git push origin <branch>  # 推送
git pull origin <branch>  # 拉取並合併
```

#### 分支操作

```bash
git branch                    # 查看分支
git branch <name>            # 創建分支
git switch <name>            # 切換分支（新）
git checkout <name>          # 切換分支（舊）
git switch -c <name>         # 創建並切換
git branch -d <name>         # 刪除分支
git merge <branch>           # 合併分支
```

#### 查看歷史

```bash
git log                     # 詳細記錄
git log --oneline          # 簡潔記錄 ⭐
git log --graph            # 圖形化
git diff                   # 查看改動
git show <commit>          # 查看特定 commit
```

#### 撤銷操作

```bash
git reset --soft HEAD~1    # 撤銷 commit，保留改動
git reset --hard HEAD~1    # 撤銷 commit，丟棄改動 ⚠️
git revert <commit>        # 創建反向 commit
git checkout -- <file>     # 放棄檔案改動
git stash                  # 暫存改動
git stash pop              # 恢復暫存
```

### 🎯 Commit 訊息規範

```
<type>: <subject>

<body>

<footer>
```

**Type 類型**：

- `feat`: 新功能
- `fix`: 修復 bug
- `docs`: 文檔變更
- `style`: 格式調整（不影響程式碼）
- `refactor`: 重構（不是新功能也不是修 bug）
- `test`: 測試相關
- `chore`: 建置工具或輔助工具變更

**範例**：

```
feat: add user authentication

- Implement login form
- Add JWT token validation
- Create session management

Closes #123
```

### 🔗 .gitignore 常用規則

```gitignore
# 依賴套件
node_modules/
vendor/

# 建置輸出
dist/
build/
*.min.js

# 環境設定
.env
.env.local
*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系統檔案
.DS_Store
Thumbs.db

# 日誌
*.log
logs/

# 暫存檔
*.tmp
*.temp
```

### 🚀 效率提升別名（Aliases）

```bash
# 設定常用別名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.sw switch
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.last 'log -1 HEAD'
git config --global alias.unstage 'reset HEAD --'
git config --global alias.visual 'log --graph --oneline --all'

# 使用範例
git st              # = git status
git co main        # = git checkout main
git visual         # = git log --graph --oneline --all
```

### 📊 分支策略決策樹

```
你的專案有多少人？
├─ 1-2 人：GitHub Flow
│         (main + feature branches)
│
├─ 3-10 人：簡化 Git Flow
│          (main + develop + feature branches)
│
└─ 10+ 人：完整 Git Flow
           (main + develop + feature + release + hotfix)

需要多個環境？
├─ 是：每個環境一個長期分支
│     (main=production, staging, develop)
│
└─ 否：只用 main + feature branches
```

### 🎓 學習資源

**官方文件**：

- [Git 官方文檔](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)

**互動教學**：

- [Learn Git Branching](https://learngitbranching.js.org/) - 視覺化互動教學
- [Oh My Git!](https://ohmygit.org/) - Git 遊戲

**進階閱讀**：

- Pro Git（免費電子書）
- Git from the Bottom Up

---

## 💡 最後的建議

### 給新手的話

1. **不要怕犯錯**：Git 幾乎所有操作都可以復原
2. **多用 `git status`**：隨時知道自己在哪裡
3. **小步前進**：頻繁 commit，描述清楚
4. **看不懂就問**：團隊協作，溝通最重要

### 給進階使用者的話

1. **保持歷史乾淨**：使用 rebase、squash 整理 commits
2. **善用工具**：GUI 工具（GitKraken、SourceTree）輔助複雜操作
3. **自動化**：設定 hooks、CI/CD 提升效率
4. **分享知識**：幫助新手，也能加深自己的理解

### 記住這個心法

```
Git 不是魔法，是工具
理解原理，善用指令
遇到問題，冷靜分析
團隊協作，溝通為先
```

---

**🎉 恭喜你看完這本手冊！**

現在你已經掌握了 Git 的核心概念和常用操作。記住：

> **最好的學習方式就是實際操作！**

建議你：

1. 創建一個練習專案
2. 試著用不同的分支策略
3. 故意製造衝突並解決它
4. 在團隊中實踐這些流程

**Git 熟練度 = 操作次數 × 理解深度**

祝你在版本控制的世界中游刃有餘！🚀

---

*最後更新：2026-03-03*
*如有問題或建議，歡迎提交 Issue 或 PR*
