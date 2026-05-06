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
勾選 `repo` 權限，生成後複製（只顯示一次）。

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

> ⚠️ 確認你在 **repo 根目錄**（`data-science-2026/`），不是在子專案目錄裡。
> 如果剛才進去過子目錄，先 `cd ..` 回到根目錄。

```bash
# 確認你在 repo 根目錄
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

課程有新章節、修了 bug 時，做這四步（回到 repo 根目錄執行）：

```bash
# 1. 確認先 commit 好你的工作
git status   # 應該是 clean（nothing to commit）

# 2. 拉取最新的課程內容
git fetch upstream

# 3. 切到 main，把課程更新合併進來
git checkout main
git merge upstream/main
# → 如果你的 main 是乾淨的（沒有你自己的 commit），這一步不會有任何衝突

# 4. 把 main 的更新推到你的 fork
git push origin main

# 5. 切回你的工作分支，把課程更新帶進來
git checkout my-domain
git merge main
# → 如果你沒有動過課程檔案，這一步也不會有衝突
```

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

# 5. 完成 merge commit
git merge --continue
# 或 git commit -m "merge: 跟上課程更新"
```

遇到衝突幾乎都代表「你改了不該改的課程檔案」。
處理完後，把那段修改移到你自己的新檔案裡，下次就不會再衝突。

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
git pull origin my-domain   # 先拉下來合併
git push origin my-domain   # 再推
```
