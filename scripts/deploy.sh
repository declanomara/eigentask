#!/bin/bash
# Deployment script for staging and production environments
# This script is executed on the GitHub Actions runner and SSHs to the server

set -euo pipefail

# Determine environment from ENVIRONMENT variable (set by workflow)
ENV="${ENVIRONMENT:-staging}"
ENV_DIR="${ENV}"

# Use the branch that triggered the deployment (or default based on environment)
if [ -n "${GITHUB_REF_NAME:-}" ]; then
    DEPLOY_BRANCH="${GITHUB_REF_NAME}"
elif [ "$ENV" = "production" ]; then
    DEPLOY_BRANCH="main"
else
    DEPLOY_BRANCH="staging"
fi

# Map environment to compose files (base + overlay) and network
if [ "$ENV" = "production" ]; then
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    NETWORK_NAME="eigentask-prod"
else
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.staging.yml"
    NETWORK_NAME="eigentask-staging"
fi

echo "Deploying to ${ENV} environment (branch: ${DEPLOY_BRANCH})"

# Env files must already exist on the server at /etc/eigentask/production/ and /etc/eigentask/staging/
# Deploy application
ssh ${DEPLOY_USER}@${DEPLOY_HOST} << EOF
    set -e
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
    
    echo "Checking if deployment directory exists and is a git repository..."
    if [ ! -d "${DEPLOY_PATH}" ]; then
        echo "Deployment directory does not exist. Creating parent directory and cloning repository..."
        mkdir -p $(dirname ${DEPLOY_PATH})
        git clone https://github.com/${GITHUB_REPOSITORY:-declanomara/eigentask}.git ${DEPLOY_PATH}
        cd ${DEPLOY_PATH}
        git checkout ${DEPLOY_BRANCH} || git checkout -b ${DEPLOY_BRANCH} origin/${DEPLOY_BRANCH} || git checkout ${GITHUB_SHA}
    elif [ ! -d "${DEPLOY_PATH}/.git" ]; then
        echo "Directory exists but is not a git repository. Removing and cloning..."
        rm -rf ${DEPLOY_PATH}
        git clone https://github.com/${GITHUB_REPOSITORY:-declanomara/eigentask}.git ${DEPLOY_PATH}
        cd ${DEPLOY_PATH}
        git checkout ${DEPLOY_BRANCH} || git checkout -b ${DEPLOY_BRANCH} origin/${DEPLOY_BRANCH} || git checkout ${GITHUB_SHA}
    else
        echo "Directory is a git repository. Pulling latest code from ${DEPLOY_BRANCH} branch..."
        cd ${DEPLOY_PATH}
        git fetch origin
        # Try to checkout the branch, fallback to specific commit if branch doesn't exist
        if git show-ref --verify --quiet refs/remotes/origin/${DEPLOY_BRANCH}; then
            git checkout ${DEPLOY_BRANCH}
            git pull origin ${DEPLOY_BRANCH}
        else
            echo "Branch ${DEPLOY_BRANCH} doesn't exist remotely, checking out commit ${GITHUB_SHA}"
            git checkout ${GITHUB_SHA}
        fi
    fi
    
    echo "Copying Keycloak themes to environment themes directory..."
    mkdir -p "\${ENV_PATH}/${ENV_DIR}/themes"
    cp -r keycloak/themes/* "\${ENV_PATH}/${ENV_DIR}/themes/"
    echo "Keycloak themes deployed."
    
    echo "Ensuring Docker network exists with correct labels..."
    # Remove network if it exists without proper Compose labels, then let Compose create it
    if docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
        if ! docker network inspect ${NETWORK_NAME} | grep -q "com.docker.compose.network"; then
            echo "Removing existing network ${NETWORK_NAME} (missing Compose labels)..."
            docker network rm ${NETWORK_NAME} 2>/dev/null || true
        fi
    fi
    
    echo "Checking disk space..."
    df -h
    
    echo "Cleaning up Docker to free space (images only, never volumes)..."
    docker system prune -af || true
    
    echo "Checking disk space..."
    df -h
    
    echo "Checking Docker Buildx version..."
    docker buildx version || echo "Buildx not installed or outdated"
    
    echo "Building and deploying ${ENV} containers..."
    ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} pull || true
    
    # Use buildx if available and version is sufficient, otherwise use regular build
    if docker buildx version 2>/dev/null | grep -q "v0\.[1-9][7-9]\|v[1-9]"; then
        echo "Using Docker Buildx for build..."
        ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} build
    else
        echo "Buildx not available or version too old, using regular build..."
        ENV_FILE_PATH=\${ENV_PATH} DOCKER_BUILDKIT=0 docker compose ${COMPOSE_FILES} build
    fi
    
    ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} up -d
    
    echo "Waiting for services to be healthy..."
    sleep 10
    
    echo "Checking service status..."
    ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} ps
    
    echo "Deployment complete!"
EOF

# Verify deployment
ssh ${DEPLOY_USER}@${DEPLOY_HOST} << EOF
    cd ${DEPLOY_PATH}
    
    ENV_PATH=\${ENV_FILE_PATH:-/etc/eigentask}
    
    # Check if containers are running
    if ! ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} ps | grep -q "Up"; then
        echo "ERROR: Some containers are not running!"
        ENV_FILE_PATH=\${ENV_PATH} docker compose ${COMPOSE_FILES} ps
        exit 1
    fi
    
    echo "All services are running successfully"
EOF

echo "Deployment to ${ENV} completed successfully!"
