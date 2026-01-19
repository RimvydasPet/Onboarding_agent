from typing import List, Tuple
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0
        )
    
    def rerank_documents(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Document]:
        if not documents:
            return []
        
        if len(documents) <= top_k:
            return documents
        
        try:
            scored_docs = self._score_documents(query, documents)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            reranked = [doc for doc, score in scored_docs[:top_k]]
            logger.info(f"Reranked {len(documents)} documents to top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}, returning original documents")
            return documents[:top_k]
    
    def _score_documents(
        self,
        query: str,
        documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        scored_docs = []
        
        for doc in documents:
            score = self._calculate_relevance_score(query, doc)
            scored_docs.append((doc, score))
        
        return scored_docs
    
    def _calculate_relevance_score(self, query: str, document: Document) -> float:
        query_lower = query.lower()
        content_lower = document.page_content.lower()
        
        score = 0.0
        
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if query_words:
            overlap = len(query_words & content_words)
            score += (overlap / len(query_words)) * 0.4
        
        if query_lower in content_lower:
            score += 0.3
        
        content_length = len(document.page_content)
        if 200 <= content_length <= 1500:
            score += 0.2
        elif content_length < 200:
            score += 0.1
        
        metadata = document.metadata
        if metadata.get("chunk_index", 0) == 0:
            score += 0.1
        
        return min(score, 1.0)
    
    def validate_sources(self, documents: List[Document]) -> List[Document]:
        validated = []
        
        for doc in documents:
            if self._is_valid_source(doc):
                validated.append(doc)
        
        return validated
    
    def _is_valid_source(self, document: Document) -> bool:
        if not document.page_content or len(document.page_content.strip()) < 50:
            return False
        
        if document.page_content.count(" ") < 10:
            return False
        
        return True
    
    def add_citations(self, documents: List[Document]) -> List[Dict[str, any]]:
        citations = []
        
        for i, doc in enumerate(documents):
            citation = {
                "index": i + 1,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "chunk_id": doc.metadata.get("chunk_id", f"chunk_{i}"),
                "relevance": "high" if i < 2 else "medium" if i < 4 else "low"
            }
            citations.append(citation)
        
        return citations
