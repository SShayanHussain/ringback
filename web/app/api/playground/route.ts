import { NextResponse } from "next/server";
import { apiPost } from "@/lib/api";

// Server route: reads the httpOnly cookie (via apiPost) and forwards to the orchestrator, so the
// access token never touches the client (Server→Client boundary, PLAYBOOK §6).
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  try {
    const data = await apiPost<{ reply: string; meta: unknown; state: unknown }>(
      "/playground/chat",
      { message: body.message, session_id: body.session_id || "web", state: body.state ?? null }
    );
    return NextResponse.json(data);
  } catch (e) {
    const message = e instanceof Error ? e.message : "playground error";
    return NextResponse.json({ error: { message } }, { status: 502 });
  }
}
