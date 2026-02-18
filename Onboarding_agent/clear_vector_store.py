#!/usr/bin/env python3
"""
Clear the vector store to force re-indexing of all documents.
Run this script when you want to reset the RAG knowledge base.
"""
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_vector_store():
    """Delete the ChromaDB vector store directory."""
    chroma_db_path = Path(__file__).parent / "chroma_db"
    
    if chroma_db_path.exists():
        logger.info(f"Deleting vector store at {chroma_db_path}")
        shutil.rmtree(chroma_db_path)
        logger.info("✅ Vector store cleared successfully")
    else:
        logger.info(f"Vector store not found at {chroma_db_path}")

if __name__ == "__main__":
    clear_vector_store()
    print("\nVector store has been cleared.")
    print("The next time you run the app, all documents will be re-indexed.")
