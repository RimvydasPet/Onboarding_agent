"""Initialize the RAG system with sample documents."""

from backend.rag.agentic_rag import AgenticRAG
from backend.rag.sample_documents import get_sample_documents
import logging

logger = logging.getLogger(__name__)


def initialize_rag_system(force_reload: bool = False) -> AgenticRAG:
    """
    Initialize the RAG system and load sample documents.
    
    Args:
        force_reload: If True, clear existing collection and reload documents
    
    Returns:
        Initialized AgenticRAG instance
    """
    rag = AgenticRAG()
    
    current_count = rag.get_stats()["total_documents"]
    
    if force_reload or current_count == 0:
        if force_reload and current_count > 0:
            logger.info("Force reload: clearing existing collection")
            rag.clear_collection()
        
        logger.info("Loading sample onboarding documents...")
        documents = get_sample_documents()
        
        texts = [doc["content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        rag.add_documents(texts, metadatas)
        
        stats = rag.get_stats()
        logger.info(f"RAG system initialized with {stats['total_documents']} document chunks")
    else:
        logger.info(f"RAG system already initialized with {current_count} documents")
    
    return rag


def test_rag_system():
    """Test the RAG system with sample queries."""
    rag = initialize_rag_system()
    
    test_queries = [
        "How do I create a new project?",
        "What are the keyboard shortcuts?",
        "I can't log in to my account",
        "Tell me about the mobile app",
        "What security features do you have?"
    ]
    
    print("\n" + "="*60)
    print("Testing RAG System")
    print("="*60 + "\n")
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        result = rag.retrieve(query, top_k=3)
        
        print(f"Analysis: {result['analysis']['intent']} - {result['analysis']['topic']}")
        print(f"Retrieved: {result['num_results']} documents")
        
        if result['citations']:
            print("\nTop Result:")
            print(result['citations'][0]['content'][:200] + "...")
        
        print()
    
    print("="*60)
    print("RAG System Test Complete")
    print("="*60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_rag_system()
