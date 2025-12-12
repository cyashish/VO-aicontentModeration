"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { generateRealtimeChatMetrics } from "@/lib/mock-data"
import { Activity, Zap, Shield, AlertTriangle } from "lucide-react"

export function RealtimePanel() {
  const [metrics, setMetrics] = useState(generateRealtimeChatMetrics())
  const [messages, setMessages] = useState<
    { id: number; text: string; status: "allowed" | "blocked"; timestamp: Date }[]
  >([])

  useEffect(() => {
    const metricsInterval = setInterval(() => {
      setMetrics(generateRealtimeChatMetrics())
    }, 2000)

    const messageInterval = setInterval(() => {
      const mockMessages = [
        { text: "GG everyone!", status: "allowed" as const },
        { text: "Nice play!", status: "allowed" as const },
        { text: "Check out my profile for...", status: "blocked" as const },
        { text: "Anyone want to team up?", status: "allowed" as const },
        { text: "!@#$ you noob", status: "blocked" as const },
        { text: "Great game!", status: "allowed" as const },
        { text: "Buy cheap coins at...", status: "blocked" as const },
      ]

      const newMsg = mockMessages[Math.floor(Math.random() * mockMessages.length)]
      setMessages((prev) => [{ id: Date.now(), ...newMsg, timestamp: new Date() }, ...prev.slice(0, 9)])
    }, 500)

    return () => {
      clearInterval(metricsInterval)
      clearInterval(messageInterval)
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
