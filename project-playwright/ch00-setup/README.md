# Ch00 — 環境設置

## 學習目標

- 安裝 Playwright 及瀏覽器引擎
- 驗證開發環境是否正確
- 認識 Playwright 的同步 / 非同步 API

## 安裝步驟

### 1. 建立虛擬環境

```bash
cd project-playwright
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

### 2. 安裝套件

```bash
pip install -e ".[all]"
```

### 3. 安裝瀏覽器

```bash
# 只裝 Chromium（推薦，最快）
playwright install chromium

# 或全部安裝
playwright install
```

### 4. 驗證安裝

```bash
python3 ch00-setup/verify_install.py
```

成功會看到（步驟 1-3 不需要網路）：
```
── 離線驗證（步驟 1-3）──
[✓] playwright 套件已安裝（版本：x.xx.x）
[✓] chromium 瀏覽器可啟動
[✓] 瀏覽器可開啟頁面（about:blank，離線）
[✓] 截圖功能正常 → output/screenshots/verify_install.png

  若要同時測試對外連線，加上 --online 參數：
  python3 ch00-setup/verify_install.py --online

🎉 環境設置完成！可以開始學習了。
```

## 常見問題

### Q: `playwright install` 卡住或失敗？

```bash
# 手動指定鏡像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
```

### Q: macOS 上出現權限錯誤？

```bash
xattr -cr ~/Library/Caches/ms-playwright
```

### Q: 要用哪個瀏覽器？

推薦 **Chromium**：最穩定、社群資源最多。後續章節預設都使用 Chromium。
