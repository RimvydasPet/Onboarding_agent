#!/bin/bash

echo "🚀 Starting Onboarding Agent Demo..."
echo ""

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q fastapi uvicorn python-jose passlib bcrypt > /dev/null 2>&1

echo ""
echo "✅ Starting FastAPI server..."
echo "📍 Open your browser to: http://localhost:8000"
echo ""

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
