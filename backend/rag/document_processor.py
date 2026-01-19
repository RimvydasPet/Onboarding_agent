from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import hashlib


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def process_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        chunks = self.text_splitter.split_text(text)
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_id": self._generate_chunk_id(chunk, i)
            }
            documents.append(Document(page_content=chunk, metadata=doc_metadata))
        
        return documents
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        processed_docs = []
        for doc in documents:
            chunks = self.text_splitter.split_documents([doc])
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_id": self._generate_chunk_id(chunk.page_content, i)
                })
                processed_docs.append(chunk)
        return processed_docs
    
    def _generate_chunk_id(self, content: str, index: int) -> str:
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{content_hash}_{index}"
    
    def extract_metadata(self, text: str) -> Dict[str, Any]:
        metadata = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_code": "```" in text or "def " in text or "class " in text,
            "has_links": "http" in text or "www." in text
        }
        return metadata
