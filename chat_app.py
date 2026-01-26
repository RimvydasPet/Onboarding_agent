import streamlit as st
import uuid
from datetime import datetime
from backend.agent.graph import run_agent
from backend.rag.initializer import initialize_rag_system
from backend.database.connection import init_db
from backend.database.connection import get_db
from backend.database.models import OnboardingProfileDB
from backend.models.schemas import OnboardingStage
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
        color: #2d3748;
    }
    .source-card {
        background: linear-gradient(135deg, #e0e7ff 0%, #dbeafe 100%);
        border: 1px solid #667eea;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        color: #1e293b;
    }
    .source-card strong {
        color: #667eea;
    }
    .source-card em {
        color: #475569;
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

if "unlocked_stages" not in st.session_state:
    st.session_state.unlocked_stages = {"welcome"}


ROLE_STAGE_FIELDS = {
    "developer": {
        "profile_setup": ["dev_stack", "dev_repo_access", "dev_env"],
        "learning_preferences": ["dev_workflow", "dev_quality", "dev_integrations"],
        "first_steps": ["dev_first_task", "dev_access_blockers", "dev_help_area"],
    },
    "pm": {
        "profile_setup": ["pm_area", "pm_reporting", "pm_stakeholders"],
        "learning_preferences": ["pm_planning_style", "pm_pain", "pm_integrations"],
        "first_steps": ["pm_first_project", "pm_team_invite", "pm_help_area"],
    },
    "it_admin": {
        "profile_setup": ["it_scope", "it_sso", "it_compliance"],
        "learning_preferences": ["it_integrations", "it_permissions", "it_notifications"],
        "first_steps": ["it_first_action", "it_users", "it_help_area"],
    },
    "general": {
        "profile_setup": ["focus_area"],
        "learning_preferences": ["preferred_learning"],
        "first_steps": ["first_setup"],
    },
}


def _role_category(role_value: str | None) -> str:
    text = str(role_value or "").strip().lower()
    if any(k in text for k in ["dev", "engineer", "developer", "software"]):
        return "developer"
    if any(k in text for k in ["pm", "project manager", "product", "scrum"]):
        return "pm"
    if any(k in text for k in ["it", "admin", "administrator"]):
        return "it_admin"
    return "general"


def _required_fields_for_stage(stage: str, facts: dict) -> list[str]:
    if stage == "welcome":
        return ["name", "role"]
    if stage == "completed":
        return []
    role_cat = _role_category(facts.get("welcome.role"))
    return list(ROLE_STAGE_FIELDS.get(role_cat, {}).get(stage, []))


def _get_onboarding_facts(user_id: int) -> dict:
    db = next(get_db())
    profile = db.query(OnboardingProfileDB).filter(OnboardingProfileDB.user_id == user_id).first()
    if not profile or not profile.progress:
        return {}
    facts = profile.progress.get("facts")
    return facts if isinstance(facts, dict) else {}


def _is_stage_complete(stage: str, facts: dict) -> bool:
    required = _required_fields_for_stage(stage, facts)
    if not required:
        return stage == "completed"
    for f in required:
        key = f"{stage}.{f}"
        if key not in facts or facts.get(key) in (None, ""):
            return False
    return True


def _generate_stage_summary_pdf(user_id: int, session_id: str, stage: str, answers: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    left_margin = 50
    y = height - 60

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(left_margin, y, f"Onboarding Summary — {stage}")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left_margin, y, f"User ID: {user_id}   Session: {session_id}")
    y -= 16
    pdf.drawString(left_margin, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 26

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left_margin, y, "Provided answers")
    y -= 18

    pdf.setFont("Helvetica", 11)
    for idx, ans in enumerate(answers, 1):
        line = f"{idx}. {ans}".strip()
        words = line.split()
        current = ""
        for w in words:
            candidate = (current + " " + w).strip()
            if pdf.stringWidth(candidate, "Helvetica", 11) > (width - left_margin * 2):
                pdf.drawString(left_margin, y, current)
                y -= 14
                current = w
            else:
                current = candidate
        if current:
            pdf.drawString(left_margin, y, current)
            y -= 14
        y -= 6
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 60

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def _generate_structured_stage_pdf(user_id: int, session_id: str, stage: str, facts: dict) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    stage_titles = {
        "welcome": "Welcome",
        "profile_setup": "Profile Setup",
        "learning_preferences": "Learning Preferences",
        "first_steps": "First Steps",
        "completed": "Completed",
    }
    title = stage_titles.get(stage, stage)

    left_margin = 50
    y = height - 60

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left_margin, y, "TechVenture Solutions — Onboarding Summary")
    y -= 22

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(left_margin, y, f"Stage: {title}")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left_margin, y, f"User ID: {user_id}   Session: {session_id}")
    y -= 14
    pdf.drawString(left_margin, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 22

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left_margin, y, "Summary")
    y -= 16

    pdf.setFont("Helvetica", 11)
    for field in _required_fields_for_stage(stage, facts):
        key = f"{stage}.{field}"
        value = facts.get(key, "")
        label = field.replace("_", " ").title()
        line = f"{label}: {value}".strip()
        words = line.split()
        current = ""
        for w in words:
            candidate = (current + " " + w).strip()
            if pdf.stringWidth(candidate, "Helvetica", 11) > (width - left_margin * 2):
                pdf.drawString(left_margin, y, current)
                y -= 14
                current = w
            else:
                current = candidate
        if current:
            pdf.drawString(left_margin, y, current)
            y -= 16
        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 60

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def _save_stage_answers_to_profile(user_id: int, stage: str, answers: list[str]) -> None:
    db = next(get_db())
    profile = db.query(OnboardingProfileDB).filter(OnboardingProfileDB.user_id == user_id).first()
    if not profile:
        return
    if profile.progress is None:
        profile.progress = {}
    profile.progress[stage] = {
        "answers": answers,
        "updated_at": datetime.now().isoformat()
    }
    db.commit()


