"""Diagnostic script to test the RAG pipeline end-to-end."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from backend.rag.vector_store import VectorStore
from backend.rag.document_processor import DocumentProcessor
from backend.rag.initializer import load_internal_rules_documents
from langchain_core.documents import Document

print("=" * 60)
print("RAG DIAGNOSTIC")
print("=" * 60)

# 1. Check Internal rules folder path
print("\n--- Step 1: Check Internal rules folder ---")
initializer_path = Path(__file__).resolve().parent / "backend" / "rag" / "initializer.py"
internal_rules_path = Path(__file__).resolve().parent.parent / "Internal rules"
print(f"Script location: {Path(__file__).resolve()}")
print(f"Internal rules path: {internal_rules_path}")
print(f"Exists: {internal_rules_path.exists()}")

if internal_rules_path.exists():
    files = list(internal_rules_path.glob("*"))
    print(f"Files found: {len(files)}")
    for f in files:
        print(f"  - {f.name} ({f.suffix})")

# 2. Check what load_internal_rules_documents returns
print("\n--- Step 2: Load internal rules documents ---")
docs = load_internal_rules_documents()
print(f"Documents loaded: {len(docs)}")
for doc in docs:
    print(f"  - Source: {doc.metadata.get('source')}")
    print(f"    Origin: {doc.metadata.get('origin')}")
    print(f"    Content length: {len(doc.page_content)}")
    print(f"    First 100 chars: {doc.page_content[:100]}...")

# 3. Check vector store
print("\n--- Step 3: Check vector store ---")
vs = VectorStore()
count = vs.get_collection_count()
print(f"Vector store document count: {count}")

all_docs = vs.list_all_documents()
print(f"Unique sources: {len(all_docs)}")
for d in all_docs:
    print(f"  - Source: {d['source']}, Origin: {d['origin']}, Chunks: {d['chunks']}")

# 4. Test similarity search
print("\n--- Step 4: Test similarity search ---")
query = "IT Administrator Responsibilities"
results = vs.similarity_search(query, k=10)
print(f"Results for '{query}': {len(results)}")
for i, r in enumerate(results):
    print(f"  Result {i+1}:")
    print(f"    Source: {r.metadata.get('source')}")
    print(f"    Origin: {r.metadata.get('origin')}")
    print(f"    Score: {r.metadata.get('score', 'N/A')}")
    print(f"    Content: {r.page_content[:100]}...")

# 5. Test with another query
print("\n--- Step 5: Test 'Work environment' query ---")
query2 = "Work environment"
results2 = vs.similarity_search(query2, k=10)
print(f"Results for '{query2}': {len(results2)}")
for i, r in enumerate(results2):
    print(f"  Result {i+1}:")
    print(f"    Source: {r.metadata.get('source')}")
    print(f"    Origin: {r.metadata.get('origin')}")
    print(f"    Score: {r.metadata.get('score', 'N/A')}")
    print(f"    Content: {r.page_content[:100]}...")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
