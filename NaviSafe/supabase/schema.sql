-- Run this in Supabase SQL Editor before deploying.
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now()
);
create table if not exists public.reports (
  id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  actor text not null,
  idem text not null,
  fingerprint text not null,
  street text not null,
  category text not null,
  description text not null default '',
  observed_at timestamptz not null,
  submitted_at timestamptz not null default now(),
  latitude double precision,
  longitude double precision,
  status text not null default 'pending_review',
  version integer not null default 1,
  expires_at timestamptz not null,
  visibility_consent boolean not null default false,
  checks jsonb not null default '{}'::jsonb,
  history jsonb not null default '[]'::jsonb,
  personally_observed boolean not null default false,
  duplicate_candidates jsonb not null default '[]'::jsonb,
  corroboration_candidates jsonb not null default '[]'::jsonb,
  has_image boolean not null default false,
  unique(actor, idem)
);
create table if not exists public.report_reviews (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  kind text not null,
  reason text not null,
  created_at timestamptz not null default now()
);
create table if not exists public.curated_training (
  report_id text primary key references public.reports(id) on delete cascade,
  label text not null check (label in ('unsafe_location','safe_location','unresolved')),
  eligible boolean not null default false,
  reviewer text not null,
  reason text not null,
  timestamp timestamptz not null default now()
);
insert into storage.buckets (id, name, public)
values ('report-media', 'report-media', false)
on conflict (id) do update set public = false;
alter table public.profiles enable row level security;
alter table public.reports enable row level security;
alter table public.report_reviews enable row level security;
alter table public.curated_training enable row level security;
create policy "users read own profile" on public.profiles for select using (auth.uid() = id);
create policy "users manage own profile" on public.profiles for all using (auth.uid() = id) with check (auth.uid() = id);
create policy "users create reports" on public.reports for insert with check (auth.uid() = user_id);
create policy "users read visible reports" on public.reports for select using ((auth.uid() = user_id) or (visibility_consent and status in ('provisionally_published','corroborated','verified','disputed','expired')));
create policy "users request reviews" on public.report_reviews for insert with check (auth.uid() = user_id);
