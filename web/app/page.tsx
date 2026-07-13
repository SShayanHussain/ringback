import Link from "next/link";
import { Button, Card, Logo } from "@ringback/ui";
import { isAuthed } from "@/lib/session";

export default function Landing() {
  const authed = isAuthed();
  return (
    <div className="rb-container">
      <nav className="rb-nav-top">
        <Logo />
        <div className="rb-row">
          <Link href="/pricing" className="rb-navlink">Pricing</Link>
          {authed ? (
            <Link href="/dashboard"><Button variant="ghost">Dashboard</Button></Link>
          ) : (
            <>
              <Link href="/login"><Button variant="ghost">Log in</Button></Link>
              <Link href="/signup"><Button>Get started</Button></Link>
            </>
          )}
        </div>
      </nav>

      <header className="rb-hero">
        <h1>Never miss a call, never miss a booking.</h1>
        <p>
          Ringback answers your business phone 24/7, books and reschedules appointments in natural
          conversation, updates your calendar and CRM, and hands off to a human when it should.
        </p>
        <div className="rb-row rb-mt">
          <Link href="/signup"><Button>Start free</Button></Link>
          <Link href="/playground"><Button variant="ghost">Try it in text (free)</Button></Link>
        </div>
        <p className="rb-muted" style={{ marginTop: "1rem", fontSize: ".9rem" }}>
          Built <strong>text-first</strong> — the whole booking brain is proven in chat before a single
          voice minute is spent.
        </p>
      </header>

      <section className="rb-grid-3 rb-mt">
        {[
          ["Answers every call", "24/7 coverage for clinics, home services, and small businesses — a missed call is lost revenue."],
          ["Takes real action", "Checks live availability and books, reschedules, or cancels — writing straight to your calendar and CRM."],
          ["Knows its limits", "Confirms before every booking, never invents a time slot, and warm-transfers anything risky to a human."],
        ].map(([t, d]) => (
          <Card key={t}>
            <h3>{t}</h3>
            <p className="rb-muted" style={{ margin: 0 }}>{d}</p>
          </Card>
        ))}
      </section>

      <section className="rb-mt" style={{ padding: "2rem 0 4rem" }}>
        <Card>
          <h3>The signature screen: the call view</h3>
          <p className="rb-muted">
            Every call is logged — live transcript, detected intent, the action it took (with the
            booking that landed), the outcome, and per-call cost. See it in the{" "}
            <Link href="/dashboard" style={{ color: "var(--brand)" }}>dashboard</Link>.
          </p>
        </Card>
      </section>
    </div>
  );
}
