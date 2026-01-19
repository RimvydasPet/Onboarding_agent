import streamlit as st
import sys
import json
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db, init_db
from backend.database.models import UserDB, OnboardingProfileDB
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory
from backend.models.schemas import OnboardingStage

st.set_page_config(
    page_title="Onboarding Agent Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .status-card {
        padding: 1.5rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1rem;
    }
    .feature-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #667eea;
        margin-bottom: 1rem;
    }
    .success-badge {
        background-color: #48bb78;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        display: inline-block;
        margin: 0.25rem;
    }
    .info-badge {
        background-color: #4299e1;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        display: inline-block;
        margin: 0.25rem;
    }
    .warning-badge {
        background-color: #ed8936;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        display: inline-block;
        margin: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_system():
    init_db()
    return ShortTermMemory()

short_term_memory = initialize_system()

st.markdown('<div class="main-header">🤖 Onboarding Agent Demo</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">AI-Powered Onboarding with Memory Systems & Agentic RAG</p>', unsafe_allow_html=True)

if not short_term_memory.redis_available:
    st.warning("⚠️ **Redis not available** - Using in-memory fallback for short-term storage. To enable Redis: `brew install redis && brew services start redis`")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 System Status",
    "🧠 Memory Systems",
    "🗄️ Database",
    "🎯 Onboarding Flow",
    "📦 Models & Schema"
])

