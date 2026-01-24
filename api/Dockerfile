# API Dockerfile - Production
FROM python:3.13-slim

WORKDIR /app

# Install curl and uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Install project (PEP 621/pyproject)
# Copy dependency files and package structure for Docker layer caching
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/
RUN uv sync

# Copy remaining source files (alembic migrations, main entrypoint, etc.)
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

# Use entrypoint to run migrations before starting
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
