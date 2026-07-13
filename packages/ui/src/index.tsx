/**
 * Ringback UI kit (adapted to the Deflekt/P1 conventions).
 * Style-only components — the actual CSS variables + classes live in web/app/globals.css,
 * so there's no cross-package CSS import (keeps the Next transpile simple).
 */
import * as React from "react";

type Div = React.HTMLAttributes<HTMLDivElement>;

export function Logo({ small }: { small?: boolean }) {
  return (
    <span className={`rb-logo${small ? " rb-logo-sm" : ""}`}>
      <span className="rb-logo-dot" aria-hidden />
      Ringback
    </span>
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }
) {
  const { variant = "primary", className = "", ...rest } = props;
  return <button className={`rb-btn rb-btn-${variant} ${className}`} {...rest} />;
}

export function Card({ className = "", ...rest }: Div) {
  return <div className={`rb-card ${className}`} {...rest} />;
}

export function Badge({ tone = "neutral", children }: { tone?: string; children: React.ReactNode }) {
  return <span className={`rb-badge rb-badge-${tone}`}>{children}</span>;
}

export function StatCard({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card className="rb-stat">
      <div className="rb-stat-label">{label}</div>
      <div className="rb-stat-value">{value}</div>
      {hint ? <div className="rb-stat-hint">{hint}</div> : null}
    </Card>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return <input className={`rb-input ${className}`} {...rest} />;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="rb-field">
      <span className="rb-field-label">{label}</span>
      {children}
    </label>
  );
}

/** Maps an agent outcome to a badge tone. */
export function outcomeTone(outcome?: string): string {
  switch (outcome) {
    case "booked":
    case "rescheduled":
      return "good";
    case "answered":
    case "qualified":
      return "info";
    case "escalated":
      return "warn";
    case "cancelled":
      return "muted";
    default:
      return "neutral";
  }
}
