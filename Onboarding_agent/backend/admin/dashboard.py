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

        if st.button("🧪 Seed 5 Mock Users", use_container_width=True, key="seed_mock_users"):
            result = AdminUtils.seed_mock_onboarding_users(db)
            st.success(
                f"Mock users ready: total={result['total']} (created={result['created']}, updated={result['updated']})"
            )
            st.rerun()
        
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
    def render_newcomers_in_progress(db: Any) -> None:
        """Render newcomers currently in onboarding progress."""
        st.markdown("### 🆕 Newcomers In Progress")
        
        newcomers = AdminQueries.get_newcomers_in_progress(db, limit=15)
        
        if newcomers:
            st.info(f"📌 {len(newcomers)} newcomer(s) currently in onboarding")
            
            # Header row
            h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 2.5, 1.5, 1.5, 1.5, 1.5, 1.2])
            for col, label in zip(
                [h1, h2, h3, h4, h5, h6, h7],
                ["Name", "Email", "Role", "Dept", "Stage", "Updated", "Actions"]
            ):
                col.markdown(f"**{label}**")
            st.markdown('<hr style="margin:4px 0 8px 0"/>', unsafe_allow_html=True)
            
            # One row per user with reset button
            for idx, user in enumerate(newcomers):
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 2.5, 1.5, 1.5, 1.5, 1.5, 1.2])
                c1.write(user["name"])
                c2.write(user["email"])
                c3.write(user["role"])
                c4.write(user["department"])
                c5.write(user["current_stage"].replace("_", " ").title())
                c6.write(AdminUtils.format_date(user["updated_at"]))
                with c7:
                    if st.button("🔄 Reset", key=f"reset_inprog_{idx}", use_container_width=True):
                        st.session_state[f"confirm_reset_{user['user_id']}"] = True
                
                # Confirmation dialog
                if st.session_state.get(f"confirm_reset_{user['user_id']}", False):
                    with st.container():
                        st.warning(f"⚠️ Are you sure you want to reset onboarding for **{user['name']}** ({user['email']})? This will clear all progress and conversation history.")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes, Reset", key=f"confirm_yes_{user['user_id']}", use_container_width=True):
                                result = AdminQueries.reset_user_onboarding(user["user_id"], db)
                                if result["success"]:
                                    st.success(f"✅ Onboarding reset for {result['user_email']}. Cleared {result['deleted_memories']} memories, {result['deleted_conversations']} conversations.")
                                    del st.session_state[f"confirm_reset_{user['user_id']}"]
                                    st.rerun()
                                else:
                                    st.error(f"❌ Reset failed: {result.get('error', 'Unknown error')}")
                        with col_no:
                            if st.button("❌ Cancel", key=f"confirm_no_{user['user_id']}", use_container_width=True):
                                del st.session_state[f"confirm_reset_{user['user_id']}"]
                                st.rerun()
        else:
            st.success("✅ No newcomers in progress - all users have completed onboarding!")
        
        st.markdown("---")
    
    @staticmethod
    def render_all_onboarded_users(db: Any) -> None:
        """Render full list of all onboarded users with PDF reports."""
        import base64
        st.markdown("### 📋 All Onboarded Users")
        
        all_users = AdminQueries.get_all_onboarded_users(db)
        
        if all_users:
            st.caption(f"Total: {len(all_users)} users")

            # Pre-generate all PDFs using user_id directly
            user_pdfs = {}
            pdf_errors = []
            for user in all_users:
                try:
                    full_details = AdminQueries.get_full_onboarding_details(user["user_id"], db)
                    if not full_details:
                        pdf_errors.append(f"No details found for user_id={user['user_id']}")
                        continue
                    buf = AdminUtils.generate_onboarding_pdf(full_details)
                    if not buf:
                        pdf_errors.append(f"PDF buffer is None for user_id={user['user_id']}")
                        continue
                    pdf_bytes = buf.read()
                    user_pdfs[user["user_id"]] = {
                        "bytes": pdf_bytes,
                        "b64": base64.b64encode(pdf_bytes).decode(),
                    }
                except Exception as e:
                    pdf_errors.append(f"user_id={user['user_id']}: {type(e).__name__}: {e}")
            if pdf_errors:
                for err in pdf_errors:
                    st.warning(f"PDF error: {err}")

            # Header row
            h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.8, 2, 1.3, 1, 1.1, 1.1, 1.1, 1.1])
            for col, label in zip(
                [h1, h2, h3, h4, h5, h6, h7, h8],
                ["Name", "Email", "Role", "Dept", "First Day", "Completed", "Download", "View"]
            ):
                col.markdown(f"**{label}**")
            st.markdown('<hr style="margin:4px 0 8px 0"/>', unsafe_allow_html=True)

            # One row per user with inline buttons
            for idx, user in enumerate(all_users):
                pdf_data = user_pdfs.get(user["user_id"])
                first_day = user["created_at"].strftime("%Y-%m-%d") if user["created_at"] else "N/A"
                
                # Show "In Progress" if user hasn't completed onboarding
                current_stage = user.get("current_stage", "")
                if current_stage == "completed":
                    completed_date = user["completed_at"].strftime("%Y-%m-%d") if user["completed_at"] else "N/A"
                else:
                    completed_date = "In Progress"

                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.8, 2, 1.3, 1, 1.1, 1.1, 1.1, 1.1])
                c1.write(user["name"])
                c2.write(user["email"])
                c3.write(user["role"])
                c4.write(user["department"])
                c5.write(first_day)
                c6.write(completed_date)
                with c7:
                    if pdf_data:
                        st.download_button(
                            label="📥",
                            data=pdf_data["bytes"],
                            file_name=f"{user['email']}_onboarding.pdf",
                            mime="application/pdf",
                            key=f"dl_{idx}",
                            use_container_width=True,
                        )
                with c8:
                    if pdf_data:
                        st.markdown(
                            f'<a href="data:application/pdf;base64,{pdf_data["b64"]}" target="_blank" '
                            f'style="display:block;padding:6px 8px;background:#667eea;color:white;'
                            f'text-decoration:none;border-radius:4px;text-align:center;font-size:0.85rem;font-weight:bold;">👁️</a>',
                            unsafe_allow_html=True,
                        )
        else:
            st.info("No onboarded users yet.")
        
        st.markdown("---")
        
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
            
            ingest_clicked = st.button("📤 Ingest Documents", use_container_width=True, key="admin_ingest_files")
            
            uploaded_files = st.file_uploader(
                "Upload .md, .pdf, or .txt files",
                type=["md", "markdown", "pdf", "txt"],
                accept_multiple_files=True,
                key="admin_upload_files",
            )
            
            # Use default values for category and stage
            upload_category = "company_docs"
            upload_stage = ""
            
            if ingest_clicked:
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
