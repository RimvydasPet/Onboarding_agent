from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from backend.rag.document_processor import DocumentProcessor
from backend.rag.vector_store import VectorStore
from backend.rag.query_planner import QueryPlanner
from backend.rag.reranker import Reranker
import logging

logger = logging.getLogger(__name__)


class AgenticRAG:
    """Agentic RAG system with query planning and reranking."""
    
    def __init__(self):
        """Initialize the agentic RAG system."""
        self.document_processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        self.vector_store = VectorStore(collection_name="onboarding_docs")
        self.query_planner = QueryPlanner()
        self.reranker = Reranker()
        
        logger.info("Initialized AgenticRAG system")
    
    def initialize_knowledge_base(self, documents: List[Document]) -> None:
        """
        Initialize the knowledge base with documents.
        
        Args:
            documents: List of raw documents to add
        """
        logger.info(f"Initializing knowledge base with {len(documents)} documents")
        
        chunked_docs = self.document_processor.process_documents(documents)
        
        self.vector_store.add_documents(chunked_docs)
        
        count = self.vector_store.get_collection_count()
        logger.info(f"Knowledge base initialized with {count} chunks")
    
    def retrieve(
        self, 
        query: str, 
        current_stage: str = "welcome",
        top_k: int = 5,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query using agentic approach.
        
        Args:
            query: User's query
            current_stage: Current onboarding stage
            top_k: Number of documents to return
            use_reranking: Whether to use reranking
            
        Returns:
            Dictionary with retrieved documents and metadata
        """
        logger.info(f"Retrieving documents for query: {query[:100]}...")
        
        analysis = self.query_planner.analyze_query(query, current_stage)
        
        if not analysis.get("needs_retrieval", True):
            logger.info("Query doesn't need document retrieval")
            return {
                "documents": [],
                "analysis": analysis,
                "message": "No document retrieval needed"
            }
        
        search_queries = self.query_planner.generate_search_queries(query, analysis)
        
        all_documents = []
        seen_content = set()
        
        k_per_query = max(3, analysis.get("suggested_k", 5))
        
        for search_query in search_queries:
            docs = self.vector_store.similarity_search(
                query=search_query,
                k=k_per_query
            )
            
            for doc in docs:
                content_hash = hash(doc.page_content)
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    all_documents.append(doc)
        
        logger.info(f"Retrieved {len(all_documents)} unique documents from {len(search_queries)} queries")
        
        if use_reranking and len(all_documents) > top_k:
            categories = analysis.get("categories", [])
            if categories:
                filtered_docs = self.reranker.filter_by_metadata(
                    all_documents,
                    category=categories[0] if categories else None
                )
                if filtered_docs:
                    all_documents = filtered_docs
            
            final_documents = self.reranker.rerank_documents(
                query=query,
                documents=all_documents,
                top_k=top_k
            )
        else:
            final_documents = all_documents[:top_k]
        
        return {
            "documents": final_documents,
            "analysis": analysis,
            "num_retrieved": len(all_documents),
            "num_returned": len(final_documents),
            "search_queries": search_queries
        }
    
    def get_context_string(self, documents: List[Document]) -> str:
        """
        Convert documents to a context string for the LLM.
        
        Args:
            documents: List of documents
            
        Returns:
            Formatted context string
        """
        if not documents:
            return ""
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', 'unknown')
            category = doc.metadata.get('category', 'general')
            score = doc.metadata.get('score', 0.0)
            
            context_parts.append(
                f"[Source {i}: {source} | Category: {category} | Relevance: {score:.2f}]\n"
                f"{doc.page_content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def reset_knowledge_base(self) -> None:
        """Delete and reset the knowledge base."""
        self.vector_store.delete_collection()
        self.vector_store = VectorStore(collection_name="onboarding_docs")
        logger.info("Knowledge base reset")
