import streamlit as st
import uuid
from datetime import datetime
from backend.agent.graph import run_agent
from backend.rag.initializer import initialize_rag_system
from backend.database.connection import init_db
from backend.database.connection import get_db
from backend.database.models import OnboardingProfileDB
from backend.models.schemas import OnboardingStage
from backend.config import settings
from backend.memory.long_term import LongTermMemory
from backend.agent.nodes import AgentNodes
import logging
from sqlalchemy.orm.attributes import flag_modified
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import urllib.request
import urllib.error
import time

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


@st.cache_data(ttl=600)
def _tavily_connectivity_check(_api_key_len: int) -> dict:
    api_key = str(getattr(settings, "TAVILY_API_KEY", "") or "").strip()
    if not api_key:
        return {"configured": False, "ok": False, "error": "TAVILY_API_KEY missing"}

    payload = {
        "api_key": api_key,
        "query": "onboarding checklist",
        "max_results": 1,
        "include_answer": False,
        "include_raw_content": False,
    }

    req = urllib.request.Request(
        url="https://api.tavily.com/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        ok = isinstance(data, dict) and isinstance(data.get("results"), list)
        return {
            "configured": True,
            "ok": bool(ok),
            "latency_ms": int((time.time() - t0) * 1000),
            "error": None,
        }
    except urllib.error.HTTPError as e:
        return {
            "configured": True,
            "ok": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": f"HTTP {getattr(e, 'code', '?')} from Tavily",
        }
    except Exception as e:
        return {
            "configured": True,
            "ok": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": f"Request failed: {type(e).__name__}",
        }

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

if "resume_kickoff_done" not in st.session_state:
    st.session_state.resume_kickoff_done = False


ROLE_STAGE_FIELDS = {
    "developer": {
        "department_info": ["dev_team_structure", "dev_key_repos", "dev_stakeholders"],
        "key_responsibilities": ["dev_duties", "dev_kpis", "dev_first_tasks"],
        "tools_systems": ["dev_ide", "dev_ci_cd", "dev_access"],
        "training_needs": ["dev_onboarding_modules", "dev_skill_gaps", "dev_certifications"],
    },
    "pm": {
        "department_info": ["pm_team_structure", "pm_cross_functional", "pm_stakeholders"],
        "key_responsibilities": ["pm_duties", "pm_kpis", "pm_first_tasks"],
        "tools_systems": ["pm_project_tools", "pm_reporting_tools", "pm_access"],
        "training_needs": ["pm_onboarding_modules", "pm_skill_gaps", "pm_certifications"],
    },
    "it_admin": {
        "department_info": ["it_team_structure", "it_infrastructure", "it_stakeholders"],
        "key_responsibilities": ["it_duties", "it_kpis", "it_first_tasks"],
        "tools_systems": ["it_admin_tools", "it_monitoring", "it_access"],
        "training_needs": ["it_onboarding_modules", "it_skill_gaps", "it_certifications"],
    },
    "general": {
        "department_info": ["team_overview"],
        "key_responsibilities": ["role_duties"],
        "tools_systems": ["core_tools"],
        "training_needs": ["learning_path"],
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
        return ["name", "name_alias", "role", "department", "email_preference", "phone_number", "emergency_contact", "pronouns", "accessibility_needs"]
    if stage == "completed":
        return []
    role_cat = _role_category(facts.get("welcome.role"))
    return list(ROLE_STAGE_FIELDS.get(role_cat, {}).get(stage, []))


def _get_onboarding_facts(user_id: int) -> dict:
    db = next(get_db())
    profile = db.query(OnboardingProfileDB).filter(OnboardingProfileDB.user_id == user_id).first()
    profile_facts = {}
    if profile and profile.progress:
        profile_facts = profile.progress.get("facts", {})

    # Fallback: also read from LongTermMemoryDB (the agent always saves there)
    ltm = LongTermMemory(db)
    ltm_memories = ltm.get_memories_by_type(user_id, "onboarding")
    ltm_facts = {}
    for m in ltm_memories or []:
        k = m.get("key")
        if k:
            ltm_facts[str(k)] = m.get("value")

    # Merge: LTM facts as base, profile facts override
    merged = {**ltm_facts, **profile_facts}

    # Backfill to profile if there are LTM facts missing from profile
    if merged and merged != profile_facts and profile:
        if profile.progress is None:
            profile.progress = {}
        profile.progress["facts"] = merged
        flag_modified(profile, "progress")
        db.commit()

    return merged


def _is_stage_complete(stage: str, facts: dict) -> bool:
    if stage == "welcome":
        # Welcome stage requires name and role
        return bool(facts.get("welcome.name") and facts.get("welcome.role"))
    if stage == "completed":
        return False
    
    # For other stages, check if ANY facts exist for that stage
    # This works with both static and dynamic field keys (q1, q2, etc.)
    # Exclude internal metadata keys (_qlabel.*, qa.pending_stage)
    stage_prefix = f"{stage}."
    stage_facts = [
        k for k in facts.keys()
        if k.startswith(stage_prefix)
        and facts.get(k) not in (None, "")
        and not k[len(stage_prefix):].startswith("_qlabel.")
        and k[len(stage_prefix):] != "qa.pending_stage"
    ]
    return len(stage_facts) > 0


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

    session_id_style = ParagraphStyle(
        'SessionIdStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        wordWrap='CJK'
    )
    
    # Header
    story.append(Paragraph("🎯 TechVenture Solutions", title_style))
    story.append(Paragraph("Onboarding Summary Report", subtitle_style))
    
    # Metadata table
    user_name = facts.get('welcome.name', 'N/A')
    user_role = facts.get('welcome.role', 'N/A')

    session_id_text = str(session_id or 'N/A')
    session_id_cell = Paragraph(session_id_text, session_id_style)
    
    metadata = [
        ['Participant:', user_name],
        ['Role:', user_role],
        ['Session ID:', session_id_cell],
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
        ("welcome", "👋 Welcome & Profile Setup", "Name, nickname, role, department, email preference, phone, emergency contact, pronouns, accessibility"),
        ("department_info", "🏢 Department Information", "Org structure, team directory, and key stakeholders"),
        ("key_responsibilities", "🎯 Key Responsibilities", "Role duties, KPIs, goals, and initial tasks"),
        ("tools_systems", "🛠️ Tools & Systems", "IT setup, software, hardware, and access credentials"),
        ("training_needs", "📚 Training Needs", "Compliance training, skill gaps, and learning paths")
    ]
    
    # Process each stage
    for stage_id, stage_title, stage_desc in stage_info:
        # Find all facts for this stage (works with both static and dynamic field keys)
        stage_facts = {k: v for k, v in facts.items() if k.startswith(f"{stage_id}.") and v not in (None, "")}
        
        if not stage_facts:
            continue
        
        # Stage header
        story.append(Paragraph(stage_title, stage_title_style))
        story.append(Paragraph(f"<i>{stage_desc}</i>", subtitle_style))
        
        # Stage data
        stage_data = []
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=4,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
        )
        # Build a lookup of question labels: field_key -> question text
        qlabel_map = {}
        for k, v in stage_facts.items():
            parts = k.split(".", 1)
            if len(parts) == 2 and parts[1].startswith("_qlabel."):
                actual_field = parts[1].replace("_qlabel.", "", 1)
                qlabel_map[actual_field] = str(v)

        for key, value in sorted(stage_facts.items()):
            field = key.split(".", 1)[1] if "." in key else key
            # Skip internal metadata keys
            if field.startswith("_qlabel.") or field == "qa.pending_stage":
                continue
            # Use stored question text if available, otherwise humanise the key
            label = qlabel_map.get(field, field.replace("_", " ").title())
            label_cell = Paragraph(label, label_style)
            # Wrap all text in Paragraph for proper text wrapping
            value_text = str(value)
            
            # Check if value is a file path (uploaded photo)
            if value_text.startswith("/") or value_text.startswith("C:") or "uploaded_profile_pics" in value_text:
                # Make it a clickable link
                value_cell = Paragraph(f'<link href="file://{value_text}" color="blue"><u>{value_text}</u></link>', field_style)
            else:
                value_cell = Paragraph(value_text, field_style)
            stage_data.append([label_cell, value_cell])
        
        if stage_data:
            stage_table = Table(stage_data, colWidths=[2*inch, 4*inch])
            stage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0e7ff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
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
    flag_modified(profile, "progress")
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
    flag_modified(profile, "progress")
    db.commit()

rag = initialize_system()

st.sidebar.title("🎯 Onboarding Progress")

stages = [
    ("welcome", "Welcome & Profile Setup", "🎉"),
    ("department_info", "Department Information", "🏢"),
    ("key_responsibilities", "Key Responsibilities", "🎯"),
    ("tools_systems", "Tools & Systems", "🛠️"),
    ("training_needs", "Training Needs", "📚"),
    ("completed", "Completed", "✅")
]


def _derive_current_stage_from_facts(facts: dict) -> str:
    for stage_id, _, _ in stages:
        if stage_id == "completed":
            continue
        if not _is_stage_complete(stage_id, facts):
            return stage_id
    return "completed"


def _is_onboarding_fully_complete(facts: dict) -> bool:
    """Return True when every onboarding stage has been completed."""
    for stage_id, _, _ in stages:
        if stage_id == "completed":
            continue
        if not _is_stage_complete(stage_id, facts):
            return False
    return True


# ---------------------------------------------------------------------------
# Early check: if onboarding is fully complete, switch to Document Search mode
# ---------------------------------------------------------------------------
_early_facts = _get_onboarding_facts(st.session_state.user_id)
_onboarding_complete = _is_onboarding_fully_complete(_early_facts)

if _onboarding_complete:
    # Force stage to "completed" so the agent knows we're in post-onboarding mode
    st.session_state.current_stage = "completed"

    # --- Sidebar for Document Search mode ---
    st.sidebar.title("📖 Internal Rules Search")
    st.sidebar.markdown("✅ **Onboarding complete!**")
    _user_name = _early_facts.get("welcome.name", "")
    _user_role = _early_facts.get("welcome.role", "")
    if _user_name:
        st.sidebar.markdown(f"👤 **{_user_name}**" + (f" — {_user_role}" if _user_role else ""))
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "Ask any question about company policies, rules, or procedures and "
        "I'll search our internal documents for you."
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 RAG Status")
    try:
        _ds_doc_count = rag.vector_store.get_collection_count()
        st.sidebar.success(f"✅ {_ds_doc_count} documents indexed")
    except Exception:
        st.sidebar.warning("⚠️ RAG system initializing...")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📄 Onboarding Summary")
    _ds_completed_stages = [
        (sid, sname)
        for sid, sname, _ in stages
        if sid != "completed" and _is_stage_complete(sid, _early_facts)
    ]
    if _ds_completed_stages:
        _ds_pdf = _generate_comprehensive_onboarding_pdf(
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id,
            facts=_early_facts,
        )
        st.sidebar.download_button(
            label="📥 Download Complete Summary",
            data=_ds_pdf,
            file_name=f"onboarding_summary_{st.session_state.session_id[:8]}.pdf",
            mime="application/pdf",
            key="ds_comprehensive_dl",
            use_container_width=True,
        )

    if st.sidebar.button("🔄 Restart Onboarding", use_container_width=True, key="ds_restart"):
        from backend.memory.short_term import ShortTermMemory as _STM
        try:
            db = next(get_db())
            ltm = LongTermMemory(db)
            ltm.clear_user_memories(st.session_state.user_id)
            ltm.reset_onboarding_profile(st.session_state.user_id)
        except Exception as e:
            logger.warning(f"Could not clear long-term memory: {e}")
        try:
            stm = _STM()
            stm.clear_session(st.session_state.session_id)
        except Exception as e:
            logger.warning(f"Could not clear short-term memory: {e}")
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.current_stage = "welcome"
        st.session_state.unlocked_stages = {"welcome"}
        st.session_state.onboarding_started = False
        st.session_state.resume_kickoff_done = False
        st.rerun()

    # --- Main area for Document Search mode ---
    st.markdown(
        '<div class="main-header">📖 Internal Rules & Policy Search</div>',
        unsafe_allow_html=True,
    )

    if _user_name:
        st.markdown(
            f'<p style="text-align:center;color:#666;">Welcome back, <strong>{_user_name}</strong>! '
            f'Your onboarding is complete. Ask me anything about company policies, rules, or procedures.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="text-align:center;color:#666;">Your onboarding is complete. '
            'Ask me anything about company policies, rules, or procedures.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Initialise document-search message history (separate from onboarding messages)
    if "ds_messages" not in st.session_state:
        st.session_state.ds_messages = []

    # Display document-search conversation
    for _ds_msg in st.session_state.ds_messages:
        if _ds_msg["role"] == "user":
            st.markdown(
                f'<div class="chat-message user-message"><strong>You:</strong><br>{_ds_msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-message assistant-message"><strong>📖 Assistant:</strong><br>{_ds_msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            if _ds_msg.get("sources"):
                with st.expander(f"📚 Sources ({len(_ds_msg['sources'])})"):
                    for _si, _src in enumerate(_ds_msg["sources"], 1):
                        _src_display = _src.get("file_name") or _src.get("source", "unknown")
                        st.markdown(
                            f'<div class="source-card">'
                            f'<strong>Source {_si}:</strong> {_src_display}<br>'
                            f'<strong>Category:</strong> {_src.get("category", "general")}<br>'
                            f'<strong>Relevance:</strong> {_src.get("score", 0):.2f}<br>'
                            f'<em>{_src.get("preview", "")}</em>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # Chat input for document search
    _ds_input = st.chat_input("Search internal rules and policies...")

    if _ds_input:
        st.session_state.ds_messages.append({
            "role": "user",
            "content": _ds_input,
            "timestamp": datetime.now().isoformat(),
        })

        with st.spinner("🔍 Searching internal documents..."):
            try:
                _ds_result = run_agent(
                    user_input=_ds_input,
                    user_id=st.session_state.user_id,
                    session_id=st.session_state.session_id,
                    current_stage="completed",
                    history=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.ds_messages[-6:]
                    ],
                )
                st.session_state.ds_messages.append({
                    "role": "assistant",
                    "content": _ds_result["response"],
                    "sources": _ds_result.get("sources", []),
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Document search error: {e}")
                st.session_state.ds_messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error while searching: {e}",
                    "sources": [],
                    "timestamp": datetime.now().isoformat(),
                })
        st.rerun()

    # Footer metrics
    st.markdown("---")
    _fc1, _fc2 = st.columns(2)
    with _fc1:
        st.metric("💬 Messages", len(st.session_state.ds_messages))
    with _fc2:
        try:
            _ds_dc = rag.vector_store.get_collection_count()
            st.metric("📚 Knowledge Base", f"{_ds_dc} docs")
        except Exception:
            st.metric("📚 Knowledge Base", "Loading...")

    st.stop()  # Skip the entire onboarding UI below

# ---------------------------------------------------------------------------
# Normal onboarding flow (onboarding NOT yet complete)
# ---------------------------------------------------------------------------
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

    st.markdown("---")
    st.markdown("**Web search (Tavily)**")
    _provider = str(getattr(settings, "WEB_SEARCH_PROVIDER", "tavily") or "tavily").strip().lower()
    _key_len = len(str(getattr(settings, "TAVILY_API_KEY", "") or "").strip())
    st.caption(f"Provider: `{_provider}`")
    st.caption(f"TAVILY_API_KEY configured: `{'yes' if _key_len > 0 else 'no'}`")

    col_tav_a, col_tav_b = st.columns([1, 1])
    with col_tav_a:
        if st.button("Check Tavily", use_container_width=True, key="dev_check_tavily"):
            _tavily_connectivity_check.clear()
    with col_tav_b:
        st.caption("(cached 10 min)")

    _tav_status = _tavily_connectivity_check(_api_key_len=_key_len)
    if not _tav_status.get("configured"):
        st.warning("Tavily not configured")
    elif _tav_status.get("ok"):
        st.success(f"Tavily OK ({_tav_status.get('latency_ms', '?')} ms)")
    else:
        err = _tav_status.get("error") or "unknown error"
        st.error(f"Tavily error: {err}")

    st.markdown("---")
    st.markdown("**Onboarding generation debug**")
    try:
        _facts = _get_onboarding_facts(st.session_state.user_id) or {}
        _role = str(_facts.get("welcome.role") or "").strip()
        st.caption(f"Current stage: `{st.session_state.current_stage}`")
        st.caption(f"Stored role (welcome.role): `{_role or '(empty)'}`")

        _agent_tmp = AgentNodes()
        _role_cat_value = _agent_tmp._role_category(_role) if _role else "(none)"
        st.caption(f"Role category: `{_role_cat_value}`")

        db = next(get_db())
        ltm = LongTermMemory(db)

        stage_rows = []
        for _stage_key in ["department_info", "key_responsibilities", "tools_systems", "training_needs"]:
            bank_key = AgentNodes._generated_bank_cache_key(_role, _stage_key)
            research_key = AgentNodes._role_research_cache_key(_role, _stage_key)
            cached_bank = ltm.get_memory(st.session_state.user_id, "onboarding_generated", bank_key)
            cached_research = ltm.get_memory(st.session_state.user_id, "onboarding_generated", research_key)
            stage_rows.append(
                {
                    "stage": _stage_key,
                    "bank_questions": len(cached_bank) if isinstance(cached_bank, list) else 0,
                    "research_cached": bool(isinstance(cached_research, dict) and cached_research),
                }
            )

        st.dataframe(stage_rows, use_container_width=True, hide_index=True)
        st.caption("If stage is `welcome`, generated questions are not created yet. They generate when you enter the next stages.")
    except Exception as e:
        st.caption(f"Debug unavailable: {type(e).__name__}")

    st.markdown("---")
    st.markdown("**Upload Documents to RAG**")
    _upload_category = st.text_input(
        "Upload category",
        value="uploaded",
        key="dev_upload_category",
        help="Optional metadata category to help retrieval/reranking.",
    )
    _upload_stage = st.selectbox(
        "Upload stage (optional)",
        options=["", "welcome", "department_info", "key_responsibilities", "tools_systems", "training_needs"],
        key="dev_upload_stage",
    )
    _uploaded_files = st.file_uploader(
        "Upload .md, .pdf, or .txt files",
        type=["md", "markdown", "pdf", "txt"],
        accept_multiple_files=True,
        key="dev_upload_files",
        label_visibility="collapsed",
    )
    if st.button("📤 Ingest uploaded files", use_container_width=True, key="dev_ingest_files"):
        if not _uploaded_files:
            st.warning("No files selected")
        else:
            try:
                from langchain_core.documents import Document
            except Exception:
                Document = None

            upload_root = (Path(__file__).resolve().parent / "uploaded_docs")
            upload_root.mkdir(parents=True, exist_ok=True)

            docs_to_add = []
            saved = 0
            for f in _uploaded_files:
                upload_id = str(uuid.uuid4())
                file_name = str(getattr(f, "name", "uploaded.md"))
                try:
                    raw = f.getvalue()
                except Exception:
                    raw = f.read()

                if file_name.lower().endswith(".pdf"):
                    try:
                        from PyPDF2 import PdfReader
                        reader = PdfReader(BytesIO(raw))
                        text = "\n".join(
                            page.extract_text() or "" for page in reader.pages
                        )
                    except Exception as pdf_err:
                        st.warning(f"Could not extract text from {file_name}: {pdf_err}")
                        continue
                else:
                    text = raw.decode("utf-8", errors="replace")

                safe_name = f"{upload_id}_{Path(file_name).name}"
                (upload_root / safe_name).write_bytes(raw)
                saved += 1

                meta = {
                    "origin": "upload",
                    "upload_id": upload_id,
                    "file_name": Path(file_name).name,
                    "category": _upload_category or "uploaded",
                }
                if _upload_stage:
                    meta["stage"] = _upload_stage

                if Document is not None:
                    docs_to_add.append(Document(page_content=text, metadata=meta))
                else:
                    docs_to_add.append(rag.document_processor.create_document(content=text, metadata=meta, source=Path(file_name).name))

            with st.spinner("Indexing uploaded documents..."):
                rag.initialize_knowledge_base(docs_to_add)

            st.success(f"Ingested {len(docs_to_add)} file(s) and saved {saved} raw file(s) to {upload_root}")
            st.rerun()

    st.markdown("---")
    st.markdown("**Manage uploaded files**")
    _known_uploads = []
    try:
        _known_uploads = rag.vector_store.list_uploaded_files()
    except Exception:
        _known_uploads = []

    if not _known_uploads:
        st.caption("No uploaded files indexed yet.")
    else:
        _upload_label_to_id = {
            f"{u.get('file_name','unknown')} ({u.get('chunks',0)} chunks)": u.get("upload_id")
            for u in _known_uploads
        }
        _selected_label = st.selectbox(
            "Select uploaded file",
            options=list(_upload_label_to_id.keys()),
            key="dev_selected_upload",
        )
        _selected_upload_id = _upload_label_to_id.get(_selected_label)

        col_del_a, col_del_b = st.columns([1, 1])
        with col_del_a:
            if st.button("🗑️ Delete from index", use_container_width=True, key="dev_delete_upload"):
                removed = rag.vector_store.delete_by_upload_id(str(_selected_upload_id or ""))
                st.success(f"Removed {removed} chunk(s) from the vector index")
                st.rerun()

        with col_del_b:
            if st.button("🧹 Delete raw file(s)", use_container_width=True, key="dev_delete_raw"):
                upload_root = (Path(__file__).resolve().parent / "uploaded_docs")
                deleted = 0
                if upload_root.exists() and _selected_upload_id:
                    for p in upload_root.glob(f"{_selected_upload_id}_*"):
                        try:
                            p.unlink()
                            deleted += 1
                        except Exception as e:
                            logger.warning(f"Could not delete {p}: {e}")
                st.success(f"Deleted {deleted} raw file(s)")
                st.rerun()

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
        st.session_state.resume_kickoff_done = False
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

if has_existing_progress and not st.session_state.messages and not st.session_state.resume_kickoff_done:
    derived_stage = _derive_current_stage_from_facts(_sidebar_facts)
    if derived_stage != st.session_state.current_stage:
        st.session_state.current_stage = derived_stage

    unlocked = {"welcome"}
    for stage_id, _, _ in stages:
        unlocked.add(stage_id)
        if stage_id == derived_stage:
            break
    st.session_state.unlocked_stages = unlocked

    if not st.session_state.onboarding_started:
        st.session_state.onboarding_started = True

    with st.spinner("🤖 Resuming your onboarding..."):
        try:
            result = run_agent(
                user_input="I just arrived and I'm ready to continue onboarding",
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
                current_stage=st.session_state.current_stage,
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "stage": result.get("next_stage") or st.session_state.current_stage,
                "sources": result.get("sources", []),
                "timestamp": datetime.now().isoformat(),
            })

            next_stage = result.get("next_stage")
            if next_stage and next_stage != st.session_state.current_stage:
                st.session_state.current_stage = next_stage
                st.session_state.unlocked_stages.add(next_stage)

        except Exception as e:
            logger.error(f"Error resuming onboarding: {e}")

    st.session_state.resume_kickoff_done = True
    st.rerun()

is_resume_banner = (
    has_existing_progress
    and len(st.session_state.messages) == 0
)

if "skip_next_stage_intro" not in st.session_state:
    st.session_state.skip_next_stage_intro = False

if "resume_initialized" not in st.session_state:
    st.session_state.resume_initialized = False

if has_existing_progress and not st.session_state.resume_initialized:
    stage_ids_in_order = [s[0] for s in stages]
    interactive_stage_ids = [s for s in stage_ids_in_order if s != "completed"]

    completed_stage_ids: list[str] = [
        stage_id
        for stage_id in interactive_stage_ids
        if _is_stage_complete(stage_id, _sidebar_facts)
    ]

    next_stage_id = "completed"
    for stage_id in interactive_stage_ids:
        if stage_id not in completed_stage_ids:
            next_stage_id = stage_id
            break

    st.session_state.resume_completed_stage_ids = completed_stage_ids
    st.session_state.resume_next_stage_id = next_stage_id
    st.session_state.resume_total_stages = len(interactive_stage_ids)
    st.session_state.resume_completed_count = len(completed_stage_ids)
    st.session_state.resume_initialized = True

_skip_stage_intro = bool(st.session_state.get("skip_next_stage_intro"))
if _skip_stage_intro:
    if is_resume_banner:
        st.session_state.skip_next_stage_intro = False
    else:
        stage_titles = {stage_id: stage_name for stage_id, stage_name, _ in stages}
        stage_title = stage_titles.get(st.session_state.current_stage, st.session_state.current_stage)
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem 2rem 0.5rem 2rem;">
            <h2>{stage_title}</h2>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.skip_next_stage_intro = False

if (
    len(current_stage_messages) == 0
    and (has_existing_progress or st.session_state.onboarding_started)
    and not (has_existing_progress and st.session_state.current_stage == "welcome" and len(st.session_state.messages) == 0)
    and not _skip_stage_intro
    and not is_resume_banner
):
    stage_titles = {stage_id: stage_name for stage_id, stage_name, _ in stages}
    stage_title = stage_titles.get(st.session_state.current_stage, st.session_state.current_stage)

    intro_body = {
        "welcome": "At TechVenture Solutions, we're committed to making your onboarding experience smooth and engaging. Let's start by getting to know you!",
        "department_info": "Let's get you familiar with your team and department! We'll cover the org structure, introduce key stakeholders, and schedule some intro meetings.",
        "key_responsibilities": "Now let's outline your role in detail — duties, KPIs, goals, and initial tasks to get you started.",
        "tools_systems": "Time to get your tech stack set up! We'll walk through IT access, software installs, and make sure everything works.",
        "training_needs": "Let's build your personalized learning path — compliance training, role-specific modules, and skill development.",
        "completed": "You're all set! You're ready to work independently with clear next steps to explore advanced features and get ongoing support."
    }.get(st.session_state.current_stage, "Let's continue your onboarding journey.")

    st.markdown(f"""
    <div style="text-align: center; padding: 2rem;">
        <h2>{stage_title}</h2>
        <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
            {intro_body}
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
                    _src_file_name = source.get('file_name', '')
                    _src_upload_id = source.get('upload_id', '')
                    _src_display_name = _src_file_name or source.get('source', 'unknown')

                    st.markdown(f"""
                    <div class="source-card">
                        <strong>Source {i}:</strong> {_src_display_name}<br>
                        <strong>Category:</strong> {source.get('category', 'general')}<br>
                        <strong>Relevance:</strong> {source.get('score', 0):.2f}<br>
                        <em>{source.get('preview', '')}</em>
                    </div>
                    """, unsafe_allow_html=True)

                    if _src_file_name and _src_upload_id:
                        with st.expander(f"📄 View full document: {_src_file_name}"):
                            _upload_root = Path(__file__).resolve().parent / "uploaded_docs"
                            _found_files = list(_upload_root.glob(f"{_src_upload_id}_*")) if _upload_root.exists() else []
                            if _found_files:
                                try:
                                    _doc_text = _found_files[0].read_text(encoding="utf-8", errors="replace")
                                    st.markdown(_doc_text)
                                except Exception as _read_err:
                                    st.error(f"Could not read file: {_read_err}")
                            else:
                                st.warning(f"Raw file not found for upload ID: {_src_upload_id}")


user_input = None
if has_existing_progress or st.session_state.onboarding_started:
    _last_msg = st.session_state.messages[-1] if st.session_state.messages else None
    _last_content = (
        str(_last_msg.get("content") or "").lower()
        if isinstance(_last_msg, dict)
        else ""
    )
    _expecting_profile_pic = bool(
        isinstance(_last_msg, dict)
        and _last_msg.get("role") == "assistant"
        and isinstance(_last_msg.get("content"), str)
        and _last_msg.get("stage") == st.session_state.current_stage
        and any(
            k in _last_content
            for k in [
                "profile picture",
                "profile photo",
                "headshot",
                "upload a photo",
                "upload your photo",
                "upload a headshot",
                "upload your headshot",
            ]
        )
    )

    if _expecting_profile_pic:
        _img = st.file_uploader(
            "Upload a profile picture",
            type=["png", "jpg", "jpeg"],
            key=f"profile_pic_uploader_{st.session_state.current_stage}",
        )
        if _img is not None:
            try:
                upload_root = (Path(__file__).resolve().parent / "uploaded_profile_pics")
                upload_root.mkdir(parents=True, exist_ok=True)
                ext = Path(_img.name).suffix.lower() or ".png"
                safe_ext = ext if ext in (".png", ".jpg", ".jpeg") else ".png"
                filename = f"user{st.session_state.user_id}_{st.session_state.session_id[:8]}_{int(time.time())}{safe_ext}"
                target = upload_root / filename
                target.write_bytes(_img.getvalue())
                st.image(_img, caption="Selected profile picture", use_container_width=True)
                user_input = str(target)
            except Exception as e:
                st.error(f"Could not save image: {type(e).__name__}")
    else:
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
        _resume_next_stage_id = st.session_state.get("resume_next_stage_id", "welcome")
        _resume_completed_count = int(st.session_state.get("resume_completed_count", 0) or 0)
        _resume_total_stages = int(st.session_state.get("resume_total_stages", 0) or 0)
        _stage_titles = {stage_id: stage_name for stage_id, stage_name, _ in stages}
        _next_stage_title = _stage_titles.get(_resume_next_stage_id, _resume_next_stage_id)

        _next_intro_body = {
            "welcome": "At TechVenture Solutions, we're committed to making your onboarding experience smooth and engaging. Let's start by getting to know you!",
            "department_info": "Let's get you familiar with your team and department! We'll cover the org structure, introduce key stakeholders, and schedule some intro meetings.",
            "key_responsibilities": "Now let's outline your role in detail — duties, KPIs, goals, and initial tasks to get you started.",
            "tools_systems": "Time to get your tech stack set up! We'll walk through IT access, software installs, and make sure everything works.",
            "training_needs": "Let's build your personalized learning path — compliance training, role-specific modules, and skill development.",
            "completed": "You're all set! You're ready to work independently with clear next steps to explore advanced features and get ongoing support."
        }.get(_resume_next_stage_id, "Let's continue your onboarding journey.")

        st.markdown(f"""
        <div style="text-align: center; padding: 2rem;">
            <h2>👋 Welcome back!</h2>
            <p style="font-size: 1.65rem; color: #667eea; margin: 0.6rem 0 0 0; font-weight: 800;">
                {_next_stage_title}
            </p>
            <p style="font-size: 1rem; color: #666; margin: 1.25rem 0;">
                I found your saved onboarding progress.
            </p>
            <p style="font-size: 1.1rem; color: #2d3748; margin: 0.75rem 0;">
                <strong>Progress:</strong> {_resume_completed_count}/{_resume_total_stages} stage(s) completed
            </p>
            <p style="font-size: 1rem; color: #666; margin: 1rem auto 0 auto; max-width: 850px;">
                {_next_intro_body}
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_resume_a, col_resume_b, col_resume_c = st.columns([1, 1, 1])
        with col_resume_b:
            if st.button("▶️ Continue where I left off", use_container_width=True, key="resume_continue"):
                st.session_state.onboarding_started = True
                st.session_state.current_stage = _resume_next_stage_id
                st.session_state.skip_next_stage_intro = True
                if "unlocked_stages" in st.session_state and isinstance(st.session_state.unlocked_stages, set):
                    st.session_state.unlocked_stages.add(_resume_next_stage_id)
                st.rerun()

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