with tab1:
    st.markdown('<div class="status-card">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("System Status", "🟢 Operational")
    with col2:
        st.metric("Database", "✅ Connected")
    with col3:
        redis_status = "✅ Redis" if short_term_memory.redis_available else "⚠️ Fallback"
        st.metric("Short-term", redis_status)
    with col4:
        st.metric("Long-term", "✅ SQL")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("📋 Implementation Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Completed Features")
        st.markdown("""
        - **Configuration System** - Environment-based settings
        - **Database Layer** - 6 tables with SQLAlchemy ORM
        - **Pydantic Models** - Type-safe data validation
        - **Short-term Memory** - Redis-based sessions
        - **Long-term Memory** - SQL persistent storage
        - **Memory Integration** - Dual-layer architecture
        """)
    
    with col2:
        st.markdown("### 🚧 In Development")
        st.markdown("""
        - **Agentic RAG System** - Document retrieval
        - **LangGraph Agent** - Conversation flow
        - **JWT Authentication** - Secure access
        - **React Frontend** - Modern UI
        - **WebSocket Chat** - Real-time messaging
        - **API Documentation** - Interactive docs
        """)
    
    st.markdown("### 🎯 Task Requirements Coverage")
    progress_col1, progress_col2, progress_col3 = st.columns(3)
    
    with progress_col1:
        st.markdown("**MEDIUM Task 1**")
        st.progress(100)
        st.caption("✅ Memory Systems (Complete)")
    
    with progress_col2:
        st.markdown("**MEDIUM Task 2**")
        st.progress(0)
        st.caption("⏳ Authentication (Pending)")
    
    with progress_col3:
        st.markdown("**HARD Task**")
        st.progress(0)
        st.caption("⏳ Agentic RAG (Pending)")

with tab2:
    st.header("🧠 Memory Systems Testing")
    
    st.markdown("### Short-term Memory (Redis)")
    if short_term_memory.redis_available:
        st.info("✅ Session-based memory with TTL expiration. Perfect for conversation context.")
    else:
        st.warning("⚠️ Using in-memory fallback (Redis not available). Data will be lost on restart.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        test_message = st.text_input("Enter a test message:", "Hello from Streamlit!")
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🧪 Test Short-term Memory", use_container_width=True):
            session_id = str(uuid.uuid4())
            
            short_term_memory.save_message(session_id, "user", test_message)
            short_term_memory.save_message(session_id, "assistant", f"Echo: {test_message}")
            
            short_term_memory.save_context(session_id, {
                "user_intent": "testing",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "streamlit_demo"
            })
            
            messages = short_term_memory.get_messages(session_id)
            context = short_term_memory.get_context(session_id)
            
            st.success(f"✅ Saved to session: {session_id[:8]}...")
            
            st.markdown("**Messages:**")
            st.json(messages)
            
            st.markdown("**Context:**")
            st.json(context)
    
    st.markdown("---")
    st.markdown("### Long-term Memory (SQL)")
    st.info("Persistent memory with importance scoring and access tracking.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        memory_key = st.text_input("Memory Key:", "favorite_language")
        memory_value = st.text_input("Memory Value:", "Python")
    
    with col2:
        memory_importance = st.slider("Importance (1-5):", 1, 5, 4)
        st.write("")
        if st.button("💾 Save to Long-term Memory", use_container_width=True):
            db = next(get_db())
            ltm = LongTermMemory(db)
            
            ltm.save_memory(
                user_id=1,
                memory_type="preference",
                key=memory_key,
                value=memory_value,
                importance=memory_importance
            )
            
            st.success(f"✅ Memory saved: {memory_key} = {memory_value}")
            
            important_memories = ltm.get_important_memories(1, min_importance=3)
            
            st.markdown("**Important Memories (importance ≥ 3):**")
            st.json(important_memories)

with tab3:
    st.header("🗄️ Database Schema")
    
    db = next(get_db())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Database Statistics")
        users_count = db.query(UserDB).count()
        profiles_count = db.query(OnboardingProfileDB).count()
        
        st.metric("Total Users", users_count)
        st.metric("Onboarding Profiles", profiles_count)
    
    with col2:
        st.markdown("### 📋 Database Tables")
        tables = [
            "users",
            "onboarding_profiles",
            "conversations",
            "messages",
            "long_term_memories",
            "documents"
        ]
        for table in tables:
            st.markdown(f'<span class="success-badge">✓ {table}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🔍 Table Relationships")
    
    st.markdown("""
    ```
    users (1) ──→ (1) onboarding_profiles
       │
       ├──→ (n) conversations
       │         └──→ (n) messages
       │
       └──→ (n) long_term_memories
    
    documents (standalone knowledge base)
    ```
    """)
    
    st.markdown("### 📝 Schema Details")
    
    schema_info = {
        "users": ["id", "email", "full_name", "hashed_password", "is_active", "role", "created_at"],
        "onboarding_profiles": ["id", "user_id", "current_stage", "preferences", "progress", "completed_steps"],
        "conversations": ["id", "user_id", "session_id", "created_at", "updated_at"],
        "messages": ["id", "conversation_id", "role", "content", "message_metadata", "timestamp"],
        "long_term_memories": ["id", "user_id", "memory_type", "key", "value", "importance", "access_count"],
        "documents": ["id", "title", "content", "source", "doc_metadata", "created_at"]
    }
    
    for table, columns in schema_info.items():
        with st.expander(f"📊 {table}"):
            st.code(", ".join(columns))

with tab4:
    st.header("🎯 Onboarding Flow")
    
    st.markdown("### User Journey Stages")
    
    stages = [
        ("welcome", "Welcome", "Initial greeting and introduction", "🎉"),
        ("profile_setup", "Profile Setup", "User profile configuration", "👤"),
        ("learning_preferences", "Learning Preferences", "Learning style and preferences", "📚"),
        ("first_steps", "First Steps", "Getting started guide", "🚀"),
        ("completed", "Completed", "Onboarding finished", "✅")
    ]
    
    for i, (stage_id, title, description, emoji) in enumerate(stages):
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"### {emoji}")
        with col2:
            st.markdown(f"**{i+1}. {title}**")
            st.caption(description)
            st.markdown(f'<span class="info-badge">{stage_id}</span>', unsafe_allow_html=True)
        
        if i < len(stages) - 1:
            st.markdown("↓")
    
    st.markdown("---")
    st.markdown("### 🧪 Test Onboarding Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_stage = st.selectbox(
            "Select Current Stage:",
            [s[0] for s in stages],
            format_func=lambda x: next(s[1] for s in stages if s[0] == x)
        )
    
    with col2:
        completed_step = st.text_input("Completed Step:", "intro_video_watched")
    
    if st.button("📝 Update Progress", use_container_width=True):
        db = next(get_db())
        ltm = LongTermMemory(db)
        
        ltm.update_onboarding_progress(
            user_id=1,
            stage=selected_stage,
            completed_step=completed_step
        )
        
        progress = ltm.get_onboarding_progress(1)
        
        st.success("✅ Progress updated!")
        st.json(progress)

with tab5:
    st.header("📦 Data Models & Schemas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Pydantic Models")
        st.markdown("""
        **User Models:**
        - `UserBase` - Base user information
        - `UserCreate` - User registration
        - `UserLogin` - Authentication
        - `User` - Complete user profile
        
        **Authentication:**
        - `Token` - JWT access token
        - `TokenData` - Token payload
        
        **Chat Models:**
        - `ChatMessage` - Individual message
        - `ChatRequest` - User input
        - `ChatResponse` - Agent response
        
        **Agent:**
        - `AgentState` - Conversation state
        - `OnboardingProfile` - User progress
        """)
    
    with col2:
        st.markdown("### Database Models")
        st.markdown("""
        **SQLAlchemy ORM:**
        - `UserDB` - User accounts
        - `OnboardingProfileDB` - Progress tracking
        - `ConversationDB` - Chat sessions
        - `MessageDB` - Message history
        - `LongTermMemoryDB` - Persistent memories
        - `DocumentDB` - Knowledge base
        
        **Enums:**
        - `OnboardingStage` - Journey stages
        - `UserRole` - Access levels (user/admin)
        """)
    
    st.markdown("---")
    st.markdown("### 🔍 Model Examples")
    
    example_type = st.selectbox(
        "Select Model to View:",
        ["UserCreate", "ChatMessage", "AgentState", "OnboardingProfile"]
    )
    
    examples = {
        "UserCreate": {
            "email": "user@example.com",
            "password": "secure_password",
            "full_name": "John Doe"
        },
        "ChatMessage": {
            "role": "user",
            "content": "How do I get started?",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"intent": "onboarding_help"}
        },
        "AgentState": {
            "messages": [],
            "user_id": 1,
            "session_id": str(uuid.uuid4()),
            "current_stage": "welcome",
            "context": {"user_name": "John"},
            "retrieved_docs": [],
            "next_action": "greet_user"
        },
        "OnboardingProfile": {
            "user_id": 1,
            "current_stage": "profile_setup",
            "preferences": {"language": "en", "theme": "dark"},
            "progress": {"completion": 40},
            "completed_steps": ["welcome_message", "profile_created"]
        }
    }
    
    st.json(examples[example_type])

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><strong>Onboarding Agent Demo v1.0</strong></p>
    <p>Built with LangGraph, FastAPI, Redis, SQLAlchemy, and Streamlit</p>
    <p>🎯 Task Coverage: Memory Systems ✅ | Authentication ⏳ | Agentic RAG ⏳</p>
</div>
""", unsafe_allow_html=True)
