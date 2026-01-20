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
from backend.utils.voice_input import VoiceInputHandler
from backend.utils.continuous_voice import ContinuousVoiceListener
from backend.services.task_manager import TaskManager
import logging
import time

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

if "voice_handler" not in st.session_state:
    st.session_state.voice_handler = VoiceInputHandler(language="en-US")

if "listening" not in st.session_state:
    st.session_state.listening = False

if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

if "continuous_listener" not in st.session_state:
    st.session_state.continuous_listener = ContinuousVoiceListener(session_id=st.session_state.session_id, language="en-US")
    st.session_state.voice_enabled = False
    st.session_state.processing_response = False

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
st.sidebar.markdown("### ✅ Current Stage Tasks")

db = next(get_db())
task_manager = TaskManager(db)
task_manager.initialize_stage_tasks(st.session_state.user_id, st.session_state.current_stage)
tasks = task_manager.get_stage_tasks(st.session_state.user_id, st.session_state.current_stage)
progress = task_manager.get_stage_progress(st.session_state.user_id, st.session_state.current_stage)

for task in tasks:
    checkbox = "✅" if task["completed"] else "⬜"
    task_style = "~~" if task["completed"] else ""
    optional_tag = " (optional)" if task["optional"] else ""
    st.sidebar.markdown(f"{checkbox} {task_style}{task['description']}{task_style}{optional_tag}")

if progress['stage_complete']:
    st.sidebar.success("🎉 Stage Complete! Ready to advance.")
else:
    st.sidebar.info(f"📊 {progress['required_completed']}/{progress['required_total']} required tasks done")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")

if st.sidebar.button("🔄 New Session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.current_stage = "welcome"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Manual Stage Control")
st.sidebar.caption("(Normally auto-advances when tasks complete)")
new_stage = st.sidebar.selectbox(
    "Override stage:",
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

# Voice control and chat input in same row
col_input, col_voice = st.columns([5, 1])

with col_input:
    # Check for voice input from file
    voice_input = None
    if st.session_state.voice_enabled:
        voice_input = st.session_state.continuous_listener.read_voice_text()
        if voice_input:
            st.info(f"🎤 Voice: {voice_input}")
    
    # Get user input (voice or text)
    if voice_input:
        user_input = voice_input
    else:
        voice_status = "🔴 Voice ON" if st.session_state.voice_enabled else "🎤 Voice OFF"
        user_input = st.chat_input(f"Ask me anything... [{voice_status}]")
    
    # Auto-refresh to check for voice input
    if st.session_state.voice_enabled and not user_input:
        time.sleep(0.3)
        st.rerun()

with col_voice:
    if st.session_state.voice_enabled:
        if st.button("🔴", use_container_width=True, type="primary", help="Stop voice recognition"):
            st.session_state.continuous_listener.stop()
            st.session_state.voice_enabled = False
            st.rerun()
    else:
        if st.button("🎤", use_container_width=True, type="secondary", help="Start continuous voice recognition"):
            if ContinuousVoiceListener.is_microphone_available():
                st.session_state.continuous_listener.start()
                st.session_state.voice_enabled = True
                st.rerun()
            else:
                st.error("❌ Microphone not available")

if user_input:
    # Pause voice recognition while processing
    was_voice_enabled = st.session_state.voice_enabled
    if was_voice_enabled:
        st.session_state.continuous_listener.stop()
        st.session_state.voice_enabled = False
        st.session_state.processing_response = True
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    memory.save_message(st.session_state.session_id, "user", user_input)
    
    with st.spinner("🤔 Thinking... (Voice paused)"):
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
            
            # Check if stage is complete and auto-advance
            task_mgr = TaskManager(db)
            if task_mgr.is_stage_complete(st.session_state.user_id, st.session_state.current_stage):
                # Find next stage
                stage_order = [s[0] for s in stages]
                current_idx = stage_order.index(st.session_state.current_stage)
                if current_idx < len(stage_order) - 1:
                    next_stage = stage_order[current_idx + 1]
                    st.session_state.current_stage = next_stage
                    task_mgr.initialize_stage_tasks(st.session_state.user_id, next_stage)
                    st.success(f"🎉 Stage complete! Moving to: {stages[current_idx + 1][1]}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    # Resume voice recognition after response
    if was_voice_enabled:
        time.sleep(1)  # Brief pause before resuming
        st.session_state.continuous_listener.start()
        st.session_state.voice_enabled = True
        st.session_state.processing_response = False
    
    st.rerun()

if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #666;">
        <h3>👋 Welcome! I'm your onboarding assistant.</h3>
        <p>I'll guide you step-by-step through getting started.</p>
        <p><strong>I'll ask you questions to complete each task.</strong></p>
        <p>Check the sidebar to see your current tasks and progress!</p>
        <p style="margin-top: 2rem; color: #999; font-size: 0.9rem;">💡 Tip: Click the 🎤 button next to the input field for voice!</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    redis_status = "✅ Active" if memory.redis_available else "⚠️ Fallback"
    st.metric("Memory", redis_status)
with col3:
    db = next(get_db())
    tm = TaskManager(db)
    prog = tm.get_stage_progress(st.session_state.user_id, st.session_state.current_stage)
    st.metric("✅ Tasks", f"{prog['completed']}/{prog['total']}")
with col4:
    stage_progress = (current_stage_index + 1) / len(stages) * 100
    st.metric("📊 Overall", f"{stage_progress:.0f}%")
