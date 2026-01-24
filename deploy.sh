#!/bin/bash
# Deployment script for staging and production environments
# This script is executed on the GitHub Actions runner and SSHs to the server

set -euo pipefail

# Determine environment from ENVIRONMENT variable (set by workflow)
ENV="${ENVIRONMENT:-staging}"
ENV_DIR="${ENV}"

# Map environment to branch and compose file
if [ "$ENV" = "production" ]; then
    BRANCH="main"
    COMPOSE_FILE="docker-compose.prod.yml"
    NETWORK_NAME="eigentask-prod"
else
    BRANCH="staging"
    COMPOSE_FILE="docker-compose.staging.yml"
    NETWORK_NAME="eigentask-staging"
fi

echo "Deploying to ${ENV} environment (branch: ${BRANCH})"

# Deploy environment files
ssh ${DEPLOY_USER}@${DEPLOY_HOST} bash -s << EOF
    set -e
    ENV_PATH=\${ENV_FILE_PATH:-/etc/eigentask}
    ENV_DIR="\${ENV_PATH}/${ENV_DIR}"
    
    echo "Creating ${ENV} environment files directory..."
    sudo mkdir -p "\${ENV_DIR}"
    sudo chown \${USER}:\${USER} "\${ENV_DIR}"
    
    echo "Deploying environment files from GitHub Secrets..."
    
    # Write each env file (GitHub automatically masks secrets in logs)
    echo "$API_ENV" | sudo tee "\${ENV_DIR}/api.env" > /dev/null
    echo "$WEB_ENV" | sudo tee "\${ENV_DIR}/web.env" > /dev/null
    echo "$APP_DB_ENV" | sudo tee "\${ENV_DIR}/app-db.env" > /dev/null
    echo "$KEYCLOAK_ENV" | sudo tee "\${ENV_DIR}/keycloak.env" > /dev/null
    echo "$KEYCLOAK_DB_ENV" | sudo tee "\${ENV_DIR}/keycloak-db.env" > /dev/null
    
    # Set secure permissions
    sudo chmod 600 "\${ENV_DIR}"/*.env
    sudo chown \${USER}:\${USER} "\${ENV_DIR}"/*.env
    
    echo "Environment files deployed successfully!"
    ls -la "\${ENV_DIR}"
EOF

# Deploy application
ssh ${DEPLOY_USER}@${DEPLOY_HOST} << EOF
    set -e
    cd ${DEPLOY_PATH}
    
    ENV_PATH=\${ENV_FILE_PATH:-/etc/eigentask}
    
    echo "Verifying environment files exist..."
    REQUIRED_ENV_FILES=(
        "\${ENV_PATH}/${ENV_DIR}/api.env"
        "\${ENV_PATH}/${ENV_DIR}/web.env"
        "\${ENV_PATH}/${ENV_DIR}/app-db.env"
        "\${ENV_PATH}/${ENV_DIR}/keycloak.env"
        "\${ENV_PATH}/${ENV_DIR}/keycloak-db.env"
    )
    for env_file in "\${REQUIRED_ENV_FILES[@]}"; do
        if [ ! -f "\$env_file" ]; then
            echo "ERROR: Required env file missing: \$env_file"
            exit 1
        fi
    done
    echo "All required env files found."
    
    echo "Pulling latest code from ${BRANCH} branch..."
    git fetch origin
    git checkout ${BRANCH}
    git pull origin ${BRANCH}
    
    echo "Creating Docker network if it doesn't exist..."
    docker network create ${NETWORK_NAME} 2>/dev/null || true
    
    echo "Building and deploying ${ENV} containers..."
    ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} pull || true
    ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} build --no-cache
    ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} up -d
    
    echo "Waiting for services to be healthy..."
    sleep 10
    
    echo "Checking service status..."
    ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} ps
    
    echo "Deployment complete!"
EOF

# Verify deployment
ssh ${DEPLOY_USER}@${DEPLOY_HOST} << EOF
    cd ${DEPLOY_PATH}
    
    ENV_PATH=\${ENV_FILE_PATH:-/etc/eigentask}
    
    # Check if containers are running
    if ! ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} ps | grep -q "Up"; then
        echo "ERROR: Some containers are not running!"
        ENV_FILE_PATH=\${ENV_PATH} docker compose -f ${COMPOSE_FILE} ps
        exit 1
    fi
    
    echo "All services are running successfully"
EOF

echo "Deployment to ${ENV} completed successfully!"
