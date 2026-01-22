import streamlit as st
import uuid
from datetime import datetime
from backend.agent.graph import run_agent
from backend.rag.initializer import initialize_rag_system
from backend.database.connection import init_db
from backend.models.schemas import OnboardingStage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Onboarding Assistant with RAG",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        margin-right: 20%;
    }
    .source-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stage-badge {
        background: #667eea;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        display: inline-block;
    }
    .rag-badge {
        background: #48bb78;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        display: inline-block;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_system():
    """Initialize database and RAG system."""
    init_db()
    rag = initialize_rag_system()
    logger.info("System initialized")
    return rag

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_stage" not in st.session_state:
    st.session_state.current_stage = "welcome"

if "user_id" not in st.session_state:
    st.session_state.user_id = 1

if "show_sources" not in st.session_state:
    st.session_state.show_sources = True

rag = initialize_system()

st.sidebar.title("🎯 Onboarding Progress")

stages = [
    ("welcome", "Welcome", "🎉"),
    ("profile_setup", "Profile Setup", "👤"),
    ("learning_preferences", "Learning Preferences", "📚"),
    ("first_steps", "First Steps", "🚀"),
    ("completed", "Completed", "✅")
]

current_stage_index = next((i for i, s in enumerate(stages) if s[0] == st.session_state.current_stage), 0)

for i, (stage_id, stage_name, emoji) in enumerate(stages):
    if i < current_stage_index:
        st.sidebar.markdown(f"{emoji} ~~{stage_name}~~ ✓")
    elif i == current_stage_index:
        st.sidebar.markdown(f"**{emoji} {stage_name}** ← Current")
    else:
        st.sidebar.markdown(f"{emoji} {stage_name}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")

if st.sidebar.button("🔄 New Session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.current_stage = "welcome"
    st.rerun()

st.sidebar.markdown("---")
new_stage = st.sidebar.selectbox(
    "Change stage:",
    [s[0] for s in stages],
    index=current_stage_index,
    format_func=lambda x: next(s[1] for s in stages if s[0] == x)
)
if new_stage != st.session_state.current_stage:
    st.session_state.current_stage = new_stage
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 Settings")
st.session_state.show_sources = st.sidebar.checkbox("Show sources", value=st.session_state.show_sources)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 RAG Status")
try:
    doc_count = rag.vector_store.get_collection_count()
    st.sidebar.success(f"✅ {doc_count} documents indexed")
except:
    st.sidebar.warning("⚠️ RAG system initializing...")

st.markdown('<div class="main-header">🤖 AI Onboarding Assistant</div>', unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align: center;">'
    f'<span class="stage-badge">{next(s[1] for s in stages if s[0] == st.session_state.current_stage)}</span>'
    f'<span class="rag-badge">RAG Enabled</span>'
    f'</p>', 
    unsafe_allow_html=True
)

st.markdown("---")

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant:</strong><br>{content}</div>', unsafe_allow_html=True)
        
        if st.session_state.show_sources and "sources" in message and message["sources"]:
            with st.expander(f"📚 Sources ({len(message['sources'])})"):
                for i, source in enumerate(message["sources"], 1):
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>Source {i}:</strong> {source.get('source', 'unknown')}<br>
                        <strong>Category:</strong> {source.get('category', 'general')}<br>
                        <strong>Relevance:</strong> {source.get('score', 0):.2f}<br>
                        <em>{source.get('preview', '')}</em>
                    </div>
                    """, unsafe_allow_html=True)

user_input = st.chat_input("Ask me anything about TechVenture Solutions...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    with st.spinner("🤔 Thinking and searching knowledge base..."):
        try:
            result = run_agent(
                user_input=user_input,
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
                current_stage=st.session_state.current_stage
            )
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "sources": result.get("sources", []),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "sources": [],
                "timestamp": datetime.now().isoformat()
            })
    
    st.rerun()

if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h2>👋 Welcome to TechVenture Solutions!</h2>
        <p style="font-size: 1.2rem; font-style: italic; color: #667eea; margin: 1.5rem 0;">
            "Success is not final, failure is not fatal: it is the courage to continue that counts." - Winston Churchill
        </p>
        <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
            I'm your AI onboarding assistant, powered by advanced RAG (Retrieval-Augmented Generation) 
            and agentic AI technology. I can answer questions about our platform using our comprehensive 
            knowledge base.
        </p>
        <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
            💡 Try asking: "How do I create my first project?" or "What integrations are available?"
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    stage_progress = (current_stage_index + 1) / len(stages) * 100
    st.metric("📊 Progress", f"{stage_progress:.0f}%")
with col3:
    try:
        doc_count = rag.vector_store.get_collection_count()
        st.metric("📚 Knowledge Base", f"{doc_count} docs")
    except:
        st.metric("📚 Knowledge Base", "Loading...")
with col4:
    st.metric("🤖 AI Mode", "RAG + Agent")
