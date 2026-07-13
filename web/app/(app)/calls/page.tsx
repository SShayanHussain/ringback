import Link from "next/link";
import { Badge, Card, outcomeTone } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Call = { id: string; session_id?: string; intent?: string; outcome?: string; escalated?: boolean; channel?: string };

export default async function CallsPage() {
  let calls: Call[] = [];
  let error = "";
  try {
    calls = await apiGet<Call[]>("/calls");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load calls";
  }

  return (
    <div>
      <div className="rb-page-title"><h1>Calls</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}
      <Card>
        {calls.length === 0 ? (
          <div className="rb-empty">No calls logged yet.</div>
        ) : (
          <div className="rb-scroll">
            <table className="rb-table">
              <thead><tr><th>Session</th><th>Channel</th><th>Intent</th><th>Outcome</th><th></th></tr></thead>
              <tbody>
                {calls.map((c) => (
                  <tr key={c.id}>
                    <td>{c.session_id || c.id}</td>
                    <td>{c.channel || "text"}</td>
                    <td>{c.intent || "—"}</td>
                    <td><Badge tone={outcomeTone(c.outcome)}>{c.outcome}</Badge></td>
                    <td><Link href={`/calls/${c.id}`} style={{ color: "var(--brand)" }}>Transcript</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
