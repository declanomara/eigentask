# Eigentask

A full‑stack task planning app.

- Backend: `FastAPI` + `SQLAlchemy` + `Alembic` + `Redis` (sessions)
- Frontend: `SvelteKit` + `Vite` + `Tailwind`
- Infrastructure: Docker Compose for local development, PostgreSQL 16, Redis 7


## Quick start (local dev)

1) Install prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Node 20+ (optional if you run the web app outside Docker)

2) Configure environment

- Copy and adjust the example env files in `envs/` as needed.
  - `envs/api.dev.env` (API, Redis, Postgres, OIDC settings)
  - `envs/web.dev.env` (Web → API origins)

3) Start services

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

This runs:

- Postgres at `app-db:5432`
- Redis at `redis:6379`
- API at `http://localhost:8000`
- Web at `http://localhost:3000`

4) Apply database migrations

```bash
./migrate.sh upgrade
```

The API also creates tables on startup as a safeguard, but you should treat Alembic migrations as the source of truth and always run them.

5) Open the app

Visit `http://localhost:3000`. Protected routes will redirect you to Keycloak for login (see OIDC settings in `envs/api.dev.env`).


## Project layout

- `api/` — FastAPI app
  - `app/core/` — configuration, DB setup, auth/session helpers
  - `app/models/` — SQLAlchemy models
  - `app/routers/` — API routers (auth, users, tasks)
  - `alembic/` — Alembic env and versioned migrations
- `web/` — SvelteKit app
  - `src/routes/` — public and protected routes
  - `src/lib/` — API client and UI components
  - `static/` — static assets (e.g., `favicon.svg`)
- `envs/` — environment files for local dev
- `docker-compose.dev.yml` — dev services
- `migrate.sh` — Alembic helper script (see below)


## Conventions

- Python code is formatted and linted with `ruff` (see `api/pyproject.toml`).
- Use explicit, readable names; avoid unnecessary nesting and broad try/excepts.
- Svelte components follow idiomatic SvelteKit structure; server actions are used for mutations on protected routes.
- API routes prefer small, explicit request/response payloads. Database entities should not be exposed directly.
- When updating HTTP methods, make sure CORS is configured to allow them (API already allows `GET, POST, PUT, PATCH, DELETE, OPTIONS`).


## Database migrations (migrate.sh)

We use a simple wrapper `migrate.sh` to run Alembic commands consistently in local Docker or on a host.

Usage:

```bash
# Create a new autogenerate migration
./migrate.sh revision "Add foo to bar"

# Apply all migrations
./migrate.sh upgrade

# Downgrade one step (or pass a specific revision)
./migrate.sh downgrade -1

# Show current head
./migrate.sh current

# Show history
./migrate.sh history

# Stamp the DB to head without applying migrations
./migrate.sh stamp
```

Notes:

- The script will execute inside the running API container when available, so `DATABASE_URL` from `envs/api.dev.env` is used automatically.
- Autogenerate will diff model metadata (`app/core/db.Base.metadata`) against the DB. Review autogen results before committing.
- Commit migration files in `api/alembic/versions/` with your changes.


## Developing

- Web: `cd web && npm i && npm run dev` (outside Docker). When running in Compose, the container already runs Vite dev server and watches files.
- API: `docker compose -f docker-compose.dev.yml logs -f api` to tail backend logs.


## Troubleshooting

- Favicon 404 in dev: we serve `web/static/favicon.svg` and now link it explicitly in `web/src/app.html`. If your browser still requests `/favicon.ico`, a fallback `<link rel="alternate icon" href="/favicon.ico" />` is present (optional to provide).
- Browser console error mentioning `content_script.js`: that originates from a browser extension content script, not this app. Test in a private window or with extensions disabled.
- Task creation not persisting: ensure migrations are applied (`./migrate.sh upgrade`) and that you are authenticated (protected routes require a valid session). The create task payload is `{"title": string, "description"?: string}`; the API now validates this shape.


## Contribution guide

1) Create a feature branch from `main`.
2) Make changes with clear, focused commits.
3) If you change models:
   - Update SQLAlchemy models.
   - Generate a migration: `./migrate.sh revision "Your message"`
   - Review and apply: `./migrate.sh upgrade`
4) Ensure the app runs locally (Compose up + smoke test the feature).
5) Open a PR with a concise description, screenshots if UI changes, and any migration notes (including backfill/ops steps if needed).

Code style:

- Python: keep code readable and explicit; prefer early returns; only catch exceptions you handle meaningfully.
- TypeScript/Svelte: keep types clear; avoid `any`; colocate server actions with pages where practical.


## Licensing

TBD.


