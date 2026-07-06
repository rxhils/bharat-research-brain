import { NextResponse } from "next/server";
import { getIndexPerformance, getSectorPerformance } from "@/lib/maven/dataTools";

// Lightweight, read-only market snapshot for the chat-page ticker. Reuses the same
// Yahoo-Finance-backed, TTL-cached functions the research pipeline already calls -
// no new data source, no new fetch cost beyond what dataTools.ts already caches.
export const dynamic = "force-dynamic";

export async function GET() {
  const [indices, sectors] = await Promise.all([getIndexPerformance(), getSectorPerformance()]);
  return NextResponse.json({ indices, sectors, asOf: new Date().toISOString() });
}
