# Volume Migration Guide

This guide helps you migrate from the old production volumes to the new environment-specific volumes.

## Current Situation

**Old production setup** (`docker-compose.yml`):
- `keycloak_db_data` (external, pre-existing)
- `app_db_data` (normal volume)
- `redis_data` (normal volume)

**New production setup** (`docker-compose.prod.yml`):
- `keycloak_db_data_prod` (new volume)
- `app_db_data_prod` (new volume)
- `redis_data_prod` (new volume)

## Migration Strategy

You have two options:

### Option 1: Migrate Data to New Volumes (Recommended)

This preserves your existing data and aligns with the new naming convention.

**Steps:**

1. **Stop the current production services** (using old `docker-compose.yml`):
   ```bash
   cd /opt/eigentask
   docker compose down
   ```

2. **Backup existing databases** (safety first):
   ```bash
   # Backup Keycloak database
   docker run --rm \
     --network host \
     -v keycloak_db_data:/source:ro \
     -v $(pwd):/backup \
     postgres:15 pg_dump -h localhost -U <keycloak-user> -d <keycloak-db> > /backup/keycloak-backup-$(date +%Y%m%d).sql
   
   # Backup App database
   docker run --rm \
     --network host \
     -v app_db_data:/source:ro \
     -v $(pwd):/backup \
     postgres:16-alpine pg_dump -h localhost -U <app-user> -d <app-db> > /backup/app-backup-$(date +%Y%m%d).sql
   ```

3. **Start new production stack** (creates new volumes):
   ```bash
   cd /opt/eigentask
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml up -d
   ```

4. **Migrate data from old volumes to new volumes**:
   ```bash
   # Migrate Keycloak database
   # Method 1: Using pg_dump/pg_restore
   docker exec eigentask-prod-keycloak-db pg_dump -U <old-keycloak-user> -d <old-keycloak-db> -h <old-container> | \
     docker exec -i eigentask-prod-keycloak-db psql -U <new-keycloak-user> -d <new-keycloak-db>
   
   # Method 2: Direct volume copy (if same PostgreSQL version)
   docker run --rm \
     -v keycloak_db_data:/source:ro \
     -v eigentask-prod_keycloak_db_data_prod:/dest \
     alpine sh -c "cp -a /source/. /dest/"
   
   # Migrate App database
   docker exec eigentask-prod-app-db pg_dump -U <old-app-user> -d <old-app-db> -h <old-container> | \
     docker exec -i eigentask-prod-app-db psql -U <new-app-user> -d <new-app-db>
   ```

5. **Restart services to verify**:
   ```bash
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml restart
   ```

6. **Verify data migrated correctly**:
   ```bash
   # Check Keycloak
   curl http://localhost:8080/health/ready
   
   # Check API
   curl http://localhost:8000/health
   ```

7. **Clean up old volumes** (after verifying everything works):
   ```bash
   # ⚠️ Only after confirming new setup works!
   docker volume rm keycloak_db_data app_db_data redis_data
   ```

### Option 2: Use Existing Volumes (Quick Migration)

If you want to keep using the existing volumes without migration:

**Update `docker-compose.prod.yml` volumes section:**

```yaml
volumes:
  keycloak_db_data_prod:
    external: true
    name: keycloak_db_data  # Use existing volume
  app_db_data_prod:
    external: true
    name: app_db_data  # Use existing volume
  redis_data_prod:
    external: true
    name: redis_data  # Use existing volume
```

**Pros:**
- No data migration needed
- Immediate switch

**Cons:**
- Doesn't follow new naming convention
- Harder to distinguish staging vs production volumes
- If you later add staging, you'll need different names anyway

## Recommended Approach

**Use Option 1** (migrate to new volumes) because:
1. ✅ Clear naming convention (`*_prod` suffix)
2. ✅ Better separation between staging and production
3. ✅ Easier to identify volumes: `docker volume ls | grep eigentask`
4. ✅ Consistent with staging setup
5. ✅ Future-proof if you need to add more environments

## Migration Script

Here's a helper script to automate the migration:

```bash
#!/bin/bash
# migrate-volumes.sh - Migrate from old volumes to new production volumes

set -e

echo "Starting volume migration..."

# 1. Stop old services
echo "Stopping old services..."
docker compose down

# 2. Start new services (creates new volumes)
echo "Starting new services with new volumes..."
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml up -d

# 3. Wait for databases to be ready
echo "Waiting for databases to be ready..."
sleep 10

# 4. Migrate Keycloak database
echo "Migrating Keycloak database..."
# Add your migration commands here based on your setup

# 5. Migrate App database
echo "Migrating App database..."
# Add your migration commands here based on your setup

# 6. Restart services
echo "Restarting services..."
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml restart

echo "Migration complete! Verify your services are working before cleaning up old volumes."
```

## Rollback Plan

If something goes wrong:

1. **Stop new services**:
   ```bash
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.prod.yml down
   ```

2. **Start old services**:
   ```bash
   docker compose up -d
   ```

3. **Your old volumes are still intact** (they weren't deleted)

## After Migration

Once migration is complete and verified:

1. Update your deployment workflow to use `docker-compose.prod.yml`
2. Remove or archive the old `docker-compose.yml` (or keep it as backup)
3. Update any documentation referencing the old volume names
