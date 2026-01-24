# Nginx Configuration

This directory contains nginx configuration files for the EigenTask deployment. These configs are stored in the repository for version control and easy deployment.

## File Structure

- `production.conf` - Production environment server blocks (HTTP only, Certbot will add SSL)
- `staging.conf` - Staging environment server blocks (HTTP only, Certbot will add SSL)
- `README.md` - This file

**Note**: These are the base HTTP configurations. After running Certbot, SSL blocks and redirects will be automatically added to these files on the server.

## Integration with Existing Setup

Your existing nginx configuration is managed by Certbot and stored in `/etc/nginx/conf.d/`. These config files in the repo represent the base HTTP configuration before Certbot adds SSL.

### Current State

You already have production configs set up with Certbot. The `production.conf` file in this repo documents your production setup for version control.

### Staging Setup (One-Time)

1. **Copy staging config to server**:
   ```bash
   # On your server
   sudo cp /opt/eigentask/nginx/staging.conf /etc/nginx/conf.d/staging.conf
   ```

2. **Test nginx configuration**:
   ```bash
   sudo nginx -t
   ```

3. **Reload nginx**:
   ```bash
   sudo systemctl reload nginx
   ```

4. **Get SSL certificates for staging domains**:
   ```bash
   sudo certbot --nginx \
     -d staging.eigentask.com \
     -d staging-api.eigentask.com \
     -d staging-auth.eigentask.com
   ```

   Certbot will automatically:
   - Add SSL configuration to each server block
   - Add HTTP to HTTPS redirects (matching your production pattern)
   - Set up certificate auto-renewal

### Syncing Production Config

If you make changes to your production nginx configs on the server, you can sync them back to the repo:

```bash
# On your server, copy the current production configs back to repo
# (Be careful - Certbot has modified these, so you may want to extract just the base HTTP blocks)
```

Or, if you want to start fresh with the repo version:

```bash
# Backup current configs first!
sudo cp /etc/nginx/conf.d/*.conf /etc/nginx/conf.d/backup/

# Copy production config (if you want to replace existing)
sudo cp /opt/eigentask/nginx/production.conf /etc/nginx/conf.d/production.conf

# Re-run Certbot to restore SSL configs
sudo certbot --nginx -d eigentask.com -d www.eigentask.com -d api.eigentask.com -d auth.eigentask.com
```

### How It Works

- Nginx reads all `.conf` files from `/etc/nginx/conf.d/`
- Your existing production configs remain untouched
- Staging config is in a separate file, so it's easy to manage
- Certbot modifies the staging.conf file just like it does with your production configs

## SSL Certificate Setup

After adding the staging server blocks, get SSL certificates for staging domains:

```bash
sudo certbot --nginx \
  -d staging.eigentask.com \
  -d staging-api.eigentask.com \
  -d staging-auth.eigentask.com
```

Certbot will automatically:
- Add SSL configuration to each server block
- Add HTTP to HTTPS redirects
- Set up certificate auto-renewal

## Deployment Integration

Since you're using Certbot-managed configs, nginx config updates should be handled carefully:

### Recommended Approach

1. **One-time setup**: Copy `staging.conf` to the server manually and run Certbot
2. **Future updates**: Only update manually if nginx config structure changes
3. **Certbot preservation**: Certbot will preserve your SSL config when it auto-renews certificates

### Optional: Automated Config Updates

If you want the deployment workflow to update nginx configs (when the file changes in git), you can add this step. **Warning**: This will overwrite Certbot's SSL blocks, so you'd need to re-run Certbot after.

```bash
# In deployment workflow (optional, not recommended)
sudo cp ${STAGING_DEPLOY_PATH}/nginx/staging.conf /etc/nginx/conf.d/staging.conf
sudo nginx -t && sudo systemctl reload nginx
```

**Better approach**: Keep nginx configs as infrastructure-as-code but update them manually when needed, since Certbot modifies them.

## Port Mapping

- **Production**: 3000 (web), 8000 (api), 8080 (keycloak)
- **Staging**: 3001 (web), 8001 (api), 8081 (keycloak)

This allows both environments to run on the same host without port conflicts.

## Testing

After setup, test the staging routes:

```bash
# Test HTTP (should redirect to HTTPS after Certbot)
curl -H "Host: staging.eigentask.com" http://localhost

# Test HTTPS (after SSL setup)
curl https://staging.eigentask.com
curl https://staging-api.eigentask.com
curl https://staging-auth.eigentask.com
```

## Conventional Storage

Storing nginx configs in the repository is a common practice (Infrastructure as Code):

- ✅ **Version controlled** - Changes are tracked and reviewable
- ✅ **Easy to review** - PRs can include nginx config changes
- ✅ **Documentation** - Shows how the infrastructure is configured
- ✅ **Reproducible** - Easy to set up on new servers
- ✅ **Testable** - Can validate configs before deploying

The configs are stored in `nginx/` directory at the repo root, which is a conventional location for infrastructure-as-code configurations. This follows the same pattern as:
- `docker-compose.yml` files
- CI/CD workflows in `.github/workflows/`
- Other infrastructure configuration files

## File Locations

- **Repository**: 
  - `nginx/production.conf` (version controlled, documents production setup)
  - `nginx/staging.conf` (version controlled)
- **Server**: 
  - `/etc/nginx/conf.d/production.conf` (or your existing production config files)
  - `/etc/nginx/conf.d/staging.conf` (after one-time setup)
  - All configs are managed by Certbot (SSL blocks added automatically)

## Why Store Production Config?

Even though your production config is already set up, storing it in the repo provides:

- **Documentation**: Shows exactly how production is configured
- **Version control**: Track changes to nginx config over time
- **Reproducibility**: Easy to set up production on a new server
- **Review process**: Nginx config changes can be reviewed in PRs
- **Disaster recovery**: If server configs are lost, you have a backup

**Note**: The repo version is the "source of truth" for the base HTTP configuration. Certbot modifies the server files to add SSL, but the base structure should match what's in the repo.
