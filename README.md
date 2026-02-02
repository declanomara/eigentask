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

| Path | Purpose |
|------|---------|
| `api/` | FastAPI app (core, models, routers, alembic) |
| `web/` | SvelteKit app (routes, lib, static) |
| `keycloak/` | Keycloak realm export, config, and custom themes (`themes/`) |
| `nginx/` | Nginx configs for staging/production |
| `envs/` | Env files: `*.dev.env` for local dev, `*.example.env` as templates |
| `docs/` | Deployment, volume migration, and other docs |
| `scripts/` | `deploy.sh` (CI deploy), `migrate.py` (Alembic helper) |
| Root | `docker-compose.yml` (base), `docker-compose.override.yml` (dev), `docker-compose.staging.yml` / `.prod.yml` (overlays) |

**Deployment**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for GitHub Actions, server setup, and env files.

## Database migrations (scripts/migrate.py)

Python script to run Alembic in the API container. **Run from repo root.** Pass the environment (`staging`, `production`, or `local`) then the Alembic command.

```bash
# Apply migrations (after deploy or locally)
python scripts/migrate.py staging upgrade
python scripts/migrate.py production upgrade
python scripts/migrate.py local upgrade

# Create a new autogenerate migration (local only)
python scripts/migrate.py local revision "Add foo to bar"

# Downgrade one step
python scripts/migrate.py staging downgrade -1

# Show current head / history / stamp
python scripts/migrate.py staging current
python scripts/migrate.py staging history
python scripts/migrate.py staging stamp
```

- **local**: uses `docker-compose.yml` + `docker-compose.override.yml` (dev stack).
- **staging** / **production**: use the matching overlay and `ENV_FILE_PATH` (default `/etc/eigentask` on the server). Run on the server after deploy, or from your machine if Docker can reach the stack.

When run *inside* the API container (e.g. `docker compose run api python scripts/migrate.py staging upgrade`), it runs Alembic directly. Otherwise it runs `docker compose exec api ... alembic ...`.

Review autogenerate output before committing; commit migration files in `api/alembic/versions/`.

# Installation

1) Install prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Node 20+ (optional if you run the web app outside Docker)

2) Configure environment

- Copy example env files from `envs/*.example.env` to `envs/*.dev.env` and adjust. The repo includes `envs/*.dev.env` for local dev (API, web, Keycloak, Keycloak DB, app DB); use `envs/*.example.env` as templates for staging/production or new setups.

3) Start services

```bash
docker compose up -d --build
```

The API container mounts only source and config dirs (e.g. `app/`, `alembic/`, `main.py`), so the image’s `.venv` (from `RUN uv sync` in the Dockerfile) stays in place and is ephemeral—no volume and no writes to the host. You can run `uv` and tests locally in `api/` with your own `.venv` without conflict.

This merges the base compose with the dev override (no env or ports in base, so base-only is not runnable). To run staging or production locally you would use: `docker compose -f docker-compose.yml -f docker-compose.staging.yml up` (with env files in place).

This runs:

- Keycloak DB at `keycloak-db:5432`
- Keycloak at `http://localhost:8080` (admin: `admin` / `admin`)
- Postgres at `app-db:5432`
- Redis at `redis:6379`
- API at `http://localhost:8000`
- Web at `http://localhost:3000`

**Note:** Keycloak automatically imports the `eigentask` realm on first startup (configured in `keycloak/realm-export/eigentask-realm.json`). This includes:
- The `eigentask` realm
- The `eigentask` client with proper redirect URIs
- The **eigentask** custom theme (login, account, email) matching the web app design
- Test users:
  - `testuser` / `password` (email: `test@example.com`)
  - `admin` / `admin` (email: `admin@example.com`)

If you need to modify the realm configuration, you can:
1. Export the realm from Keycloak admin console (Realm Settings → Export)
2. Update `keycloak/realm-export/eigentask-realm.json`
3. Restart Keycloak (it will re-import only if the realm doesn't exist)

4) Apply database migrations

```bash
python scripts/migrate.py local upgrade
```

The API also creates tables on startup as a safeguard, but you should treat Alembic migrations as the source of truth and always run them.

6) Open the app

Visit `http://localhost:3000`. Protected routes will redirect you to Keycloak for login. Use the test user you created (or create one in Keycloak admin console).


# Contribution guide

Contributions are welcome, but must follow existing style conventions and design principles.

## Style Conventions

- **No emojis**: Emojis are not allowed in code, commit messages, PR descriptions, or documentation. Use GitHub Flavored Markdown (checkboxes, bold text, etc.) for formatting instead.
- **PR titles must follow convention**: PR titles must start with a prefix matching the branch type: `feature:`, `fix:`, `docs:`, `refactor:`, or `chore:` followed by a brief description (e.g., `fix: Update CI workflow to run on staging branch PRs`).
- Follow existing code style and formatting (enforced by linters and type checkers).

## Branch Naming Conventions

All branches must follow a naming convention with a required prefix:

- **`feature/`** - New features and enhancements
  - Example: `feature/user-dashboard`, `feature/task-prioritization`
- **`fix/`** - Bug fixes
  - Example: `fix/session-timeout`, `fix/auth-token-expiry`
