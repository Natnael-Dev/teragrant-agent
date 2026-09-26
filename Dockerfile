# Production container for TeraGrant Agent
# Compatible with Hugging Face Spaces (port 7860), Render, Fly.io, and local Docker
FROM python:3.11-slim

WORKDIR /app

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir sqlalchemy>=2.0.0

# Copy application source code
COPY . .

# Default port: 7860 for Hugging Face Spaces; overridden by $PORT on Render / cloud providers
ENV PORT=7860
EXPOSE 7860

# Start FastAPI application
CMD sh -c "uvicorn app.server:app --host 0.0.0.0 --port ${PORT}"
