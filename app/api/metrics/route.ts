import { NextResponse } from "next/server"

export async function GET() {
  try {
    const baseUrl = process.env.DATABASE_API_URL ?? "http://localhost:8000"
    // Query PostgreSQL for hourly metrics
    const metrics = await fetch(`${baseUrl}/metrics/hourly`, {
      cache: "no-store",
    }).then((res) => res.json())

    return NextResponse.json(metrics)
  } catch (error) {
    console.error("[v0] Error fetching metrics:", error)
    return NextResponse.json({ error: "Failed to fetch metrics" }, { status: 500 })
  }
}