- **`docs/`** - Documentation updates
  - Example: `docs/api-documentation`, `docs/deployment-guide`
- **`refactor/`** - Code refactoring (no new features)
  - Example: `refactor/auth-module`, `refactor/database-layer`
- **`chore/`** - Maintenance tasks, dependencies, configuration
  - Example: `chore/update-dependencies`, `chore/ci-improvements`

Branch names are enforced by repository rules. Invalid branch names will be rejected.

## Branch Lifecycle

EigenTask uses a three-tier branch strategy:

```
Contribution Branch → Staging → Main (Production)
```

### 1. Contribution Branches

All development happens on contribution branches with the naming convention above:

- Create from `staging`: `git checkout -b <type>/<description> staging`
  - Examples: `feature/user-dashboard`, `fix/auth-bug`, `docs/api-guide`, `refactor/auth-module`, `chore/update-deps`
- Make changes with clear, focused commits
- Open a Pull Request targeting `staging`
- CI checks must pass (lint, type check, tests)
- After review and approval, merge into `staging`

### 2. Staging Branch

The `staging` branch serves as the integration and testing environment:

- **Purpose**: Integration testing and validation before production
- **Auto-deployment**: Changes to `staging` automatically deploy to the dev environment
- **Merge source**: Contribution branches merge here via PR
- **Protection**: Requires PRs and CI checks, but allows faster iteration than `main`

### 3. Main Branch (Production)

The `main` branch represents production-ready code:

- **Purpose**: Production deployments
- **Merge source**: Weekly automated merges from `staging`
- **Protection**: Strict protection rules requiring:
  - Pull request reviews
  - All CI checks passing
  - Up-to-date branches
  - Linear history
- **Deployment**: Production deployments occur weekly after staging → main merges

### Workflow Summary

1. **Development**: Create a contribution branch using the appropriate prefix (e.g., `feature/new-feature`, `fix/bug-description`, `docs/guide-update`)
2. **Integration**: Merge contribution branch → `staging` via PR
3. **Testing**: Changes auto-deploy to dev environment for validation
4. **Production**: Weekly automated merge `staging` → `main`
5. **Deployment**: Production redeploys from `main` weekly

This workflow ensures:
- ✅ Fast feedback through dev environment deployments
- ✅ Controlled production releases
- ✅ Quality gates at each stage
- ✅ Clear separation between development, staging, and production

## High Level Overview

1) Create a contribution branch from `staging` using the naming convention with the appropriate prefix:
   - `feature/` for new features
   - `fix/` for bug fixes
   - `docs/` for documentation
   - `refactor/` for refactoring
   - `chore/` for maintenance tasks
   - Example: `git checkout -b fix/my-fix staging`
2) Make changes with clear, focused commits.
3) If you change models:
   - Update SQLAlchemy models.
   - Generate a migration: `python scripts/migrate.py local revision "Your message"`
   - Review and apply: `python scripts/migrate.py local upgrade`
4) Open a PR targeting `staging` with a concise description, screenshots if UI changes, and any migration notes.
5) After merge to `staging`, changes will auto-deploy to the dev environment for testing.
6) Weekly, `staging` is automatically merged to `main` for production deployment.

## Local checks

Run these before opening a PR:

- Backend (FastAPI):
  - Install deps incl. dev tools: `cd api && uv sync --all-groups`
  - Lint: `cd api && uv run ruff check .`
  - Tests: `cd api && uv run pytest`
  - Run specific test file: `cd api && uv run pytest tests/test_tasks.py`
  - Run tests with coverage: `cd api && uv run pytest --cov=app --cov-report=term-missing`
- Frontend (SvelteKit):
  - Install deps: `cd web && npm install`
  - Lint/type-check: `cd web && npm run check`

## Testing Guide

### Backend Integration Tests

The API includes comprehensive integration tests covering:
- Task CRUD operations (create, read, update, delete)
- User authentication and authorization
- OIDC authentication flow
- Session management

**Test Infrastructure:**
- Uses SQLite in-memory database for fast, isolated tests
- FakeRedis for mocking Redis sessions
- Mocked OIDC/JWT authentication for testing protected endpoints
- Transaction rollback after each test for isolation

**Running Tests:**

```bash
# Run all tests
cd api && uv run pytest

# Run with verbose output
cd api && uv run pytest -v

# Run specific test class
cd api && uv run pytest tests/test_tasks.py::TestTasksList

# Run tests marked as integration
cd api && uv run pytest -m integration

# Run tests with coverage report
cd api && uv run pytest --cov=app --cov-report=html
# Then open htmlcov/index.html in your browser
```

**Writing New Tests:**

1. Create test files in `api/tests/` with the naming pattern `test_*.py`
2. Use fixtures from `conftest.py`:
   - `authenticated_client`: HTTP client with mocked authentication
   - `db_session`: Database session with transaction rollback
   - `fake_redis`: Mocked Redis instance
3. Use factories from `tests/factories.py` to create test data
4. Mark integration tests with `@pytest.mark.integration`

Example test structure:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_my_endpoint(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test description."""
    response = await authenticated_client.get("/my-endpoint")
    assert response.status_code == 200
```

# Licensing

GNU Affero General Public License v3. See [LICENSE](LICENSE) for details. 


