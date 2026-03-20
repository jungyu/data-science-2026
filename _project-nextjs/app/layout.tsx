import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DS Dashboard',
  description: '資料科學 RAG 儀表板',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    // data-theme 切換主題：corporate（預設）或 dark
    <html lang="zh-TW" data-theme="corporate">
      <body className="min-h-screen bg-base-200">
        {children}
      </body>
    </html>
  )
}
