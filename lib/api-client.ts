/**
 * API client for fetching data from backend
 */

export async function fetchMetrics() {
  const response = await fetch("/api/metrics", { cache: "no-store" })
  if (!response.ok) throw new Error("Failed to fetch metrics")
  return response.json()
}

export async function fetchQueue(priority?: string) {
  const url = priority ? `/api/queue?priority=${priority}` : "/api/queue"
  const response = await fetch(url, { cache: "no-store" })
  if (!response.ok) throw new Error("Failed to fetch queue")
  return response.json()
}

export async function fetchRealtimeData() {
  const response = await fetch("/api/realtime", { cache: "no-store" })
  if (!response.ok) throw new Error("Failed to fetch realtime data")
  return response.json()
}
