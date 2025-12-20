import { NextResponse } from "next/server"

export async function GET() {
  try {
    const baseUrl = process.env.DATABASE_API_URL ?? "http://localhost:8000"
    // Query PostgreSQL for recent real-time decisions
    const realtimeData = await fetch(`${baseUrl}/realtime/recent`, { cache: "no-store" }).then(
      (res) => res.json(),
    )

    return NextResponse.json(realtimeData)
  } catch (error) {
    console.error("[v0] Error fetching realtime data:", error)
    return NextResponse.json({ error: "Failed to fetch realtime data" }, { status: 500 })
  }
}
