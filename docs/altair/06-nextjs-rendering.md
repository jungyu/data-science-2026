# Chapter 06：Next.js 渲染圖表

> 第 5 週 — 真正產品化：讓圖表活在瀏覽器裡

---

## 本章目標

- 在 Next.js 中安裝並使用 Vega-Lite 渲染引擎
- 建立可重用的圖表 React 元件
- 從 API 取得 Spec 並渲染
- 理解 Client Component 的必要性
- 做出一個「圖表清單頁」

---

## 6.1 為什麼用 Next.js？

| 特性 | 說明 |
|------|------|
| **React 生態系** | 豐富的元件庫和社群 |
| **全端框架** | 前端 + API Route 一站搞定 |
| **Server Component** | 伺服器端渲染提升效能 |
| **App Router** | 現代化的路由系統 |
| **TypeScript** | 型別安全 |

---

## 6.2 專案建立

```bash
# 建立 Next.js 專案
npx create-next-app@latest chart-gallery --typescript --tailwind --app --src-dir

cd chart-gallery

# 安裝 Vega 相關套件
npm install react-vega vega vega-lite vega-embed
```

### 專案結構

```
chart-gallery/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # 首頁（圖表清單）
│   │   └── charts/
│   │       └── [id]/
│   │           └── page.tsx      # 單一圖表頁
│   ├── components/
│   │   ├── VegaChart.tsx         # Vega 渲染元件
│   │   ├── ChartCard.tsx         # 圖表卡片
│   │   └── ChartList.tsx         # 圖表清單
│   └── lib/
│       └── api.ts                # API 呼叫函數
├── package.json
└── tsconfig.json
```

---

## 6.3 建立 Vega 圖表元件

### 核心元件：VegaChart

```typescript
// src/components/VegaChart.tsx
"use client"

import { useEffect, useRef } from 'react'
import embed from 'vega-embed'

interface VegaChartProps {
  spec: Record<string, unknown>
  width?: number
  height?: number
  className?: string
}

export default function VegaChart({
  spec,
  width,
  height,
  className = ''
}: VegaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || !spec) return

    // 合併尺寸設定
    const fullSpec = {
      ...spec,
      ...(width && { width }),
      ...(height && { height }),
    }

    const result = embed(containerRef.current, fullSpec as any, {
      actions: false,  // 隱藏匯出按鈕
      renderer: 'svg',  // 使用 SVG 渲染（較清晰）
    })

    // 清理函數
    return () => {
      result.then(res => res.finalize())
    }
  }, [spec, width, height])

  return <div ref={containerRef} className={className} />
}
```

> **為什麼需要 `"use client"`？**
>
> Vega 需要操作 DOM（瀏覽器環境）。Next.js 的 Server Component 在伺服器端執行，
> 沒有 DOM。因此必須標記為 Client Component，讓它在瀏覽器中執行。

### 替代方案：使用 react-vega

```typescript
// src/components/VegaLiteChart.tsx
"use client"

import { VegaLite } from 'react-vega'

interface VegaLiteChartProps {
  spec: Record<string, unknown>
}

export default function VegaLiteChart({ spec }: VegaLiteChartProps) {
  return (
    <VegaLite
      spec={spec as any}
      actions={false}
      renderer="svg"
    />
  )
}
```

兩種方式都可以，`vega-embed` 更靈活，`react-vega` 更 React 風格。

---

## 6.4 API 整合

### API 呼叫函數

```typescript
// src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// 也可以用 Supabase
// const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
// const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export interface ChartMeta {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface ChartDetail extends ChartMeta {
  spec: Record<string, unknown>
}

// 取得所有圖表
export async function getCharts(): Promise<ChartMeta[]> {
  const res = await fetch(`${API_BASE}/charts`, {
    next: { revalidate: 60 }  // ISR：每 60 秒重新驗證
  })
  if (!res.ok) throw new Error('Failed to fetch charts')
  return res.json()
}

// 取得單一圖表
export async function getChart(id: string): Promise<ChartDetail> {
  const res = await fetch(`${API_BASE}/charts/${id}`, {
    next: { revalidate: 60 }
  })
  if (!res.ok) throw new Error('Chart not found')
  return res.json()
}

// 取得圖表 spec
export async function getChartSpec(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/charts/${id}/spec`, {
    next: { revalidate: 60 }
  })
  if (!res.ok) throw new Error('Spec not found')
  return res.json()
}
```

### 使用 Supabase 的版本

```typescript
// src/lib/api.ts (Supabase 版)

import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function getCharts() {
  const { data, error } = await supabase
    .from('chart_specs')
    .select('id, name, description, created_at')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}

