// Server-side config. Validate the one thing we truly need, fail fast with a named message.
export const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL || "http://localhost:8000";

export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
