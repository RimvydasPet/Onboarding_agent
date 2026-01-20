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
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import json

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
    .checklist-container {
        background: #f8f9fa;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .checklist-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #667eea;
        margin-bottom: 1rem;
    }
    .checklist-item {
        font-size: 1.1rem;
        padding: 0.5rem 0;
        display: flex;
        align-items: center;
    }
    .checklist-item.completed {
        color: #28a745;
        text-decoration: line-through;
    }
    .progress-text {
        font-size: 1rem;
        color: #667eea;
        font-weight: bold;
        margin-top: 1rem;
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

def generate_pdf(user_data):
    """Generate PDF with onboarding information."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    story = []
    
    story.append(Paragraph("🎉 Onboarding Summary", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Personal Information", heading_style))
    
    data = [
        ['Field', 'Information'],
        ['Name', user_data.get('name', 'Not provided')],
        ['Role/Position', user_data.get('role', 'Not provided')],
        ['Goals', user_data.get('goals', 'Not provided')],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Key Points", heading_style))
    
    key_points = [
        "✓ Welcome message acknowledged",
        "✓ Personal information collected",
        "✓ Role and position documented",
    ]
    
    if user_data.get('goals'):
        key_points.append("✓ Goals and objectives discussed")
    
    for point in key_points:
        story.append(Paragraph(f"• {point}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Next Steps", heading_style))
    
    next_steps = [
        "Continue to the next onboarding stage",
        "Explore the platform features",
        "Set up your workspace preferences",
        "Connect with your team members"
    ]
    
    for step in next_steps:
        story.append(Paragraph(f"• {step}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Thank you for completing the first stage of onboarding! 🚀", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_stage" not in st.session_state:
    st.session_state.current_stage = "welcome"

if "user_id" not in st.session_state:
    st.session_state.user_id = 1

if "checklist" not in st.session_state:
    st.session_state.checklist = {
        "welcome_read": False,
        "name_provided": False,
        "role_provided": False,
        "goals_discussed": False
    }

if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "name": "",
        "role": "",
        "goals": ""
    }

if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

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

if st.session_state.current_stage == "welcome":
    st.sidebar.markdown("### ✅ Current Stage Tasks")
    
    checklist_items = [
        ("welcome_read", "Read welcome message"),
        ("name_provided", "Provide your name"),
        ("role_provided", "Share your role/position"),
        ("goals_discussed", "Discuss your goals (optional)")
    ]
    
    completed_count = sum(1 for key, _ in checklist_items[:3] if st.session_state.checklist[key])
    
    for key, label in checklist_items:
        if st.session_state.checklist[key]:
            st.sidebar.markdown(f"✅ ~~{label}~~")
        else:
            st.sidebar.markdown(f"⬜ {label}")
    
    st.sidebar.markdown(f"**📊 {completed_count}/3 required tasks done**")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
st.sidebar.markdown(f"**Messages:** {len(st.session_state.messages)}")

if st.sidebar.button("🔄 New Session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.current_stage = "welcome"
    st.session_state.checklist = {
        "welcome_read": False,
        "name_provided": False,
        "role_provided": False,
        "goals_discussed": False
    }
    st.session_state.user_data = {
        "name": "",
        "role": "",
        "goals": ""
    }
    st.session_state.conversation_started = False
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

if len(st.session_state.messages) == 0 and not st.session_state.conversation_started:
    welcome_message = """
    <div style="text-align: center; padding: 2rem;">
        <h2>👋 Welcome to Your Onboarding Journey!</h2>
        <p style="font-size: 1.1rem; margin: 1.5rem 0;">
            I'm your personal onboarding assistant, here to help you get started with our platform.
        </p>
        <p style="font-size: 1rem; color: #666;">
            To complete this stage, I'll need to collect some basic information from you:
        </p>
    </div>
    """
    st.markdown(welcome_message, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="checklist-container">
        <div class="checklist-title">✅ Current Stage Tasks</div>
        <div class="checklist-item">⬜ Read welcome message</div>
        <div class="checklist-item">⬜ Provide your name</div>
        <div class="checklist-item">⬜ Share your role/position</div>
        <div class="checklist-item">⬜ Discuss your goals (optional)</div>
        <div class="progress-text">📊 0/3 required tasks done</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f0f7ff; border-radius: 10px; margin: 1rem 0;">
        <p style="margin: 0; color: #667eea; font-weight: bold;">
            💡 Type anything in the chat below to get started!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.session_state.conversation_started = True

user_input = st.chat_input("Type your message here...")

if user_input:
    if not st.session_state.checklist["welcome_read"]:
        st.session_state.checklist["welcome_read"] = True
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    memory.save_message(st.session_state.session_id, "user", user_input)
    
    with st.spinner("🤔 Thinking..."):
        try:
            completed_count = sum(1 for key in ["welcome_read", "name_provided", "role_provided"] 
                                if st.session_state.checklist[key])
            
            checklist_status = "\n".join([
                f"- Welcome read: {'✓' if st.session_state.checklist['welcome_read'] else '✗'}",
                f"- Name provided: {'✓' if st.session_state.checklist['name_provided'] else '✗'}",
                f"- Role provided: {'✓' if st.session_state.checklist['role_provided'] else '✗'}",
                f"- Goals discussed: {'✓' if st.session_state.checklist['goals_discussed'] else '✗'}"
            ])
            
            user_data_status = "\n".join([
                f"- Name: {st.session_state.user_data['name'] or 'Not provided'}",
                f"- Role: {st.session_state.user_data['role'] or 'Not provided'}",
                f"- Goals: {st.session_state.user_data['goals'] or 'Not provided'}"
            ])
            
            system_prompt = f"""You are a friendly onboarding assistant helping new users get started.

Current Stage: Welcome Stage (First Stage)

Your goal is to collect the following information from the user:
1. Their name (REQUIRED)
2. Their role/position (REQUIRED)
3. Their goals (OPTIONAL)

Current Checklist Status:
{checklist_status}

Information Collected So Far:
{user_data_status}

IMPORTANT INSTRUCTIONS:
- Be warm, welcoming, and conversational
- Ask for ONE piece of information at a time
- When the user provides information, acknowledge it and extract the key details
- Remember ALL information provided across the conversation
- If the user provides their name, acknowledge it and ask about their role
- If the user provides their role, acknowledge it and ask about their goals
- Once you have name and role (3/3 required tasks), inform them they can now export a PDF summary
- Keep responses concise and friendly
- Use the user's name once you know it

Current Progress: {completed_count}/3 required tasks completed"""

            recent_messages = memory.get_messages(st.session_state.session_id, limit=10)
            
            messages = [SystemMessage(content=system_prompt)]
            
            for msg in recent_messages[-5:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=user_input))
            
            response = llm.invoke(messages)
            response_content = response.content
            
            user_input_lower = user_input.lower()
            response_lower = response_content.lower()
            
            if not st.session_state.checklist["name_provided"]:
                if any(word in user_input_lower for word in ["my name is", "i'm", "i am", "call me", "name's", "this is"]):
                    name_parts = user_input.split()
                    for i, word in enumerate(name_parts):
                        if word.lower() in ["is", "i'm", "am", "me", "name's"] and i + 1 < len(name_parts):
                            potential_name = name_parts[i + 1].strip('.,!?')
                            if potential_name and len(potential_name) > 1 and potential_name[0].isupper():
                                st.session_state.user_data["name"] = potential_name.capitalize()
                                st.session_state.checklist["name_provided"] = True
                                break
            
            if not st.session_state.checklist["role_provided"]:
                role_indicators = [
                    "role", "position", "job", "work as", "working as", "i'm a", "i am a",
                    "developer", "engineer", "manager", "designer", "analyst", "student", 
                    "teacher", "consultant", "director", "lead", "senior", "junior", "intern",
                    "specialist", "coordinator", "assistant", "administrator", "officer",
                    "architect", "scientist", "researcher", "professor", "instructor"
                ]
                
                if any(indicator in user_input_lower for indicator in role_indicators):
                    st.session_state.user_data["role"] = user_input
                    st.session_state.checklist["role_provided"] = True
                elif "role" in response_lower or "position" in response_lower:
                    if len(user_input.split()) >= 2:
                        st.session_state.user_data["role"] = user_input
                        st.session_state.checklist["role_provided"] = True
            
            if not st.session_state.checklist["goals_discussed"]:
                goal_keywords = ["goal", "want to", "hoping to", "plan to", "learn", "improve", "achieve", 
                               "objective", "aim", "aspire", "interested in", "looking to"]
                if any(keyword in user_input_lower for keyword in goal_keywords):
                    st.session_state.user_data["goals"] = user_input
                    st.session_state.checklist["goals_discussed"] = True
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat()
            })
            
            memory.save_message(st.session_state.session_id, "assistant", response_content)
            
            memory.update_context(st.session_state.session_id, {
                "checklist": st.session_state.checklist,
                "user_data": st.session_state.user_data
            })
            
            db = next(get_db())
            ltm = LongTermMemory(db)
            ltm.update_onboarding_progress(
                st.session_state.user_id,
                st.session_state.current_stage,
                f"checklist_{completed_count}_of_3"
            )
            
            if st.session_state.user_data["name"]:
                ltm.save_memory(
                    st.session_state.user_id,
                    "user_profile",
                    "user_name",
                    st.session_state.user_data["name"],
                    importance=5
                )
            
            if st.session_state.user_data["role"]:
                ltm.save_memory(
                    st.session_state.user_id,
                    "user_profile",
                    "user_role",
                    st.session_state.user_data["role"],
                    importance=5
                )
            
            if st.session_state.user_data["goals"]:
                ltm.save_memory(
                    st.session_state.user_id,
                    "user_profile",
                    "user_goals",
                    st.session_state.user_data["goals"],
                    importance=4
                )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    st.rerun()

st.markdown("---")

completed_required = sum(1 for key in ["welcome_read", "name_provided", "role_provided"] 
                        if st.session_state.checklist[key])

if completed_required >= 3:
    st.success("🎉 Congratulations! You've completed all required tasks for this stage!")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        pdf_buffer = generate_pdf(st.session_state.user_data)
        st.download_button(
            label="📄 Download PDF Summary",
            data=pdf_buffer,
            file_name=f"onboarding_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        if st.button("➡️ Continue to Next Stage", use_container_width=True):
            st.session_state.current_stage = "profile_setup"
            st.success("Moving to Profile Setup stage!")
            st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    redis_status = "✅ Active" if memory.redis_available else "⚠️ Fallback"
    st.metric("Memory", redis_status)
with col3:
    st.metric("✅ Tasks", f"{completed_required}/3")
