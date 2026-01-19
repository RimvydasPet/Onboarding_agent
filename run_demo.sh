#!/bin/bash

echo "🚀 Starting Onboarding Agent Streamlit Demo..."
echo ""

# Install required dependencies
echo "📦 Installing dependencies..."
pip install -q streamlit email-validator 2>/dev/null

echo ""
echo "✅ Launching Streamlit app..."
echo "📍 The app will open in your browser automatically"
echo ""

streamlit run demo_app.py
