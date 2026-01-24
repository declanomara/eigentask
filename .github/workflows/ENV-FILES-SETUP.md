# Environment Files Automation Setup

This document explains how to set up automated deployment of environment files using GitHub Environments and Secrets.

## Overview

Instead of manually creating `.env` files on the server, the deployment workflows automatically create them from GitHub Environment Secrets. This provides:

- ✅ **Automated deployment** - No manual file creation needed
- ✅ **Environment isolation** - Separate secrets for staging and production
- ✅ **Secure storage** - Secrets stored in GitHub's encrypted secret store
- ✅ **Easy updates** - Update secrets in GitHub, next deployment applies them
- ✅ **Audit trail** - GitHub Actions logs show when secrets were deployed (but not their values)
- ✅ **Simpler configuration** - No base64 encoding needed, GitHub handles secret masking

## Required GitHub Environments

The workflows use GitHub Environments to organize secrets. You need to create two environments:

1. **`staging`** - For staging deployments
2. **`production`** - For production deployments

## Setting Up Environments

1. Go to: **Settings → Environments**
2. Click **"New environment"**
3. Create **`staging`** environment
4. Create **`production`** environment

## Required Secrets per Environment

For each environment, add the following secrets:

### Staging Environment Secrets

- `SSH_PRIVATE_KEY` - SSH private key for accessing the staging server
- `HOST` - Hostname or IP address of the staging server
- `USER` - SSH username for the staging server
- `DEPLOY_PATH` - (Optional) Path to deployment directory (defaults to `/opt/eigentask`)
- `API_ENV` - Complete contents of `/etc/eigentask/staging/api.env`
- `WEB_ENV` - Complete contents of `/etc/eigentask/staging/web.env`
- `APP_DB_ENV` - Complete contents of `/etc/eigentask/staging/app-db.env`
- `KEYCLOAK_ENV` - Complete contents of `/etc/eigentask/staging/keycloak.env`
- `KEYCLOAK_DB_ENV` - Complete contents of `/etc/eigentask/staging/keycloak-db.env`

### Production Environment Secrets

- `SSH_PRIVATE_KEY` - SSH private key for accessing the production server
- `HOST` - Hostname or IP address of the production server
- `USER` - SSH username for the production server
- `DEPLOY_PATH` - (Optional) Path to deployment directory (defaults to `/opt/eigentask`)
- `API_ENV` - Complete contents of `/etc/eigentask/prod/api.env`
- `WEB_ENV` - Complete contents of `/etc/eigentask/prod/web.env`
- `APP_DB_ENV` - Complete contents of `/etc/eigentask/prod/app-db.env`
- `KEYCLOAK_ENV` - Complete contents of `/etc/eigentask/prod/keycloak.env`
- `KEYCLOAK_DB_ENV` - Complete contents of `/etc/eigentask/prod/keycloak-db.env`

## How to Add Secrets

### Step 1: Create Your .env Files Locally

Create the env files with your actual values (see `DEPLOYMENT.md` for examples):

```bash
# staging-api.env (example)
DATABASE_URL=postgresql+asyncpg://user:password@eigentask-staging-app-db:5432/eigentask
REDIS_URL=redis://eigentask-staging-redis:6379/0
FRONTEND_ORIGIN=https://staging.eigentask.com
BACKEND_ORIGIN=https://staging-api.eigentask.com
# ... etc
```

### Step 2: Add Secrets to Environments

For each environment, add the secrets:

**For Staging Environment:**

1. Go to GitHub → Settings → Environments
2. Click on **`staging`** environment
3. In the "Secrets" section, click **"Add secret"**
4. For each secret:
   - Name: `API_ENV` (or `WEB_ENV`, `APP_DB_ENV`, etc.)
   - Value: Paste the entire contents of your corresponding `.env` file
   - Click **"Add secret"**

**For Production Environment:**

1. Go to GitHub → Settings → Environments
2. Click on **`production`** environment
3. Repeat the same process as staging

**Benefits of Environments:**
- Secrets are automatically scoped to the environment
- Same secret names (`API_ENV`, `HOST`, etc.) can be used in both environments with different values
- Cleaner workflow files (no `STAGING_` or `PROD_` prefixes needed)
- Better organization and security

### Step 3: Verify Deployment

