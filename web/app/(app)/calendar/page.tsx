import { Card } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Action = { type: string; start_iso?: string; service_id?: string; booking_id?: string };
type Call = { id: string; actions?: Action[]; session_id?: string };

function pretty(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default async function CalendarPage() {
  let calls: Call[] = [];
  let error = "";
  try {
    calls = await apiGet<Call[]>("/calls");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load bookings";
  }

  const bookings = calls.flatMap((c) =>
    (c.actions || [])
      .filter((a) => a.type === "booking_created" && a.start_iso)
      .map((a) => ({ ...a, session: c.session_id || c.id }))
  ).sort((a, b) => String(a.start_iso).localeCompare(String(b.start_iso)));

  return (
    <div>
      <div className="rb-page-title"><h1>Calendar</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}
      <Card>
        <h3>Bookings the agent made</h3>
        {bookings.length === 0 ? (
          <div className="rb-empty">No agent-made bookings yet. The first one is the activation moment.</div>
        ) : (
          <div className="rb-list">
            {bookings.map((b, i) => (
              <div key={i} className="rb-kv">
                <span><strong>{b.service_id}</strong> — {b.session}</span>
                <span>{pretty(b.start_iso as string)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
