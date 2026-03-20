import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // 讓 Next.js 可以在 Docker 容器內正常運行
  output: 'standalone',
}

export default nextConfig
