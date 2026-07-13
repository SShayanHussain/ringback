import Link from "next/link";
import { Button, Card, Logo } from "@ringback/ui";

const PLANS = [
  { name: "Trial", price: "$0", tag: "Test number, limited minutes", features: ["Text playground (free)", "1 test workflow", "Community support"] },
  { name: "Pro", price: "$79/mo", tag: "One real number", features: ["Monthly minute bundle", "Calendar + CRM", "Call log + transcripts", "Spend cap + alarm"], highlight: true },
  { name: "Team", price: "$199/mo", tag: "Multiple numbers/locations", features: ["Everything in Pro", "Multiple numbers", "Roles & members", "Priority support"] },
];

export default function Pricing() {
  return (
    <div className="rb-container">
      <nav className="rb-nav-top">
        <Link href="/"><Logo /></Link>
        <Link href="/signup"><Button>Get started</Button></Link>
      </nav>
      <header className="rb-hero" style={{ paddingBottom: "1rem" }}>
        <h1>Simple pricing. Minutes are gated.</h1>
        <p>Minutes cost real money, so plans gate minutes, numbers, and integrations. Start in text for free.</p>
      </header>
      <section className="rb-grid-3">
        {PLANS.map((p) => (
          <Card key={p.name} style={p.highlight ? { borderColor: "var(--brand)" } : undefined}>
            <h3>{p.name}</h3>
            <div style={{ fontSize: "1.8rem", fontWeight: 800 }}>{p.price}</div>
            <p className="rb-muted">{p.tag}</p>
            <ul style={{ paddingLeft: "1.1rem", margin: ".5rem 0 1rem" }}>
              {p.features.map((f) => <li key={f}>{f}</li>)}
            </ul>
            <Link href="/signup"><Button variant={p.highlight ? "primary" : "ghost"}>Choose {p.name}</Button></Link>
          </Card>
        ))}
      </section>
    </div>
  );
}
