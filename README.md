# EigenTask

EigenTask is an opinionated task management platform intended to minimize time and effort spent deciding _what_ to do _when_ so you can spend more time actually **_doing_**. Visit [eigentask.com](https://eigentask.com) to get started.

# Table of Contents

1. [Design](#design)
2. [Installation Guide](#installation)
3. [Contribution Guide](#contribution-guide)
4. [License](#licensing)

# Design

EigenTask is a [Svelte](https://svelte.dev/) 5 app built with a [FastAPI](https://fastapi.tiangolo.com/) backend. It uses [KeyCloak](https://www.keycloak.org/) for user management, [PostgreSQL](https://www.postgresql.org/) with [Alembic](https://alembic.sqlalchemy.org/en/latest/) for database migrations, and [Redis](https://redis.io/) for session storage and caching.

The guiding philosophy of EigenTask's design is to minimize vendor lock-in and promote FOSS for the benefit of all.

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

# Installation

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


# Contribution guide

Contributions are welcome, but must follow existing style conventions and design principles.

## High Level Overview

1) Create a feature branch from `main`.
2) Make changes with clear, focused commits.
3) If you change models:
   - Update SQLAlchemy models.
   - Generate a migration: `./migrate.sh revision "Your message"`
   - Review and apply: `./migrate.sh upgrade`
4) Open a PR with a concise description, screenshots if UI changes, and any migration notes.

## Local checks

Run these before opening a PR:

- Backend (FastAPI):
  - Install deps incl. dev tools: `cd api && uv sync --all-groups`
  - Lint: `cd api && uv run ruff check .`
  - Tests: `cd api && uv run pytest` (when tests are present)
- Frontend (SvelteKit):
  - Install deps: `cd web && npm install`
  - Lint/type-check: `cd web && npm run check`

# Licensing

GNU Affero General Public License v3. See [LICENSE](LICENSE) for details. 


