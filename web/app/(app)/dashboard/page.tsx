import Link from "next/link";
import { Badge, Card, StatCard, outcomeTone } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Call = { id: string; session_id?: string; intent?: string; outcome?: string; escalated?: boolean };

export default async function Dashboard() {
  let calls: Call[] = [];
  let error = "";
  try {
    calls = await apiGet<Call[]>("/calls");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load calls";
  }

  const booked = calls.filter((c) => c.outcome === "booked" || c.outcome === "rescheduled").length;
  const answered = calls.filter((c) => c.outcome === "answered").length;
  const escalated = calls.filter((c) => c.escalated).length;

  return (
    <div>
      <div className="rb-page-title"><h1>Dashboard</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}

      <div className="rb-grid-4">
        <StatCard label="Calls" value={calls.length} hint="all channels" />
        <StatCard label="Bookings made" value={booked} hint="booked + rescheduled" />
        <StatCard label="Questions answered" value={answered} />
        <StatCard label="Escalations" value={escalated} hint="handed to a human" />
      </div>

      <Card className="rb-mt">
        <h3>Recent calls</h3>
        {calls.length === 0 ? (
          <div className="rb-empty">
            No calls yet. Try the <Link href="/playground" style={{ color: "var(--brand)" }}>text playground</Link> — it&apos;s free.
          </div>
        ) : (
          <div className="rb-scroll">
            <table className="rb-table">
              <thead><tr><th>Session</th><th>Intent</th><th>Outcome</th><th></th></tr></thead>
              <tbody>
                {calls.slice(0, 6).map((c) => (
                  <tr key={c.id}>
                    <td>{c.session_id || c.id}</td>
                    <td>{c.intent || "—"}</td>
                    <td><Badge tone={outcomeTone(c.outcome)}>{c.outcome}</Badge></td>
                    <td><Link href={`/calls/${c.id}`} style={{ color: "var(--brand)" }}>View</Link></td>
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
