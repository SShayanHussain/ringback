-- Migration 0001 — initial schema. Apply on the Supabase SESSION/direct URL (:5432), which supports
-- the prepared statements DDL needs (PLAYBOOK §12.1). Idempotent (IF NOT EXISTS) so re-runs are safe.
-- Keep this identical to db/schema.sql; both are the source of truth for the tables.

\i schema.sql
-- If your migration runner can't \i, paste db/schema.sql contents here instead.
