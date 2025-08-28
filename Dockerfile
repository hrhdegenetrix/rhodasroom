# Multi-stage build for Rhoda AI Interface
# Optimized for Synology NAS deployment

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"

# Final stage - smaller image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    libportaudio2 \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/nltk_data /root/nltk_data

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p \
    /app/Logs \
    /app/Journal \
    /app/JournalEntries \
    /app/Rhoda_SOC \
    /app/Fleeting/Convos \
    /app/Memory/JSONs \
    /app/PodcastRecordings \
    /app/Datasets \
    /app/Errors/debug_prompts \
    /app/MigratedChatMemory \
    /app/heraldai/Posts

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting Rhoda AI Interface..."\n\
echo "Checking Redis connection..."\n\
python -c "import redis; r = redis.Redis(host=\"${REDIS_HOST:-127.0.0.1}\", port=6379); r.ping(); print(\"Redis connected successfully\")"\n\
echo "Initializing database..."\n\
python -c "import database; database.init_db()"\n\
echo "Starting Flask application with Gunicorn..."\n\
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 --timeout 300 --keep-alive 5 --log-level info app:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# Environment variables (can be overridden by docker-compose)
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=5)" || exit 1

# Run the startup script
CMD ["/app/start.sh"]