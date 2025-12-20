"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { fetchQueue } from "@/lib/api-client"
import { CheckCircle, XCircle, Clock, AlertTriangle, MessageSquare, ImageIcon, User, Gamepad2 } from "lucide-react"
import { cn } from "@/lib/utils"

type QueueRow = {
  id: string
  content_type: string
  text_preview: string | null
  image_urls: string[] | null
  user_id: string
  username: string | null
  priority: number
  sla_deadline: string
  escalation_reason: string | null
  detected_violations: string[] | null
  ml_confidence: number | null
}

type QueueItem = {
  id: string
  contentType: "forum_post" | "image" | "profile" | "chat"
  severity: "critical" | "high" | "medium" | "low"
  preview: string
  username: string
  userId: string
  violationTypes: string[]
  mlScore: number
  userReputation: number
  slaDeadline: Date
}

const severityColors = {
  critical: "bg-[#ef4444] text-white",
  high: "bg-[#f59e0b] text-white",
  medium: "bg-[#eab308] text-black",
  low: "bg-[#22c55e] text-white",
}

const contentTypeIcons = {
  forum_post: MessageSquare,
  image: ImageIcon,
  profile: User,
  chat: Gamepad2,
}

export function ModerationQueue() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [selectedItem, setSelectedItem] = useState<QueueItem | null>(null)

  useEffect(() => {
    let cancelled = false

    const severityFromPriority = (priority: number): QueueItem["severity"] => {
      if (priority >= 5) return "critical"
      if (priority === 4) return "high"
      if (priority === 3) return "medium"
      return "low"
    }

    const contentTypeFromDb = (ct: string): QueueItem["contentType"] => {
      if (ct === "forum_post") return "forum_post"
      if (ct === "image") return "image"
      if (ct === "profile") return "profile"
      return "chat"
    }

    const load = async () => {
      try {
        const rows = (await fetchQueue()) as QueueRow[]
        const items: QueueItem[] = rows.map((r) => {
          const mlConfidence = r.ml_confidence ?? 0.5
          return {
            id: r.id,
            contentType: contentTypeFromDb(r.content_type),
            severity: severityFromPriority(r.priority),
            preview: r.text_preview ?? (r.escalation_reason ?? "(no preview)"),
            username: r.username ?? "unknown",
            userId: r.user_id,
            violationTypes: r.detected_violations ?? [],
            // show "risk" style bar: high risk when confidence is low
            mlScore: Math.max(0, Math.min(1, 1 - mlConfidence)),
            userReputation: 50,
            slaDeadline: new Date(r.sla_deadline),
          }
        })
        if (!cancelled) setQueue(items)
      } catch (e) {
        console.error("Failed to load review queue", e)
      }
    }

    load()
    const interval = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const handleAction = (id: string, action: "approve" | "reject") => {
    setQueue((prev) => prev.filter((item) => item.id !== id))
    if (selectedItem?.id === id) {
      setSelectedItem(null)
    }
  }

  const getTimeRemaining = (deadline: Date) => {
    const diff = deadline.getTime() - Date.now()
    if (diff < 0) return "OVERDUE"
    const minutes = Math.floor(diff / 60000)
    if (minutes < 60) return `${minutes}m`
    return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
  }

  return (
    <Card className="bg-card h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-foreground">Review Queue</CardTitle>
          <Badge variant="secondary" className="bg-secondary text-foreground">
            {queue.length} pending
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex h-[500px]">
          <ScrollArea className="w-1/2 border-r border-border">
            <div className="space-y-1 p-2">
              {queue.map((item) => {
                const Icon = contentTypeIcons[item.contentType]
                const timeRemaining = getTimeRemaining(item.slaDeadline)
                const isOverdue = timeRemaining === "OVERDUE"

                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={cn(
                      "p-3 rounded-md cursor-pointer transition-colors",
                      selectedItem?.id === item.id ? "bg-secondary" : "hover:bg-secondary/50",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                      </div>
                      <Badge className={cn("text-xs", severityColors[item.severity])}>{item.severity}</Badge>
                    </div>
                    <p className="text-sm text-foreground mt-1 line-clamp-2">{item.preview}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-muted-foreground">@{item.username}</span>
                      <div
                        className={cn(
                          "flex items-center gap-1 text-xs",
                          isOverdue ? "text-[#ef4444]" : "text-muted-foreground",
                        )}
                      >
                        <Clock className="h-3 w-3" />
                        {timeRemaining}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>

          <div className="w-1/2 p-4">
            {selectedItem ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm text-foreground">{selectedItem.id}</span>
                  <Badge className={cn(severityColors[selectedItem.severity])}>{selectedItem.severity}</Badge>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase">Content Preview</h4>
                  <div className="p-3 bg-secondary rounded-md">
                    <p className="text-sm text-foreground">{selectedItem.preview}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground uppercase mb-1">ML Score</h4>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#ef4444] rounded-full"
                          style={{ width: `${selectedItem.mlScore * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-foreground">
                        {(selectedItem.mlScore * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground uppercase mb-1">User Rep</h4>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#22c55e] rounded-full"
                          style={{ width: `${selectedItem.userReputation}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-foreground">{selectedItem.userReputation}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">Detected Violations</h4>
                  <div className="flex flex-wrap gap-1">
                    {selectedItem.violationTypes.map((v) => (
                      <Badge key={v} variant="outline" className="text-xs border-border text-foreground">
                        {v}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-medium text-muted-foreground uppercase mb-2">User Info</h4>
                  <div className="text-sm text-foreground">
                    <p>Username: @{selectedItem.username}</p>
                    <p>User ID: {selectedItem.userId}</p>
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={() => handleAction(selectedItem.id, "approve")}
                    className="flex-1 bg-[#22c55e] hover:bg-[#16a34a] text-white"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Approve
                  </Button>
                  <Button
                    onClick={() => handleAction(selectedItem.id, "reject")}
                    className="flex-1 bg-[#ef4444] hover:bg-[#dc2626] text-white"
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Reject
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <AlertTriangle className="h-8 w-8 mb-2" />
                <p className="text-sm">Select an item to review</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
