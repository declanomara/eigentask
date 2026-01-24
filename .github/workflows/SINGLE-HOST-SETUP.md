# Single-Host Multi-Environment Setup

This document explains how staging and production deployments run on the same AWS host using Docker Compose and nginx.

## Architecture Overview

```
Internet
   │
   ├─ DNS (eigentask.com, staging.eigentask.com, etc.)
   │
   └─ AWS EC2 Instance (Single Host)
       │
       ├─ Nginx (System service, Port 80/443) - Routes by hostname
       │   ├─ eigentask.com → Production Web (localhost:3000)
       │   ├─ api.eigentask.com → Production API (localhost:8000)
       │   ├─ auth.eigentask.com → Production Keycloak (localhost:8080)
       │   ├─ staging.eigentask.com → Staging Web (localhost:3001)
       │   ├─ staging-api.eigentask.com → Staging API (localhost:8001)
       │   └─ staging-auth.eigentask.com → Staging Keycloak (localhost:8081)
       │   └─ Configs in /etc/nginx/conf.d/ (managed by Certbot)
       │
       ├─ Production Stack (docker-compose.prod.yml)
       │   ├─ Web (port 3000)
       │   ├─ API (port 8000)
       │   ├─ Keycloak (port 8080)
       │   ├─ App DB
       │   ├─ Keycloak DB
       │   └─ Redis
       │
       └─ Staging Stack (docker-compose.staging.yml)
           ├─ Web (port 3001)
           ├─ API (port 8001)
           ├─ Keycloak (port 8081)
           ├─ App DB
           ├─ Keycloak DB
           └─ Redis
```

## Key Design Decisions

### 1. Separate Docker Compose Files
- `docker-compose.staging.yml` - Staging environment
- `docker-compose.prod.yml` - Production environment
- Nginx runs as a system service (not in Docker), configured via `/etc/nginx/conf.d/`

### 2. Isolated Networks
- Each environment has its own Docker network (`eigentask-staging`, `eigentask-prod`)
- Containers can't accidentally communicate between environments
- Nginx (system service) accesses containers via localhost ports

### 3. Different Ports
- Production: 3000 (web), 8000 (api), 8080 (keycloak)
- Staging: 3001 (web), 8001 (api), 8081 (keycloak)
- Prevents port conflicts on the same host

### 4. Unique Container Names
- Production: `eigentask-prod-*`
- Staging: `eigentask-staging-*`
- Prevents naming conflicts

### 5. Separate Volumes (Persistent Storage)
- **Production volumes**: `keycloak_db_data_prod`, `app_db_data_prod`, `redis_data_prod`
- **Staging volumes**: `keycloak_db_data_staging`, `app_db_data_staging`, `redis_data_staging`
- **Complete data isolation**: Each environment has its own persistent storage
- **Long-lived storage**: Volumes persist across container restarts, deployments, and code changes
- **Automatic creation**: Docker creates volumes on first deployment
- **Storage location**: `/var/lib/docker/volumes/` on the host
- **Backup required**: Set up regular backups of database volumes (see `DEPLOYMENT.md` for backup commands)

### 6. Configurable Environment File Paths
- Uses `${ENV_FILE_PATH:-/etc/eigentask}` with defaults
- Staging: `/etc/eigentask/staging/*.env`
- Production: `/etc/eigentask/prod/*.env`
- Can be overridden via `ENV_FILE_PATH` environment variable

## Deployment Workflows

### Staging Deployment
- Triggered automatically when code is pushed to `staging` branch (after CI passes)
- Uses `docker-compose.staging.yml`
- Deploys to ports 3001, 8001, 8081

### Production Deployment
- Triggered automatically when code is pushed to `main` branch (after CI passes)
- Uses `docker-compose.prod.yml`
- Deploys to ports 3000, 8000, 8080

### Nginx Setup
- Runs as system service (already configured on your server)
- Config files stored in repo: `nginx/staging.conf`
- One-time setup: Copy `nginx/staging.conf` to `/etc/nginx/conf.d/staging.conf`
- Run Certbot to get SSL certificates for staging domains
- Routes traffic based on hostname
- Handles SSL termination (Certbot-managed)

## Benefits

1. **Cost Effective**: Single host for both environments
2. **Isolated**: Complete separation between staging and production
3. **Automated**: GitHub Actions handles deployments
4. **Flexible**: Easy to add more environments or move to separate hosts later
5. **Safe**: Production and staging can't interfere with each other

## Migration Path

If you later want to separate staging and production:

1. **Option A: Separate Hosts**
   - Deploy staging to a different EC2 instance
   - Update DNS records
   - No code changes needed (just different `STAGING_HOST` secret)

2. **Option B: Separate AWS Accounts**
   - Use different AWS accounts for staging/prod
   - Same deployment workflows, different secrets

3. **Option C: Container Orchestration**
   - Migrate to ECS/EKS/Kubernetes
   - Use the same docker-compose files as reference
   - Deploy to different clusters/namespaces

## Security Considerations

- Environment files are stored outside the repository (`/etc/eigentask/`)
- Different secrets for staging vs production
- Separate databases prevent data leakage
- Nginx handles SSL termination
- Docker networks isolate services

## Monitoring

Both environments can be monitored independently:

```bash
# Check staging
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml ps
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml logs

# Check production
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml ps
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml logs
```
