import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const priority = searchParams.get("priority")
    const limit = searchParams.get("limit") || "50"

    // Query PostgreSQL for review queue
    const queue = await fetch(`${process.env.DATABASE_API_URL}/queue?priority=${priority}&limit=${limit}`, {
      cache: "no-store",
    }).then((res) => res.json())

    return NextResponse.json(queue)
  } catch (error) {
    console.error("[v0] Error fetching queue:", error)
    return NextResponse.json({ error: "Failed to fetch queue" }, { status: 500 })
  }
}
