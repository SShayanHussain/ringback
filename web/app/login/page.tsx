import Link from "next/link";
import { Button, Card, Field, Input, Logo } from "@ringback/ui";
import { loginAction } from "@/app/auth/actions";

export default function LoginPage({ searchParams }: { searchParams: { error?: string } }) {
  return (
    <div className="rb-container" style={{ maxWidth: 440, paddingTop: "3rem" }}>
      <Link href="/"><Logo /></Link>
      <Card className="rb-mt">
        <h2>Log in</h2>
        {searchParams.error ? <div className="rb-alert">{searchParams.error}</div> : null}
        <form action={loginAction}>
          <Field label="Email"><Input name="email" type="email" required autoComplete="email" /></Field>
          <Field label="Password"><Input name="password" type="password" required autoComplete="current-password" /></Field>
          <Button type="submit">Log in</Button>
        </form>
        <p className="rb-muted rb-mt">No account? <Link href="/signup" style={{ color: "var(--brand)" }}>Sign up</Link></p>
      </Card>
    </div>
  );
}
