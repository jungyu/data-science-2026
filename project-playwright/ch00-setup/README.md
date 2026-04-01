# Ch00 — 環境設置

## 學習目標

- 安裝 Playwright 及瀏覽器引擎
- 驗證開發環境是否正確
- 認識 Playwright 的同步 / 非同步 API

---

## 安裝步驟

請依照你的作業系統選擇對應的指令。

### macOS

```bash
# 1. 建立虛擬環境並啟動
cd project-playwright
python3 -m venv .venv
source .venv/bin/activate

# 2. 安裝套件
pip install -e ".[all]"

# 3. 安裝 Chromium（Playwright 管理的獨立版本）
playwright install chromium

# 4. 驗證安裝
python3 ch00-setup/verify_install.py
```

---

### Ubuntu / WSL（Windows Subsystem for Linux）

> WSL1 / WSL2 通用。Chromium 在 `headless=True` 模式下不需要圖形介面，WSL1 也能正常執行。

```bash
# 1. 建立虛擬環境並啟動
cd project-playwright
python3 -m venv .venv
source .venv/bin/activate

# 2. 安裝套件
pip install -e ".[all]"

# 3. 安裝系統共享函式庫（Linux 必要步驟，macOS/Windows 不需要）
playwright install-deps chromium

# 4. 安裝 Chromium
playwright install chromium

# 5. 驗證安裝
python3 ch00-setup/verify_install.py
```

> **為什麼 Linux 多一個步驟？**
> Playwright 的 Chromium 雖是獨立打包版本，但仍依賴部分系統層函式庫
>（`libnss3`、`libatk-bridge2.0-0`、`libdrm2` 等）。
> `playwright install-deps` 會用 `apt` 自動安裝這些套件（需要 sudo 權限）。
> 若跳過此步驟，步驟 4 會出現「error while loading shared libraries」錯誤。

---

### Windows 10 / 11

> 建議使用 **PowerShell** 或 **Windows Terminal**，不建議用舊版 CMD。
> 詳細實戰說明（含常見障礙排除）：[windows-install.md](windows-install.md)

```powershell
# 1. 建立虛擬環境並啟動
cd project-playwright
python -m venv .venv
.venv\Scripts\activate

# 2. 安裝套件
python -m pip install -e ".[all]"

# 3. 安裝 Chromium
playwright install chromium

# 4. 驗證安裝
python ch00-setup\verify_install.py
```

> **注意**：Windows 上的 Python 指令是 `python`，不是 `python3`。
> 若同時裝了多個版本，建議用 Python Launcher：`py -3.11 -m venv .venv`。

---

## 驗證安裝成功的輸出

執行 `verify_install.py` 後，步驟 1-3 不需要網路：

```
── 離線驗證（步驟 1-3）──
[✓] playwright 套件已安裝（版本：x.xx.x）
[✓] chromium 瀏覽器可啟動
[✓] 瀏覽器可開啟頁面（about:blank，離線）
[✓] 截圖功能正常 → output/screenshots/verify_install.png

  若要同時測試對外連線，加上 --online 參數：
  python ch00-setup/verify_install.py --online

🎉 環境設置完成！可以開始學習了。
```

---

## 常見問題排除

### Q: Linux/WSL — `error while loading shared libraries`

```bash
# 補裝系統依賴，再重裝 Chromium
playwright install-deps chromium
playwright install chromium
```

### Q: macOS — 瀏覽器被 Gatekeeper 封鎖

```bash
xattr -cr ~/Library/Caches/ms-playwright
playwright install chromium
```

### Q: Windows — `.venv\Scripts\activate` 出現「執行原則」錯誤

```powershell
# 允許本機腳本執行（僅限目前使用者）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

### Q: Windows — 出現 `UnicodeEncodeError`

```powershell
# 強制 Python 使用 UTF-8 輸出
$env:PYTHONUTF8="1"
```

### Q: `playwright install` 下載緩慢或失敗

```bash
# macOS / Linux：使用 npmmirror 鏡像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
```

```powershell
# Windows PowerShell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"
playwright install chromium
```

### Q: 要用哪個瀏覽器？

推薦 **Chromium**：最穩定、社群資源最多。後續章節預設都使用 Chromium。
若需要多瀏覽器測試（ch07），再執行 `playwright install` 安裝全部。
