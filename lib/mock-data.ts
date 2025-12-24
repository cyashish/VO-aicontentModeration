// This provides real-time mock data for the dashboard until database integration is live

export interface ModerationMetrics {
  timestamp: number
  throughput: number
  latency: number
  approvalRate: number
  rejectionRate: number
}

export interface QueueItem {
  id: string
  content: string
  type: "text" | "image" | "profile"
  priority: "high" | "medium" | "low"
  timeInQueue: number
  user: string
  scores: {
    toxicity: number
    spam: number
    hateSpeech: number
  }
}

export interface RealtimeChatMetric {
  timestamp: number
  messageCount: number
  blockedCount: number
  latency: number
  burstDetected: boolean
}

export interface ViolationBreakdown {
  type: string
  count: number
  percentage: number
  color: string
}

export interface TimeSeries {
  time: string
  value: number
}

// Generate mock hourly metrics for the overview dashboard
export function generateMockMetrics(): {
  totalProcessed: number
  approvedCount: number
  rejectedCount: number
  pendingReview: number
  avgLatencyMs: number
  throughputPerSec: number
  slaCompliance: number
} {
  return {
    totalProcessed: Math.floor(Math.random() * 10000) + 5000,
    approvedCount: Math.floor(Math.random() * 7000) + 3500,
    rejectedCount: Math.floor(Math.random() * 2000) + 800,
    pendingReview: Math.floor(Math.random() * 500) + 50,
    avgLatencyMs: Math.floor(Math.random() * 300) + 50,
    throughputPerSec: Math.floor(Math.random() * 500) + 100,
    slaCompliance: 92 + Math.random() * 7,
  }
}

// Generate mock review queue items
export function generateMockQueue(): QueueItem[] {
  const contents = [
    "This is totally unfair and I hate this",
    "BUY NOW at spamsite.com!!!",
    "Check out my profile for more",
    "This user violated community guidelines",
    "Inappropriate profile picture detected",
  ]

  const users = ["user_123", "user_456", "user_789", "user_012", "user_345"]
  const types: Array<"text" | "image" | "profile"> = ["text", "image", "profile"]
  const priorities: Array<"high" | "medium" | "low"> = ["high", "medium", "low"]

  return Array.from({ length: 15 }, (_, i) => ({
    id: `queue_${i}`,
    content: contents[Math.floor(Math.random() * contents.length)],
    type: types[Math.floor(Math.random() * types.length)],
    priority: priorities[Math.floor(Math.random() * priorities.length)],
    timeInQueue: Math.floor(Math.random() * 3600),
    user: users[Math.floor(Math.random() * users.length)],
    scores: {
      toxicity: Math.random(),
      spam: Math.random(),
      hateSpeech: Math.random(),
    },
  }))
}

// Generate mock real-time chat metrics
export function generateRealtimeChatMetrics(): RealtimeChatMetric[] {
  const now = Date.now()
  const metrics: RealtimeChatMetric[] = []

  for (let i = 59; i >= 0; i--) {
    metrics.push({
      timestamp: now - i * 1000,
      messageCount: Math.floor(Math.random() * 100) + 50,
      blockedCount: Math.floor(Math.random() * 10) + 2,
      latency: Math.floor(Math.random() * 8) + 2,
      burstDetected: Math.random() > 0.9,
    })
  }

  return metrics
}

// Generate mock time series data for throughput/latency charts
export function generateTimeSeries(
  dataPoints = 24,
  maxValue = 500,
  minValue = 200,
): Array<{ timestamp: Date; value: number }> {
  const now = new Date()
  const data: Array<{ timestamp: Date; value: number }> = []
  const interval = (30 * 60 * 1000) / dataPoints // 30 minutes divided by data points

  for (let i = dataPoints - 1; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * interval)
    data.push({
      timestamp,
      value: Math.floor(Math.random() * (maxValue - minValue + 1)) + minValue,
    })
  }

  return data
}

// Generate mock violation breakdown data
export function generateViolationBreakdown(): ViolationBreakdown[] {
  const violations = [
    { type: "Hate Speech", percentage: 25, color: "#ef4444" },
    { type: "Spam", percentage: 35, color: "#f97316" },
    { type: "Toxicity", percentage: 20, color: "#eab308" },
    { type: "Profanity", percentage: 12, color: "#3b82f6" },
    { type: "Other", percentage: 8, color: "#8b5cf6" },
  ]

  return violations.map((v) => ({
    ...v,
    count: Math.floor(Math.random() * 500) + 100,
  }))
}
