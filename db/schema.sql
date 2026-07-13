-- Ringback schema. Mounted into the LOCAL postgres container on first boot (docker-compose).
-- For Supabase this is applied as migration 0001 on the SESSION/direct URL (:5432) — a mounted
-- init.sql does NOT run against a managed DB (PLAYBOOK §2). Every tenant table carries workspace_id.

CREATE TABLE IF NOT EXISTS workspaces (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'owner',   -- owner | member
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_workspace ON users(workspace_id);

CREATE TABLE IF NOT EXISTS calls (
  id            TEXT PRIMARY KEY,
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  channel       TEXT NOT NULL DEFAULT 'text',     -- text | voice
  intent        TEXT,
  outcome       TEXT,
  escalated     BOOLEAN NOT NULL DEFAULT false,
  payload       JSONB NOT NULL,                   -- full CallLog (transcript, actions, cost, latency)
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_calls_workspace ON calls(workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS configs (
  workspace_id  TEXT PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
  data          JSONB NOT NULL DEFAULT '{}',
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Integration credentials are stored ENCRYPTED (Fernet). enc_blob is ciphertext, never plaintext.
CREATE TABLE IF NOT EXISTS integrations (
  workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  provider      TEXT NOT NULL,                    -- google_calendar | outlook_calendar | crm
  enc_blob      TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, provider)
);
