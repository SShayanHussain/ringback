import Link from "next/link";
import { Badge, Card, outcomeTone } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Turn = { role: string; text: string };
type Call = {
  id: string; session_id?: string; intent?: string; outcome?: string; escalated?: boolean;
  escalation_reason?: string; transcript?: Turn[]; actions?: { type: string }[]; cost_usd?: number;
};

export default async function CallDetail({ params }: { params: { id: string } }) {
  let call: Call | null = null;
  let error = "";
  try {
    call = await apiGet<Call>(`/calls/${params.id}`);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load call";
  }

  if (error || !call) {
    return (
      <div>
        <div className="rb-page-title"><h1>Call</h1><Link href="/calls" className="rb-navlink">← Back</Link></div>
        <div className="rb-alert">{error || "Not found"}</div>
      </div>
    );
  }

  return (
    <div>
      <div className="rb-page-title">
        <h1>Call transcript</h1>
        <Link href="/calls" className="rb-navlink">← Back</Link>
      </div>

      <Card>
        <div className="rb-row" style={{ marginBottom: ".8rem" }}>
          <Badge tone={outcomeTone(call.outcome)}>{call.outcome}</Badge>
          {call.intent ? <Badge tone="neutral">intent: {call.intent}</Badge> : null}
          {call.escalated ? <Badge tone="warn">escalated</Badge> : null}
          <Badge tone="muted">cost ${Number(call.cost_usd || 0).toFixed(3)}</Badge>
        </div>
        {call.escalated && call.escalation_reason ? (
          <p className="rb-muted">Escalation reason: {call.escalation_reason}</p>
        ) : null}

        <div className="rb-chat-log" style={{ maxHeight: 420 }}>
          {(call.transcript || []).map((t, i) => (
            <div key={i} className={`rb-msg ${t.role === "user" ? "rb-msg-user" : "rb-msg-agent"}`}>
              {t.text}
            </div>
          ))}
        </div>
      </Card>

      <Card className="rb-mt">
        <h3>Actions taken</h3>
        {call.actions && call.actions.length ? (
          <ul>{call.actions.map((a, i) => <li key={i}>{a.type}</li>)}</ul>
        ) : (
          <p className="rb-muted">No state-changing actions.</p>
        )}
      </Card>
    </div>
  );
}
