# Keycloak Local Development Configuration

This directory contains Keycloak configuration for local development: realm export and custom themes.

## Themes

The `themes/` directory contains the **eigentask** custom theme (Keycloak 26 compliant). It extends the **base** theme (not keycloak.v2) so we use minimal styling from scratch—no PatternFly, no nuclear overrides. The login page matches the web app (white background, blue primary, logo above “Eigentask” text, tight spacing).

- **Login**: Login, logout, registration, error, and other auth pages use the eigentask theme.
- **Account**: Account console uses the same styling.
- **Email**: Email theme extends the default keycloak email theme.

The realm export configures the `eigentask` realm to use the eigentask theme for login, account, and email (admin console remains keycloak). The login theme uses centered logo + brand name and an optional slogan ("Plan. Schedule. Finish.") in the realm's displayNameHtml; if you already have the realm imported, re-import it (or update Realm Settings → General → Realm display name in Admin Console) to see the slogan.

**Local dev**: The dev override mounts `keycloak/themes` into the Keycloak container and disables theme/template caching (`--spi-theme-cache-themes=false`, `--spi-theme-cache-templates=false`, `--spi-theme-static-max-age=-1`), so theme changes (CSS, templates) are reflected on refresh without restarting Keycloak.

**Staging/Production**: The deploy script copies `keycloak/themes` to the environment themes directory on the server (`/etc/eigentask/staging/themes` or `/etc/eigentask/prod/themes`) before starting containers.

To customize the theme, edit CSS under `themes/eigentask/<type>/resources/css/eigentask.css` and templates under `themes/eigentask/<type>/templates/` as needed. See [Keycloak theme docs](https://www.keycloak.org/ui-customization/themes).

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
