-- ============================================================
-- NeuralGuard MVP — Supabase Schema
-- Run this in your Supabase project's SQL Editor
-- ============================================================

-- ─── API Keys ────────────────────────────────────────────────
create table if not exists api_keys (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade not null,
  key_hash    text not null unique,
  label       text default 'Default Key',
  is_active   boolean default true,
  created_at  timestamptz default now(),
  revoked_at  timestamptz
);

create index if not exists api_keys_hash_idx   on api_keys(key_hash);
create index if not exists api_keys_user_idx   on api_keys(user_id);

-- ─── Query Logs ──────────────────────────────────────────────
create table if not exists query_logs (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid references auth.users(id) on delete set null,
  model_requested  text,
  model_used       text,
  prompt_snippet   text,
  token_usage      integer default 0,
  cost_usd         numeric(12, 8) default 0,
  cost_saved_usd   numeric(12, 8) default 0,
  cache_hit        boolean default false,
  latency_ms       numeric(10, 2),
  trust_score      integer,           -- 0-100, nullable until trust engine runs
  trust_details    jsonb,             -- per-claim JSON from trust engine
  created_at       timestamptz default now()
);

create index if not exists query_logs_user_idx    on query_logs(user_id);
create index if not exists query_logs_created_idx on query_logs(created_at desc);

-- ─── Row-Level Security ──────────────────────────────────────
alter table api_keys   enable row level security;
alter table query_logs enable row level security;

-- Service-role key bypasses RLS automatically.
-- These policies are for the dashboard's anon/authenticated clients:

-- Users can read their own keys
drop policy if exists "users_read_own_keys"   on api_keys;
create policy "users_read_own_keys"
  on api_keys for select
  using (auth.uid() = user_id);

-- Users can read their own logs
drop policy if exists "users_read_own_logs"   on query_logs;
create policy "users_read_own_logs"
  on query_logs for select
  using (auth.uid() = user_id);
