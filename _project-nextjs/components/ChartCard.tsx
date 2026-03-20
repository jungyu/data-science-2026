'use client'

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ChartData,
  ChartType,
} from 'chart.js'
import { Line, Bar, Pie, Doughnut } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Title, Tooltip, Legend, Filler
)

interface ChartCardProps {
  title: string
  type: 'line' | 'bar' | 'pie' | 'doughnut'
  data: ChartData<ChartType>
  height?: number
  description?: string
}

const CHART_COMPONENTS = {
  line: Line,
  bar: Bar,
  pie: Pie,
  doughnut: Doughnut,
} as const

/**
 * 通用圖表容器
 *
 * 使用方式：
 * <ChartCard title="銷售趨勢" type="line" data={myData} />
 *
 * data 格式遵循 Chart.js ChartData 規格。
 */
export default function ChartCard({
  title,
  type,
  data,
  height = 300,
  description,
}: ChartCardProps) {
  const ChartComponent = CHART_COMPONENTS[type] as React.ComponentType<{
    data: ChartData<ChartType>
    height: number
    options: object
  }>

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' as const },
    },
  }

  return (
    <div className="card bg-base-100 shadow">
      <div className="card-body p-4">
        <h2 className="card-title text-base">{title}</h2>
        {description && (
          <p className="text-sm text-base-content/60">{description}</p>
        )}
        <div style={{ height }}>
          <ChartComponent data={data} height={height} options={options} />
        </div>
      </div>
    </div>
  )
}
