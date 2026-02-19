from backend.rag.agentic_rag import AgenticRAG
from pathlib import Path
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)


def load_internal_rules_documents() -> list[Document]:
    """
    Load all markdown, PDF, and text files from the Internal rules folder.
    
    Returns:
        List of Document objects from the Internal rules folder
    """
    documents = []
    internal_rules_path = Path(__file__).resolve().parent.parent.parent.parent / "Internal rules"
    
    if not internal_rules_path.exists():
        logger.warning(f"Internal rules folder not found at {internal_rules_path}")
        return documents
    
    logger.info(f"Loading documents from {internal_rules_path}")
    
    for file_path in internal_rules_path.glob("*"):
        if not file_path.is_file():
            continue
        
        file_name = file_path.name
        file_ext = file_path.suffix.lower()
        
        if file_ext not in [".md", ".markdown", ".pdf", ".txt"]:
            continue
        
        try:
            if file_ext == ".pdf":
                try:
                    from PyPDF2 import PdfReader
                    with open(file_path, "rb") as f:
                        reader = PdfReader(f)
                        text = "\n".join(
                            page.extract_text() or "" for page in reader.pages
                        )
                except Exception as pdf_err:
                    logger.warning(f"Could not extract text from {file_name}: {pdf_err}")
                    continue
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            
            if text.strip():
                # Add filename to content for better searchability
                enhanced_content = f"Document: {file_name}\n\n{text}"
                doc = Document(
                    page_content=enhanced_content,
                    metadata={
                        "source": file_name,
                        "file_name": file_name,
                        "file_path": str(file_path),
                        "category": "internal_rules",
                        "origin": "internal_rules"
                    }
                )
                documents.append(doc)
                logger.info(f"Loaded {file_name}")
        
        except Exception as e:
            logger.error(f"Error loading {file_name}: {e}")
    
    logger.info(f"Loaded {len(documents)} documents from Internal rules folder")
    return documents


def initialize_rag_system(force_reload: bool = False) -> AgenticRAG:
    """
    Initialize the RAG system with internal rules documents and sample documents.
    
    Args:
        force_reload: If True, reset and reload all documents even if knowledge base exists
    
    Returns:
        Initialized AgenticRAG instance
    """
    logger.info("Initializing RAG system...")
    
    rag = AgenticRAG()
    
    try:
        current_count = rag.vector_store.get_collection_count()
        logger.info(f"Current vector store count: {current_count}")
        
        # Always reload to ensure internal rules are included
        if current_count == 0 or force_reload:
            if force_reload and current_count > 0:
                logger.info("Force reloading knowledge base - deleting existing collection...")
                try:
                    rag.reset_knowledge_base()
                    logger.info("Collection deleted successfully")
                except Exception as e:
                    logger.warning(f"Could not delete collection: {e}")
                # Recreate RAG instance to get fresh vector store
                rag = AgenticRAG()
            else:
                logger.info("Knowledge base is empty, loading documents...")
            
            documents = []
            
            # Load internal rules documents
            logger.info("Loading internal rules documents...")
            internal_docs = load_internal_rules_documents()
            logger.info(f"Loaded {len(internal_docs)} internal rules documents")
            documents.extend(internal_docs)
            
            if documents:
                logger.info(f"Initializing knowledge base with {len(documents)} documents...")
                rag.initialize_knowledge_base(documents)
                final_count = rag.vector_store.get_collection_count()
                logger.info(f"Knowledge base initialized with {final_count} chunks")
            else:
                logger.warning("No documents to load")
        else:
            logger.info(f"Knowledge base already contains {current_count} chunks")
    
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")
        logger.info("Attempting to load documents anyway...")
        try:
            documents = []
            internal_docs = load_internal_rules_documents()
            documents.extend(internal_docs)
            if documents:
                rag.initialize_knowledge_base(documents)
                logger.info(f"Loaded {len(documents)} documents in fallback mode")
        except Exception as e2:
            logger.error(f"Failed to load documents: {e2}")
    
    return rag
