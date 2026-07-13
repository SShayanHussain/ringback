import Link from "next/link";
import { Button, Card, Field, Input, Logo } from "@ringback/ui";
import { signupAction } from "@/app/auth/actions";

export default function SignupPage({ searchParams }: { searchParams: { error?: string } }) {
  return (
    <div className="rb-container" style={{ maxWidth: 440, paddingTop: "3rem" }}>
      <Link href="/"><Logo /></Link>
      <Card className="rb-mt">
        <h2>Create your workspace</h2>
        {searchParams.error ? <div className="rb-alert">{searchParams.error}</div> : null}
        <form action={signupAction}>
          <Field label="Business name"><Input name="workspace_name" placeholder="Ace Plumbing" /></Field>
          <Field label="Email"><Input name="email" type="email" required autoComplete="email" /></Field>
          <Field label="Password (8+ chars)"><Input name="password" type="password" required minLength={8} autoComplete="new-password" /></Field>
          <Button type="submit">Get started</Button>
        </form>
        <p className="rb-muted rb-mt">Already have an account? <Link href="/login" style={{ color: "var(--brand)" }}>Log in</Link></p>
      </Card>
    </div>
  );
}
