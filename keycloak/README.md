# Keycloak Local Development Configuration

This directory contains Keycloak configuration for local development.

## Realm Export

The `realm-export/` directory contains a Keycloak realm export that is automatically imported when Keycloak starts in development mode.

### Automatic Import

When you start the dev environment with `docker compose up`, Keycloak will:
1. Check if the `eigentask` realm exists
2. If it doesn't exist, import `realm-export/eigentask-realm.json`
3. If it already exists, skip the import (to preserve any manual changes)

### Pre-configured Resources

The realm export includes:

- **Realm**: `eigentask`
- **Client**: `eigentask` (public client)
  - Redirect URI: `http://localhost:8000/auth/callback`
  - Web origins: `http://localhost:3000`
- **Test Users**:
  - `testuser` / `password` (email: `test@example.com`)
  - `admin` / `admin` (email: `admin@example.com`)

### Modifying the Realm

If you need to modify the realm configuration:

1. **Option 1: Use Keycloak Admin Console**
   - Make changes in the admin console at `http://localhost:8080`
   - Export the realm: Realm Settings → Export
   - Replace `realm-export/eigentask-realm.json` with the exported file
   - Note: You'll need to delete the realm first or use `--import-realm` with `--override` flag

2. **Option 2: Edit the JSON directly**
   - Edit `realm-export/eigentask-realm.json`
   - Delete the Keycloak volume to force re-import:
     ```bash
     docker compose down -v keycloak_db_data_dev
     docker compose up -d
     ```

### Resetting Keycloak

To reset Keycloak to the default configuration:

```bash
# Stop and remove the Keycloak database volume
docker compose down -v keycloak_db_data_dev

# Start services again (realm will be re-imported)
docker compose up -d
```
