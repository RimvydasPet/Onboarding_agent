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
    page_title="Onboarding Assistant",
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
st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")

if st.sidebar.button("🔄 New Session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.current_stage = "welcome"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Change Stage")
new_stage = st.sidebar.selectbox(
    "Select stage:",
    [s[0] for s in stages],
    index=current_stage_index,
    format_func=lambda x: next(s[1] for s in stages if s[0] == x)
)
if new_stage != st.session_state.current_stage:
    st.session_state.current_stage = new_stage
    st.rerun()

st.markdown('<div class="main-header">🤖 Onboarding Assistant</div>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align: center;"><span class="stage-badge">{next(s[1] for s in stages if s[0] == st.session_state.current_stage)}</span></p>', unsafe_allow_html=True)

st.markdown("---")

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant:</strong><br>{content}</div>', unsafe_allow_html=True)
        
        if message.get("sources"):
            with st.expander("📚 View Sources"):
                for i, source in enumerate(message["sources"][:3], 1):
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>Source {i}</strong> ({source.get('relevance', 'medium')} relevance)<br>
                        <small>{source['content'][:200]}...</small>
                    </div>
                    """, unsafe_allow_html=True)

user_input = st.chat_input("Ask me anything about getting started...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    with st.spinner("🤔 Thinking..."):
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
                "sources": result.get("retrieved_docs", []),
                "analysis": result.get("query_analysis", {}),
                "timestamp": datetime.now().isoformat()
            })
            
            st.session_state.current_stage = result.get("current_stage", st.session_state.current_stage)
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error. Please try again. Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    st.rerun()

if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #666;">
        <h3>👋 Welcome! I'm your onboarding assistant.</h3>
        <p>I'm here to help you get started with our onboarding process.</p>
        <p>Try asking me:</p>
        <ul style="list-style: none; padding: 0;">
            <li>• "How do I create a new project?"</li>
            <li>• "What are the keyboard shortcuts?"</li>
            <li>• "Tell me about the mobile app"</li>
            <li>• "I need help with my account"</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    st.metric("📄 Documents", rag.get_stats()["total_documents"])
with col3:
    stage_progress = (current_stage_index + 1) / len(stages) * 100
    st.metric("📊 Progress", f"{stage_progress:.0f}%")
