#!/bin/bash
# SpendLens Startup Script for GitHub Codespaces

set -e

echo "🚀 Starting SpendLens..."
echo ""

# Kill any existing processes on ports 3000 and 8000
echo "🧹 Cleaning up existing processes..."
pkill -f "reflex run" || true
sleep 1

# Detect environment
if [ -n "$CODESPACE_NAME" ]; then
    echo "🔗 GitHub Codespaces detected: $CODESPACE_NAME"
    BACKEND_URL="https://${CODESPACE_NAME}-8000.app.github.dev"
    echo "📡 Backend URL: $BACKEND_URL"
    echo "🌐 Frontend URL: https://${CODESPACE_NAME}-3000.app.github.dev"
else
    echo "💻 Local development mode detected"
    BACKEND_URL="http://localhost:8000"
    echo "📡 Backend URL: $BACKEND_URL"
    echo "🌐 Frontend URL: http://localhost:3000"
fi

echo ""
echo "⏳ Starting Reflex app (this may take 30-60 seconds)..."
echo ""

# Start Reflex with the resolved configuration
python -m reflex run \
    --backend-host 0.0.0.0 \
    --backend-port 8000 \
    --frontend-port 3000
