import { NextRequest, NextResponse } from "next/server";
import { getRun } from "@/lib/runs-registry";
import { SELECTED_RUN_COOKIE } from "@/lib/selected-run";

// Sets the dashboard-wide selected run. Called from the Database tab; every
// Data Analysis tab reads this cookie server-side via lib/selected-run.ts.
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const runId = body?.runId;

  if (typeof runId !== "string" || !runId) {
    return NextResponse.json({ error: "runId is required" }, { status: 400 });
  }

  const run = getRun(runId);
  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }

  const res = NextResponse.json({ ok: true, run });
  res.cookies.set(SELECTED_RUN_COOKIE, runId, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  return res;
}
