import { NextResponse } from "next/server"

export async function GET() {
  try {
    // Query PostgreSQL for recent real-time decisions
    const realtimeData = await fetch(`${process.env.DATABASE_API_URL}/realtime/recent`, { cache: "no-store" }).then(
      (res) => res.json(),
    )

    return NextResponse.json(realtimeData)
  } catch (error) {
    console.error("[v0] Error fetching realtime data:", error)
    return NextResponse.json({ error: "Failed to fetch realtime data" }, { status: 500 })
  }
}
