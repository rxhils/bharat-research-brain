import { NextResponse } from "next/server";
import { getAgentBoard } from "@/lib/data";

// Polled by the Agent Activity board every ~4s. force-dynamic so each poll is fresh
// (the mock board is time-driven; the real one reads agent_run_log live).
export const dynamic = "force-dynamic";

export async function GET() {
  const board = await getAgentBoard();
  return NextResponse.json(board, { headers: { "Cache-Control": "no-store" } });
}
