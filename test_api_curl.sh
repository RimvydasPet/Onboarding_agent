#!/bin/bash

# Simple curl-based tests for the REST API
# Make sure the API is running: uvicorn api:app --reload --port 8000

echo "========================================"
echo "REST API Test Suite (curl)"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Health Check
echo "=== Test 1: Health Check ==="
curl -s "$BASE_URL/" | jq '.'
echo ""
echo ""

# Test 2: Detailed Health
echo "=== Test 2: Detailed Health ==="
curl -s "$BASE_URL/health" | jq '.'
echo ""
echo ""

# Test 3: Chat Endpoint
echo "=== Test 3: Chat Endpoint ==="
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I create a new project?",
    "session_id": "test-session-curl",
    "user_id": 1
  }' | jq '.'
echo ""
echo ""

# Test 4: Chat Without Session ID
echo "=== Test 4: Chat Without Session ID (auto-generated) ==="
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What features are available?",
    "user_id": 1
  }' | jq '.'
echo ""
echo ""

# Test 5: Follow-up in Same Session
echo "=== Test 5: Follow-up Message in Same Session ==="
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me more about that",
    "session_id": "test-session-curl",
    "user_id": 1
  }' | jq '.'
echo ""
echo ""

echo "========================================"
echo "Tests Complete!"
echo "========================================"
