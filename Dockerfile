FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies & install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists
RUN mkdir -p data user/memory

ENV PORT=5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Run Gunicorn with 1 worker and 2 threads to stay under Render 512MB limit (~120MB usage)
CMD exec gunicorn -w 1 --threads 2 -b 0.0.0.0:${PORT} main:app
