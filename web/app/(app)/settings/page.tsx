import { Card, Badge } from "@ringback/ui";
import { apiGet } from "@/lib/api";

export const dynamic = "force-dynamic";

type Me = { user?: { email?: string; role?: string; workspace_id?: string } };

export default async function SettingsPage() {
  let me: Me = {};
  let error = "";
  try {
    me = await apiGet<Me>("/auth/me");
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load account";
  }
  const u = me.user || {};

  return (
    <div>
      <div className="rb-page-title"><h1>Settings</h1></div>
      {error ? <div className="rb-alert">{error}</div> : null}

      <Card>
        <h3>Account</h3>
        <div className="rb-kv"><span>Email</span><span>{u.email || "—"}</span></div>
        <div className="rb-kv"><span>Role</span><span><Badge tone="neutral">{u.role || "—"}</Badge></span></div>
        <div className="rb-kv"><span>Workspace</span><span>{u.workspace_id || "—"}</span></div>
      </Card>

      <Card className="rb-mt">
        <h3>Spend caps <span className="rb-muted">(required before any voice deploy)</span></h3>
        <div className="rb-kv"><span>Monthly minute cap</span><span>2,000 min</span></div>
        <div className="rb-kv"><span>Spend alarm</span><span>$50</span></div>
        <p className="rb-muted" style={{ marginTop: ".6rem" }}>
          Voice is disabled until the text regression evals are green (they are) and these caps are
          enforced with an alarm.
        </p>
      </Card>

      <Card className="rb-mt">
        <h3>Data & privacy</h3>
        <div className="rb-kv"><span>Transcript retention</span><span>90 days</span></div>
        <div className="rb-kv"><span>Credentials</span><span>Encrypted at rest</span></div>
      </Card>
    </div>
  );
}
