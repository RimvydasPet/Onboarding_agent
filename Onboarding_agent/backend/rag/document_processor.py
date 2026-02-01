from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and chunk documents for RAG."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        logger.info(f"Initialized DocumentProcessor with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """
        Process and chunk documents.
        
        Args:
            documents: List of raw documents
            
        Returns:
            List of chunked documents
        """
        if not documents:
            logger.warning("No documents to process")
            return []
        
        chunked_docs = self.text_splitter.split_documents(documents)
        
        for i, doc in enumerate(chunked_docs):
            doc.metadata['chunk_id'] = i
            doc.metadata['chunk_size'] = len(doc.page_content)
        
        logger.info(f"Processed {len(documents)} documents into {len(chunked_docs)} chunks")
        return chunked_docs
    
    def create_document(
        self, 
        content: str, 
        metadata: dict = None,
        source: str = "manual"
    ) -> Document:
        """
        Create a single document.
        
        Args:
            content: Document content
            metadata: Optional metadata
            source: Source identifier
            
        Returns:
            Document object
        """
        if metadata is None:
            metadata = {}
        
        metadata['source'] = source
        
        return Document(
            page_content=content,
            metadata=metadata
        )
