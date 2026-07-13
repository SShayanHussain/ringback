import { Card, Badge } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Service = { id: string; name: string; duration_min: number; price: string };
type Config = {
  defaults?: { business_name?: string; services?: Service[]; business_hours?: Record<string, string[]>; transfer_number?: string };
  overrides?: Record<string, unknown>;
};

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export default async function ConfigurationPage() {
  let cfg: Config = {};
  let error = "";
  try {
    cfg = await apiGet<Config>("/config");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load configuration";
  }
  const d = cfg.defaults || {};

  return (
    <div>
      <div className="rb-page-title"><h1>Configuration</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}
      <p className="rb-muted">
        These are the facts the agent is allowed to state — hours, services, prices, escalation.
        They come from the active vertical and are never improvised. Edit-in-place lands next.
      </p>

      <Card className="rb-mt">
        <h3>Services {d.business_name ? <span className="rb-muted">· {d.business_name}</span> : null}</h3>
        <div className="rb-scroll">
          <table className="rb-table">
            <thead><tr><th>Service</th><th>Duration</th><th>Price</th></tr></thead>
            <tbody>
              {(d.services || []).map((s) => (
                <tr key={s.id}><td>{s.name}</td><td>{s.duration_min} min</td><td>{s.price}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="rb-mt">
        <h3>Business hours</h3>
        <div className="rb-list">
          {DAYS.map((day) => {
            const h = d.business_hours?.[day];
            return (
              <div key={day} className="rb-kv">
                <span style={{ textTransform: "capitalize" }}>{day}</span>
                <span>{h && h.length ? `${h[0]} – ${h[1]}` : "Closed"}</span>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="rb-mt">
        <h3>Escalation</h3>
        <p>Warm transfer to <Badge tone="neutral">{d.transfer_number || "—"}</Badge> on high-risk requests, frustration, or repeated misunderstanding.</p>
      </Card>
    </div>
  );
}
