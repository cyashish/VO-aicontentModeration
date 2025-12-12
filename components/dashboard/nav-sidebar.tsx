"use client"

import { cn } from "@/lib/utils"
import { LayoutDashboard, ListTodo, BarChart3, Settings, Shield, Activity } from "lucide-react"

interface NavSidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "queue", label: "Review Queue", icon: ListTodo },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "realtime", label: "Real-time", icon: Activity },
]

export function NavSidebar({ activeTab, onTabChange }: NavSidebarProps) {
  return (
    <div className="w-16 bg-card border-r border-border flex flex-col items-center py-4 gap-2">
      <div className="p-2 mb-4">
        <Shield className="h-8 w-8 text-primary" />
      </div>

      {navItems.map((item) => {
        const Icon = item.icon
        return (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={cn(
              "p-3 rounded-md transition-colors",
              activeTab === item.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
            title={item.label}
          >
            <Icon className="h-5 w-5" />
          </button>
        )
      })}

      <div className="mt-auto">
        <button
          className="p-3 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title="Settings"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
