FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製原始碼
COPY . .

# SSE port（給 Claude Desktop）
EXPOSE 3000
# REST port（給 Next.js Dashboard）
EXPOSE 3001

CMD ["python", "server.py"]
