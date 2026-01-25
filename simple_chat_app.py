import streamlit as st
import uuid
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from backend.config import settings
from backend.database.connection import init_db
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory
from backend.database.connection import get_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Onboarding Assistant",
    page_icon="🤖",
    layout="wide"
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
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-right: 20%;
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
    init_db()
    return ShortTermMemory()

@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.7
    )

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_stage" not in st.session_state:
    st.session_state.current_stage = "welcome"

if "user_id" not in st.session_state:
    st.session_state.user_id = 1

memory = initialize_system()
llm = get_llm()

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

st.markdown('<div class="main-header">🤖 Onboarding Assistant</div>', unsafe_allow_html=True)

st.markdown("---")

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant:</strong><br>{content}</div>', unsafe_allow_html=True)

user_input = st.chat_input("Ask me anything about getting started...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    memory.save_message(st.session_state.session_id, "user", user_input)
    
    with st.spinner("🤔 Thinking..."):
        try:
            stage_prompts = {
                "welcome": "You are greeting a new user. Be warm and welcoming.",
                "profile_setup": "You are helping the user set up their profile.",
                "learning_preferences": "You are learning about the user's preferences.",
                "first_steps": "You are guiding the user through their first steps.",
                "completed": "The user has completed onboarding. Offer ongoing support."
            }
            
            system_prompt = f"""You are a friendly onboarding assistant helping new users get started.

Current Stage: {st.session_state.current_stage}
{stage_prompts.get(st.session_state.current_stage, '')}

Provide helpful, concise answers. Be encouraging and supportive."""

            recent_messages = memory.get_messages(st.session_state.session_id, limit=5)
            
            messages = [SystemMessage(content=system_prompt)]
            
            for msg in recent_messages[-3:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=user_input))
            
            response = llm.invoke(messages)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            })
            
            memory.save_message(st.session_state.session_id, "assistant", response.content)
            
            db = next(get_db())
            ltm = LongTermMemory(db)
            ltm.update_onboarding_progress(
                st.session_state.user_id,
                st.session_state.current_stage,
                f"message_{len(st.session_state.messages)}"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
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
            At TechVenture Solutions, we're committed to making your onboarding experience smooth and engaging.
        </p>
        <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
            📖 Please read this welcome message, then type below to begin your journey with us!
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    redis_status = "✅ Active" if memory.redis_available else "⚠️ Fallback"
    st.metric("Memory", redis_status)
with col3:
    stage_progress = (current_stage_index + 1) / len(stages) * 100
    st.metric("📊 Progress", f"{stage_progress:.0f}%")
