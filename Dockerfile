FROM python:3.11-slim

# Labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/mateof/yt-music-player-server"
LABEL org.opencontainers.image.description="YouTube Music API Backend"
LABEL org.opencontainers.image.licenses="MIT"

# Build argument for version
ARG VERSION=1.0.0
ENV APP_VERSION=${VERSION}

# Install FFmpeg for audio conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data and userdata directories
RUN mkdir -p /app/data /app/userdata

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
