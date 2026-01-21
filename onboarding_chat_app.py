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

def generate_pdf(user_data, role_type=None, it_profile=None, sales_profile=None, learning_preferences=None, current_stage="welcome"):
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
    
    if role_type:
        data.append(['Role Type', role_type])
    
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
    
    # Add role-specific profile information
    if current_stage == "profile_setup" or (it_profile and any(it_profile.values())) or (sales_profile and any(sales_profile.values())):
        if role_type == "IT" and it_profile:
            story.append(Paragraph("IT Profile Details", heading_style))
            
            it_data = [['Field', 'Information']]
            if it_profile.get('department'):
                it_data.append(['Department', summarize_text(it_profile['department'], 15)])
            if it_profile.get('role_level'):
                it_data.append(['Role Level', summarize_text(it_profile['role_level'], 10)])
            if it_profile.get('tech_stack'):
                it_data.append(['Tech Stack', summarize_text(it_profile['tech_stack'], 20)])
            if it_profile.get('experience_years'):
                it_data.append(['Experience', summarize_text(it_profile['experience_years'], 10)])
            if it_profile.get('specialization'):
                it_data.append(['Specialization', summarize_text(it_profile['specialization'], 15)])
            if it_profile.get('preferred_ide'):
                it_data.append(['Preferred IDE', summarize_text(it_profile['preferred_ide'], 10)])
            if it_profile.get('os_preference'):
                it_data.append(['OS Preference', summarize_text(it_profile['os_preference'], 10)])
            if it_profile.get('github_username'):
                it_data.append(['GitHub', summarize_text(it_profile['github_username'], 15)])
            
            if len(it_data) > 1:
                it_table = Table(it_data, colWidths=[2*inch, 4*inch])
                it_table.setStyle(TableStyle([
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
                story.append(it_table)
                story.append(Spacer(1, 0.3*inch))
        
        elif role_type == "Sales" and sales_profile:
            story.append(Paragraph("Sales Profile Details", heading_style))
            
            sales_data = [['Field', 'Information']]
            if sales_profile.get('sales_role'):
                sales_data.append(['Sales Role', summarize_text(sales_profile['sales_role'], 15)])
            if sales_profile.get('seniority'):
                sales_data.append(['Seniority', summarize_text(sales_profile['seniority'], 10)])
            if sales_profile.get('territory'):
                sales_data.append(['Territory', summarize_text(sales_profile['territory'], 15)])
            if sales_profile.get('product_lines'):
                sales_data.append(['Product Lines', summarize_text(sales_profile['product_lines'], 20)])
            if sales_profile.get('crm_system'):
                sales_data.append(['CRM System', summarize_text(sales_profile['crm_system'], 10)])
            if sales_profile.get('sales_methodology'):
                sales_data.append(['Methodology', summarize_text(sales_profile['sales_methodology'], 15)])
            if sales_profile.get('quota'):
                sales_data.append(['Quota', summarize_text(sales_profile['quota'], 15)])
            if sales_profile.get('experience_years'):
                sales_data.append(['Experience', summarize_text(sales_profile['experience_years'], 10)])
            
            if len(sales_data) > 1:
                sales_table = Table(sales_data, colWidths=[2*inch, 4*inch])
                sales_table.setStyle(TableStyle([
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
                story.append(sales_table)
                story.append(Spacer(1, 0.3*inch))
    
    # Add Learning Preferences section
    if current_stage == "learning_preferences" or (learning_preferences and any(learning_preferences.values())):
        story.append(Paragraph("Learning Preferences", heading_style))
        
        learning_data = [['Field', 'Information']]
        if learning_preferences:
            if learning_preferences.get('learning_style'):
                learning_data.append(['Learning Style', summarize_text(learning_preferences['learning_style'], 20)])
            if learning_preferences.get('preferred_format'):
                learning_data.append(['Preferred Format', summarize_text(learning_preferences['preferred_format'], 15)])
            if learning_preferences.get('time_commitment'):
                learning_data.append(['Time Commitment', summarize_text(learning_preferences['time_commitment'], 15)])
            if learning_preferences.get('specific_goals'):
                learning_data.append(['Skills to Develop', summarize_text(learning_preferences['specific_goals'], 25)])
            if learning_preferences.get('support_needed'):
                learning_data.append(['Support Needed', summarize_text(learning_preferences['support_needed'], 20)])
            if learning_preferences.get('timeline'):
                learning_data.append(['Timeline', summarize_text(learning_preferences['timeline'], 15)])
        
        if len(learning_data) > 1:
            learning_table = Table(learning_data, colWidths=[2*inch, 4*inch])
            learning_table.setStyle(TableStyle([
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
            story.append(learning_table)
            story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Key Points", heading_style))
    
    key_points = [
        "✓ Welcome message acknowledged",
        "✓ Personal information collected",
        "✓ Role and position documented",
    ]
    
    if user_data.get('goals'):
        key_points.append("✓ Goals and objectives discussed")
    
    if current_stage == "profile_setup" or (it_profile and any(it_profile.values())) or (sales_profile and any(sales_profile.values())):
        key_points.append("✓ Profile setup initiated")
        if role_type == "IT":
            key_points.append("✓ IT-specific configuration started")
        elif role_type == "Sales":
            key_points.append("✓ Sales-specific setup started")
    
    if current_stage == "learning_preferences" or (learning_preferences and any(learning_preferences.values())):
        key_points.append("✓ Learning preferences discussed")
        if learning_preferences:
            if learning_preferences.get('learning_style'):
                key_points.append("✓ Learning style identified")
            if learning_preferences.get('specific_goals'):
                key_points.append("✓ Skills to develop documented")
            if learning_preferences.get('time_commitment'):
                key_points.append("✓ Time commitment established")
            if learning_preferences.get('support_needed'):
                key_points.append("✓ Support resources identified")
    
    for point in key_points:
        story.append(Paragraph(f"• {point}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Next Steps", heading_style))
    
    if current_stage == "welcome":
        next_steps = [
            "Continue to Profile Setup stage",
            "Complete role-specific configuration",
            "Set up your workspace preferences",
            "Connect with your team members"
        ]
    else:
        next_steps = [
            "Complete profile setup",
            "Continue to Learning Preferences stage",
            "Explore the platform features",
            "Connect with your team and mentor"
        ]
    
    for step in next_steps:
        story.append(Paragraph(f"• {step}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Thank you for your progress in the onboarding journey! 🚀", styles['Normal']))
    
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

if "role_type" not in st.session_state:
    st.session_state.role_type = None

if "it_profile" not in st.session_state:
    st.session_state.it_profile = {
        "department": "",
        "role_level": "",
        "tech_stack": "",
        "experience_years": "",
        "specialization": "",
        "preferred_ide": "",
        "os_preference": "",
        "github_username": ""
    }

if "sales_profile" not in st.session_state:
    st.session_state.sales_profile = {
        "sales_role": "",
        "seniority": "",
        "territory": "",
        "product_lines": "",
        "crm_system": "",
        "sales_methodology": "",
        "quota": "",
        "experience_years": "",
        "previous_industry": "",
        "training_needs": ""
    }

if "profile_setup_checklist" not in st.session_state:
    st.session_state.profile_setup_checklist = {
        "profile_started": False,
        "field_1": False,
        "field_2": False,
        "field_3": False,
        "field_4": False
    }

if "learning_preferences" not in st.session_state:
    st.session_state.learning_preferences = {
        "learning_style": "",
        "preferred_format": "",
        "time_commitment": "",
        "specific_goals": "",
        "support_needed": "",
        "timeline": ""
    }

if "learning_checklist" not in st.session_state:
    st.session_state.learning_checklist = {
        "learning_started": False,
        "field_1": False,
        "field_2": False,
        "field_3": False,
        "field_4": False
    }

if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

def detect_role_type(role_text):
    """Detect if role is IT, Sales, or Other based on keywords."""
    if not role_text:
        return None
    
    role_lower = role_text.lower()
    
    it_keywords = [
        "developer", "engineer", "programmer", "architect", "devops", "sre",
        "data scientist", "analyst", "qa", "tester", "security", "admin",
        "sysadmin", "dba", "frontend", "backend", "fullstack", "full stack",
        "software", "tech lead", "cto", "technical", "it", "infrastructure",
        "cloud", "machine learning", "ai", "data engineer", "ml engineer"
    ]
    
    sales_keywords = [
        "sales", "account executive", "ae", "sdr", "bdr", "account manager",
        "sales engineer", "business development", "sales rep", "representative",
        "inside sales", "field sales", "sales manager", "sales director",
        "revenue", "quota", "hunter", "closer"
    ]
    
    if any(keyword in role_lower for keyword in it_keywords):
        return "IT"
    elif any(keyword in role_lower for keyword in sales_keywords):
        return "Sales"
    else:
        return "Other"

def generate_stage_briefing(user_data, role_type, llm_instance):
    """Generate personalized briefing for profile setup stage based on user's role."""
    name = user_data.get('name', 'there')
    role = user_data.get('role', 'team member')
    goals = user_data.get('goals', '')
    
    if role_type == "IT":
        topics = [
            "Your team and who you'll be working with",
            "The tools and technologies you'll be using",
            "Your development environment setup",
            "Access to systems and resources you'll need"
        ]
        focus = "technical setup and team introduction"
        help_examples = "which team you'll join, what tools you'll use, or who your manager will be"
    elif role_type == "Sales":
        topics = [
            "Your sales team and territory",
            "The CRM and sales tools you'll be using",
            "Your product lines and target customers",
            "Your quota structure and support resources"
        ]
        focus = "sales setup and team introduction"
        help_examples = "your territory, which CRM you'll use, or who your sales manager is"
    else:
        topics = [
            "Your department and team members",
            "The tools and systems you'll be using",
            "Your key responsibilities and projects",
            "Training and resources available to you"
        ]
        focus = "team introduction and setup"
        help_examples = "your team, what tools you'll use, or who your manager will be"
    
    topics_formatted = "\n".join([f"• {topic}" for topic in topics])
    
    prompt = f"""Generate a brief, focused introduction message for {name} who is a {role} starting the Profile Setup stage.

Goals mentioned: {goals if goals else 'Not specified'}

The message should:
1. Welcome them to Profile Setup and mention this is a TIME-LIMITED meeting
2. Explain you'll efficiently guide them through their {focus}
3. List these 4 key areas you MUST cover:
{topics_formatted}
4. Emphasize you'll help them understand what they need while moving efficiently
5. Ask them to start with the first topic to make the most of your time together
6. Be warm but focused and efficient (3-4 sentences max)

The tone should be: "We have limited time, so I'll help you efficiently understand and set up everything you need. Let's get started!"

Keep it energetic and action-oriented."""

    try:
        response = llm_instance.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"Failed to generate briefing with LLM: {e}")
        return f"""Welcome to Profile Setup, {name}! 👋

Our meeting time is limited, so let's efficiently cover the key areas for your role as a {role}:
{topics_formatted}

I'll guide you through each area and help you understand what you need. Let's get started with the first topic - which team or department will you be joining?"""

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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧪 Testing Mode")
st.sidebar.markdown("Jump to any stage for testing:")

stage_options = {f"{emoji} {name}": stage_id for stage_id, name, emoji in stages}
selected_stage = st.sidebar.selectbox(
    "Select Stage",
    options=list(stage_options.keys()),
    index=next((i for i, (stage_id, _, _) in enumerate(stages) if stage_id == st.session_state.current_stage), 0),
    key="stage_selector"
)

if st.sidebar.button("🚀 Jump to Stage", use_container_width=True):
    new_stage = stage_options[selected_stage]
    if new_stage != st.session_state.current_stage:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_stage = new_stage
        st.session_state.messages = []
        
        if new_stage == "profile_setup" and not st.session_state.user_data.get('name'):
            st.session_state.user_data['name'] = "Test User"
            st.session_state.user_data['role'] = "Test Role"
            st.session_state.checklist['name_provided'] = True
            st.session_state.checklist['role_provided'] = True
        
        if new_stage == "learning_preferences":
            if not st.session_state.user_data.get('name'):
                st.session_state.user_data['name'] = "Test User"
                st.session_state.user_data['role'] = "Test Role"
            if not st.session_state.role_type:
                st.session_state.role_type = "IT"
        
        st.sidebar.success(f"Jumped to {selected_stage}!")
        st.rerun()

st.sidebar.markdown("---")

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

elif st.session_state.current_stage == "profile_setup":
    st.sidebar.markdown("### ✅ Profile Setup Tasks")
    
    if st.session_state.role_type:
        st.sidebar.markdown(f"**Role Type:** {st.session_state.role_type}")
    
    if st.session_state.role_type == "IT":
        checklist_items = [
            ("profile_started", "Start profile setup"),
            ("field_1", "Department/Team"),
            ("field_2", "Tech stack & tools"),
            ("field_3", "Experience & specialization"),
            ("field_4", "Development preferences")
        ]
    elif st.session_state.role_type == "Sales":
        checklist_items = [
            ("profile_started", "Start profile setup"),
            ("field_1", "Sales role & territory"),
            ("field_2", "CRM & tools setup"),
            ("field_3", "Sales methodology"),
            ("field_4", "Quota & targets")
        ]
    else:
        checklist_items = [
            ("profile_started", "Start profile setup"),
            ("field_1", "Department information"),
            ("field_2", "Key responsibilities"),
            ("field_3", "Tools & systems"),
            ("field_4", "Training needs")
        ]
    
    completed_count = sum(1 for key, _ in checklist_items if st.session_state.profile_setup_checklist[key])
    
    for key, label in checklist_items:
        if st.session_state.profile_setup_checklist[key]:
            st.sidebar.markdown(f"✅ ~~{label}~~")
        else:
            st.sidebar.markdown(f"⬜ {label}")
    
    st.sidebar.markdown(f"**📊 {completed_count}/{len(checklist_items)} tasks done**")

elif st.session_state.current_stage == "learning_preferences":
    st.sidebar.markdown("### ✅ Learning Preferences")
    
    role_type = st.session_state.role_type or "Other"
    
    if role_type == "IT":
        checklist_items = [
            ("learning_started", "Start learning preferences"),
            ("field_1", "Learning style & format"),
            ("field_2", "Technical skills to develop"),
            ("field_3", "Time commitment & pace"),
            ("field_4", "Support & resources needed")
        ]
    elif role_type == "Sales":
        checklist_items = [
            ("learning_started", "Start learning preferences"),
            ("field_1", "Learning style & format"),
            ("field_2", "Product & sales training"),
            ("field_3", "Time commitment & pace"),
            ("field_4", "Support & resources needed")
        ]
    else:
        checklist_items = [
            ("learning_started", "Start learning preferences"),
            ("field_1", "Learning style & format"),
            ("field_2", "Skills to develop"),
            ("field_3", "Time commitment & pace"),
            ("field_4", "Support & resources needed")
        ]
    
    completed_count = sum(1 for key, _ in checklist_items if st.session_state.learning_checklist[key])
    
    for key, label in checklist_items:
        if st.session_state.learning_checklist[key]:
            st.sidebar.markdown(f"✅ ~~{label}~~")
        else:
            st.sidebar.markdown(f"⬜ {label}")
    
    st.sidebar.markdown(f"**📊 {completed_count}/{len(checklist_items)} tasks done**")

st.sidebar.markdown("---")

with st.sidebar.expander("🔧 Developer Info"):
    st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")
    st.markdown(f"**Current Stage:** `{st.session_state.current_stage}`")
    st.markdown(f"**Role Type:** `{st.session_state.role_type or 'Not set'}`")

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
    st.session_state.role_type = None
    st.session_state.it_profile = {
        "department": "",
        "role_level": "",
        "tech_stack": "",
        "experience_years": "",
        "specialization": "",
        "preferred_ide": "",
        "os_preference": "",
        "github_username": ""
    }
    st.session_state.sales_profile = {
        "sales_role": "",
        "seniority": "",
        "territory": "",
        "product_lines": "",
        "crm_system": "",
        "sales_methodology": "",
        "quota": "",
        "experience_years": "",
        "previous_industry": "",
        "training_needs": ""
    }
    st.session_state.profile_setup_checklist = {
        "profile_started": False,
        "field_1": False,
        "field_2": False,
        "field_3": False,
        "field_4": False
    }
    st.session_state.learning_preferences = {
        "learning_style": "",
        "preferred_format": "",
        "time_commitment": "",
        "specific_goals": "",
        "support_needed": "",
        "timeline": ""
    }
    st.session_state.learning_checklist = {
        "learning_started": False,
        "field_1": False,
        "field_2": False,
        "field_3": False,
        "field_4": False
    }
    st.session_state.conversation_started = False
    st.rerun()

st.markdown('<div class="main-header">🤖 Onboarding Assistant</div>', unsafe_allow_html=True)

st.markdown("---")

import html

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        escaped_content = html.escape(content)
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{escaped_content}</div>', unsafe_allow_html=True)
    else:
        escaped_content = content.replace('\n', '<br>')
        st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant:</strong><br>{escaped_content}</div>', unsafe_allow_html=True)

if len(st.session_state.messages) == 0:
    if st.session_state.current_stage == "welcome":
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
    
    elif st.session_state.current_stage == "profile_setup":
        role_type = st.session_state.role_type or "Other"
        user_name = st.session_state.user_data.get('name', 'there')
        
        if role_type == "IT":
            icon = "💻"
            title = "IT Profile Setup"
            description = "Let's configure your technical environment and preferences."
        elif role_type == "Sales":
            icon = "📊"
            title = "Sales Profile Setup"
            description = "Let's set up your sales tools and territory information."
        else:
            icon = "👤"
            title = "Profile Setup"
            description = "Let's gather some information to personalize your experience."
        
        profile_message = f"""
        <div style="text-align: center; padding: 2rem;">
            <h2>{icon} {title}</h2>
            <p style="font-size: 1.2rem; color: #667eea; margin: 1.5rem 0;">
                Welcome, {user_name}!
            </p>
            <p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
                {description}
            </p>
            <p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
                💬 I'll ask you a few questions to help set up your profile. Let's get started!
            </p>
        </div>
        """
        st.markdown(profile_message, unsafe_allow_html=True)
    
    elif st.session_state.current_stage == "learning_preferences":
        role_type = st.session_state.role_type or "Other"
        user_name = st.session_state.user_data.get('name', 'there')
        
        if role_type == "IT":
            icon = "📚"
            title = "Learning Preferences - Technical Development"
            why_important = "Understanding how you learn best helps us create a personalized training path that accelerates your technical growth and ensures you master the tools and technologies efficiently."
            what_to_know = [
                "Your preferred learning style (hands-on, documentation, video tutorials, mentoring)",
                "Technical skills you want to develop and your current proficiency",
                "Time you can dedicate to learning and your preferred pace",
                "Support resources you'll need (mentors, courses, documentation)"
            ]
        elif role_type == "Sales":
            icon = "📚"
            title = "Learning Preferences - Sales Development"
            why_important = "Knowing your learning preferences allows us to design a ramp-up plan that gets you selling effectively faster, while building confidence in our products and sales methodology."
            what_to_know = [
                "Your preferred learning approach (role-play, shadowing, self-study, coaching)",
                "Product knowledge and sales skills you need to develop",
                "Time you can commit to training and your target timeline",
                "Support you'll need (sales mentors, training resources, practice opportunities)"
            ]
        else:
            icon = "📚"
            title = "Learning Preferences"
            why_important = "Understanding your learning preferences helps us tailor your onboarding experience, ensuring you acquire the knowledge and skills you need in a way that works best for you."
            what_to_know = [
                "Your preferred learning style and format (visual, hands-on, reading, discussion)",
                "Skills and knowledge areas you want to develop",
                "Time you can dedicate to learning and your preferred pace",
                "Support and resources you'll need to succeed"
            ]
        
        what_to_know_formatted = "<br>".join([f"• {item}" for item in what_to_know])
        
        learning_message = f"""
<div style="text-align: center; padding: 2rem;">
<h2>{icon} {title}</h2>
<p style="font-size: 1.2rem; color: #667eea; margin: 1.5rem 0;">
Welcome, {user_name}!
</p>
<p style="font-size: 1rem; color: #666; margin: 1.5rem 0;">
🎯 <strong>Why This Stage Matters:</strong> {why_important}
</p>
<p style="font-size: 1rem; color: #666; margin: 1.5rem 0; text-align: left; max-width: 600px; margin-left: auto; margin-right: auto;">
📋 <strong>What We Need to Know About You:</strong><br>
{what_to_know_formatted}
</p>
<p style="font-size: 1rem; color: #667eea; font-weight: bold; margin-top: 1.5rem;">
💬 Let's create a learning plan that works perfectly for you. Ready to start?
</p>
</div>
"""
        st.markdown(learning_message, unsafe_allow_html=True)
    
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
            if st.session_state.current_stage == "welcome":
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
            
            elif st.session_state.current_stage == "profile_setup":
                if not st.session_state.profile_setup_checklist["profile_started"]:
                    st.session_state.profile_setup_checklist["profile_started"] = True
                
                role_type = st.session_state.role_type or "Other"
                
                if role_type == "IT":
                    profile_status = "\n".join([
                        f"- Department: {st.session_state.it_profile['department'] or 'Not provided'}",
                        f"- Role Level: {st.session_state.it_profile['role_level'] or 'Not provided'}",
                        f"- Tech Stack: {st.session_state.it_profile['tech_stack'] or 'Not provided'}",
                        f"- Experience: {st.session_state.it_profile['experience_years'] or 'Not provided'}",
                        f"- Specialization: {st.session_state.it_profile['specialization'] or 'Not provided'}",
                        f"- Preferred IDE: {st.session_state.it_profile['preferred_ide'] or 'Not provided'}",
                        f"- OS Preference: {st.session_state.it_profile['os_preference'] or 'Not provided'}",
                        f"- GitHub Username: {st.session_state.it_profile['github_username'] or 'Not provided'}"
                    ])
                    
                    system_prompt = f"""You are a helpful IT onboarding guide assisting a new technical team member.

Current Stage: Profile Setup - IT Professional (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Department/Team - Which team they're joining and who they'll work with
2. ✅ Tech stack & tools - Programming languages, frameworks, and development tools
3. ✅ Experience & specialization - Their background and areas of expertise
4. ✅ Development preferences - IDE, OS, GitHub, and environment setup

Current Profile Status:
{profile_status}

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through each area while providing helpful context
- Offer specific examples and suggestions to speed up the conversation
- If they're unsure, PROVIDE typical options and ask them to choose
- Move through topics systematically to ensure all areas are covered
- Keep responses concise but informative (2-3 sentences max)
- Proactively suggest common setups to help them decide quickly
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "Let's start with your team. You'll be joining the [Engineering/DevOps/Data] team. Which area fits your role best?"
- "For tech stack, most {st.session_state.user_data['role']}s here use Python, JavaScript, or Java. Which languages will you be working with?"
- "For your development environment, popular choices are VS Code, IntelliJ, or PyCharm. Which would you prefer?"
- "What's your experience level - junior, mid-level, or senior? And any specializations like frontend, backend, or full-stack?"

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Don't spend too long on any single topic.

CRITICAL: You MUST ensure ALL 4 areas are covered before the profile setup is complete. Check the profile status and guide the conversation to cover any missing areas.
"""

                elif role_type == "Sales":
                    profile_status = "\n".join([
                        f"- Sales Role: {st.session_state.sales_profile['sales_role'] or 'Not provided'}",
                        f"- Seniority: {st.session_state.sales_profile['seniority'] or 'Not provided'}",
                        f"- Territory: {st.session_state.sales_profile['territory'] or 'Not provided'}",
                        f"- Product Lines: {st.session_state.sales_profile['product_lines'] or 'Not provided'}",
                        f"- CRM System: {st.session_state.sales_profile['crm_system'] or 'Not provided'}",
                        f"- Sales Methodology: {st.session_state.sales_profile['sales_methodology'] or 'Not provided'}",
                        f"- Quota: {st.session_state.sales_profile['quota'] or 'Not provided'}",
                        f"- Experience: {st.session_state.sales_profile['experience_years'] or 'Not provided'}"
                    ])
                    
                    system_prompt = f"""You are a helpful sales onboarding guide assisting a new sales team member.

Current Stage: Profile Setup - Sales Professional (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Sales role & territory - Their specific role type and territory assignment
2. ✅ CRM & tools setup - Salesforce/HubSpot and sales engagement tools
3. ✅ Sales methodology - Their approach (SPIN, Challenger, MEDDIC, etc.)
4. ✅ Quota & targets - Performance metrics and support structure

Current Profile Status:
{profile_status}

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through each area while providing helpful context
- Offer specific examples and suggestions to speed up the conversation
- If they're unsure, PROVIDE typical options and ask them to choose
- Move through topics systematically to ensure all areas are covered
- Keep responses concise but energetic (2-3 sentences max)
- Proactively suggest common setups to help them decide quickly
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "Let's start with your role. Are you an AE (Account Executive), SDR/BDR, or Account Manager? And which territory - geographic or vertical?"
- "For CRM, we use Salesforce/HubSpot. Have you used it before? I'll help you get set up."
- "What sales methodology do you prefer - SPIN, Challenger, or MEDDIC? Or would you like me to explain our approach?"
- "Let's discuss your quota structure and the support resources available to help you hit your targets."

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Don't spend too long on any single topic.

CRITICAL: You MUST ensure ALL 4 areas are covered before the profile setup is complete. Check the profile status and guide the conversation to cover any missing areas.
"""

                else:
                    system_prompt = f"""You are a helpful onboarding guide assisting a new team member.

Current Stage: Profile Setup (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Department information - Which department/team they're joining
2. ✅ Key responsibilities - Main tasks and projects they'll work on
3. ✅ Tools & systems - Software and platforms they'll use daily
4. ✅ Training needs - Learning resources and support available

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through each area while providing helpful context
- Offer specific examples and suggestions to speed up the conversation
- If they're unsure, PROVIDE typical options and ask them to choose
- Move through topics systematically to ensure all areas are covered
- Keep responses warm but concise (2-3 sentences max)
- Proactively suggest common setups to help them decide quickly
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "Let's start with your department. As a {st.session_state.user_data['role']}, which team are you joining - [suggest relevant departments]?"
- "What will be your main responsibilities? I can outline typical tasks for your role if that helps."
- "For tools, you'll likely use [suggest common tools for their role]. Which ones are you familiar with?"
- "What training or support would be most helpful for you to get started?"

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Don't spend too long on any single topic.

CRITICAL: You MUST ensure ALL 4 areas are covered before the profile setup is complete. Check the profile status and guide the conversation to cover any missing areas.
"""
            
            elif st.session_state.current_stage == "learning_preferences":
                if not st.session_state.learning_checklist["learning_started"]:
                    st.session_state.learning_checklist["learning_started"] = True
                
                role_type = st.session_state.role_type or "Other"
                
                learning_status = "\n".join([
                    f"- Learning Style: {st.session_state.learning_preferences['learning_style'] or 'Not provided'}",
                    f"- Preferred Format: {st.session_state.learning_preferences['preferred_format'] or 'Not provided'}",
                    f"- Time Commitment: {st.session_state.learning_preferences['time_commitment'] or 'Not provided'}",
                    f"- Specific Goals: {st.session_state.learning_preferences['specific_goals'] or 'Not provided'}",
                    f"- Support Needed: {st.session_state.learning_preferences['support_needed'] or 'Not provided'}",
                    f"- Timeline: {st.session_state.learning_preferences['timeline'] or 'Not provided'}"
                ])
                
                if role_type == "IT":
                    system_prompt = f"""You are a helpful learning advisor for a new technical team member.

Current Stage: Learning Preferences (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Learning style & format - How they learn best (visual, hands-on, reading, videos, etc.)
2. ✅ Technical skills to develop - Languages, frameworks, tools, certifications they want to learn
3. ✅ Time commitment & pace - Hours per week, intensive vs gradual, best time for learning
4. ✅ Support & resources needed - Mentorship, courses, budget, learning platforms

Current Learning Status:
{learning_status}

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through creating a personalized learning plan
- Offer specific examples and suggestions (Udemy, Pluralsight, AWS certifications, etc.)
- If they're unsure, PROVIDE typical learning paths for their role
- Move through topics systematically to ensure all areas are covered
- Keep responses concise and actionable (2-3 sentences max)
- Proactively suggest learning resources and timelines
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "How do you learn best - through hands-on coding, video tutorials, documentation, or a mix? Most developers prefer hands-on practice with some video guidance."
- "What technical skills would you like to develop? For a {st.session_state.user_data['role']}, popular areas are cloud platforms (AWS/Azure), new frameworks, or system design."
- "How much time can you dedicate to learning each week - 2-3 hours, 5-10 hours, or more? Let's create a realistic schedule."
- "Would you benefit from a mentor, online courses, or both? We can set you up with learning resources and pair you with an experienced team member."

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Create an actionable learning plan.

CRITICAL: You MUST ensure ALL 4 areas are covered before learning preferences are complete. Check the status and guide the conversation to cover any missing areas.
"""
                
                elif role_type == "Sales":
                    system_prompt = f"""You are a helpful learning advisor for a new sales team member.

Current Stage: Learning Preferences (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Learning style & format - How they learn best (role-play, shadowing, reading, videos, etc.)
2. ✅ Product & sales training - Product knowledge, sales methodology, industry expertise needed
3. ✅ Time commitment & pace - Hours per week, ramp-up timeline, best time for training
4. ✅ Support & resources needed - Mentorship, sales enablement, training programs, certifications

Current Learning Status:
{learning_status}

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through creating a personalized sales ramp-up plan
- Offer specific examples (sales methodology training, product demos, shadowing top reps)
- If they're unsure, PROVIDE typical ramp-up paths for their sales role
- Move through topics systematically to ensure all areas are covered
- Keep responses energetic and actionable (2-3 sentences max)
- Proactively suggest training resources and timelines
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "How do you learn best - through shadowing experienced reps, role-playing, product demos, or reading materials? Most sales reps benefit from a mix of shadowing and hands-on practice."
- "What do you need to learn first - product knowledge, our sales process, or industry expertise? Let's prioritize your ramp-up."
- "How much time can you dedicate to training each week before you start taking calls? Typical ramp-up is 2-4 weeks of intensive training."
- "Would you like to shadow a top performer, have a mentor, or both? We can pair you with someone who matches your learning style."

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Create an actionable ramp-up plan.

CRITICAL: You MUST ensure ALL 4 areas are covered before learning preferences are complete. Check the status and guide the conversation to cover any missing areas.
"""
                
                else:
                    system_prompt = f"""You are a helpful learning advisor for a new team member.

Current Stage: Learning Preferences (Time-Limited Meeting)

User Information:
- Name: {st.session_state.user_data['name']}
- Role: {st.session_state.user_data['role']}

CRITICAL: Our meeting time is limited. You MUST efficiently cover these 4 key areas:
1. ✅ Learning style & format - How they learn best (visual, hands-on, reading, videos, etc.)
2. ✅ Skills to develop - Role-specific competencies and knowledge areas
3. ✅ Time commitment & pace - Hours per week, learning timeline, best time for training
4. ✅ Support & resources needed - Mentorship, training programs, learning resources

Current Learning Status:
{learning_status}

IMPORTANT INSTRUCTIONS:
- Be FOCUSED and EFFICIENT - we have limited time to cover all topics
- GUIDE them through creating a personalized learning plan
- Offer specific examples relevant to their role
- If they're unsure, PROVIDE typical learning paths for similar roles
- Move through topics systematically to ensure all areas are covered
- Keep responses warm and actionable (2-3 sentences max)
- Proactively suggest learning resources and timelines
- Use their name: {st.session_state.user_data['name']}

Example approach:
- "How do you learn best - through hands-on practice, videos, reading, or a combination? Understanding your style helps us provide the right resources."
- "What skills or knowledge areas would you like to develop for your role as a {st.session_state.user_data['role']}? Let's identify your priorities."
- "How much time can you dedicate to learning each week? Let's create a realistic schedule that works for you."
- "What support would help you most - a mentor, training courses, or learning resources? We can set you up with what you need."

Remember: Be helpful but MOVE EFFICIENTLY through all 4 areas. Create an actionable learning plan.

CRITICAL: You MUST ensure ALL 4 areas are covered before learning preferences are complete. Check the status and guide the conversation to cover any missing areas.
"""

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
            
            import re
            if '<div' in response_content or '<p' in response_content or '<h' in response_content:
                response_content = re.sub(r'<[^>]+>', '', response_content)
                response_content = response_content.strip()
            
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
                    st.session_state.role_type = detect_role_type(user_input)
                elif len(user_input.split()) >= 1 and len(user_input) >= 3:
                    st.session_state.user_data["role"] = user_input
                    st.session_state.checklist["role_provided"] = True
                    st.session_state.role_type = detect_role_type(user_input)
            
            if not st.session_state.checklist["goals_discussed"]:
                goal_keywords = ["goal", "want to", "hoping to", "plan to", "learn", "improve", "achieve", 
                               "objective", "aim", "aspire", "interested in", "looking to"]
                if any(keyword in user_input_lower for keyword in goal_keywords):
                    # Summarize goals to key points using LLM
                    summarized_goals = summarize_goals_with_llm(user_input, llm)
                    st.session_state.user_data["goals"] = summarized_goals
                    st.session_state.checklist["goals_discussed"] = True
            
            # Profile Setup stage data extraction
            if st.session_state.current_stage == "profile_setup":
                role_type = st.session_state.role_type or "Other"
                
                if role_type == "IT":
                    # Extract IT profile information
                    # Field 1: Department/Team - be more flexible with matching
                    if not st.session_state.it_profile["department"]:
                        dept_keywords = ["engineering", "devops", "data", "qa", "security", "infrastructure", 
                                       "team", "department", "backend", "frontend", "platform", "mobile", 
                                       "cloud", "sre", "ops", "development", "product", "research"]
                        # Also check if it's a short answer (likely a team name)
                        if any(word in user_input_lower for word in dept_keywords) or (len(user_input.split()) <= 5 and len(user_input) > 2):
                            st.session_state.it_profile["department"] = user_input
                            st.session_state.profile_setup_checklist["field_1"] = True
                    
                    # Field 2: Tech stack & tools
                    if not st.session_state.it_profile["tech_stack"]:
                        tech_keywords = ["python", "java", "javascript", "react", "node", "go", "rust", "c++", "ruby", 
                                       "php", "typescript", "framework", "language", "stack", "tool", "angular", "vue",
                                       "django", "flask", "spring", "express", ".net", "docker", "kubernetes", "aws", "azure"]
                        if any(word in user_input_lower for word in tech_keywords) or (len(user_input.split()) <= 10 and not st.session_state.it_profile["department"]):
                            st.session_state.it_profile["tech_stack"] = user_input
                            st.session_state.profile_setup_checklist["field_2"] = True
                    
                    # Field 3: Experience & specialization
                    if not st.session_state.it_profile["experience_years"]:
                        exp_keywords = ["year", "experience", "junior", "senior", "mid-level", "lead", "beginner", "expert", "1", "2", "3", "4", "5"]
                        if any(word in user_input_lower for word in exp_keywords):
                            st.session_state.it_profile["experience_years"] = user_input
                            if not st.session_state.it_profile["specialization"]:
                                st.session_state.profile_setup_checklist["field_3"] = True
                    
                    if not st.session_state.it_profile["specialization"]:
                        spec_keywords = ["frontend", "backend", "full-stack", "fullstack", "mobile", "cloud", "devops", 
                                       "data", "ml", "ai", "security", "architect", "specialist", "engineer"]
                        if any(word in user_input_lower for word in spec_keywords) or (st.session_state.it_profile["experience_years"] and len(user_input.split()) <= 8):
                            st.session_state.it_profile["specialization"] = user_input
                            st.session_state.profile_setup_checklist["field_3"] = True
                    
                    # Field 4: Development preferences (IDE, OS, GitHub)
                    if not st.session_state.it_profile["preferred_ide"]:
                        ide_keywords = ["vscode", "vs code", "visual studio", "intellij", "pycharm", "webstorm", "sublime", 
                                      "vim", "emacs", "atom", "ide", "editor", "code", "studio"]
                        if any(word in user_input_lower for word in ide_keywords):
                            st.session_state.it_profile["preferred_ide"] = user_input
                            st.session_state.profile_setup_checklist["field_4"] = True
                    
                    if not st.session_state.it_profile["os_preference"]:
                        os_keywords = ["windows", "macos", "mac", "linux", "ubuntu", "debian", "fedora", "os", "operating"]
                        if any(word in user_input_lower for word in os_keywords):
                            st.session_state.it_profile["os_preference"] = user_input
                            if not st.session_state.it_profile["preferred_ide"]:
                                st.session_state.profile_setup_checklist["field_4"] = True
                    
                    if not st.session_state.it_profile["github_username"]:
                        github_keywords = ["github", "gitlab", "bitbucket", "username", "@", "git"]
                        if any(word in user_input_lower for word in github_keywords):
                            st.session_state.it_profile["github_username"] = user_input
                
                elif role_type == "Sales":
                    # Extract Sales profile information
                    if not st.session_state.sales_profile["sales_role"] and any(word in user_input_lower for word in ["ae", "account executive", "sdr", "bdr", "account manager", "sales engineer", "inside", "field"]):
                        st.session_state.sales_profile["sales_role"] = user_input
                        st.session_state.profile_setup_checklist["field_1"] = True
                    
                    if not st.session_state.sales_profile["territory"] and any(word in user_input_lower for word in ["territory", "region", "north", "south", "east", "west", "emea", "apac", "americas", "enterprise", "smb", "mid-market"]):
                        st.session_state.sales_profile["territory"] = user_input
                        if not st.session_state.sales_profile["sales_role"]:
                            st.session_state.profile_setup_checklist["field_1"] = True
                    
                    if not st.session_state.sales_profile["crm_system"] and any(word in user_input_lower for word in ["salesforce", "hubspot", "pipedrive", "crm", "zoho", "dynamics"]):
                        st.session_state.sales_profile["crm_system"] = user_input
                        st.session_state.profile_setup_checklist["field_2"] = True
                    
                    if not st.session_state.sales_profile["sales_methodology"] and any(word in user_input_lower for word in ["spin", "challenger", "meddic", "sandler", "solution selling", "methodology"]):
                        st.session_state.sales_profile["sales_methodology"] = user_input
                        st.session_state.profile_setup_checklist["field_3"] = True
                    
                    if not st.session_state.sales_profile["quota"] and any(word in user_input_lower for word in ["quota", "target", "$", "k", "million", "revenue"]):
                        st.session_state.sales_profile["quota"] = user_input
                        st.session_state.profile_setup_checklist["field_4"] = True
                    
                    if not st.session_state.sales_profile["experience_years"] and any(word in user_input_lower for word in ["year", "experience", "junior", "senior", "mid-level"]):
                        st.session_state.sales_profile["experience_years"] = user_input
            
            # Learning Preferences stage data extraction
            if st.session_state.current_stage == "learning_preferences":
                # Field 1: Learning style & format
                if not st.session_state.learning_preferences["learning_style"]:
                    style_keywords = ["hands-on", "visual", "reading", "video", "tutorial", "documentation", 
                                     "mentoring", "shadowing", "practice", "learn by doing", "watching",
                                     "interactive", "self-paced", "instructor", "classroom", "online"]
                    if any(word in user_input_lower for word in style_keywords):
                        st.session_state.learning_preferences["learning_style"] = user_input
                        st.session_state.learning_checklist["field_1"] = True
                
                # Field 2: Skills to develop / Specific goals
                if not st.session_state.learning_preferences["specific_goals"]:
                    skill_keywords = ["python", "java", "javascript", "react", "aws", "cloud", "docker", 
                                     "kubernetes", "sql", "data", "machine learning", "ai", "api",
                                     "framework", "language", "certification", "skill", "learn", "develop",
                                     "product", "sales", "methodology", "communication", "leadership"]
                    if any(word in user_input_lower for word in skill_keywords):
                        st.session_state.learning_preferences["specific_goals"] = user_input
                        st.session_state.learning_checklist["field_2"] = True
                
                # Field 3: Time commitment & pace
                if not st.session_state.learning_preferences["time_commitment"]:
                    time_keywords = ["hour", "week", "day", "month", "time", "schedule", "pace", 
                                    "intensive", "gradual", "morning", "evening", "weekend",
                                    "2-3", "5-10", "full-time", "part-time", "dedicate"]
                    if any(word in user_input_lower for word in time_keywords):
                        st.session_state.learning_preferences["time_commitment"] = user_input
                        st.session_state.learning_checklist["field_3"] = True
                
                # Field 4: Support & resources needed
                if not st.session_state.learning_preferences["support_needed"]:
                    support_keywords = ["mentor", "course", "udemy", "pluralsight", "coursera", "training",
                                       "resource", "budget", "platform", "help", "support", "guide",
                                       "pair", "buddy", "coach", "workshop", "book", "documentation"]
                    if any(word in user_input_lower for word in support_keywords):
                        st.session_state.learning_preferences["support_needed"] = user_input
                        st.session_state.learning_checklist["field_4"] = True
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat()
            })
            
            memory.save_message(st.session_state.session_id, "assistant", response_content)
            
            memory.update_context(st.session_state.session_id, {
                "checklist": st.session_state.checklist,
                "user_data": st.session_state.user_data,
                "profile_setup_checklist": st.session_state.profile_setup_checklist,
                "learning_checklist": st.session_state.learning_checklist,
                "learning_preferences": st.session_state.learning_preferences,
                "role_type": st.session_state.role_type,
                "it_profile": st.session_state.it_profile,
                "sales_profile": st.session_state.sales_profile
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

if completed_required >= 3 and st.session_state.current_stage == "welcome":
    st.success("🎉 Congratulations! You've completed all required tasks for this stage!")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        pdf_buffer = generate_pdf(
            st.session_state.user_data,
            role_type=st.session_state.role_type,
            it_profile=st.session_state.it_profile,
            sales_profile=st.session_state.sales_profile,
            learning_preferences=st.session_state.learning_preferences,
            current_stage=st.session_state.current_stage
        )
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
            st.session_state.messages = []
            
            briefing_message = generate_stage_briefing(
                st.session_state.user_data,
                st.session_state.role_type,
                llm
            )
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": briefing_message,
                "timestamp": datetime.now().isoformat()
            })
            
            memory.save_message(st.session_state.session_id, "assistant", briefing_message)
            
            st.success("Moving to Profile Setup stage!")
            st.rerun()

elif st.session_state.current_stage == "profile_setup":
    profile_completed = sum(1 for key in st.session_state.profile_setup_checklist.values() if key)
    
    if profile_completed >= 5:
        st.success("🎉 Great! You've completed all 4 profile setup areas!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            pdf_buffer = generate_pdf(
                st.session_state.user_data,
                role_type=st.session_state.role_type,
                it_profile=st.session_state.it_profile,
                sales_profile=st.session_state.sales_profile,
                learning_preferences=st.session_state.learning_preferences,
                current_stage=st.session_state.current_stage
            )
            st.download_button(
                label="📄 Download Profile Summary",
                data=pdf_buffer,
                file_name=f"profile_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.button("➡️ Continue to Learning Preferences", use_container_width=True):
                st.session_state.current_stage = "learning_preferences"
                st.session_state.messages = []
                st.success("Moving to Learning Preferences stage!")
                st.rerun()

elif st.session_state.current_stage == "learning_preferences":
    learning_completed = sum(1 for key in st.session_state.learning_checklist.values() if key)
    
    if learning_completed >= 4:
        st.success("🎉 Great! You've completed all 4 learning preference areas!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            pdf_buffer = generate_pdf(
                st.session_state.user_data,
                role_type=st.session_state.role_type,
                it_profile=st.session_state.it_profile,
                sales_profile=st.session_state.sales_profile,
                learning_preferences=st.session_state.learning_preferences,
                current_stage=st.session_state.current_stage
            )
            st.download_button(
                label="📄 Download Learning Plan Summary",
                data=pdf_buffer,
                file_name=f"learning_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.button("➡️ Continue to First Steps", use_container_width=True):
                st.session_state.current_stage = "first_steps"
                st.session_state.messages = []
                st.success("Moving to First Steps stage!")
                st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💬 Messages", len(st.session_state.messages))
with col2:
    redis_status = "✅ Active" if memory.redis_available else "⚠️ Fallback"
    st.metric("Memory", redis_status)
with col3:
    if st.session_state.current_stage == "welcome":
        st.metric("✅ Tasks", f"{completed_required}/3")
    elif st.session_state.current_stage == "profile_setup":
        profile_completed = sum(1 for key in st.session_state.profile_setup_checklist.values() if key)
        st.metric("✅ Tasks", f"{profile_completed}/5")
    elif st.session_state.current_stage == "learning_preferences":
        learning_completed = sum(1 for key in st.session_state.learning_checklist.values() if key)
        st.metric("✅ Tasks", f"{learning_completed}/5")
    else:
        st.metric("✅ Stage", st.session_state.current_stage.replace('_', ' ').title())
