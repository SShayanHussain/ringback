import { Card, Badge } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Integration = { provider: string; connected: boolean };

const CATALOG = [
  { provider: "google_calendar", label: "Google Calendar", desc: "Read availability and write bookings." },
  { provider: "outlook_calendar", label: "Outlook Calendar", desc: "Read availability and write bookings." },
  { provider: "crm", label: "CRM", desc: "Capture leads and log every interaction." },
];

export default async function IntegrationsPage() {
  let connected: Integration[] = [];
  let error = "";
  try {
    connected = await apiGet<Integration[]>("/integrations");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load integrations";
  }
  const isConnected = (p: string) => connected.some((c) => c.provider === p);

  return (
    <div>
      <div className="rb-page-title"><h1>Integrations</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}
      <p className="rb-muted">
        Calendar + CRM connections. Credentials are <strong>encrypted at rest</strong>. OAuth connect
        flows land in Phase 2 — or route these through your n8n workflow (see the automation guide).
      </p>
      <div className="rb-grid-3 rb-mt">
        {CATALOG.map((c) => (
          <Card key={c.provider}>
            <h3>{c.label}</h3>
            <p className="rb-muted">{c.desc}</p>
            {isConnected(c.provider) ? (
              <Badge tone="good">Connected</Badge>
            ) : (
              <Badge tone="muted">Not connected</Badge>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
