from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from backend.rag.document_processor import DocumentProcessor
from backend.rag.vector_store import VectorStore
from backend.rag.query_planner import QueryPlanner
from backend.rag.reranker import Reranker
import logging

logger = logging.getLogger(__name__)


class AgenticRAG:
    """
    Agentic RAG system with query planning, multi-step retrieval, and reranking.
    
    Features:
    - Intelligent query analysis and planning
    - Multi-strategy retrieval (similarity, MMR)
    - Document reranking for relevance
    - Source validation and citation
    - Context-aware retrieval
    """
    
    def __init__(self, collection_name: str = "onboarding_docs"):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore(collection_name)
        self.query_planner = QueryPlanner()
        self.reranker = Reranker()
        logger.info("AgenticRAG initialized")
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> List[str]:
        """Process and add documents to the vector store."""
        if not texts:
            return []
        
        metadatas = metadatas or [{}] * len(texts)
        
        all_documents = []
        for text, metadata in zip(texts, metadatas):
            docs = self.document_processor.process_text(text, metadata)
            all_documents.extend(docs)
        
        ids = self.vector_store.add_documents(all_documents)
        logger.info(f"Added {len(all_documents)} document chunks from {len(texts)} sources")
        return ids
    
    def add_document_objects(self, documents: List[Document]) -> List[str]:
        """Process and add Document objects to the vector store."""
        processed_docs = self.document_processor.process_documents(documents)
        ids = self.vector_store.add_documents(processed_docs)
        logger.info(f"Added {len(processed_docs)} processed document chunks")
        return ids
    
    def retrieve(
        self,
        query: str,
        context: Dict[str, Any] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Agentic retrieval with query planning and reranking.
        
        Args:
            query: User query
            context: Additional context (user info, conversation history, etc.)
            top_k: Number of top documents to return
        
        Returns:
            Dictionary with retrieved documents, citations, and metadata
        """
        context = context or {}
        
        # Step 1: Analyze query
        analysis = self.query_planner.analyze_query(query, context)
        logger.info(f"Query analysis: {analysis}")
        
        # Step 2: Check if retrieval is needed
        if not self.query_planner.should_retrieve(query, analysis):
            return {
                "documents": [],
                "citations": [],
                "analysis": analysis,
                "retrieval_performed": False,
                "message": "No retrieval needed for this query"
            }
        
        # Step 3: Plan retrieval strategy
        strategy = self.query_planner.plan_retrieval_strategy(analysis)
        logger.info(f"Retrieval strategy: {strategy}")
        
        # Step 4: Generate search queries
        search_queries = self.query_planner.generate_search_queries(query, analysis)
        logger.info(f"Search queries: {search_queries}")
        
        # Step 5: Retrieve documents
        all_documents = []
        for search_query in search_queries:
            docs = self._retrieve_with_strategy(search_query, strategy)
            all_documents.extend(docs)
        
        # Remove duplicates based on content
        unique_docs = self._deduplicate_documents(all_documents)
        
        # Step 6: Rerank if needed
        if strategy.get("rerank", False) and len(unique_docs) > top_k:
            final_docs = self.reranker.rerank_documents(query, unique_docs, top_k)
        else:
            final_docs = unique_docs[:top_k]
        
        # Step 7: Validate sources
        validated_docs = self.reranker.validate_sources(final_docs)
        
        # Step 8: Generate citations
        citations = self.reranker.add_citations(validated_docs)
        
        return {
            "documents": validated_docs,
            "citations": citations,
            "analysis": analysis,
            "strategy": strategy,
            "retrieval_performed": True,
            "num_results": len(validated_docs)
        }
    
    def _retrieve_with_strategy(
        self,
        query: str,
        strategy: Dict[str, Any]
    ) -> List[Document]:
        """Retrieve documents using the specified strategy."""
        method = strategy.get("method", "similarity")
        k = strategy.get("k", 5)
        
        if method == "mmr":
            fetch_k = strategy.get("fetch_k", 20)
            return self.vector_store.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k
            )
        else:
            return self.vector_store.similarity_search(query, k=k)
    
    def _deduplicate_documents(self, documents: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content similarity."""
        if not documents:
            return []
        
        seen_contents = set()
        unique_docs = []
        
        for doc in documents:
            content_hash = hash(doc.page_content.strip())
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "total_documents": self.vector_store.get_collection_count(),
            "collection_name": self.vector_store.collection_name,
            "components": {
                "document_processor": "active",
                "vector_store": "active",
                "query_planner": "active",
                "reranker": "active"
            }
        }
    
    def clear_collection(self):
        """Clear all documents from the vector store."""
        self.vector_store.delete_collection()
        self.vector_store._initialize_store()
        logger.info("Collection cleared and reinitialized")
