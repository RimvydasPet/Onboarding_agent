#!/bin/bash
# Run Streamlit chat app with correct Python environment

cd "$(dirname "$0")"
python3.14 -m streamlit run simple_chat_app.py
