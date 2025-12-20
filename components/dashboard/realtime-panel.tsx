"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { fetchRealtimeData } from "@/lib/api-client"
import { Activity, Zap, Shield, AlertTriangle } from "lucide-react"

type RealtimeDecisionRow = {
  message_id: string
  decision: string
  processing_time_ms: number
  is_burst_detected: boolean
  created_at: string
}

type RealtimeSummary = {
  messagesPerSecond: number
  avgLatencyMs: number
  blockedMessages: number
  burstDetections: number
}

export function RealtimePanel() {
  const [metrics, setMetrics] = useState<RealtimeSummary>({
    messagesPerSecond: 0,
    avgLatencyMs: 0,
    blockedMessages: 0,
    burstDetections: 0,
  })
  const [messages, setMessages] = useState<
    { id: number; text: string; status: "allowed" | "blocked"; timestamp: Date }[]
  >([])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const rows = (await fetchRealtimeData()) as RealtimeDecisionRow[]
        const now = Date.now()
        const last10s = rows.filter((r) => now - new Date(r.created_at).getTime() <= 10_000)
        const avgLatency =
          rows.reduce((acc, r) => acc + (Number(r.processing_time_ms) || 0), 0) / Math.max(1, rows.length)
        const blocked = rows.filter((r) => r.decision === "rejected").length
        const bursts = rows.filter((r) => Boolean(r.is_burst_detected)).length

        const stream = rows.slice(0, 10).map((r) => ({
          id: new Date(r.created_at).getTime(),
          text: `msg ${r.message_id.slice(0, 8)}...`,
          status: r.decision === "rejected" ? "blocked" : "allowed",
          timestamp: new Date(r.created_at),
        }))

        if (cancelled) return
        setMetrics({
          messagesPerSecond: Number((last10s.length / 10).toFixed(1)),
          avgLatencyMs: Number(avgLatency.toFixed(1)),
          blockedMessages: blocked,
          burstDetections: bursts,
        })
        setMessages(stream)
      } catch (e) {
        console.error("Failed to load realtime decisions", e)
      }
    }

    load()
    const interval = setInterval(load, 2000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return (
    <Card className="bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-foreground">Real-time Chat (Flow B)</CardTitle>
          <Badge variant="secondary" className="bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]/30">
            <Activity className="h-3 w-3 mr-1 animate-pulse" />
            Live
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-secondary rounded-md">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Activity className="h-4 w-4" />
              <span className="text-xs">Messages/sec</span>
            </div>
            <span className="text-xl font-bold text-foreground">{metrics.messagesPerSecond.toLocaleString()}</span>
          </div>
          <div className="p-3 bg-secondary rounded-md">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Zap className="h-4 w-4" />
              <span className="text-xs">Latency</span>
            </div>
            <span className="text-xl font-bold text-[#22c55e]">{metrics.avgLatencyMs.toFixed(1)}ms</span>
          </div>
          <div className="p-3 bg-secondary rounded-md">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Shield className="h-4 w-4" />
              <span className="text-xs">Blocked</span>
            </div>
            <span className="text-xl font-bold text-[#ef4444]">{metrics.blockedMessages}</span>
          </div>
          <div className="p-3 bg-secondary rounded-md">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs">Bursts</span>
            </div>
            <span className="text-xl font-bold text-[#f59e0b]">{metrics.burstDetections}</span>
          </div>
        </div>

        <div>
          <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">Live Stream</h4>
          <div className="space-y-1 max-h-[200px] overflow-hidden">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-center justify-between p-2 rounded text-xs ${
                  msg.status === "blocked" ? "bg-[#ef4444]/10" : "bg-secondary"
                }`}
              >
                <span className={msg.status === "blocked" ? "text-[#ef4444] line-through" : "text-foreground"}>
                  {msg.text}
                </span>
                <Badge
                  variant="outline"
                  className={`text-[10px] ${
                    msg.status === "blocked" ? "border-[#ef4444] text-[#ef4444]" : "border-[#22c55e] text-[#22c55e]"
                  }`}
                >
                  {msg.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