export async function getChart(id: string) {
  const { data, error } = await supabase
    .from('chart_specs')
    .select('*')
    .eq('id', id)
    .single()

  if (error) throw error
  return data
}
```

---

## 6.5 建立頁面

### 首頁：圖表清單

```typescript
// src/app/page.tsx
import Link from 'next/link'
import { getCharts } from '@/lib/api'

export default async function HomePage() {
  const charts = await getCharts()

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Chart Gallery</h1>
      <p className="text-gray-600 mb-8">
        Vega-Lite 圖表管理系統
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {charts.map(chart => (
          <Link
            key={chart.id}
            href={`/charts/${chart.id}`}
            className="block p-6 bg-white rounded-lg border border-gray-200
                       hover:border-blue-400 hover:shadow-md transition-all"
          >
            <h2 className="text-xl font-semibold mb-2">{chart.name}</h2>
            {chart.description && (
              <p className="text-gray-500 text-sm">{chart.description}</p>
            )}
            <p className="text-gray-400 text-xs mt-3">
              {new Date(chart.created_at).toLocaleDateString('zh-TW')}
            </p>
          </Link>
        ))}
      </div>

      {charts.length === 0 && (
        <p className="text-center text-gray-400 py-12">
          還沒有圖表，用 Python 建立一些吧！
        </p>
      )}
    </main>
  )
}
```

### 圖表詳情頁

```typescript
// src/app/charts/[id]/page.tsx
import { getChart } from '@/lib/api'
import VegaChart from '@/components/VegaChart'
import Link from 'next/link'

interface Props {
  params: Promise<{ id: string }>
}

export default async function ChartPage({ params }: Props) {
  const { id } = await params
  const chart = await getChart(id)

  return (
    <main className="max-w-4xl mx-auto p-8">
      <Link
        href="/"
        className="text-blue-500 hover:underline text-sm mb-4 inline-block"
      >
        ← 返回清單
      </Link>

      <h1 className="text-2xl font-bold mb-2">{chart.name}</h1>
      {chart.description && (
        <p className="text-gray-600 mb-6">{chart.description}</p>
      )}

      {/* 圖表渲染 */}
      <div className="bg-white rounded-lg border p-6 mb-6">
        <VegaChart spec={chart.spec} />
      </div>

      {/* Spec 原始碼 */}
      <details className="bg-gray-50 rounded-lg border p-4">
        <summary className="cursor-pointer font-medium text-gray-700">
          查看 Vega-Lite Spec
        </summary>
        <pre className="mt-4 text-sm overflow-x-auto text-gray-600">
          {JSON.stringify(chart.spec, null, 2)}
        </pre>
      </details>
    </main>
  )
}
```

---

## 6.6 圖表卡片元件（帶預覽）

```typescript
// src/components/ChartCard.tsx
"use client"

import Link from 'next/link'
import VegaChart from './VegaChart'

interface ChartCardProps {
  id: string
  name: string
  description: string | null
  spec: Record<string, unknown>
}

export default function ChartCard({ id, name, description, spec }: ChartCardProps) {
  // 縮小版 spec 用於預覽
  const previewSpec = {
    ...spec,
    width: 280,
    height: 180,
    title: undefined,  // 預覽不顯示標題
  }

  return (
    <Link
      href={`/charts/${id}`}
      className="block bg-white rounded-lg border border-gray-200
                 hover:border-blue-400 hover:shadow-md transition-all overflow-hidden"
    >
      {/* 圖表預覽 */}
      <div className="p-4 bg-gray-50 flex justify-center">
        <VegaChart spec={previewSpec} />
      </div>

      {/* 資訊 */}
      <div className="p-4">
        <h2 className="font-semibold text-lg">{name}</h2>
        {description && (
          <p className="text-gray-500 text-sm mt-1">{description}</p>
        )}
      </div>
    </Link>
  )
}
```

---

## 6.7 使用 Next.js API Route（全端方案）

如果不想用外部 API，可以直接在 Next.js 中寫 API Route：

```typescript
// src/app/api/charts/route.ts
import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!  // 伺服器端用 service key
)

export async function GET() {
  const { data, error } = await supabase
    .from('chart_specs')
    .select('id, name, description, created_at')
    .order('created_at', { ascending: false })

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json(data)
}

export async function POST(request: Request) {
  const body = await request.json()

  const { data, error } = await supabase
    .from('chart_specs')
    .insert(body)
    .select()
    .single()

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 })
  }

  return NextResponse.json(data, { status: 201 })
}
```

```typescript
// src/app/api/charts/[id]/route.ts
import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
)

interface Props {
  params: Promise<{ id: string }>
}

