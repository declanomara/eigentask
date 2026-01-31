# Volume Migration Guide

This guide helps you migrate from the old production volumes to the new environment-specific volumes.

## Current Situation

**Old production setup** (single compose file with `/etc/eigentask/*.env`):
- `keycloak_db_data` (external, pre-existing)
- `app_db_data` (normal volume)
- `redis_data` (normal volume)

**New production setup** (base + overlay: `docker-compose.yml` + `docker-compose.prod.yml`):
- `keycloak_db_data_prod` (new volume)
- `app_db_data_prod` (new volume)
- `redis_data_prod` (new volume)

## Migration Strategy

### Option 1: Migrate Data to New Volumes (Recommended)

1. **Stop the current production services**:
   ```bash
   cd /opt/eigentask
   docker compose down
   ```

2. **Backup existing databases** (safety first), then start the new stack:
   ```bash
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Migrate data** (pg_dump/pg_restore or volume copy as needed), then verify.

4. **Restart to verify**:
   ```bash
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
   ```

5. **Clean up old volumes** only after confirming the new setup works:  
   `docker volume rm keycloak_db_data app_db_data redis_data`

### Option 2: Use Existing Volumes (Quick)

In `docker-compose.prod.yml`, set the overlay volumes to `external: true` and `name: keycloak_db_data` (etc.) so they point at the existing volume names. See [DEPLOYMENT.md](DEPLOYMENT.md) for volume layout.

**Recommendation**: Prefer Option 1 for clear `*_prod` naming and separation from staging.

## Rollback

1. **Stop new stack**:  
   `ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.yml -f docker-compose.prod.yml down`
2. **Start old stack** again; old volumes are unchanged until you remove them.
