#!/bin/bash

# Run the FastAPI server for the AI Onboarding Assistant

echo "Starting AI Onboarding Assistant REST API..."
echo "API will be available at: http://localhost:8000"
echo "Interactive API docs at: http://localhost:8000/docs"
echo ""

uvicorn api:app --reload --port 8000
