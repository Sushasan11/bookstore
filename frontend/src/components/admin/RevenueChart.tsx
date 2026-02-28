'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'

// ---------------------------------------------------------------------------
// Chart configuration — maps data keys to labels and CSS variable colors
// ---------------------------------------------------------------------------

const chartConfig = {
  current: {
    label: 'Current Period',
    color: 'hsl(var(--chart-1))',
  },
  prior: {
    label: 'Prior Period',
    color: 'hsl(var(--chart-2))',
  },
} satisfies ChartConfig

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RevenueChartProps {
  currentRevenue: number
  priorRevenue: number | null
  periodLabel: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RevenueChart({
  currentRevenue,
  priorRevenue,
  periodLabel,
}: RevenueChartProps) {
  const chartData = [
    {
      name: periodLabel,
      current: currentRevenue,
      prior: priorRevenue ?? 0,
    },
  ]

  const hasPriorData = priorRevenue !== null

  return (
    <div className="space-y-2">
      <ChartContainer config={chartConfig} className="h-[300px] w-full">
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tickFormatter={(v: number) => '$' + v.toLocaleString('en-US')}
          />
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                formatter={(value) =>
                  typeof value === 'number'
                    ? '$' + Math.round(value).toLocaleString('en-US')
                    : String(value)
                }
              />
            }
          />
          <Bar
            dataKey="current"
            fill="var(--color-current)"
            radius={4}
            name="Current Period"
          />
          <Bar
            dataKey="prior"
            fill="var(--color-prior)"
            radius={4}
            name="Prior Period"
          />
        </BarChart>
      </ChartContainer>
      {!hasPriorData && (
        <p className="text-center text-xs text-muted-foreground">
          No prior period data available for comparison
        </p>
      )}
    </div>
  )
}
