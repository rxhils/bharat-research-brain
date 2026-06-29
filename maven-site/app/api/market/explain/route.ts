import { NextResponse } from "next/server";
import { getSnapshot } from "@/lib/market";
import { deepseekExplain } from "@/lib/deepseek";

export const dynamic = "force-dynamic";

// AI "why the market moved": live reasons from DeepSeek over the current snapshot
// when a key is set; otherwise available:false so the UI shows an honest placeholder.
export async function GET() {
  const snap = await getSnapshot();
  const reasons = await deepseekExplain(snap);
  return NextResponse.json({ available: !!reasons && reasons.length > 0, reasons: reasons ?? [], live: snap.live });
}