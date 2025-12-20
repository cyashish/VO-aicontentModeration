"use client"

import { useState, useEffect } from "react"
import { NavSidebar } from "@/components/dashboard/nav-sidebar"
import { MetricCard } from "@/components/dashboard/metric-card"
import { ThroughputChart } from "@/components/dashboard/throughput-chart"
import { ViolationChart } from "@/components/dashboard/violation-chart"
import { ModerationQueue } from "@/components/dashboard/moderation-queue"
import { RealtimePanel } from "@/components/dashboard/realtime-panel"
import { SLAGauge } from "@/components/dashboard/sla-gauge"
import { fetchMetrics } from "@/lib/api-client"
import { Activity, CheckCircle, XCircle, Clock, Zap, Target } from "lucide-react"

type DashboardMetrics = {
  totalProcessed: number
  approvedCount: number
  rejectedCount: number
  pendingReview: number
  avgLatencyMs: number
  throughputPerSec: number
  slaCompliance: number
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("overview")
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const data = (await fetchMetrics()) as DashboardMetrics
        if (!cancelled) setMetrics(data)
      } catch (e) {
        console.error("Failed to load metrics", e)
      }
    }

    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  if (!metrics) return <div className="flex h-screen items-center justify-center bg-background">Loading...</div>

  return (
    <div className="flex h-screen bg-background">
      <NavSidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 overflow-auto">
        <header className="border-b border-border px-6 py-4">
          <h1 className="text-xl font-semibold text-foreground">AI Content Moderation</h1>
          <p className="text-sm text-muted-foreground">Real-time monitoring and analytics</p>
        </header>

        <main className="p-6">
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* KPI Cards */}
              <div className="grid grid-cols-6 gap-4">
                <MetricCard
                  title="Total Processed"
                  value={metrics.totalProcessed.toLocaleString()}
                  subtitle="Last 24h"
                  trend="up"
                  trendValue="+12.5%"
                  icon={<Activity className="h-4 w-4" />}
                />
                <MetricCard
                  title="Approved"
                  value={metrics.approvedCount.toLocaleString()}
                  subtitle={`${((metrics.approvedCount / metrics.totalProcessed) * 100).toFixed(1)}% rate`}
                  variant="success"
                  icon={<CheckCircle className="h-4 w-4" />}
                />
                <MetricCard
                  title="Rejected"
                  value={metrics.rejectedCount.toLocaleString()}
                  subtitle={`${((metrics.rejectedCount / metrics.totalProcessed) * 100).toFixed(1)}% rate`}
                  variant="critical"
                  icon={<XCircle className="h-4 w-4" />}
                />
                <MetricCard
                  title="Pending Review"
                  value={metrics.pendingReview}
                  subtitle="In queue"
                  variant="warning"
                  icon={<Clock className="h-4 w-4" />}
                />
                <MetricCard
                  title="Avg Latency"
                  value={`${metrics.avgLatencyMs}ms`}
                  subtitle="P50"
                  trend="down"
                  trendValue="-8%"
                  icon={<Zap className="h-4 w-4" />}
                />
                <MetricCard
                  title="Throughput"
                  value={`${metrics.throughputPerSec}/s`}
                  subtitle="Requests"
                  trend="up"
                  trendValue="+5%"
                  icon={<Target className="h-4 w-4" />}
                />
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-3 gap-4">
                <ThroughputChart />
                <ViolationChart />
              </div>

              {/* SLA Gauges */}
              <div className="grid grid-cols-4 gap-4">
                <SLAGauge value={metrics.slaCompliance} label="Overall SLA" target={95} />
                <SLAGauge value={98.2} label="Critical (5min)" target={99} />
                <SLAGauge value={96.5} label="High (15min)" target={95} />
                <SLAGauge value={94.1} label="Medium (1h)" target={90} />
              </div>
            </div>
          )}

          {activeTab === "queue" && <ModerationQueue />}

          {activeTab === "analytics" && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <ThroughputChart />
                <ViolationChart />
              </div>
              <div className="grid grid-cols-4 gap-4">
                <SLAGauge value={metrics.slaCompliance} label="Overall SLA" target={95} />
                <SLAGauge value={98.2} label="Critical (5min)" target={99} />
                <SLAGauge value={96.5} label="High (15min)" target={95} />
                <SLAGauge value={94.1} label="Medium (1h)" target={90} />
              </div>
            </div>
          )}

          {activeTab === "realtime" && (
            <div className="grid grid-cols-2 gap-6">
              <RealtimePanel />
              <div className="space-y-4">
                <MetricCard
                  title="Active Channels"
                  value="2,847"
                  subtitle="Monitored"
                  icon={<Activity className="h-4 w-4" />}
                />
                <MetricCard
                  title="P99 Latency"
                  value="8.2ms"
                  subtitle="Target: <10ms"
                  variant="success"
                  icon={<Zap className="h-4 w-4" />}
                />
                <MetricCard
                  title="Block Rate"
                  value="2.1%"
                  subtitle="Last hour"
                  variant="warning"
                  icon={<XCircle className="h-4 w-4" />}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
