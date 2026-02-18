"""Test full RAG initialization and search."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from backend.rag.initializer import initialize_rag_system

print("Initializing RAG system with force_reload=True...")
rag = initialize_rag_system(force_reload=True)

count = rag.vector_store.get_collection_count()
print(f"\nVector store count after init: {count}")

docs = rag.vector_store.list_all_documents()
print(f"Unique sources: {len(docs)}")
for d in docs:
    print(f"  - {d['source']} (origin={d['origin']}, chunks={d['chunks']})")

print("\n--- Search: 'IT Administrator Responsibilities' ---")
results = rag.vector_store.similarity_search("IT Administrator Responsibilities", k=5)
print(f"Results: {len(results)}")
for i, r in enumerate(results):
    print(f"  {i+1}. source={r.metadata.get('source')}, origin={r.metadata.get('origin')}, score={r.metadata.get('score', 'N/A')}")
    print(f"     {r.page_content[:120]}...")

print("\n--- Search: 'Work environment' ---")
results2 = rag.vector_store.similarity_search("Work environment", k=5)
print(f"Results: {len(results2)}")
for i, r in enumerate(results2):
    print(f"  {i+1}. source={r.metadata.get('source')}, origin={r.metadata.get('origin')}, score={r.metadata.get('score', 'N/A')}")
    print(f"     {r.page_content[:120]}...")

print("\nDONE")
