# Fork 子專案 + 跟上上游更新

> 適用：`data-science-2026` monorepo 裡的任意子專案
> （`project-linebot-rag-skills`、`project-playwright` 等）

---

## 先看懂全局

在開始任何指令之前，先理解你要建立什麼樣的結構：

```
upstream（課程原始 repo）
     │
     │ git fetch + git merge（你主動拉，不會自動更新）
     ▼
  main 分支（你的 fork，保持乾淨，只跟課程同步）
     │
     │ git merge main（把課程更新帶進你的工作）
     ▼
my-domain 分支（你真正工作的地方，放你的客製化）
  - skills/your_domain.py   ← 你的技能定義
  - tests/cases/golden.yaml ← 你的測試案例
  - WEEK*.md                ← 你的學習週記
  - docs/RAG/your_kb/       ← 你的知識庫
```

**核心規則只有一條**：

```
課程原有的檔案（docs/Lesson_*、app/graph/ 等）→ 不要動
你的客製化內容                                 → 新增自己的檔案
```

只要你只新增檔案、不改課程檔案，同步上游時永遠不會有衝突。

---

## 前置條件

在開始之前，確認你的電腦有以下工具：

```bash
# 確認 git 已安裝（版本 2.25 以上）
git --version
```

如果出現 `command not found`：
- **macOS**：`brew install git`（需先裝 [Homebrew](https://brew.sh)）或安裝 [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/)
- **Windows**：從 [git-scm.com](https://git-scm.com/download/win) 下載安裝包
- **Linux（Ubuntu/Debian）**：`sudo apt install git`

```bash
# 確認 uv 已安裝（用來管理 Python 環境）
uv --version
```

如果 `uv` 尚未安裝：

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows（PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> ⚠️ **安裝 `uv` 後，需要重新啟動終端機**（關掉再開），`uv` 指令才會生效。
> 或者執行 `source ~/.bashrc`（bash）/ `source ~/.zshrc`（zsh）讓設定立即生效。

你還需要一個 **GitHub 帳號**，並設定好驗證方式（見下方 Step 2 說明）。

---

## Step 1：在 GitHub 上 Fork

1. 打開 [https://github.com/jungyu/data-science-2026](https://github.com/jungyu/data-science-2026)
2. 點右上角的 **Fork** 按鈕（在 Star 旁邊）
3. 選擇你自己的帳號，按 **Create fork**
4. Fork 完成後，你的 fork URL 會是：

```
https://github.com/你的帳號/data-science-2026
```

> 你只需要 fork 一次。monorepo 裡的所有子專案都在同一個 fork 裡。

---

## Step 2：Clone 你的 fork + 設定驗證

### 選擇驗證方式（二選一）

**方案 A：SSH（推薦，不用每次輸入密碼）**

如果你還沒設定 SSH key，照 [GitHub 官方文件](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) 設定一次。
設定好之後，用 SSH 格式 clone：

```bash
git clone git@github.com:你的帳號/data-science-2026.git
cd data-science-2026
```

**方案 B：HTTPS + Personal Access Token（PAT）**

⚠️ GitHub 已於 2021 年移除密碼驗證——輸入 GitHub 密碼會直接失敗。
你需要用 **Personal Access Token（PAT）** 代替密碼。

取得 PAT：GitHub → 右上角頭像 → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token。
勾選 `repo` 權限，Expiration 建議選 **90 days**（夠用一學期）。生成後複製（只顯示一次）。

```bash
git clone https://github.com/你的帳號/data-science-2026.git
# Username: 輸入你的 GitHub 帳號
# Password: 貼上你的 PAT（不是 GitHub 密碼）

cd data-science-2026
```

---

### 加入 upstream remote

```bash
# 加入課程原始 repo 為 upstream
git remote add upstream https://github.com/jungyu/data-science-2026.git

# 確認兩個 remote 都在
git remote -v
# origin    https://github.com/你的帳號/data-science-2026.git  (fetch)
# origin    https://github.com/你的帳號/data-science-2026.git  (push)
# upstream  https://github.com/jungyu/data-science-2026.git    (fetch)
# upstream  https://github.com/jungyu/data-science-2026.git    (push)
```

---

## Step 3：開你的工作分支

```bash
# 確認你在 repo 根目錄（Step 2 結束時應已在這裡）
pwd
# 應該顯示：.../data-science-2026

# 從 main 開一條工作分支（名字可以改成你的領域）
git checkout -b my-domain
# 例如：git checkout -b medical-domain
#       git checkout -b legal-domain

# 確認現在在哪個分支
git branch
# * my-domain
#   main
```

---

## Step 4：進入子專案，設定環境

```bash
# 進入你要做的子專案
cd project-linebot-rag-skills

# 複製環境設定範本
cp .env.example .env

# 用你的編輯器打開 .env，填入你的 API keys
# 至少要填：OPENAI_API_KEY、SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY

# 安裝 Python 環境和依賴
uv sync
```

---

## Step 5：新增你自己的檔案

你的客製化內容放在以下位置（這些路徑都在 `project-linebot-rag-skills/` 裡）：

```
project-linebot-rag-skills/
├── skills/
│   └── your_domain.py        ← 你的技能定義
├── tests/cases/
│   └── golden.yaml           ← 你的測試案例（覆蓋預設的）
├── docs/RAG/
│   └── your_domain/          ← 你的知識庫文件
│       └── *.md
├── WEEK1.md                  ← 你的第一週學習記錄
└── .env                      ← 你的 API keys（不要 commit）
```

新增完檔案後，commit 你的工作：

```bash
# 回到 repo 根目錄
cd ..

# 確認你在正確的分支
git branch   # 應該是 * my-domain

# 確認哪些是新增的檔案
git status

# 只 add 你自己的檔案（不要 git add . 以免誤加課程檔案的修改）
git add project-linebot-rag-skills/skills/your_domain.py
git add project-linebot-rag-skills/WEEK1.md

# Commit
git commit -m "feat: 加入醫療領域 skill 初稿"

# 推到你的 fork
git push origin my-domain
```

> ⚠️ **每次切換分支前，先 commit 或 stash 你的修改**。
> 若有未 commit 的修改就切分支，git 可能報錯或把修改帶到另一條分支。
>
> ```bash
> # 不想 commit 的話，先暫存
> git stash
> # 切換完分支後，把暫存取回
> git stash pop
> ```

---

## Step 6：跟上課程更新

課程有新章節、修了 bug 時，依序執行以下步驟（在 repo 根目錄）：

```bash
# 1. 確認先 commit 好你的工作
git status   # 應該顯示 nothing to commit

# 2. 拉取最新的課程內容
git fetch upstream

# 3. 切到 main，把課程更新合併進來
git checkout main
git merge upstream/main --no-edit
# → 如果你的 main 是乾淨的（沒有你自己的 commit），這一步不會有任何衝突

# 4. 把 main 的更新推到你的 fork
git push origin main

# 5. 切回你的工作分支，把課程更新帶進來
git checkout my-domain
git merge main --no-edit
# → 如果你沒有動過課程檔案，這一步也不會有衝突
```

> 💡 **`--no-edit` 的作用**：git merge 預設會開啟文字編輯器（通常是 vim）讓你填寫 commit 訊息。
> `--no-edit` 直接使用預設訊息跳過這個步驟。對新手來說幾乎永遠都不需要手動改 merge commit 訊息。
>
> 如果不小心進了 vim，輸入 `:q!` 按 Enter 可以強制離開（不存檔）。

**推薦用 `merge` 而不是 `rebase`**：merge 保留完整歷史、出錯容易復原，
對 git 還不熟的學生更安全。熟悉 rebase 之後再考慮切換。

---

## Step 7：如果真的有衝突怎麼辦

衝突訊息長這樣：

```bash
git merge main
# Auto-merging app/graph/nodes.py
# CONFLICT (content): Merge conflict in app/graph/nodes.py
# Automatic merge failed; fix conflicts and then commit the result.
```

**完整處理流程**：

```bash
# 1. 看哪些檔案衝突了
git status
# both modified: app/graph/nodes.py

# 2. 打開衝突檔案，找到這樣的標記並手動選擇
# <<<<<<< HEAD（my-domain 的版本）
# your_code_here
# =======
# upstream_code_here
# >>>>>>> main（課程的版本）

# 3. 用指令選擇哪一版（不用手動改檔案）
git checkout --theirs app/graph/nodes.py   # 用課程版本（推薦，因為你不應該改課程檔案）
git checkout --ours   app/graph/nodes.py   # 用你的版本

# 4. 標記衝突已解決
git add app/graph/nodes.py

# 5. 完成 merge commit（--no-edit 跳過 vim，使用預設訊息）
git merge --continue --no-edit
# 或 git commit --no-edit
```

遇到衝突幾乎都代表「你改了不該改的課程檔案」。
處理完後，把那段修改移到你自己的新檔案裡，下次就不會再衝突。

---

## 局部比對與選擇性引入

有時你只想知道「上游的某支程式改了什麼」，或者只想把某一個修復帶進來，
不想整個 merge。以下從「搞清楚哪裡有變化」到「選擇引入哪些」逐步說明。

---

### 第一步：搞清楚哪裡有變化

```bash
# 先確保拿到最新的上游資訊
git fetch upstream
```

**看哪些 commit 觸碰了你在意的子專案**

```bash
git log upstream/main --oneline -- project-linebot-rag-skills/
# 輸出範例：
# a1b2c3d fix(graph): 修正 reflect 節點的 retry 計數問題
# 9f8e7d6 feat(eval): 新增 forbidden_phrase_rate metric
```

**比對整個子專案的程式碼差異（你的分支 vs 上游）**

```bash
git diff my-domain upstream/main -- project-linebot-rag-skills/app/
# 太多了看不完？只看有哪些檔案改了：
git diff my-domain upstream/main --name-only -- project-linebot-rag-skills/app/
```

**聚焦到單一檔案**

```bash
git diff my-domain upstream/main -- project-linebot-rag-skills/app/graph/nodes.py
# + 號開頭 = 上游新增的行
# - 號開頭 = 上游刪除的行（你目前還有這些行）
```

---

### 第二步：選擇引入方式

根據情況選一種：

---

#### 方法 A：引入特定檔案的完整上游版本

適合：上游修了你從未動過的檔案（例如 bug fix 在你未碰的 `app/eval/metrics.py`）

```bash
# 用上游版本直接覆蓋該檔案
git checkout upstream/main -- project-linebot-rag-skills/app/eval/metrics.py

# 確認改了什麼
git diff HEAD project-linebot-rag-skills/app/eval/metrics.py

# 沒問題就 commit
git add project-linebot-rag-skills/app/eval/metrics.py
git commit -m "chore: 引入上游 metrics.py 最新版（修正 forbidden_phrase_rate 計算）"
```

> ⚠️ 這會用上游版本**完整覆蓋**你的版本。如果你也改過這個檔案，改動會被清除。
> 使用前先用 `git diff` 確認你沒有要保留的修改。

---

#### 方法 B：Cherry-pick 特定 commit

適合：某個 commit 只改了一個清楚的功能點，你想完整帶進來

```bash
# 找到那個 commit 的 hash
git log upstream/main --oneline -- project-linebot-rag-skills/app/graph/nodes.py
# a1b2c3d fix(graph): 修正 reflect 節點的 retry 計數問題

# 把那個 commit 套用到你的分支
git cherry-pick a1b2c3d

# 如果有衝突，照 Step 7 的方式處理，完成後：
git cherry-pick --continue --no-edit
```

> ⚠️ Cherry-pick 會套用整個 commit 觸碰的所有檔案（不只是單一子專案）。
> 套用前先確認：`git show a1b2c3d --name-only` 看那個 commit 改了哪些檔案。

---

#### 方法 C：看著 diff，手動融合（最精準）

適合：上游和你都改了同一支程式，想把上游的某幾行改動加進你的版本，而不是覆蓋

```bash
# 在終端並排看 diff
git diff my-domain upstream/main -- project-linebot-rag-skills/app/graph/nodes.py

# 或者把 diff 存成檔案慢慢看
git diff my-domain upstream/main -- project-linebot-rag-skills/app/graph/nodes.py > /tmp/nodes_diff.txt
```

看著 diff，在你的編輯器裡手動把需要的改動加進去。
改完後正常 `git add` + `git commit`。

---

### 三種方法的選擇指引

```
上游改的檔案，你從未動過？
  └─ 方法 A（整個檔案換掉，最快）

一個完整的 bug fix commit，想原封不動帶進來？
  └─ 方法 B（cherry-pick，保留 commit 歷史）

上游和你都改了同一個地方，需要融合？
  └─ 方法 C（手動融合，最安全）
```

---

## 日常工作節奏

```bash
# ── 每天開始工作 ──────────────────────────────────────────
git checkout my-domain

# 如果你在多台電腦工作，先拉最新的自己的 commit
git pull origin my-domain

# 開始寫你的 skill、KB、測試……
# 告一段落時 commit
git add <你新增的檔案>
git commit -m "feat: 完成 golden cases 的 FAQ 類型"
git push origin my-domain

# ── 每週同步課程（或課程有更新時）────────────────────────
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
git checkout my-domain
git merge main

# ── 完成里程碑 ────────────────────────────────────────────
# 確認你的 eval 跑通
cd project-linebot-rag-skills
uv run pytest tests/ -q
cd ..

# Push 到你的 fork
git push origin my-domain
```

---

## 只想使用單一子專案：Sparse Checkout（進階選項）

如果你只需要 `project-linebot-rag-skills`，不想佔用其他子專案的硬碟空間：

```bash
# Clone 但不下載任何檔案
git clone --no-checkout https://github.com/你的帳號/data-science-2026.git
cd data-science-2026

# 啟用 sparse checkout
git sparse-checkout init --cone

# 只 checkout 你要的目錄
git sparse-checkout set project-linebot-rag-skills docs

# 完成 checkout
git checkout main
```

之後所有 `git fetch` / `git merge` 都只影響你 checkout 的目錄。

若之後想加入另一個子專案：

```bash
git sparse-checkout add project-playwright
```

---

## 常見問題

**Q：上游改了 `pyproject.toml`，我需要做什麼？**

```bash
git merge main         # pyproject.toml 自動更新
cd project-linebot-rag-skills
uv sync                # 安裝新依賴
```

如果你也有改 `pyproject.toml`（例如加了自己的套件），合併時照 Step 7 處理衝突，
手動把兩邊的依賴都保留。

**Q：我想把我的客製化分享給同學**

把你的 `my-domain` 分支推到你的 fork，把你的 fork URL 分享給同學即可：

```bash
git push origin my-domain
# 同學 clone 你的 fork，然後 git checkout my-domain
```

**Q：課程做了很大的重構，我怎麼知道影響範圍？**

```bash
git fetch upstream
git log upstream/main --oneline -15   # 看最近的 commit 說明
git diff main upstream/main -- project-linebot-rag-skills/   # 只看你在意的子專案
```

確認影響範圍後，再決定要不要 merge。

**Q：我 `git merge main` 之後想反悔**

```bash
git merge --abort       # merge 進行中，直接放棄
# 或者 merge 已完成但想撤銷：
git reset --hard HEAD~1
```

**Q：`git push origin my-domain` 出現「rejected」**

代表遠端有你本地沒有的 commit（通常是你在另一台電腦 push 過）：

```bash
git pull origin my-domain --no-edit   # 先拉下來合併（--no-edit 跳過 vim）
git push origin my-domain             # 再推
```
