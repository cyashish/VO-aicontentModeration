"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts"
import { useEffect, useState } from "react"
import { generateTimeSeries } from "@/lib/mock-data"

export function ThroughputChart() {
  const [data, setData] = useState<{ time: string; throughput: number; latency: number }[]>([])

  useEffect(() => {
    const updateData = () => {
      const throughputSeries = generateTimeSeries(30, 1200, 400)
      const latencySeries = generateTimeSeries(30, 25, 15)

      setData(
        throughputSeries.map((t, i) => ({
          time: t.timestamp.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
          throughput: Math.round(t.value),
          latency: Math.round(latencySeries[i].value),
        })),
      )
    }

    updateData()
    const interval = setInterval(updateData, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="bg-card col-span-2">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-foreground">Throughput & Latency (Last 30 min)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="throughputGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis
                yAxisId="left"
                stroke="#71717a"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#71717a"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}ms`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#111217",
                  border: "1px solid #27272a",
                  borderRadius: "6px",
                  color: "#e4e4e7",
                }}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="throughput"
                stroke="#3b82f6"
                fill="url(#throughputGradient)"
                strokeWidth={2}
                name="Throughput (req/s)"
              />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="latency"
                stroke="#22c55e"
                fill="url(#latencyGradient)"
                strokeWidth={2}
                name="Latency (ms)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#3b82f6]" />
            <span className="text-xs text-muted-foreground">Throughput</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#22c55e]" />
            <span className="text-xs text-muted-foreground">Latency</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
