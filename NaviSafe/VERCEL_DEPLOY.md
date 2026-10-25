# Vercel and Supabase deployment

## Supabase setup

1. Create a Supabase project.
2. Run [`supabase/schema.sql`](./supabase/schema.sql) in the SQL Editor.
3. In Authentication, enable Email provider and configure email confirmation/SMTP.
4. Create a private Storage bucket named `report-media` if media is moved to Supabase Storage.

## Vercel variables

Set these variables for Preview and Production:

```text
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<public anon or publishable key>
VITE_API_URL=/api
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<public anon or publishable key>
SUPABASE_SERVICE_ROLE_KEY=<server-only service role key>
SAFEPATH_MODERATOR_TOKEN=<long random server-only token>
```

Never use `SUPABASE_SERVICE_ROLE_KEY` as a `VITE_` variable.

## Deployment

Import the repository into Vercel. [`vercel.json`](./vercel.json) builds `frontend/` and exposes the FastAPI application through `api/index.py`.

When `SUPABASE_URL` is configured, the API uses Supabase Postgres and the private `report-media` Storage bucket. It will not silently fall back to SQLite. `data/safepath.sqlite3` and `data/private_media/` are used only when no Supabase URL is configured for local development.
