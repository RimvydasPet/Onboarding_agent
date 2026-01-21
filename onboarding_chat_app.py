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
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSPIRATIONAL_QUOTES = [
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Your limitation—it's only your imagination.", "Unknown"),
    ("Great things never come from comfort zones.", "Unknown"),
    ("Dream it. Wish it. Do it.", "Unknown"),
    ("Success doesn't just find you. You have to go out and get it.", "Unknown"),
    ("The harder you work for something, the greater you'll feel when you achieve it.", "Unknown"),
    ("Don't stop when you're tired. Stop when you're done.", "Unknown"),
    ("Wake up with determination. Go to bed with satisfaction.", "Unknown"),
    ("Do something today that your future self will thank you for.", "Unknown"),
    ("Little things make big days.", "Unknown"),
    ("It's going to be hard, but hard does not mean impossible.", "Unknown"),
    ("Don't wait for opportunity. Create it.", "Unknown"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Everything you've ever wanted is on the other side of fear.", "George Addair"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
    ("Your future is created by what you do today, not tomorrow.", "Robert Kiyosaki"),
    ("Start where you are. Use what you have. Do what you can.", "Arthur Ashe")
]

def get_random_quote():
    """Get a random inspirational quote."""
    quote, author = random.choice(INSPIRATIONAL_QUOTES)
    return quote, author

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

def summarize_text(text, max_words=15):
    """Summarize text to key points."""
    if not text:
        return "Not provided"
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]) + "..."

def summarize_goals_with_llm(goals_text, llm_instance):
    """Use LLM to extract key points from user's goals."""
    if not goals_text or len(goals_text.strip()) < 5:
        return goals_text
    
    try:
        summary_prompt = f"""Extract 2-3 key goal points from this text. Return ONLY a brief comma-separated list of goals (max 20 words total). No explanations.

User said: "{goals_text}"

Key goals:"""
        
        response = llm_instance.invoke([HumanMessage(content=summary_prompt)])
        summary = response.content.strip()
        
        # Clean up the response
        if summary and len(summary) < 150:
            return summary
        return summarize_text(goals_text, 20)
    except Exception as e:
        logger.warning(f"Failed to summarize goals with LLM: {e}")
        return summarize_text(goals_text, 20)

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
    
    story.append(Paragraph("Onboarding Summary", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Personal Information", heading_style))
    
    name = user_data.get('name', 'Not provided')
    role = summarize_text(user_data.get('role', ''), 10)
    goals = summarize_text(user_data.get('goals', ''), 15)
    
    data = [
        ['Field', 'Information'],
        ['Name', name],
        ['Role/Position', role],
        ['Goals', goals],
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

st.markdown("---")

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant:</strong><br>{content}</div>', unsafe_allow_html=True)

if len(st.session_state.messages) == 0:
    quote, author = get_random_quote()
    welcome_message = f"""
    <div style="text-align: center; padding: 2rem;">
        <h2>👋 Welcome to TechVenture Solutions!</h2>
        <p style="font-size: 1.2rem; font-style: italic; color: #667eea; margin: 1.5rem 0;">
            "{quote}" - {author}
        </p>
        <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
            At TechVenture Solutions, we're committed to making your onboarding experience smooth and engaging.
        </p>
        <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
            📖 Please read this welcome message, then type your name below or introduce yourself to begin your journey with us!
        </p>
    </div>
    """
    st.markdown(welcome_message, unsafe_allow_html=True)
    
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
            
            # Add previous messages (excluding the current one we just saved)
            for msg in recent_messages[:-1][-5:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add current user input
            messages.append(HumanMessage(content=user_input))
            
            response = llm.invoke(messages)
            response_content = response.content
            
            user_input_lower = user_input.lower()
            response_lower = response_content.lower()
            
            name_just_provided = False
            
            if not st.session_state.checklist["name_provided"]:
                name_triggers = ["my name is", "i'm", "i am", "call me", "name's", "this is", "hey", "hi", "hello"]
                
                if any(trigger in user_input_lower for trigger in name_triggers):
                    name_parts = user_input.split()
                    for i, word in enumerate(name_parts):
                        if word.lower() in ["is", "i'm", "am", "me", "name's"] and i + 1 < len(name_parts):
                            potential_name = name_parts[i + 1].strip('.,!?')
                            if potential_name and len(potential_name) > 1:
                                st.session_state.user_data["name"] = potential_name.capitalize()
                                st.session_state.checklist["name_provided"] = True
                                name_just_provided = True
                                break
                
                if not st.session_state.checklist["name_provided"]:
                    clean_input = user_input.strip().strip('.,!?')
                    words = clean_input.split()
                    if len(words) <= 3 and len(clean_input) >= 2:
                        st.session_state.user_data["name"] = clean_input.title()
                        st.session_state.checklist["name_provided"] = True
                        name_just_provided = True
            
            if not st.session_state.checklist["role_provided"] and st.session_state.checklist["name_provided"] and not name_just_provided:
                role_keywords = [
                    "developer", "engineer", "manager", "designer", "analyst", "student", 
                    "teacher", "consultant", "director", "lead", "senior", "junior", "intern",
                    "specialist", "coordinator", "administrator", "officer",
                    "architect", "scientist", "researcher", "professor", "instructor",
                    "accountant", "lawyer", "doctor", "nurse", "sales", "marketing",
                    "hr", "human resources", "ceo", "cto", "cfo", "founder", "owner",
                    "programmer", "writer", "editor", "artist", "musician", "chef",
                    "driver", "pilot", "mechanic", "electrician", "plumber", "carpenter",
                    "technician", "support", "customer", "service", "agent", "representative"
                ]
                
                role_phrases = ["work as", "working as", "i'm a", "i am a", "my role", "my position", "my job",
                               "i work", "i do", "profession", "occupation", "career"]
                
                has_role_keyword = any(keyword in user_input_lower for keyword in role_keywords)
                has_role_phrase = any(phrase in user_input_lower for phrase in role_phrases)
                
                if has_role_keyword or has_role_phrase:
                    st.session_state.user_data["role"] = user_input
                    st.session_state.checklist["role_provided"] = True
                elif len(user_input.split()) >= 1 and len(user_input) >= 3:
                    st.session_state.user_data["role"] = user_input
                    st.session_state.checklist["role_provided"] = True
            
            if not st.session_state.checklist["goals_discussed"]:
                goal_keywords = ["goal", "want to", "hoping to", "plan to", "learn", "improve", "achieve", 
                               "objective", "aim", "aspire", "interested in", "looking to"]
                if any(keyword in user_input_lower for keyword in goal_keywords):
                    # Summarize goals to key points using LLM
                    summarized_goals = summarize_goals_with_llm(user_input, llm)
                    st.session_state.user_data["goals"] = summarized_goals
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
