import streamlit as st
from pathlib import Path
from typing import List, Dict, Any
import uuid
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class AdminUtils:
    """Utility functions for admin operations."""
    
    @staticmethod
    def format_date(date_obj) -> str:
        """Format datetime object to readable string."""
        if not date_obj:
            return "N/A"
        return date_obj.strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def get_upload_directory() -> Path:
        """Get or create the upload directory for admin documents."""
        upload_root = Path(__file__).resolve().parent.parent.parent / "Internal rules"
        upload_root.mkdir(parents=True, exist_ok=True)
        return upload_root
    
    @staticmethod
    def save_uploaded_file(file_obj, category: str = "admin", stage: str = "") -> tuple[bool, str, str]:
        """
        Save uploaded file to disk.
        Returns: (success, file_path, upload_id)
        """
        try:
            upload_id = str(uuid.uuid4())
            upload_root = AdminUtils.get_upload_directory()
            
            file_name = str(getattr(file_obj, "name", "uploaded.md"))
            raw = file_obj.getvalue() if hasattr(file_obj, "getvalue") else file_obj.read()
            
            safe_name = Path(file_name).name
            if (upload_root / safe_name).exists():
                stem = Path(file_name).stem
                suffix = Path(file_name).suffix
                safe_name = f"{stem}_{upload_id[:8]}{suffix}"
            
            file_path = upload_root / safe_name
            file_path.write_bytes(raw)
            
            return True, str(file_path), upload_id
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, "", ""
    
    @staticmethod
    def extract_pdf_text(pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(pdf_bytes))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return ""
    
    @staticmethod
    def get_file_metadata(file_name: str, upload_id: str, category: str, stage: str = "") -> Dict[str, Any]:
        """Create metadata dict for uploaded file."""
        meta = {
            "origin": "admin_upload",
            "upload_id": upload_id,
            "file_name": Path(file_name).name,
            "category": category or "admin",
        }
        if stage:
            meta["stage"] = stage
        return meta
    
    @staticmethod
    def list_uploaded_admin_files(rag_system) -> List[Dict[str, Any]]:
        """List all admin-uploaded files from RAG system."""
        try:
            all_uploads = rag_system.vector_store.list_uploaded_files()
            admin_uploads = [
                u for u in all_uploads 
                if u.get("metadata", {}).get("origin") == "admin_upload"
            ]
            return admin_uploads
        except Exception as e:
            logger.error(f"Error listing uploads: {e}")
            return []
    
    @staticmethod
    def delete_uploaded_file(upload_id: str, rag_system) -> tuple[bool, int]:
        """
        Delete uploaded file from RAG index and disk.
        Returns: (success, chunks_removed)
        """
        try:
            removed = rag_system.vector_store.delete_by_upload_id(str(upload_id or ""))
            
            upload_root = AdminUtils.get_upload_directory()
            deleted_files = 0
            if upload_root.exists() and upload_id:
                for p in upload_root.glob(f"*{upload_id[:8]}*"):
                    try:
                        p.unlink()
                        deleted_files += 1
                    except Exception as e:
                        logger.warning(f"Could not delete {p}: {e}")
            
            return True, removed
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False, 0
