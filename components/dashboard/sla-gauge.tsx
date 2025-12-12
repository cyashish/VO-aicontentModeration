"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"

interface SLAGaugeProps {
  value: number
  label: string
  target: number
}

export function SLAGauge({ value, label, target }: SLAGaugeProps) {
  const data = [
    { name: "value", value: value },
    { name: "remaining", value: 100 - value },
  ]

  const getColor = () => {
    if (value >= target) return "#22c55e"
    if (value >= target - 5) return "#f59e0b"
    return "#ef4444"
  }

  return (
    <Card className="bg-card">
      <CardHeader className="pb-0">
        <CardTitle className="text-sm font-medium text-foreground text-center">{label}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="h-[120px] relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="70%"
                startAngle={180}
                endAngle={0}
                innerRadius={50}
                outerRadius={70}
                dataKey="value"
                stroke="none"
              >
                <Cell fill={getColor()} />
                <Cell fill="#27272a" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pt-4">
            <span className="text-2xl font-bold text-foreground">{value.toFixed(1)}%</span>
            <span className="text-xs text-muted-foreground">Target: {target}%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