export async function GET(_request: Request, { params }: Props) {
  const { id } = await params

  const { data, error } = await supabase
    .from('chart_specs')
    .select('*')
    .eq('id', id)
    .single()

  if (error) {
    return NextResponse.json({ error: 'Chart not found' }, { status: 404 })
  }

  return NextResponse.json(data)
}
```

---

## 6.8 整體資料流

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Database (Supabase)                                    │
│  ┌─────────────────────────────┐                       │
│  │ chart_specs                 │                       │
│  │  id | name | spec (jsonb)   │                       │
│  └──────────────┬──────────────┘                       │
│                 │                                       │
│                 ▼                                       │
│  API (Supabase REST / Next.js API Route)               │
│  GET /api/charts → [{id, name, ...}]                   │
│  GET /api/charts/:id → {id, name, spec, ...}           │
│                 │                                       │
│                 ▼                                       │
│  Next.js Server Component                               │
│  ┌─────────────────────────────┐                       │
│  │ page.tsx                    │                       │
│  │   const chart = await       │                       │
│  │     getChart(id)            │                       │
│  │   <VegaChart spec={spec} /> │                       │
│  └──────────────┬──────────────┘                       │
│                 │                                       │
│                 ▼                                       │
│  Client Component (Browser)                             │
│  ┌─────────────────────────────┐                       │
│  │ VegaChart.tsx               │                       │
│  │   "use client"              │                       │
│  │   vega-embed(spec)          │                       │
│  │   → SVG/Canvas 渲染         │                       │
│  └─────────────────────────────┘                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6.9 效能優化提示

### 1. 資料分離

如果圖表資料量很大，不要把資料嵌在 spec 裡：

```typescript
// 分離資料
const spec = await getChartSpec(id)  // 不含 data
const data = await getChartData(id)  // 只有資料

// 前端組合
<VegaChart spec={{ ...spec, data: { values: data } }} />
```

### 2. 懶載入 Vega

Vega 庫很大（~1MB），使用動態匯入：

```typescript
// src/components/LazyVegaChart.tsx
"use client"

import dynamic from 'next/dynamic'

const VegaChart = dynamic(() => import('./VegaChart'), {
  ssr: false,
  loading: () => (
    <div className="animate-pulse bg-gray-100 rounded h-64 flex items-center justify-center">
      <span className="text-gray-400">載入圖表中...</span>
    </div>
  )
})

export default VegaChart
```

### 3. 錯誤處理

```typescript
// src/components/SafeVegaChart.tsx
"use client"

import { useEffect, useRef, useState } from 'react'
import embed from 'vega-embed'

interface SafeVegaChartProps {
  spec: Record<string, unknown>
}

export default function SafeVegaChart({ spec }: SafeVegaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || !spec) return
    setError(null)

    embed(containerRef.current, spec as any, { actions: false })
      .catch(err => {
        setError(`圖表渲染失敗：${err.message}`)
      })
  }, [spec])

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4 text-red-600 text-sm">
        {error}
      </div>
    )
  }

  return <div ref={containerRef} />
}
```

---

## 6.10 本章作業

### 作業 1：建立 Next.js 專案

建立一個 Next.js 專案，安裝 Vega 相關套件，做出一個能渲染硬編碼 spec 的頁面。

### 作業 2：圖表清單頁

從 API（Supabase 或 FastAPI）取得圖表清單，做出一個圖表清單頁面：
- 顯示圖表名稱和描述
- 點擊可進入詳情頁
- 詳情頁渲染圖表

### 作業 3：可展開的 Spec 檢視器

在圖表詳情頁加上一個「查看 Spec」的按鈕，點擊後顯示格式化的 JSON。

---

## 本章小結

```
本章學會的技能：
┌──────────────────────────────────────────────┐
│ 元件：                                        │
│   VegaChart — 用 vega-embed 渲染 spec         │
│   "use client" — Vega 需要瀏覽器環境          │
│                                              │
│ 資料流：                                      │
│   Database → API → Server Component           │
│     → Client Component → Vega → Browser       │
│                                              │
│ 優化：                                        │
│   資料分離、動態匯入、錯誤處理               │
│                                              │
│ 頁面：                                        │
│   / → 圖表清單                                │
│   /charts/:id → 圖表詳情 + 渲染               │
└──────────────────────────────────────────────┘
```

> **帶走一句話**：Spec 是前後端之間的「合約」。
> Python 負責產生 Spec，Next.js 負責渲染 Spec，資料庫負責保管 Spec。
> 每一層都只做自己的事，互不干擾。

---

[上一章 ← Chapter 05：Spec 存儲與 API 化](05-spec-storage-api.md) ｜ [下一章 → Chapter 07：AI 修改圖表規格](07-ai-spec-modification.md)
