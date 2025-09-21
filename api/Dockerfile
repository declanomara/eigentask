# API Dockerfile
FROM python:3.13-slim

WORKDIR /app

# (Optional) system packages if needed by deps
# RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Install project (PEP 621/pyproject)
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install .

# Copy source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
