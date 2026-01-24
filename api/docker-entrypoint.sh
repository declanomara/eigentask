#!/bin/bash
set -euo pipefail

# Safe migration runner for Docker containers
# This script runs migrations before starting the application

echo "🔍 Checking database connection..."

# Wait for database to be ready (with timeout)
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if python -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('ERROR: DATABASE_URL not set')
        exit(1)
    try:
        engine = create_async_engine(db_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute('SELECT 1')
        await engine.dispose()
        print('✅ Database is ready')
        exit(0)
    except Exception as e:
        print(f'⏳ Waiting for database... ({e})')
        exit(1)

asyncio.run(check_db())
" 2>/dev/null; then
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ ERROR: Database not ready after $MAX_ATTEMPTS attempts"
    exit 1
fi

echo "📦 Running database migrations..."

# Check if we're using uv or pip
if command -v uv &> /dev/null; then
    MIGRATE_CMD="uv run alembic upgrade head"
    ALEMBIC_CMD="uv run alembic"
else
    MIGRATE_CMD="alembic upgrade head"
    ALEMBIC_CMD="alembic"
fi

# Check current migration state first (for better error messages)
echo "   Checking current migration state..."
CURRENT_REV=$($ALEMBIC_CMD current 2>&1 | head -1 || echo "unknown")
echo "   Current revision: $CURRENT_REV"

# Run migrations with error handling
if $MIGRATE_CMD; then
    echo "✅ Migrations completed successfully"
    # Show new current state
    NEW_REV=$($ALEMBIC_CMD current 2>&1 | head -1 || echo "unknown")
    if [ "$CURRENT_REV" != "$NEW_REV" ]; then
        echo "   Updated to: $NEW_REV"
    fi
else
    echo "❌ ERROR: Migration failed!"
    echo ""
    echo "   Current state: $CURRENT_REV"
    echo "   This is a safety check - the application will not start with failed migrations."
    echo ""
    echo "   Troubleshooting:"
    echo "   1. Check migration files in api/alembic/versions/"
    echo "   2. Verify database connection and permissions"
    echo "   3. Review migration history: $ALEMBIC_CMD history"
    echo "   4. Check for conflicting migrations or manual schema changes"
    exit 1
fi

echo "🚀 Starting application..."
exec "$@"