def _save_facts_to_profile(user_id: int, new_facts: dict) -> None:
    if not new_facts:
        return
    db = next(get_db())
    profile = db.query(OnboardingProfileDB).filter(OnboardingProfileDB.user_id == user_id).first()
    if not profile:
        return
    if profile.progress is None:
        profile.progress = {}
    if not isinstance(profile.progress.get("facts"), dict):
        profile.progress["facts"] = {}
    profile.progress["facts"].update(new_facts)
    db.commit()

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

with st.sidebar.expander("Developers info", expanded=False):
    st.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")

    if st.button("🔄 New Session"):
        from backend.database.connection import get_db
        from backend.memory.long_term import LongTermMemory
        from backend.memory.short_term import ShortTermMemory
        
        try:
            db = next(get_db())
            ltm = LongTermMemory(db)
            ltm.clear_user_memories(st.session_state.user_id)
            ltm.reset_onboarding_profile(st.session_state.user_id)
        except Exception as e:
            logger.warning(f"Could not clear long-term memory: {e}")
        
        try:
            stm = ShortTermMemory()
            stm.clear_session(st.session_state.session_id)
        except Exception as e:
            logger.warning(f"Could not clear short-term memory: {e}")
        
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.current_stage = "welcome"
        st.session_state.unlocked_stages = {"welcome"}
        st.rerun()

    st.markdown("---")
    new_stage = st.selectbox(
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

st.sidebar.markdown("---")
st.sidebar.markdown("### 📄 Stage Summaries")
_sidebar_facts = _get_onboarding_facts(st.session_state.user_id)
_completed_stages_for_download = [
    (stage_id, stage_name)
    for stage_id, stage_name, _ in stages
    if stage_id != "completed" and _is_stage_complete(stage_id, _sidebar_facts)
]
if _completed_stages_for_download:
    for _dl_stage_id, _dl_stage_name in _completed_stages_for_download:
        _dl_pdf = _generate_structured_stage_pdf(
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id,
            stage=_dl_stage_id,
            facts=_sidebar_facts,
        )
        st.sidebar.download_button(
            label=f"📥 {_dl_stage_name}",
            data=_dl_pdf,
            file_name=f"onboarding_{_dl_stage_id}_{st.session_state.session_id[:8]}.pdf",
            mime="application/pdf",
            key=f"sidebar_dl_{_dl_stage_id}",
        )
else:
    st.sidebar.info("Complete a stage to download its summary.")

st.markdown('<div class="main-header">🤖 AI Onboarding Assistant</div>', unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align: center;">'
    f'<span class="rag-badge">RAG Enabled</span>'
    f'</p>', 
    unsafe_allow_html=True
)

st.markdown("---")

current_stage_messages = [m for m in st.session_state.messages if m.get("stage") == st.session_state.current_stage]
if len(current_stage_messages) == 0:
    stage_titles = {stage_id: stage_name for stage_id, stage_name, _ in stages}
    stage_title = stage_titles.get(st.session_state.current_stage, st.session_state.current_stage)

    intro_body = {
        "welcome": "At TechVenture Solutions, we're committed to making your onboarding experience smooth and engaging.",
        "profile_setup": "Now let's set up your profile. This is important because it helps personalize your experience, improves collaboration, and ensures approvals/support requests reach the right people.",
        "learning_preferences": "Next we'll learn your working style and preferences. This matters because we can tailor dashboards, integrations, and notifications so TechVenture supports your workflow — not distracts from it.",
        "first_steps": "Now we'll take your first real actions. This stage is important because it gets you productive quickly: access, integrations, and setting up your first project so you can start delivering results.",
        "completed": "You're all set. This stage is important because it confirms you're ready to work independently, and it gives you clear next steps to explore advanced features and get ongoing support."
    }.get(st.session_state.current_stage, "Let's continue your onboarding journey.")

    st.markdown(f"""
    <div style="text-align: center; padding: 2rem;">
        <h2>👋 {stage_title}</h2>
        <p style="font-size: 1.2rem; font-style: italic; color: #667eea; margin: 1.5rem 0;">
            "Success is not final, failure is not fatal: it is the courage to continue that counts." - Winston Churchill
        </p>
        <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
            {intro_body}
        </p>
        <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
            📖 Please read this message, then type below to continue.
        </p>
    </div>
    """, unsafe_allow_html=True)

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


current_stage_answers = [
    m["content"]
    for m in st.session_state.messages
    if m.get("stage") == st.session_state.current_stage and m.get("role") == "user"
]
facts = _get_onboarding_facts(st.session_state.user_id)
if _is_stage_complete(st.session_state.current_stage, facts):
    pdf_bytes = _generate_structured_stage_pdf(
        user_id=st.session_state.user_id,
        session_id=st.session_state.session_id,
        stage=st.session_state.current_stage,
        facts=facts,
    )
    st.download_button(
        label="📄 Download stage summary (PDF)",
        data=pdf_bytes,
        file_name=f"onboarding_{st.session_state.current_stage}_{st.session_state.session_id[:8]}.pdf",
        mime="application/pdf",
    )

    stage_ids = [s[0] for s in stages]
    try:
        idx = stage_ids.index(st.session_state.current_stage)
    except ValueError:
        idx = -1

    next_stage_id = stage_ids[idx + 1] if idx >= 0 and idx + 1 < len(stage_ids) else None
    if next_stage_id and next_stage_id != st.session_state.current_stage:
        st.info("This stage is complete. When you're ready, move on to the next step.")
        if st.button("➡️ Go to next step", key=f"go_next_{st.session_state.current_stage}"):
            st.session_state.current_stage = next_stage_id
            st.session_state.unlocked_stages.add(next_stage_id)
            st.rerun()

user_input = st.chat_input("Ask me anything about TechVenture Solutions...")

if user_input:
    previous_stage = st.session_state.current_stage

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "stage": previous_stage,
        "timestamp": datetime.now().isoformat()
    })
    
    with st.spinner("🤔 Thinking and searching knowledge base..."):
        try:
            recent_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m.get("stage") == previous_stage
            ][-6:]

            result = run_agent(
                user_input=user_input,
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
                current_stage=st.session_state.current_stage,
                history=recent_history,
            )
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "stage": previous_stage,
                "sources": result.get("sources", []),
                "timestamp": datetime.now().isoformat()
            })

            extracted_facts = result.get("extracted_facts")
            if isinstance(extracted_facts, dict) and extracted_facts:
                _save_facts_to_profile(st.session_state.user_id, extracted_facts)

            stage_answers = [
                m["content"]
                for m in st.session_state.messages
                if m.get("stage") == previous_stage and m.get("role") == "user"
            ]
            _save_stage_answers_to_profile(
                user_id=st.session_state.user_id,
                stage=previous_stage,
                answers=stage_answers,
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "stage": previous_stage,
                "sources": [],
                "timestamp": datetime.now().isoformat()
            })
    
    st.rerun()

if len(st.session_state.messages) == 0:
    with st.spinner("🤖 Your onboarding assistant is ready..."):
        try:
            result = run_agent(
                user_input="I just arrived and I'm ready to start onboarding",
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
                current_stage=st.session_state.current_stage
            )
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "stage": st.session_state.current_stage,
                "timestamp": datetime.now().isoformat()
            })
            st.rerun()
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h2>👋 Welcome to TechVenture Solutions!</h2>
                <p style="font-size: 1.2rem; font-style: italic; color: #667eea; margin: 1.5rem 0;">
                    "Success is not final, failure is not fatal: it is the courage to continue that counts." - Winston Churchill
                </p>
                <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                    I'm your AI onboarding assistant, here to help you get started with our platform.
                </p>
                <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
                    Type a message below to begin your journey with us!
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
