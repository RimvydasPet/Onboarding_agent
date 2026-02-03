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

    div[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        font-size: 0.85rem;
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
    }

    div[data-testid="stSidebar"] div[data-testid="stTextInput"] {
        margin-bottom: -0.75rem;
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

if "onboarding_started" not in st.session_state:
    st.session_state.onboarding_started = False


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
    from backend.memory.long_term import LongTermMemory
    db = next(get_db())
    ltm = LongTermMemory(db)
    memories = ltm.get_memories_by_type(user_id, "onboarding")
    facts = {}
    for mem in memories:
        if mem.get("key"):
            facts[mem["key"]] = mem["value"]
    return facts


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


def _generate_comprehensive_onboarding_pdf(user_id: int, session_id: str, facts: dict) -> bytes:
    """Generate a comprehensive PDF with all completed onboarding stages."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    stage_title_style = ParagraphStyle(
        'StageTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=10,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leftIndent=20
    )
    
    # Header
    story.append(Paragraph("🎯 TechVenture Solutions", title_style))
    story.append(Paragraph("Onboarding Summary Report", subtitle_style))
    
    # Metadata table
    user_name = facts.get('welcome.name', 'N/A')
    user_role = facts.get('welcome.role', 'N/A')
    
    metadata = [
        ['Participant:', user_name],
        ['Role:', user_role],
        ['Session ID:', session_id[:16] + '...'],
        ['Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')]
    ]
    
    meta_table = Table(metadata, colWidths=[1.5*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    story.append(meta_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Stage definitions
    stage_info = [
        ("welcome", "👋 Welcome", "Basic information and introduction"),
        ("profile_setup", "👤 Profile Setup", "Personal profile and preferences"),
        ("learning_preferences", "📚 Learning Preferences", "Work style and learning approach"),
        ("first_steps", "🚀 First Steps", "Initial actions and setup")
    ]
    
    # Process each stage
    for stage_id, stage_title, stage_desc in stage_info:
        required_fields = _required_fields_for_stage(stage_id, facts)
        if not required_fields:
            continue
            
        # Check if stage has any data
        has_data = any(facts.get(f"{stage_id}.{field}") for field in required_fields)
        if not has_data:
            continue
        
        # Stage header
        story.append(Paragraph(stage_title, stage_title_style))
        story.append(Paragraph(f"<i>{stage_desc}</i>", subtitle_style))
        
        # Stage data
        stage_data = []
        for field in required_fields:
            key = f"{stage_id}.{field}"
            value = facts.get(key, "Not provided")
            label = field.replace("_", " ").title()
            stage_data.append([label, str(value)])
        
        if stage_data:
            stage_table = Table(stage_data, colWidths=[2*inch, 4*inch])
            stage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0e7ff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
            ]))
            story.append(stage_table)
            story.append(Spacer(1, 0.2*inch))
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = "<i>This document contains your onboarding information collected during your TechVenture Solutions onboarding process. Keep this for your records.</i>"
    story.append(Paragraph(footer_text, subtitle_style))
    
    doc.build(story)
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
    st.markdown("**Session:**")
    st.text_input(
        "Session ID",
        value=st.session_state.session_id,
        key="dev_session_id",
        label_visibility="collapsed",
        disabled=True,
    )

    try:
        _dev_doc_count = rag.vector_store.get_collection_count()
        st.caption(f"✅ {_dev_doc_count} documents indexed")
    except Exception:
        st.caption("⚠️ RAG system initializing...")

    st.caption("🤖 AI Mode: RAG + Agent")
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")

    if st.button("🔄 New Session", use_container_width=True):
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
        st.session_state.onboarding_started = False
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
st.sidebar.markdown("### 📄 Onboarding Summary")
_sidebar_facts = _get_onboarding_facts(st.session_state.user_id)
_completed_stages_for_download = [
    (stage_id, stage_name)
    for stage_id, stage_name, _ in stages
    if stage_id != "completed" and _is_stage_complete(stage_id, _sidebar_facts)
]
if _completed_stages_for_download:
    _comprehensive_pdf = _generate_comprehensive_onboarding_pdf(
        user_id=st.session_state.user_id,
        session_id=st.session_state.session_id,
        facts=_sidebar_facts,
    )
    st.sidebar.download_button(
        label="📥 Download Complete Summary",
        data=_comprehensive_pdf,
        file_name=f"onboarding_summary_{st.session_state.session_id[:8]}.pdf",
        mime="application/pdf",
        key="sidebar_comprehensive_dl",
        use_container_width=True
    )
    st.sidebar.caption(f"✅ {len(_completed_stages_for_download)} stage(s) completed")
else:
    st.sidebar.info("Complete a stage to download your summary.")

st.markdown('<div class="main-header">🤖 AI Onboarding Assistant</div>', unsafe_allow_html=True)

st.markdown("---")

current_stage_messages = [m for m in st.session_state.messages if m.get("stage") == st.session_state.current_stage]

has_existing_progress = bool(_sidebar_facts)

if len(current_stage_messages) == 0 and (has_existing_progress or st.session_state.onboarding_started):
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


user_input = None
if has_existing_progress or st.session_state.onboarding_started:
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
            
            # Check if stage should change
            next_stage = result.get("next_stage")
            if next_stage and next_stage != st.session_state.current_stage:
                st.session_state.current_stage = next_stage
                st.session_state.unlocked_stages.add(next_stage)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "stage": st.session_state.current_stage,
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
    if not has_existing_progress:
        if not st.session_state.onboarding_started:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h2>👋 Welcome to TechVenture Solutions!</h2>
                <p style="font-size: 1.2rem; font-style: italic; color: #667eea; margin: 1.5rem 0;">
                    "Success is not final, failure is not fatal: it is the courage to continue that counts." - Winston Churchill
                </p>
                <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                    I'm your AI onboarding assistant. Please take a moment to read this introduction.
                </p>
                <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
                    When you're ready, press the button below to start your onboarding.
                </p>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_b:
                if st.button("▶️ Let's get started!", use_container_width=True):
                    st.session_state.onboarding_started = True
                    st.rerun()

            st.stop()
        else:
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
                        <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                            I'm your AI onboarding assistant, here to help you get started with our platform.
                        </p>
                        <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
                            Press “Start onboarding” above to begin.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h2>👋 Welcome back!</h2>
            <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                I'm your AI onboarding assistant. You have existing progress saved.
            </p>
            <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
                Type a message below to continue your onboarding journey!
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.stop()

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
