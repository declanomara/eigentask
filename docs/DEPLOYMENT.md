# Deployment Configuration

This document describes how to configure automated deployment for staging and production.

## Overview

The deployment workflow automatically deploys to staging or production when code is pushed (after CI passes). Compose is structured as a **base + overlay**: the base (`docker-compose.yml`) defines service topology only (no `env_file` or ports) and is not runnable alone; staging/production use the base plus an overlay file.

- **Dev**: `docker compose up` (merges base + `docker-compose.override.yml` automatically)
- **Staging**: `docker compose -f docker-compose.yml -f docker-compose.staging.yml up`
- **Production**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up`

## Required GitHub Environments and Secrets

The deployment workflows use GitHub Environments to organize secrets. You need to create two environments:

1. **`staging`** - For staging deployments
2. **`production`** - For production deployments

### Setting Up Environments

1. Go to: **Settings → Environments**
2. Click **"New environment"**
3. Create **`staging`** environment
4. Create **`production`** environment

### Required Secrets per Environment

Env files are **not** stored as GitHub secrets. They must exist on the server at `/etc/eigentask/staging/` and `/etc/eigentask/production/` (see Server Setup below).

For each environment, configure these secrets:

**Staging Environment:**
- `SSH_PRIVATE_KEY`: Private SSH key for accessing the staging server
- `HOST`: Hostname or IP address of the staging server
- `USER`: SSH username for the staging server
- `DEPLOY_PATH`: (Optional) Path to the deployment directory on the server (defaults to `/opt/eigentask`)

**Production Environment:**
- `SSH_PRIVATE_KEY`, `HOST`, `USER`, `DEPLOY_PATH`: Same keys with production-specific values

### Setting up SSH Access

1. Generate an SSH key pair on your local machine (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-staging" -f ~/.ssh/github_actions_staging
   ```

2. Copy the public key to your staging server:
   ```bash
   ssh-copy-id -i ~/.ssh/github_actions_staging.pub user@staging-server
   ```

3. Add the private key to GitHub Environment Secrets (Settings → Environments → staging → Add secret: `SSH_PRIVATE_KEY`).

4. Add the other secrets to the staging environment (`HOST`, `USER`, `DEPLOY_PATH`).

5. Repeat for the **`production`** environment with production-specific values.

## Server Setup

### Amazon Linux 2023 Setup

1. **Install Docker and Docker Compose**:
   ```bash
   sudo yum update -y
   sudo yum install -y docker git
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   sudo yum install -y docker-compose-plugin
   ```

2. **Create deployment directory**:
   ```bash
   sudo mkdir -p /opt/eigentask
   sudo chown $USER:$USER /opt/eigentask
   cd /opt/eigentask
   git clone <your-repo-url> .
   git checkout staging
   ```

3. **Create environment files directories**:
   ```bash
   sudo mkdir -p /etc/eigentask/staging /etc/eigentask/production
   sudo chown -R $USER:$USER /etc/eigentask
   ```

4. **Set up nginx reverse proxy** (see [nginx/README.md](../nginx/README.md)).

5. **Verify Docker Compose**: `docker compose version`

### Required Environment Files

**Important**: Environment files are NOT stored in git or GitHub secrets. They must be staged on the server before deploy runs.

Create them on the server in `/etc/eigentask/staging/` and `/etc/eigentask/production/`. Use the examples in [envs/](../envs/) (e.g. `envs/keycloak.example.env`) as templates; adjust for staging/production hostnames and credentials.

**Staging** (required): `api.env`, `web.env`, `app-db.env`, `keycloak.env`, `keycloak-db.env` under `/etc/eigentask/staging/`. The deploy script copies Keycloak themes into `staging/themes/`.

**Production** (required): Same filenames under `/etc/eigentask/production/`. The deploy script copies Keycloak themes into `production/themes/`.

**Example web.env** (staging): `API_ORIGIN` and `PUBLIC_API_ORIGIN` must be set or the app will fail on `/app`. Use the internal API URL for SSR and the public URL for redirects:

```bash
API_ORIGIN=http://api:8000
PUBLIC_API_ORIGIN=https://staging-api.eigentask.com
PUBLIC_APP_ORIGIN=https://staging.eigentask.com
```

**Example keycloak.env** (see [envs/keycloak.example.env](../envs/keycloak.example.env) for full template):

```bash
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=your-password
KC_DB=postgres
KC_DB_URL_HOST=eigentask-staging-keycloak-db
KC_DB_URL_DATABASE=keycloak-staging
KC_DB_USERNAME=keycloak-db-user-staging
KC_DB_PASSWORD=your-keycloak-db-password
KC_HTTP_ENABLED=true
KC_HOSTNAME=https://staging-auth.eigentask.com
KC_PROXY_HEADERS=xforwarded
KC_PROXY_ADDRESS_FORWARDING=true
```

**Security**: Run `sudo chmod 600 /etc/eigentask/staging/*.env /etc/eigentask/production/*.env`.

### Database Volume Persistence

Staging and production use Docker named volumes. Data persists across restarts and deployments.

**Existing production setups**: If you use the old single-file compose with volumes like `keycloak_db_data`, see [VOLUME-MIGRATION.md](VOLUME-MIGRATION.md) to migrate to environment-specific volumes.

**Staging volumes**: `keycloak_db_data_staging`, `app_db_data_staging`, `redis_data_staging` (created automatically).

**Production volumes**: `keycloak_db_data_prod`, `app_db_data_prod`, `redis_data_prod` (created automatically).

## Deployment Process

When code is pushed to `staging` (or `main` for production):

1. CI workflow runs (lint, type check, tests).
2. If CI passes, deploy workflow runs, SSHs to the server, verifies env files exist at `/etc/eigentask/staging/` or `/etc/eigentask/production/`, pulls code, copies Keycloak themes, runs `docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d` (or prod overlay), and verifies services.

**Manual trigger**: Actions → Deploy → Run workflow → choose branch/environment.

## Troubleshooting

- **SSH / "Required env file missing"**: Check secrets (`HOST`, `USER`, `SSH_PRIVATE_KEY`) and that env files exist under `/etc/eigentask/staging/` or `/etc/eigentask/production/`.
- **Containers fail to start**: On the server run `ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.yml -f docker-compose.staging.yml logs` (or prod). Check disk space, env file syntax, and [VOLUME-MIGRATION.md](VOLUME-MIGRATION.md) if migrating.
