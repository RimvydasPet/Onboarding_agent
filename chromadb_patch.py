"""
Compatibility patch for ChromaDB 0.5.x with Pydantic v2 and Python 3.14.
Fixes the 'unable to infer type for attribute chroma_server_nofile' error.

This patch must be imported before any ChromaDB-related imports.
"""
import os
import sys
import warnings

# Suppress the Pydantic v1 compatibility warning for Python 3.14
warnings.filterwarnings('ignore', message='.*Pydantic V1.*Python 3.14.*')

# Set all ChromaDB environment variables to bypass config issues
os.environ.setdefault("CHROMA_SERVER_NOFILE", "65536")
os.environ.setdefault("CHROMA_SERVER_HOST", "localhost")
os.environ.setdefault("CHROMA_SERVER_HTTP_PORT", "8000")
os.environ.setdefault("IS_PERSISTENT", "TRUE")

# Disable telemetry to avoid additional config issues
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

print("✓ ChromaDB compatibility patch applied (Python 3.14 + Pydantic v2)")
