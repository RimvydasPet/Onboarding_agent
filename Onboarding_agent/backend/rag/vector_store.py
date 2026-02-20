from typing import List, Dict, Any, Optional
import uuid
import chromadb
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for document retrieval."""
    
    def __init__(self, collection_name: str = "onboarding_docs", persist_directory: str = "./chroma_db"):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
        """
        if not documents:
            logger.warning("No documents to add")
            return
        
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        ids: List[str] = []
        for i, meta in enumerate(metadatas):
            upload_id = str(meta.get("upload_id") or "")
            source = str(meta.get("source") or "")
            chunk_id = meta.get("chunk_id")
            chunk_id_str = "" if chunk_id is None else str(chunk_id)
            if upload_id:
                ids.append(f"upload_{upload_id}_{chunk_id_str or i}")
            elif source:
                ids.append(f"source_{source}_{chunk_id_str or i}_{uuid.uuid4().hex}")
            else:
                ids.append(f"doc_{uuid.uuid4().hex}_{i}")
        
        embeddings = self.embeddings.embed_documents(texts)
        
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def similarity_search(
        self, 
        query: str, 
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            query: Query string
            k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of relevant Document objects
        """
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata
        )
        
        documents = []
        if results['documents'] and results['documents'][0]:
            for i, doc_text in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0.0
                
                metadata['score'] = 1 - distance
                
                documents.append(Document(
                    page_content=doc_text,
                    metadata=metadata
                ))
        
        logger.info(f"Retrieved {len(documents)} documents for query: {query[:50]}...")
        return documents

    def list_uploaded_files(self) -> List[Dict[str, Any]]:
        """List uploaded file groups based on metadata stored in ChromaDB."""

        try:
            data = self.collection.get(include=["metadatas"])
        except Exception as e:
            logger.error(f"Failed to list uploaded files: {e}")
            return []

        metadatas = data.get("metadatas") or []
        grouped: Dict[str, Dict[str, Any]] = {}
        for meta in metadatas:
            if not isinstance(meta, dict):
                continue
            # Include both "upload" and "admin_upload" origins
            origin = meta.get("origin") or ""
            if origin not in ("upload", "admin_upload"):
                continue
            upload_id = str(meta.get("upload_id") or "")
            if not upload_id:
                continue
            if upload_id not in grouped:
                grouped[upload_id] = {
                    "upload_id": upload_id,
                    "file_name": meta.get("file_name") or meta.get("source") or "unknown",
                    "category": meta.get("category") or "uploaded",
                    "stage": meta.get("stage") or "",
                    "chunks": 0,
                    "metadata": {"origin": origin},
                }
            grouped[upload_id]["chunks"] += 1

        return sorted(grouped.values(), key=lambda x: str(x.get("file_name") or ""))

    def delete_by_upload_id(self, upload_id: str) -> int:
        """Delete all chunks belonging to a given uploaded file."""

        upload_id = str(upload_id or "").strip()
        if not upload_id:
            return 0

        try:
            data = self.collection.get(where={"upload_id": upload_id}, include=[])
            ids = data.get("ids") or []
            if not ids:
                return 0
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} chunks for upload_id={upload_id}")
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to delete upload_id={upload_id}: {e}")
            return 0
    
    def delete_collection(self) -> None:
        """Delete the collection."""
        self.client.delete_collection(name=self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")
    
    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        return self.collection.count()
    
    def list_all_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the collection with their metadata."""
        try:
            data = self.collection.get(include=["metadatas"])
            metadatas = data.get("metadatas") or []
            
            # Group by source
            grouped = {}
            for meta in metadatas:
                if not isinstance(meta, dict):
                    continue
                source = str(meta.get("source", "unknown"))
                if source not in grouped:
                    grouped[source] = {
                        "source": source,
                        "category": meta.get("category", "unknown"),
                        "origin": meta.get("origin", "unknown"),
                        "chunks": 0
                    }
                grouped[source]["chunks"] += 1
            
            return sorted(grouped.values(), key=lambda x: x.get("source", ""))
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
