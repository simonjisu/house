begin;
-- New house-specific objects. Existing objects cause an error rather than being overwritten.
create schema if not exists private;
create table private.house_readers (user_id uuid primary key);
alter table private.house_readers enable row level security;
revoke all on private.house_readers from public, anon, authenticated;

create function public.house_can_read() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from private.house_readers r where r.user_id = (select auth.uid()));
$$;
revoke all on function public.house_can_read() from public, anon;
grant execute on function public.house_can_read() to authenticated;

create table public.house_snapshot (
  id text primary key check (id = 'current'),
  payload jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.house_snapshot enable row level security;
alter table public.house_snapshot force row level security;
revoke all on public.house_snapshot from public, anon, authenticated;
grant select on public.house_snapshot to authenticated;
grant select, insert, update on public.house_snapshot to service_role;
create policy house_owner_read on public.house_snapshot
for select to authenticated using ((select public.house_can_read()));
-- No client insert/update/delete policies. No public views. No personal profile table.
commit;
