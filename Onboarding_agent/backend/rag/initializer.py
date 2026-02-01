from backend.rag.agentic_rag import AgenticRAG
from backend.rag.sample_documents import get_sample_documents
import logging

logger = logging.getLogger(__name__)


def initialize_rag_system() -> AgenticRAG:
    """
    Initialize the RAG system with sample documents.
    
    Returns:
        Initialized AgenticRAG instance
    """
    logger.info("Initializing RAG system...")
    
    rag = AgenticRAG()
    
    try:
        current_count = rag.vector_store.get_collection_count()
        
        if current_count == 0:
            logger.info("Knowledge base is empty, loading sample documents...")
            documents = get_sample_documents()
            rag.initialize_knowledge_base(documents)
            logger.info(f"Loaded {len(documents)} sample documents")
        else:
            logger.info(f"Knowledge base already contains {current_count} chunks")
    
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")
        logger.info("Attempting to load sample documents anyway...")
        try:
            documents = get_sample_documents()
            rag.initialize_knowledge_base(documents)
        except Exception as e2:
            logger.error(f"Failed to load sample documents: {e2}")
    
    return rag
