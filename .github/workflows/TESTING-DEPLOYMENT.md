# Testing Staging Deployment

This guide explains how to test the staging deployment workflow.

## Prerequisites

Before testing, ensure you have:

1. **GitHub Secrets configured** (see `ENV-FILES-SETUP.md`):
   - `STAGING_SSH_PRIVATE_KEY`
   - `STAGING_HOST`
   - `STAGING_USER`
   - `STAGING_DEPLOY_PATH` (optional, defaults to `/opt/eigentask`)
   - `STAGING_API_ENV`
   - `STAGING_WEB_ENV`
   - `STAGING_APP_DB_ENV`
   - `STAGING_KEYCLOAK_ENV`
   - `STAGING_KEYCLOAK_DB_ENV`

2. **Server prepared**:
   - Docker and Docker Compose v2 installed
   - Git installed
   - Repository cloned in deployment directory
   - SSH access configured
   - User has permissions to run Docker commands

3. **Network access**:
   - GitHub Actions runner can SSH to your server
   - Server can pull from GitHub (for `git pull`)

## Testing Methods

### Method 1: Manual Trigger (Recommended for First Test)

The workflow supports `workflow_dispatch`, allowing you to manually trigger it:

1. **Go to GitHub Actions**:
   - Navigate to: `https://github.com/declanomara/eigentask/actions`
   - Click on "Deploy to Staging" workflow
   - Click "Run workflow" button (top right)
   - Select the branch (use your feature branch or `staging`)
   - Click "Run workflow"

2. **Monitor the workflow**:
   - Watch the workflow run in real-time
   - Check each step for errors
   - Review logs if any step fails

3. **Verify on server**:
   ```bash
   ssh user@your-staging-server
   cd /opt/eigentask
   
   # Check environment files were created
   ls -la /etc/eigentask/staging/
   
   # Check containers are running
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml ps
   
   # Check logs
   ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml logs
   ```

### Method 2: Push to Staging Branch

For a more realistic test (simulates actual deployment):

1. **Merge your feature branch to staging** (or push directly to staging):
   ```bash
   git checkout staging
   git pull origin staging
   git merge feature/your-branch
   git push origin staging
   ```

2. **CI workflow runs first**:
   - The "CI" workflow will run automatically
   - Wait for it to complete successfully

3. **Deployment triggers automatically**:
   - Once CI passes, "Deploy to Staging" workflow triggers
   - Monitor in GitHub Actions tab

4. **Verify deployment**:
   - Same verification steps as Method 1

### Method 3: Test on a Separate Test Branch

If you want to test without affecting staging:

1. **Create a test branch**:
   ```bash
   git checkout -b test/deployment-test staging
   git push origin test/deployment-test
   ```

2. **Manually trigger workflow**:
   - Use Method 1, but select `test/deployment-test` as the branch
   - Note: The workflow condition checks for `staging` branch in `workflow_run`, but `workflow_dispatch` works on any branch

3. **Clean up after testing**:
   ```bash
   git branch -d test/deployment-test
   git push origin --delete test/deployment-test
   ```

## What to Verify

### 1. Environment Files Created

```bash
ssh user@staging-server
ls -la /etc/eigentask/staging/

# Should see:
# - api.env (permissions: 600)
# - web.env (permissions: 600)
# - app-db.env (permissions: 600)
# - keycloak.env (permissions: 600)
# - keycloak-db.env (permissions: 600)
```

### 2. Containers Running

```bash
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml ps

# Should show all services as "Up":
# - eigentask-staging-keycloak-db
# - eigentask-staging-keycloak
# - eigentask-staging-app-db
# - eigentask-staging-redis
# - eigentask-staging-api
# - eigentask-staging-web
```

### 3. Services Healthy

```bash
# Check Keycloak health
curl http://localhost:8081/health/ready

# Check API health (if you have a health endpoint)
curl http://localhost:8001/health

# Check Web (should return HTML)
curl http://localhost:3001
```

### 4. Volumes Created

```bash
docker volume ls | grep eigentask-staging

# Should see:
# - eigentask-staging_keycloak_db_data_staging
# - eigentask-staging_app_db_data_staging
# - eigentask-staging_redis_data_staging
```

