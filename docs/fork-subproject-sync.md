# Fork 子專案 + 跟上上游更新

> 適用：`data-science-2026` monorepo 裡的任意子專案
> （`project-linebot-rag-skills`、`project-playwright` 等）

---

## 核心思維：哪些檔案是「你的」，哪些是「課程的」

這個 repo 是一個 **monorepo**——多個子專案放在同一個 git repository 裡。
你 fork 之後面對的問題是：

```
你的客製化內容（你想保留）
       ↕ 可能衝突
課程的更新（你想跟上）
```

**解法的關鍵不是 git 指令，而是「不動課程檔案」**：

```
課程基礎設施（不要改）          你的客製化（放心改）
─────────────────────           ──────────────────────
docs/Lesson_*/ch*.md            skills/your_domain.py
app/graph/nodes.py              tests/cases/golden.yaml
app/channels/base.py            docs/RAG/your_kb/
scripts/eval.py                 WEEK1.md … WEEK7.md
pyproject.toml                  .env（不 commit）
```

只要你只改「你的客製化」那一欄，跟上游同步時永遠不會有衝突。

---

## Step 1：Fork 整個 repo

在 GitHub 上點 **Fork** → 選你的帳號。

```
https://github.com/jungyu/data-science-2026
→ Fork →
https://github.com/你的帳號/data-science-2026
```

> 你只需要 fork 一次。所有子專案都在同一個 fork 裡。

---

## Step 2：Clone 你的 fork，加入 upstream

```bash
# Clone 你的 fork（用你的帳號）
git clone https://github.com/你的帳號/data-science-2026.git
cd data-science-2026

# 加入 upstream（原始課程 repo）
git remote add upstream https://github.com/jungyu/data-science-2026.git

# 確認兩個 remote 都在
git remote -v
# origin    https://github.com/你的帳號/data-science-2026.git  (fetch/push)
# upstream  https://github.com/jungyu/data-science-2026.git    (fetch/push)
```

---

## Step 3：只專注你要做的子專案

你不需要動其他子專案的檔案。
進入你要做的子專案目錄，依照它的 README 設定環境：

```bash
cd project-linebot-rag-skills
cp .env.example .env
# 填入你的 API keys
uv sync
```

---

## Step 4：建立你自己的工作分支（推薦）

```bash
# 從 main 開一條你的工作分支
git checkout -b my-domain

# 在這條分支上做你的客製化
# 例如：加你的 skill、KB、golden case、WEEK*.md 等
```

> **為什麼要開分支？**
>
> `main` 保持乾淨，方便隨時拉課程更新。
> `my-domain` 是你真正工作的地方。
> 拉更新時：先更新 `main`，再把更新合併進 `my-domain`。

---

## Step 5：跟上上游更新

課程有新章節、修了 bug、加了新功能時，做這四步：

```bash
# 1. 拉取最新的課程內容
git fetch upstream

# 2. 切回 main，merge 上游
git checkout main
git merge upstream/main

# 3. 把更新推到你自己的 fork
git push origin main

# 4. 切回你的工作分支，把課程更新帶進來
git checkout my-domain
git rebase main
# 或 git merge main（看你習慣哪種）
```

如果你沒有動課程檔案，這四步不會有任何衝突，直接完成。

---

## Step 6：如果真的有衝突怎麼辦

衝突只會在「你和課程都改了同一行」時發生。

```bash
# 看哪些檔案衝突了
git status
# 顯示 both modified: app/graph/nodes.py

# 打開衝突檔案，看到這樣的標記：
# <<<<<<< HEAD（你的版本）
# your_code_here
# =======
# upstream_code_here
# >>>>>>> upstream/main（課程的版本）
```

處理原則：

| 情境 | 怎麼做 |
|------|-------|
| 課程修了 bug，你沒改過那行 | 直接用課程版本（accept theirs） |
| 你加了新功能在課程檔案裡 | **這是根本問題**——下次把你的功能移到獨立檔案，不要改課程檔案 |
| 你的 WEEK*.md / golden.yaml 衝突 | 這些是你的檔案，課程不應該碰；若課程加了同名檔案，改個名字 |

---

## 日常工作流程總覽

```
每天開始工作
  git checkout my-domain
  # 寫你的 skill、KB、測試……

每週（或課程有更新時）
  git fetch upstream
  git checkout main && git merge upstream/main
  git push origin main
  git checkout my-domain && git rebase main

完成一個里程碑
  git add <你的檔案>
  git commit -m "feat: 加入醫療領域 skill 和 golden cases"
  git push origin my-domain
```

---

## 只想用單一子專案：Sparse Checkout（進階選項）

如果你只想 clone `project-linebot-rag-skills`，不想要其他子專案佔硬碟空間：

```bash
# Clone 但不 checkout 任何檔案
git clone --no-checkout https://github.com/你的帳號/data-science-2026.git
cd data-science-2026

# 啟用 sparse checkout
git sparse-checkout init --cone

# 只 checkout 你要的子專案
git sparse-checkout set project-linebot-rag-skills docs

# 完成 checkout
git checkout main
```

之後的 `git fetch` / `git merge` 只會下載你 sparse checkout 的目錄，其他子專案完全不影響。

---

## 常見問題

**Q：我可以直接在 `main` 上改，不開分支嗎？**

可以，但不建議。
如果你在 `main` 上改了課程檔案，下次 `git merge upstream/main` 就會衝突。
開分支的成本很低，省去的麻煩很多。

**Q：上游改了 `pyproject.toml`（加了新依賴），我需要做什麼？**

```bash
git merge upstream/main   # pyproject.toml 自動更新
uv sync                   # 安裝新依賴
```

如果你也改過 `pyproject.toml`（加了自己的依賴），合併時可能有小衝突，
手動把兩邊的依賴都保留進去即可。

**Q：我想把我的客製化分享給同學，怎麼辦？**

把你的 `my-domain` 分支推到你的 fork，分享你的 fork URL 就行了。
同學 clone 你的 fork 後，切到 `my-domain` 分支即可看到你的客製化內容。

**Q：我 fork 之後，課程 repo 做了很大的重構，怎麼辦？**

```bash
git fetch upstream
git log upstream/main --oneline -10   # 先看看改了什麼
git diff main upstream/main           # 看詳細 diff
```

了解改動範圍後，再決定 merge 還是 rebase。
大型重構建議先在測試分支試試，確認不影響你的工作後再合併到 `my-domain`。

---

## 心智模型

```
upstream（課程）
     │
     │ git fetch + merge
     ▼
  main（你的 fork，保持乾淨）
     │
     │ rebase / merge
     ▼
my-domain（你的客製化在這裡）
  - skills/your_domain.py
  - tests/cases/golden.yaml
  - WEEK*.md
  - docs/RAG/your_kb/
```

記住一句話：**課程檔案不動，你的檔案另立，永遠不衝突。**
