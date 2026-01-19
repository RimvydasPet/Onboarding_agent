from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, collection_name: str = "onboarding_docs"):
        self.collection_name = collection_name
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.GOOGLE_API_KEY
        )
        self.vectorstore = None
        self._initialize_store()
    
    def _initialize_store(self):
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY
            )
            logger.info(f"Vector store initialized: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        if not documents:
            return []
        
        try:
            ids = self.vectorstore.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")
            return ids
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        try:
            if filter:
                results = self.vectorstore.similarity_search(
                    query, k=k, filter=filter
                )
            else:
                results = self.vectorstore.similarity_search(query, k=k)
            
            logger.info(f"Retrieved {len(results)} documents for query")
            return results
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        try:
            if filter:
                results = self.vectorstore.similarity_search_with_score(
                    query, k=k, filter=filter
                )
            else:
                results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            return results
        except Exception as e:
            logger.error(f"Similarity search with score failed: {e}")
            return []
    
    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[Document]:
        try:
            results = self.vectorstore.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
            )
            logger.info(f"MMR search retrieved {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"MMR search failed: {e}")
            return []
    
    def delete_collection(self):
        try:
            self.vectorstore.delete_collection()
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
    
    def get_collection_count(self) -> int:
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0