On the next deployment, the workflow will:
1. Create the env file directories if they don't exist
2. Write each secret's content to the corresponding `.env` file
3. Set permissions to 600 (read/write for owner only)
4. Verify files exist before deploying containers

## Secret Content Format

The secret value should be the **exact contents** of the `.env` file, including:
- All variable assignments
- Comments (lines starting with `#`)
- Empty lines (if any)
- No trailing newline needed (but won't hurt)

**Example secret value for `API_ENV` in staging environment:**
```
DATABASE_URL=postgresql+asyncpg://user:pass@eigentask-staging-app-db:5432/eigentask
REDIS_URL=redis://eigentask-staging-redis:6379/0
FRONTEND_ORIGIN=https://staging.eigentask.com
BACKEND_ORIGIN=https://staging-api.eigentask.com
KEYCLOAK_URL=http://eigentask-staging-keycloak:8080
KEYCLOAK_PUBLIC_URL=https://staging-auth.eigentask.com
KEYCLOAK_REALM=eigentask
KEYCLOAK_CLIENT_ID=eigentask
CALLBACK_URL=https://staging-api.eigentask.com/auth/callback
SESSION_SECRET=your-actual-secret-here
COOKIE_DOMAIN=.eigentask.com
COOKIE_SECURE=true
```

## Updating Secrets

To update a secret value:

1. Go to GitHub → Settings → Environments
2. Click on the environment (`staging` or `production`)
3. Find the secret you want to update in the "Secrets" section
4. Click the **pencil icon** (edit)
5. Paste the new value
6. Click **"Update secret"**

The next deployment will automatically use the new value.

**Note**: There's no way to see the current value of a secret in GitHub (for security). Keep a secure backup of your secret values elsewhere if needed.

## Security Considerations

### ✅ What's Secure

- Secret values are encrypted at rest in GitHub
- Secrets are only exposed to the deployment workflow
- Secrets are never logged in GitHub Actions (they're masked)
- Files are created with 600 permissions (owner read/write only)
- Files are stored in `/etc/eigentask/` (not in the git repository)

### ⚠️ Important Notes

- **Secret rotation**: If you rotate a secret (e.g., change a password), update the environment secret immediately. The next deployment will use the new value.
- **Backup**: Keep a secure backup of your secret values. GitHub doesn't allow viewing secrets after creation.
- **Access control**: Only users with repository admin access can view/update environment secrets.
- **Audit**: GitHub Actions logs show when secrets were used, but not their values.
- **Environment protection**: You can optionally add protection rules to environments (required reviewers, wait timers, etc.) in Settings → Environments.

## Alternative Approaches

If you prefer not to use GitHub Environment Secrets for env files, you can:

1. **Manual setup** (one-time): Create files manually on the server, then disable the "Deploy environment files" step
2. **AWS Secrets Manager**: Store secrets in AWS Secrets Manager and fetch them during deployment
3. **HashiCorp Vault**: Use Vault for secret management
4. **Encrypted files in repo**: Use `git-crypt` or `SOPS` to store encrypted env files in the repo

For a single-host setup, GitHub Environment Secrets is the simplest and most secure option that doesn't require additional infrastructure.

## Troubleshooting

### Deployment fails: "Permission denied"
- Ensure the SSH user can use `sudo` without password for file operations
- Run: `sudo visudo` and add: `username ALL=(ALL) NOPASSWD: /usr/bin/tee, /bin/chmod, /bin/chown, /bin/mkdir`
- Or add the user to a group that has sudo access: `sudo usermod -aG wheel username`

### Base64 encoding issues
- The workflow uses base64 encoding to safely pass secrets through SSH
- If you see base64 errors, ensure `base64` command is available on both GitHub Actions runner and your server
- Amazon Linux 2023 includes `base64` by default

### Files created but containers can't read them
- Check file permissions: `ls -la /etc/eigentask/staging/`
- Should be `-rw-------` (600) and owned by the user running docker
- Fix: `sudo chmod 600 /etc/eigentask/staging/*.env && sudo chown $USER:$USER /etc/eigentask/staging/*.env`

### Secret value appears empty
- Verify the secret was created correctly in GitHub
- Check that you copied the entire file contents (including newlines)
- Re-create the secret if needed
