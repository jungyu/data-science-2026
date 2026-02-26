# Ch00 — 環境設置

## 學習目標

- 安裝 Playwright 及瀏覽器引擎
- 驗證開發環境是否正確
- 認識 Playwright 的同步 / 非同步 API

## 安裝步驟

### 1. 建立虛擬環境

```bash
cd project-playwright
python -m venv .venv
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
python ch00-setup/verify_install.py
```

成功會看到：
```
[✓] playwright 套件已安裝 (版本: x.xx.x)
[✓] chromium 瀏覽器可用
[✓] 成功開啟瀏覽器並導航至測試頁面
[✓] 截圖已儲存
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
