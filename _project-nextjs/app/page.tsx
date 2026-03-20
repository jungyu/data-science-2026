'use client'

import { useState } from 'react'
import ChartCard from '@/components/ChartCard'
import MermaidBlock from '@/components/MermaidBlock'
import Sidebar from '@/components/Sidebar'
import { PRESET_QUESTIONS } from '@/lib/preset-questions'

// ── 範例資料（學生替換成自己的資料來源） ──────────────────────
const SAMPLE_TREND_DATA = {
  labels: ['一月', '二月', '三月', '四月', '五月', '六月'],
  datasets: [
    {
      label: '銷售量',
      data: [65, 78, 90, 81, 95, 110],
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
    },
  ],
}

const SAMPLE_DIST_DATA = {
  labels: ['A 類', 'B 類', 'C 類', 'D 類', 'E 類'],
  datasets: [
    {
      label: '各類別數量',
      data: [42, 28, 35, 19, 24],
      backgroundColor: [
        'rgba(59, 130, 246, 0.7)',
        'rgba(16, 185, 129, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(139, 92, 246, 0.7)',
      ],
    },
  ],
}

// 系統架構圖（Mermaid）
const SAMPLE_MERMAID = `graph LR
  A[使用者] --> B[Next.js Dashboard]
  B --> C[MCP Server]
  C --> D[RAG Pipeline]
  C --> E[Supabase]
  D --> F[Qdrant 向量庫]
  D --> G[OpenAI Embedding]`

// ─────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex flex-col h-screen">

      {/* ── Navbar ── */}
      <div className="navbar bg-base-100 shadow-sm px-4 z-10">
        <div className="flex-1">
          <span className="text-xl font-bold text-primary">DS Dashboard</span>
          {/* 學生替換成自己的專案名稱 */}
          <span className="ml-3 text-base-content/50 text-sm">資料科學專題</span>
        </div>
        <div className="flex-none gap-2">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? '隱藏 AI 側欄' : '開啟 AI 側欄'}
          </button>
        </div>
      </div>

      {/* ── 主體：圖表區 + AI 側欄 ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── 圖表區（左 / 主體）── */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* 統計摘要卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '總筆數', value: '1,248', color: 'text-primary' },
              { label: '本月新增', value: '127', color: 'text-success' },
              { label: '平均分數', value: '82.4', color: 'text-warning' },
              { label: '異常筆數', value: '3', color: 'text-error' },
            ].map((stat) => (
              <div key={stat.label} className="stat bg-base-100 rounded-box shadow">
                <div className="stat-title">{stat.label}</div>
                <div className={`stat-value text-2xl ${stat.color}`}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* 趨勢圖 + 分佈圖 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ChartCard
              title="時間趨勢"
              type="line"
              data={SAMPLE_TREND_DATA}
              height={260}
            />
            <ChartCard
              title="類別分佈"
              type="bar"
              data={SAMPLE_DIST_DATA}
              height={260}
            />
          </div>

          {/* 系統架構圖 */}
          <div className="card bg-base-100 shadow">
            <div className="card-body">
              <h2 className="card-title text-base">系統架構</h2>
              <MermaidBlock chart={SAMPLE_MERMAID} />
            </div>
          </div>

        </main>

        {/* ── AI 側欄（右）── */}
        {sidebarOpen && (
          <Sidebar presetQuestions={PRESET_QUESTIONS} />
        )}

      </div>
    </div>
  )
}
