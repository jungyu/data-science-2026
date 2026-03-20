# ── Stage 1：安裝依賴 ─────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ── Stage 2：建置 ────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 建置時需要 NEXT_PUBLIC_* 環境變數（若有的話在此傳入）
RUN npm run build

# ── Stage 3：執行（最小映像）────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=4000

# next build --output standalone 只複製必要檔案
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 4000

# Next.js standalone 入口
CMD ["node", "server.js"]