### 5. Network Created

```bash
docker network ls | grep eigentask-staging

# Should see:
# - eigentask-staging
```

### 6. Code Updated

```bash
cd /opt/eigentask
git log -1 --oneline

# Should show the latest commit from your branch
```

## Common Issues and Troubleshooting

### Issue: "Required env file missing"

**Symptom**: Deployment fails with error about missing env files

**Cause**: GitHub Secrets not configured or empty

**Fix**:
1. Check GitHub Secrets are created: Settings → Secrets and variables → Actions
2. Verify secret names match exactly (case-sensitive)
3. Ensure secret values contain the full .env file contents
4. Re-run the workflow

### Issue: "Permission denied" during file creation

**Symptom**: SSH step fails with permission errors

**Cause**: SSH user doesn't have sudo access or can't write to `/etc/eigentask/`

**Fix**:
```bash
# On server, ensure user has sudo access
sudo visudo
# Add: username ALL=(ALL) NOPASSWD: /usr/bin/tee, /bin/chmod, /bin/chown, /bin/mkdir

# Or create directory with proper permissions
sudo mkdir -p /etc/eigentask/staging
sudo chown $USER:$USER /etc/eigentask/staging
```

### Issue: "Container not found" or "Network not found"

**Symptom**: Docker Compose can't find containers/networks

**Cause**: Previous deployment left things in inconsistent state

**Fix**:
```bash
# Clean up and redeploy
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml down
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml up -d
```

### Issue: "Connection refused" when accessing services

**Symptom**: Services are running but not accessible

**Cause**: Port conflicts or services not fully started

**Fix**:
```bash
# Check if ports are in use
sudo netstat -tulpn | grep -E ':(3001|8001|8081)'

# Check container logs
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml logs

# Restart services
ENV_FILE_PATH=/etc/eigentask docker compose -f docker-compose.staging.yml restart
```

### Issue: "Base64: invalid input"

**Symptom**: Environment file deployment fails with base64 error

**Cause**: Secret content has invalid characters or encoding

**Fix**:
1. Verify secret content is plain text (no binary data)
2. Ensure secret contains complete .env file (all lines)
3. Check for hidden characters or encoding issues
4. Re-create the secret with clean content

### Issue: Workflow doesn't trigger automatically

**Symptom**: Pushing to staging doesn't trigger deployment

**Cause**: CI workflow must complete first, or workflow_run condition not met

**Fix**:
1. Check CI workflow completed successfully
2. Verify you're pushing to `staging` branch (not a feature branch)
3. Use manual trigger (`workflow_dispatch`) to test immediately
4. Check workflow conditions in `deploy-staging.yml`

## Testing Checklist

Before considering the deployment "working", verify:

- [ ] GitHub Secrets are configured correctly
- [ ] Manual workflow trigger works
- [ ] Environment files are created with correct permissions (600)
- [ ] All containers start successfully
- [ ] Services are accessible on expected ports
- [ ] Volumes are created and persistent
- [ ] Network is created and isolated
- [ ] Code is updated to latest commit
- [ ] Services respond to health checks
- [ ] Logs show no critical errors
- [ ] Automatic trigger works (push to staging after CI passes)

## Dry Run Testing

For a safer first test, you can modify the workflow temporarily to add a "dry run" mode:

1. Add an environment variable check
2. Skip actual deployment steps if `DRY_RUN=true`
3. Only verify prerequisites and show what would be deployed

However, the current workflow doesn't have this built-in. For now, use Method 1 (manual trigger) on a test branch for the safest first test.

## Next Steps After Successful Test

Once staging deployment is verified:

1. **Test production deployment** (if ready):
   - Similar process but with production secrets
   - More careful verification required

2. **Set up monitoring**:
   - Monitor deployment success/failure rates
   - Set up alerts for failed deployments

3. **Document any server-specific quirks**:
   - Add notes to `DEPLOYMENT.md` if you encounter issues
   - Update troubleshooting section

4. **Regular testing**:
   - Test deployments regularly to catch issues early
   - Verify after major changes to deployment workflow
