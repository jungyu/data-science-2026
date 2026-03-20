FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（Playwright Chromium 需要）
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright Chromium（僅安裝 chromium，不裝 firefox/webkit）
RUN playwright install chromium

# 複製原始碼
COPY . .

EXPOSE 3001

CMD ["python", "crawler.py"]
