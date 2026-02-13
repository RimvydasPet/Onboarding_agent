from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class Reranker:
    """Rerank retrieved documents for better relevance."""
    
    def __init__(self):
        """Initialize the reranker with LLM."""
        self.llm = ChatGoogleGenerativeAI(
            model=str(getattr(settings, "gemini_model_id", None) or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash-latest") or "gemini-1.5-flash-latest"),
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
    
    def rerank_documents(
        self, 
        query: str, 
        documents: List[Document], 
        top_k: int = 5
    ) -> List[Document]:
        """
        Rerank documents based on relevance to query.
        
        Args:
            query: User's query
            documents: Retrieved documents
            top_k: Number of top documents to return
            
        Returns:
            Reranked list of documents
        """
        if not documents:
            return []
        
        if len(documents) <= top_k:
            return documents
        
        try:
            doc_summaries = []
            for i, doc in enumerate(documents):
                summary = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                doc_summaries.append(f"Doc {i}: {summary}")
            
            system_prompt = """You are a document relevance scorer.
Given a user query and document summaries, score each document's relevance from 0-10.
Return JSON array of scores: [score_for_doc0, score_for_doc1, ...]"""
            
            user_prompt = f"""Query: {query}

Documents:
{chr(10).join(doc_summaries)}

Score each document's relevance (0-10)."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            scores = json.loads(content)
            
            if len(scores) != len(documents):
                logger.warning(f"Score count mismatch: {len(scores)} vs {len(documents)}")
                return documents[:top_k]
            
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            reranked = [doc for doc, score in scored_docs[:top_k]]
            
            logger.info(f"Reranked {len(documents)} documents, returning top {top_k}")
            return reranked
            
        except Exception as e:
            logger.error(f"Error reranking documents: {e}")
            return documents[:top_k]
    
    def filter_by_metadata(
        self, 
        documents: List[Document], 
        stage: str = None,
        category: str = None
    ) -> List[Document]:
        """
        Filter documents by metadata.
        
        Args:
            documents: List of documents
            stage: Onboarding stage filter
            category: Category filter
            
        Returns:
            Filtered documents
        """
        filtered = documents
        
        if stage:
            filtered = [
                doc for doc in filtered 
                if doc.metadata.get('stage') == stage or not doc.metadata.get('stage')
            ]
        
        if category:
            filtered = [
                doc for doc in filtered 
                if doc.metadata.get('category') == category
            ]
        
        logger.info(f"Filtered {len(documents)} documents to {len(filtered)}")
        return filtered
