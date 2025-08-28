#!/bin/bash

echo "==========================================="
echo "Starting Rhoda AI Interface"
echo "==========================================="

# Set production environment
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Wait for Redis to be ready (if using local Redis container)
if [ "$REDIS_HOST" = "redis" ]; then
    echo "Waiting for Redis container to be ready..."
    for i in {1..30}; do
        if python -c "import redis; r = redis.Redis(host='${REDIS_HOST:-redis}', port=${REDIS_PORT:-6379}); r.ping()" 2>/dev/null; then
            echo "Redis is ready!"
            break
        fi
        echo "Waiting for Redis... (attempt $i/30)"
        sleep 2
    done
else
    echo "Using external Redis at $REDIS_HOST:$REDIS_PORT"
fi

# Test Redis connection
echo "Testing Redis connection..."
python -c "
import redis
import sys
try:
    r = redis.Redis(host='${REDIS_HOST:-127.0.0.1}', port=${REDIS_PORT:-6379}, decode_responses=True)
    r.ping()
    print('✓ Redis connection successful')
except Exception as e:
    print(f'✗ Redis connection failed: {e}')
    sys.exit(1)
"

# Initialize database
echo "Initializing SQLite database..."
python -c "
import database
database.init_db()
print('✓ Database initialized')
"

# Create required directories if they don't exist
echo "Ensuring data directories exist..."
python -c "
import os
dirs = [
    'Logs', 'Journal', 'JournalEntries', 'Rhoda_SOC', 
    'Fleeting', 'Fleeting/Convos', 'Memory', 'Memory/JSONs',
    'PodcastRecordings', 'Datasets', 'Errors', 'Errors/debug_prompts',
    'MigratedChatMemory', 'heraldai', 'heraldai/Posts'
]
for d in dirs:
    os.makedirs(d, exist_ok=True)
print('✓ All directories ready')
"

# Download NLTK data if not present
echo "Checking NLTK data..."
python -c "
import nltk
import os
nltk_data_path = '/root/nltk_data'
if not os.path.exists(nltk_data_path):
    print('Downloading NLTK data...')
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')
print('✓ NLTK data ready')
"

echo "==========================================="
echo "Starting Gunicorn with EventLet workers..."
echo "==========================================="

# Start the application with Gunicorn
# Using eventlet for WebSocket support
exec gunicorn \
    --worker-class eventlet \
    --workers 1 \
    --bind 0.0.0.0:5000 \
    --timeout 300 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --log-file - \
    app:app