# Playwright 專案 Windows 安裝指南（PowerShell）

> 適用：Windows 10 / 11 + PowerShell / Windows Terminal
> 目的：建立隔離環境、安裝 Playwright、驗證執行能力

---

## Step 0：進入專案目錄

```powershell
cd C:\Users\[your-username]\Projects\data-science-2026\project-playwright
```

---

## Step 1：建立虛擬環境（第一次才需要）

```powershell
python -m venv .venv
```

---

## Step 2：啟用虛擬環境

```powershell
.venv\Scripts\activate
```

啟用後會看到：

```
(.venv) PS C:\...>
```

---

## Step 3：安裝專案與所有依賴

```powershell
python -m pip install -e ".[all]"
```

- `-e`：editable mode（開發模式）
- `.[all]`：包含所有 optional dependencies（Playwright、測試工具等）

---

## Step 4：安裝 Playwright 瀏覽器

```powershell
playwright install chromium
```

瀏覽器會下載到：

```
C:\Users\<user>\AppData\Local\ms-playwright
```

---

## Step 5：驗證安裝

```powershell
python ch00-setup\verify_install.py
```

含連線測試：

```powershell
python ch00-setup\verify_install.py --online
```

---

## 已存在 `.venv` 的快速流程

```powershell
cd C:\Users\jungy\Projects\data-science-2026\project-playwright
.venv\Scripts\activate
python -m pip install -e ".[all]"
playwright install chromium
python ch00-setup\verify_install.py
```

---

## 安裝流程背後原理

### 1. 隔離環境（venv）

避免「套件地獄」——不同專案的 playwright 版本不會互相干擾。

### 2. 安裝程式碼 + 工具鏈

```powershell
pip install -e ".[all]"
```

同時完成三件事：安裝你的專案本體、安裝 Playwright、安裝測試工具（pytest 等）。

### 3. 安裝真正的瀏覽器

```powershell
playwright install chromium
```

Playwright ≠ Browser——Playwright 是「控制器」，Chromium 才是「引擎」，兩者需分開安裝。

---

## 常見錯誤與排除（實戰版）

### 1. playwright 未安裝

```
ModuleNotFoundError: playwright
```

解法：

```powershell
python -m pip install -e ".[all]"
```

---

### 2. Chromium 無法下載（權限問題）

```
EACCES: permission denied
```

發生位置：`C:\Users\<user>\AppData\Local\ms-playwright`

解法：在 PowerShell（非受限環境，無需系統管理員）下執行：

```powershell
playwright install chromium
```

---

### 3. PowerShell 無法啟用 venv

```
running scripts is disabled on this system
```

解法：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 4. Unicode 編碼錯誤

```
UnicodeEncodeError
```

解法：

```powershell
$env:PYTHONUTF8="1"
```

永久設定可加入 PowerShell Profile，或在 `.env` 中設定 `PYTHONUTF8=1`。

---

### 5. verify_install.py 版本讀取錯誤

原問題：`playwright.__version__` 不存在此屬性會報錯。

已修正為用 importlib.metadata 讀取：

```python
import importlib.metadata
version = importlib.metadata.version("playwright")
```

---

## 進階設定

### 環境變數標準化（.env）

```env
PYTHONUTF8=1
```

### 一鍵安裝腳本（setup.ps1）

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[all]"
playwright install chromium
python ch00-setup\verify_install.py
```
