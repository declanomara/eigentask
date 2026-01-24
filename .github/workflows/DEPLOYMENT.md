# Deployment Configuration

This document describes how to configure automated deployment for the staging branch.

## Overview

The `deploy-staging.yml` workflow automatically deploys changes to the staging environment when code is pushed to the `staging` branch (after CI passes).

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

### SSH-Based Deployment (Current Setup)

- `STAGING_SSH_PRIVATE_KEY`: Private SSH key for accessing the staging server
- `STAGING_HOST`: Hostname or IP address of the staging server
- `STAGING_USER`: SSH username for the staging server
- `STAGING_DEPLOY_PATH`: (Optional) Path to the deployment directory on the server (defaults to `/opt/eigentask`)

### Setting up SSH Access

1. Generate an SSH key pair on your local machine (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-staging" -f ~/.ssh/github_actions_staging
   ```

2. Copy the public key to your staging server:
   ```bash
   ssh-copy-id -i ~/.ssh/github_actions_staging.pub user@staging-server
   ```

3. Add the private key to GitHub Secrets:
   - Copy the contents of `~/.ssh/github_actions_staging` (the private key)
   - Go to GitHub → Settings → Secrets and variables → Actions
   - Add a new secret named `STAGING_SSH_PRIVATE_KEY` with the private key content

4. Add the other secrets:
   - `STAGING_HOST`: Your server's hostname or IP
   - `STAGING_USER`: The SSH username
   - `STAGING_DEPLOY_PATH`: The directory where the code is deployed (e.g., `/opt/eigentask`)

## Server Setup

### Amazon Linux 2023 Setup

The deployment workflow is compatible with Amazon Linux 2023. Here's how to set it up:

1. **Install Docker and Docker Compose**:
   ```bash
   sudo yum update -y
   sudo yum install -y docker git
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   
   # Install Docker Compose v2 (plugin)
   sudo yum install -y docker-compose-plugin
   # Or use standalone: sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   # sudo chmod +x /usr/local/bin/docker-compose
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
   sudo mkdir -p /etc/eigentask/staging /etc/eigentask/prod
   sudo chown -R $USER:$USER /etc/eigentask
   ```

4. **Set up nginx reverse proxy** (see `nginx/README.md` for details):
   ```bash
   # Create SSL directory
   sudo mkdir -p /etc/nginx/ssl
   sudo chmod 755 /etc/nginx/ssl
   
   # Start nginx (after setting up SSL certificates)
   cd /opt/eigentask
   docker compose -f docker-compose.nginx.yml up -d
   ```

5. **Set up environment files** (see below - can be automated via GitHub Secrets)

5. **Verify Docker Compose works**:
   ```bash
   docker compose version
   ```

### Required Environment Files

**Important**: Environment files are NOT stored in git (for security). 

**Recommended**: Use automated deployment via GitHub Secrets (see `ENV-FILES-SETUP.md`). The deployment workflow will automatically create these files from secrets.

**Alternative**: You can manually create them on the server (one-time setup).

Since staging and production run on the same host, environment files are organized in subdirectories:

**Staging files** (required for staging deployments):
- `/etc/eigentask/staging/api.env`
- `/etc/eigentask/staging/web.env`
- `/etc/eigentask/staging/app-db.env`
- `/etc/eigentask/staging/keycloak.env`
- `/etc/eigentask/staging/keycloak-db.env`

**Production files** (required for production deployments):
- `/etc/eigentask/prod/api.env`
- `/etc/eigentask/prod/web.env`
- `/etc/eigentask/prod/app-db.env`
- `/etc/eigentask/prod/keycloak.env`
- `/etc/eigentask/prod/keycloak-db.env`

**Example staging API env file** (`/etc/eigentask/staging/api.env`):

```bash
# /etc/eigentask/staging/api.env
DATABASE_URL=postgresql+asyncpg://user:password@eigentask-staging-app-db:5432/eigentask
REDIS_URL=redis://eigentask-staging-redis:6379/0
FRONTEND_ORIGIN=https://staging.eigentask.com
BACKEND_ORIGIN=https://staging-api.eigentask.com
KEYCLOAK_URL=http://eigentask-staging-keycloak:8080
KEYCLOAK_PUBLIC_URL=https://staging-auth.eigentask.com
KEYCLOAK_REALM=eigentask
KEYCLOAK_CLIENT_ID=eigentask
CALLBACK_URL=https://staging-api.eigentask.com/auth/callback
SESSION_SECRET=your-staging-secret-key-here
COOKIE_DOMAIN=.eigentask.com
COOKIE_SECURE=true

# /etc/eigentask/staging/web.env
PUBLIC_API_URL=https://staging-api.eigentask.com

# /etc/eigentask/staging/app-db.env
POSTGRES_USER=eigentask-staging
POSTGRES_PASSWORD=your-staging-db-password
POSTGRES_DB=eigentask-staging

# /etc/eigentask/staging/keycloak.env
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=your-staging-admin-password
KC_DB=postgres
KC_DB_URL_HOST=eigentask-staging-keycloak-db
KC_DB_URL_DATABASE=keycloak-staging
KC_DB_USERNAME=keycloak-db-user-staging
KC_DB_PASSWORD=your-staging-keycloak-db-password
KC_HTTP_ENABLED=true
KC_HOSTNAME_URL=https://staging-auth.eigentask.com

# /etc/eigentask/staging/keycloak-db.env
POSTGRES_DB=keycloak-staging
POSTGRES_USER=keycloak-db-user-staging
POSTGRES_PASSWORD=your-staging-keycloak-db-password
```

**Example production API env file** (`/etc/eigentask/prod/api.env`):

```bash
# /etc/eigentask/prod/api.env
DATABASE_URL=postgresql+asyncpg://user:password@eigentask-prod-app-db:5432/eigentask
REDIS_URL=redis://eigentask-prod-redis:6379/0
FRONTEND_ORIGIN=https://eigentask.com
BACKEND_ORIGIN=https://api.eigentask.com
KEYCLOAK_URL=http://eigentask-prod-keycloak:8080
KEYCLOAK_PUBLIC_URL=https://auth.eigentask.com
KEYCLOAK_REALM=eigentask
KEYCLOAK_CLIENT_ID=eigentask
CALLBACK_URL=https://api.eigentask.com/auth/callback
SESSION_SECRET=your-production-secret-key-here
COOKIE_DOMAIN=.eigentask.com
COOKIE_SECURE=true

# /etc/eigentask/prod/web.env
PUBLIC_API_URL=https://api.eigentask.com

# /etc/eigentask/prod/app-db.env
POSTGRES_USER=eigentask-prod
POSTGRES_PASSWORD=your-production-db-password
POSTGRES_DB=eigentask-prod

# /etc/eigentask/prod/keycloak.env
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=your-production-admin-password
KC_DB=postgres
KC_DB_URL_HOST=eigentask-prod-keycloak-db
KC_DB_URL_DATABASE=keycloak-prod
KC_DB_USERNAME=keycloak-db-user-prod
KC_DB_PASSWORD=your-production-keycloak-db-password
KC_HTTP_ENABLED=true
KC_HOSTNAME_URL=https://auth.eigentask.com

# /etc/eigentask/prod/keycloak-db.env
POSTGRES_DB=keycloak-prod
POSTGRES_USER=keycloak-db-user-prod
POSTGRES_PASSWORD=your-production-keycloak-db-password
```

**Important Notes**:
- Use different database names, users, and passwords for staging vs production
- Use different `SESSION_SECRET` values for staging vs production  
- Internal Docker service names match container names (e.g., `eigentask-staging-app-db`, `eigentask-prod-app-db`)
- Public URLs should match your DNS configuration
- `KEYCLOAK_URL` is internal (http), `KEYCLOAK_PUBLIC_URL` is what browsers see (https)

**Security Note**: These files contain sensitive credentials. 

If using automated deployment (GitHub Secrets), permissions are set automatically (600, owner-only).

If creating manually, ensure proper file permissions:
```bash
sudo chmod 600 /etc/eigentask/staging/*.env /etc/eigentask/prod/*.env
sudo chown -R $USER:$USER /etc/eigentask
```

**See `ENV-FILES-SETUP.md` for automated deployment setup.**

### Database Volume Persistence

**Important**: Both staging and production use Docker named volumes for persistent storage. Data persists across container restarts and deployments.

**⚠️ Existing Production Deployments**: If you have an existing production setup using `docker-compose.yml` with volumes like `keycloak_db_data` (external), you'll need to migrate to the new volume names (`*_prod` suffix). See `VOLUME-MIGRATION.md` for detailed migration instructions.

**Staging volumes** (automatically created):
- `keycloak_db_data_staging` - Keycloak database (realm configs, users, etc.)
- `app_db_data_staging` - Application database (tasks, users, etc.)
- `redis_data_staging` - Redis data (sessions, cache)

**Production volumes** (automatically created):
- `keycloak_db_data_prod` - Keycloak database
- `app_db_data_prod` - Application database
- `redis_data_prod` - Redis data

**Volume storage location**: Docker stores volumes in `/var/lib/docker/volumes/` on the host. Each volume is isolated and persists independently.

**Key points**:
- ✅ Volumes are **automatically created** on first deployment
- ✅ Data **persists** across container restarts and code deployments
- ✅ Staging and production volumes are **completely separate** (no conflicts)
- ✅ Volumes survive `docker compose down` (but not `docker compose down -v`)

**Backup recommendations**:
1. **Regular backups**: Set up automated backups of `/var/lib/docker/volumes/` or use `docker run` with volume mounts to create database dumps
2. **Before major changes**: Backup volumes before schema migrations or major deployments
3. **Disaster recovery**: Keep backups off-server (S3, separate storage, etc.)

**Example backup commands**:
```bash
# Backup staging app database
docker run --rm -v eigentask-staging_app_db_data_staging:/data -v $(pwd):/backup \
  postgres:16-alpine pg_dump -h eigentask-staging-app-db -U eigentask-staging \
  eigentask-staging > /backup/staging-app-db-$(date +%Y%m%d).sql

# Backup production Keycloak database
docker run --rm -v eigentask-prod_keycloak_db_data_prod:/data -v $(pwd):/backup \
  postgres:15 pg_dump -h eigentask-prod-keycloak-db -U keycloak-db-user-prod \
  keycloak-prod > /backup/prod-keycloak-db-$(date +%Y%m%d).sql
```

**Volume management**:
```bash
# List all volumes
docker volume ls | grep eigentask

# Inspect a volume
docker volume inspect eigentask-staging_app_db_data_staging

# Remove a volume (⚠️ DESTROYS DATA)
docker volume rm eigentask-staging_app_db_data_staging
```

### Server Requirements Summary

On your staging server, ensure:

1. Docker and Docker Compose v2 are installed and working
2. Git is installed
3. The repository is cloned in the deployment directory (`/opt/eigentask` by default)
4. **All environment files are created in `/etc/eigentask/`** (see above)
5. **Sufficient disk space** for database volumes (PostgreSQL and Keycloak databases will grow over time)
6. The SSH user has permissions to:
   - Run `docker` and `docker compose` commands (user should be in `docker` group)
   - Access the deployment directory
   - Pull from the git repository
   - Read environment files in `/etc/eigentask/`

## Testing Deployment

**See `TESTING-DEPLOYMENT.md` for a comprehensive guide on testing the staging deployment workflow**, including:
- Manual trigger instructions
- Prerequisites checklist
- Verification steps
- Troubleshooting common issues

## Deployment Process

When code is pushed to `staging`:

1. CI workflow runs (lint, type check, tests)
2. If CI passes, deployment workflow triggers
3. Workflow SSHs to the staging server
4. Creates/updates environment files from GitHub Secrets
5. Pulls latest code from `staging` branch
6. Rebuilds Docker containers
7. Restarts services with `docker compose up -d`
8. Verifies services are running

## Manual Deployment

You can manually trigger deployment from the Actions tab:
- Go to Actions → Deploy to Staging
- Click "Run workflow"
- Select the `staging` branch
- Click "Run workflow"

## Troubleshooting

### Deployment fails with SSH connection error
- Verify `STAGING_HOST`, `STAGING_USER`, and `STAGING_SSH_PRIVATE_KEY` are correct
- Check that the server is accessible from GitHub Actions runners
- Ensure the SSH key has been added to the server's authorized_keys

### Deployment fails: "Required env file missing"
- The deployment workflow checks for required env files before deploying
- Create the missing file(s) in `/etc/eigentask/staging/` or `/etc/eigentask/prod/` (see "Required Environment Files" section above)
- Ensure files have correct permissions: `chmod 600 /etc/eigentask/staging/*.env /etc/eigentask/prod/*.env`

### Containers fail to start
- Check server logs: `ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml logs` (or `docker-compose.prod.yml`)
- Verify all environment files exist in `/etc/eigentask/staging/` or `/etc/eigentask/prod/` and have correct values
- Check disk space: `df -h`
- Verify Docker is running: `docker ps`
- Check env file syntax (no spaces around `=`, proper quoting for values with spaces)
- Verify container names don't conflict: `docker ps -a` (staging uses `eigentask-staging-*`, prod uses `eigentask-prod-*`)

### Services not healthy after deployment
- Check individual service logs: `docker compose -f docker-compose.yml logs api`
- Verify database migrations ran: Check API logs for migration output
- Check service health: `docker compose -f docker-compose.yml ps`

## Alternative Deployment Methods

If you're using a different deployment method (e.g., container registry, cloud platform), you can modify the workflow accordingly. Common alternatives:

- **Container Registry**: Build and push images, then update services to pull new images
- **Cloud Platform**: Use platform-specific deployment actions (AWS, GCP, Azure, Railway, Render, etc.)
- **Webhook-based**: Trigger deployment via webhook to your deployment service
