# web/ — Ringback SaaS shell (Next.js App Router)

Reuses the Deflekt/P1 conventions: JWT auth via **Server Actions** (tokens in httpOnly cookies),
reads via Server Components, interactive bits isolated into `"use client"` components, and a
defensive API client (`lib/api.ts`) that never crashes on a non-JSON error body.

> The Deflekt repo wasn't available in this workspace, so this is a clean-equivalent shell built to
> the same rules — not a literal copy.

## Run

```bash
npm install                 # from repo root (workspaces)
npm run dev --workspace web  # http://localhost:3000  (needs the orchestrator on ORCHESTRATOR_URL)
npm run build --workspace web
```

Env: `ORCHESTRATOR_URL` (server-side, to the API), `NEXT_PUBLIC_APP_URL`.

## Surfaces (PRD §0b)

Public: landing · pricing · login · signup. App shell: **dashboard**, **calls** + transcript view
(net-new), **calendar** of agent bookings (net-new), **playground** (text, free — net-new),
configuration, integrations, settings.

The playground posts to `/api/playground` (a server route) so the access token stays server-side.
