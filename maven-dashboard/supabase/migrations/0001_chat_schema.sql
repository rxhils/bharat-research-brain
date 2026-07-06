-- Maven chat backend — per-user isolated chat history + usage metering.
-- Every table is RLS-enforced owner-only: the browser talks to Supabase with the
-- publishable (anon) key and a user JWT; Postgres row-level security is the actual
-- authorization boundary. There is no service-role usage anywhere in the app.

-- ============================================================
-- profiles: one row per auth user, auto-created on signup
-- ============================================================
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
revoke all on table public.profiles from anon;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select to authenticated using (id = (select auth.uid()));

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- Auto-create the profile row when a user signs up. SECURITY DEFINER because the
-- trigger fires as the auth admin, and search_path is pinned to '' so the function
-- cannot be hijacked via a malicious schema.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================
-- conversations: one row per chat thread, owned by exactly one user
-- ============================================================
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.conversations enable row level security;
revoke all on table public.conversations from anon;

create index if not exists conversations_user_recent_idx
  on public.conversations (user_id, updated_at desc);

drop policy if exists "conversations_select_own" on public.conversations;
create policy "conversations_select_own" on public.conversations
  for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "conversations_insert_own" on public.conversations;
create policy "conversations_insert_own" on public.conversations
  for insert to authenticated with check (user_id = (select auth.uid()));

drop policy if exists "conversations_update_own" on public.conversations;
create policy "conversations_update_own" on public.conversations
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

drop policy if exists "conversations_delete_own" on public.conversations;
create policy "conversations_delete_own" on public.conversations
  for delete to authenticated using (user_id = (select auth.uid()));

-- ============================================================
-- messages: chat turns; answer JSONB holds the Maven answer card (charts stripped
-- client-side to keep rows small). client_msg_id is the in-conversation ordinal the
-- UI already uses, kept unique per conversation so retries can't duplicate a turn.
-- ============================================================
create table if not exists public.messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  client_msg_id bigint not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null default '',
  answer jsonb,
  created_at timestamptz not null default now(),
  unique (conversation_id, client_msg_id)
);

alter table public.messages enable row level security;
revoke all on table public.messages from anon;

create index if not exists messages_conversation_idx
  on public.messages (conversation_id, client_msg_id);
create index if not exists messages_user_idx
  on public.messages (user_id, created_at desc);

drop policy if exists "messages_select_own" on public.messages;
create policy "messages_select_own" on public.messages
  for select to authenticated using (user_id = (select auth.uid()));

-- Insert requires BOTH: the row is stamped with your uid AND the target
-- conversation is yours (prevents writing rows into someone else's thread).
drop policy if exists "messages_insert_own" on public.messages;
create policy "messages_insert_own" on public.messages
  for insert to authenticated with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = (select auth.uid())
    )
  );

drop policy if exists "messages_delete_own" on public.messages;
create policy "messages_delete_own" on public.messages
  for delete to authenticated using (user_id = (select auth.uid()));

-- No UPDATE policy: chat history is append-only from the client.

-- ============================================================
-- usage_events: server-side request metering for per-user rate limits.
-- Inserted by the /api/ask route handler under the caller's own JWT.
-- SELECT+INSERT only — no update/delete policy, so a user cannot reset
-- their own counter. Append-only by construction.
-- ============================================================
create table if not exists public.usage_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  route text not null,
  created_at timestamptz not null default now()
);

alter table public.usage_events enable row level security;
revoke all on table public.usage_events from anon;

create index if not exists usage_events_user_recent_idx
  on public.usage_events (user_id, created_at desc);

drop policy if exists "usage_select_own" on public.usage_events;
create policy "usage_select_own" on public.usage_events
  for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "usage_insert_own" on public.usage_events;
create policy "usage_insert_own" on public.usage_events
  for insert to authenticated with check (user_id = (select auth.uid()));

-- ============================================================
-- updated_at maintenance for conversations
-- ============================================================
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists conversations_touch_updated_at on public.conversations;
create trigger conversations_touch_updated_at
  before update on public.conversations
  for each row execute function public.touch_updated_at();
