"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts"
import { generateViolationBreakdown } from "@/lib/mock-data"

const COLORS = ["#ef4444", "#f59e0b", "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6"]

export function ViolationChart() {
  const data = generateViolationBreakdown()

  return (
    <Card className="bg-card">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-foreground">Violations by Type</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical">
              <XAxis type="number" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="type"
                stroke="#71717a"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#111217",
                  border: "1px solid #27272a",
                  borderRadius: "6px",
                  color: "#e4e4e7",
                }}
                formatter={(value: number) => [`${value} items`, "Count"]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
