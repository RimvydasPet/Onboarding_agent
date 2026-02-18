import streamlit as st
from typing import Any
from backend.admin.queries import AdminQueries
from backend.admin.utils import AdminUtils
from backend.database.connection import get_db
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class AdminDashboard:
    """Admin dashboard UI components and logic."""
    
    @staticmethod
    def render_developers_info(rag_system: Any, session_state: Any) -> None:
        """Render always-visible developers info section."""
        st.sidebar.markdown("### 👨‍💻 Developers Info")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.caption("**Session ID:**")
            st.text_input(
                "Session ID",
                value=session_state.session_id,
                key="admin_dev_session_id",
                label_visibility="collapsed",
                disabled=True,
            )
        
        with col2:
            st.caption("**Documents:**")
            try:
                doc_count = rag_system.vector_store.get_collection_count()
                st.metric("Indexed", doc_count)
            except Exception:
                st.metric("Indexed", "N/A")
        
        col3, col4 = st.sidebar.columns(2)
        with col3:
            st.caption("**AI Mode:**")
            st.text_input(
                "AI Mode",
                value="RAG + Agent",
                key="admin_dev_ai_mode",
                label_visibility="collapsed",
                disabled=True,
            )
        
        with col4:
            st.caption("**Web Search:**")
            provider = str(getattr(settings, "WEB_SEARCH_PROVIDER", "tavily") or "tavily").strip().lower()
            st.text_input(
                "Provider",
                value=provider,
                key="admin_dev_provider",
                label_visibility="collapsed",
                disabled=True,
            )
        
        st.sidebar.markdown("---")
    
    @staticmethod
    def render_onboarded_newcomers(db: Any) -> None:
        """Render onboarded newcomers section."""
        st.markdown("### 👥 Onboarded Newcomers")
        
        stats = AdminQueries.get_onboarding_stats(db)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", stats["total_users"])
        with col2:
            st.metric("Completed", stats["completed_users"])
        with col3:
            st.metric("In Progress", stats["in_progress_users"])
        with col4:
            st.metric("Completion Rate", f"{stats['completion_rate']}%")
        
        st.markdown("---")
        
        st.markdown("#### Recent Onboarded Users")
        recent_users = AdminQueries.get_recent_onboarded_users(db, limit=15)
        
        if recent_users:
            table_data = []
            for user in recent_users:
                table_data.append({
                    "Name": user["name"],
                    "Email": user["email"],
                    "Role": user["role"],
                    "Department": user["department"],
                    "Completed": AdminUtils.format_date(user["completed_at"]),
                })
            
            st.dataframe(table_data, use_container_width=True, hide_index=True)
        else:
            st.info("No onboarded users yet.")
        
        st.markdown("---")
        
        if st.button("📊 View All Onboarded Users", use_container_width=True, key="view_all_onboarded"):
            st.session_state.admin_view_all_onboarded = True
    
    @staticmethod
    def render_all_onboarded_users(db: Any) -> None:
        """Render full list of all onboarded users."""
        st.markdown("### 📋 All Onboarded Users")
        
        all_users = AdminQueries.get_all_onboarded_users(db)
        
        if all_users:
            table_data = []
            for user in all_users:
                table_data.append({
                    "Name": user["name"],
                    "Email": user["email"],
                    "Role": user["role"],
                    "Department": user["department"],
                    "Completed": AdminUtils.format_date(user["completed_at"]),
                    "Joined": AdminUtils.format_date(user["created_at"]),
                })
            
            st.dataframe(table_data, use_container_width=True, hide_index=True)
            
            st.caption(f"Total: {len(all_users)} users")
        else:
            st.info("No onboarded users yet.")
        
        if st.button("← Back to Dashboard", use_container_width=True, key="back_to_dashboard"):
            st.session_state.admin_view_all_onboarded = False
            st.rerun()
    
    @staticmethod
    def render_documentation_upload(rag_system: Any) -> None:
        """Render company documentation upload section."""
        st.markdown("### 📚 Company Documentation")
        
        tab1, tab2 = st.tabs(["Upload Documents", "Manage Files"])
        
        with tab1:
            st.markdown("#### Upload New Documents")
            
            col1, col2 = st.columns(2)
            with col1:
                upload_category = st.text_input(
                    "Category",
                    value="company_docs",
                    help="e.g., policies, procedures, guidelines",
                    key="admin_upload_category",
                )
            
            with col2:
                upload_stage = st.selectbox(
                    "Stage (optional)",
                    options=["", "welcome", "department_info", "key_responsibilities", "tools_systems", "training_needs"],
                    key="admin_upload_stage",
                    help="Assign to specific onboarding stage",
                )
            
            uploaded_files = st.file_uploader(
                "Upload .md, .pdf, or .txt files",
                type=["md", "markdown", "pdf", "txt"],
                accept_multiple_files=True,
                key="admin_upload_files",
            )
            
            if st.button("📤 Ingest Documents", use_container_width=True, key="admin_ingest_files"):
                if not uploaded_files:
                    st.warning("No files selected")
                else:
                    try:
                        from langchain_core.documents import Document
                    except Exception:
                        Document = None
                    
                    docs_to_add = []
                    saved = 0
                    
                    with st.spinner("Processing documents..."):
                        for f in uploaded_files:
                            success, file_path, upload_id = AdminUtils.save_uploaded_file(
                                f, 
                                category=upload_category or "company_docs",
                                stage=upload_stage
                            )
                            
                            if success:
                                saved += 1
                                
                                raw = f.getvalue() if hasattr(f, "getvalue") else f.read()
                                
                                if str(f.name).lower().endswith(".pdf"):
                                    text = AdminUtils.extract_pdf_text(raw)
                                else:
                                    text = raw.decode("utf-8", errors="replace")
                                
                                meta = AdminUtils.get_file_metadata(
                                    f.name,
                                    upload_id,
                                    upload_category or "company_docs",
                                    upload_stage
                                )
                                
                                if Document is not None:
                                    docs_to_add.append(Document(page_content=text, metadata=meta))
                                else:
                                    docs_to_add.append(
                                        rag_system.document_processor.create_document(
                                            content=text,
                                            metadata=meta,
                                            source=f.name
                                        )
                                    )
                        
                        if docs_to_add:
                            rag_system.initialize_knowledge_base(docs_to_add)
                    
                    st.success(f"✅ Ingested {len(docs_to_add)} document(s) and saved {saved} file(s)")
                    st.rerun()
        
        with tab2:
            st.markdown("#### Manage Uploaded Files")
            
            admin_uploads = AdminUtils.list_uploaded_admin_files(rag_system)
            
            if not admin_uploads:
                st.info("No admin-uploaded files yet.")
            else:
                upload_label_to_id = {
                    f"{u.get('file_name', 'unknown')} ({u.get('chunks', 0)} chunks)": u.get("upload_id")
                    for u in admin_uploads
                }
                
                selected_label = st.selectbox(
                    "Select file to manage",
                    options=list(upload_label_to_id.keys()),
                    key="admin_selected_upload",
                )
                
                selected_upload_id = upload_label_to_id.get(selected_label)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Delete from Index", use_container_width=True, key="admin_delete_upload"):
                        success, removed = AdminUtils.delete_uploaded_file(selected_upload_id, rag_system)
                        if success:
                            st.success(f"Removed {removed} chunk(s) from index")
                            st.rerun()
                        else:
                            st.error("Failed to delete file")
                
                with col2:
                    if st.button("📋 View Details", use_container_width=True, key="admin_view_upload"):
                        for u in admin_uploads:
                            if u.get("upload_id") == selected_upload_id:
                                st.json(u)
                                break
    
    @staticmethod
    def render_system_status(rag_system: Any) -> None:
        """Render system status and health checks."""
        st.markdown("### 🔧 System Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### RAG System")
            try:
                doc_count = rag_system.vector_store.get_collection_count()
                st.success(f"✅ {doc_count} documents indexed")
            except Exception as e:
                st.error(f"❌ RAG Error: {str(e)[:50]}")
        
        with col2:
            st.markdown("#### Web Search")
            provider = str(getattr(settings, "WEB_SEARCH_PROVIDER", "tavily") or "tavily").strip().lower()
            key_len = len(str(getattr(settings, "TAVILY_API_KEY", "") or "").strip())
            
            if key_len > 0:
                st.success(f"✅ {provider.upper()} configured")
            else:
                st.warning(f"⚠️ {provider.upper()} not configured")
        
        st.markdown("---")
