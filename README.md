# 🤖 AI Onboarding Assistant

An intelligent onboarding assistant, powered by Google Gemini AI and featuring dual-layer memory systems. This agent helps new users get started with your platform through conversational guidance, context-aware responses, and personalised onboarding experiences.

## 📋 Table of Contents

- [Agent Purpose](#agent-purpose)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Technical Implementation](#technical-implementation)
- [Documentation](#documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## 🎯 Quick Overview

This project is a **production-ready AI onboarding assistant** featuring:

- 🤖 **Google Gemini AI** - Advanced LLM for natural conversations
- 🔐 **Google OAuth** - Secure user authentication
- 🧠 **Dual-Layer Memory** - Redis (short-term) + SQL (long-term)
- 📚 **RAG System** - ChromaDB vector store with 15 internal rules documents
- 🔄 **LangGraph Agent** - 5-node agentic workflow for intelligent responses
- 💬 **Advanced Chat with RAG** - Document retrieval with source citations
- 📊 **Stage-Based Flow** - 5 onboarding stages with progress tracking
- 👨‍💼 **Admin Dashboard** - Manage users and view onboarding statistics

---

## 🎯 Agent Purpose

### What is this agent?

The AI Onboarding Assistant is a conversational AI agent designed to guide new users through the onboarding process of a platform or product. It combines advanced retrieval-augmented generation (RAG) with stateful conversation management to provide personalized, context-aware assistance.

### Why is this agent useful?

**For Users:**
- **Instant Help**: Get answers to onboarding questions 24/7 without waiting for support
- **Personalised Guidance**: Receives tailored recommendations based on progress and preferences
- **Self-Paced Learning**: Move through onboarding at your own speed
- **Contextual Assistance**: Agent remembers your conversation and preferences

**For Organisations:**
- **Reduced Support Load**: Automates common onboarding questions
- **Improved User Retention**: Better onboarding leads to higher engagement
- **Scalable**: Handles unlimited concurrent users
- **Data-Driven Insights**: Track common questions and pain points

### Target Users

1. **New Platform Users**: Anyone signing up for a new service or product
2. **Product Teams**: Organizations wanting to improve their onboarding experience
3. **Customer Success Teams**: Support teams looking to automate repetitive onboarding tasks
4. **SaaS Companies**: Businesses with complex products requiring guided onboarding

---

## ✨ Features

### Core Functionality

#### 1. **Conversational AI Interface**
- Beautiful, intuitive Streamlit-based chat interface
- Real-time conversation with Google Gemini AI
- Stage-based onboarding flow (5 stages)
- Progress tracking and visualisation
- Session management

#### 2. **Dual-Layer Memory System**
- **Short-Term Memory**: Redis-based session storage for conversation context
  - Message history with TTL expiration
  - Session context tracking
  - Recent topics extraction
  - Fallback to in-memory storage when Redis is unavailable
  
- **Long-Term Memory**: SQL-based persistent storage
  - User preferences and important facts
  - Importance scoring (1-5 scale)
  - Access count tracking
  - Onboarding progress persistence

#### 3. **Onboarding Flow Management**
- **5 Structured Stages**:
  - Welcome - Initial greeting and introduction
  - Profile Setup - User profile configuration
  - Learning Preferences - Understanding user needs
  - First Steps - Guided first actions
  - Completed - Ongoing support

- **Progress Tracking**: Monitors completed steps and current stage
- **Adaptive Guidance**: Adjusts responses based on the user's stage

#### 4. **Context-Aware Responses**
- Stage-specific prompts and guidance
- Conversation history integration
- User preference tracking
- Personalised recommendations

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Streamlit Chat Interface                    │
│         Beautiful UI with Progress Tracking                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Google Gemini AI                           │
│              (gemini-2.0-flash-exp model)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌────────────┐ ┌──────────────┐
│  Short-Term    │ │ Long-Term  │ │  SQLite DB   │
│  Memory        │ │ Memory     │ │              │
│  (Redis/       │ │ (SQL)      │ │ - Users      │
│   In-Memory)   │ │            │ │ - Profiles   │
│                │ │            │ │ - Messages   │
└────────────────┘ └────────────┘ └──────────────┘
```

### Technology Stack

**AI & LLM:**
- **Google Gemini 2.0 Flash** - Advanced LLM for conversational responses
- **LangChain** - Framework for LLM integration and chains
- **LangGraph** - Agentic workflow orchestration

**Vector Store & Embeddings:**
- **ChromaDB** - Vector database for semantic search
- **Sentence Transformers** - HuggingFace embeddings (all-MiniLM-L6-v2)

**Backend & API:**
- **FastAPI** - Modern REST API framework
- **Uvicorn** - ASGI server
- **SQLAlchemy** - ORM for persistent storage
- **Redis** - In-memory cache for session data (with in-memory fallback)

**Authentication:**
- **google-auth-oauthlib** - Google OAuth 2.0 authentication
- **google-auth** - Google authentication library

**Frontend:**
- **Streamlit** - Interactive web interface (2 versions)

**Configuration & Validation:**
- **Pydantic** - Data validation and settings management
- **python-dotenv** - Environment variable management

**Core:**
- **Python 3.11+** - Core programming language

---

## 🚀 Installation

### Prerequisites

- Python 3.11+
- Redis (optional, falls back to in-memory storage)
- Google API Key (for Gemini)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd Onboarding_agent
git checkout feature/complete-onboarding-agent
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key from https://aistudio.google.com/app/apikey:

```env
GOOGLE_API_KEY=your_google_api_key_here
SECRET_KEY=your-secret-key-change-in-production
```

### Step 4: (Optional) Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Download from https://redis.io/download

---

## 💻 Usage

### Quick Start

#### Start the Chat Application

```bash
streamlit run chat_app.py
```

Open your browser to `http://localhost:8501`

**Features:**
- 🔐 Google OAuth authentication
- 💬 Full RAG (Retrieval-Augmented Generation) with internal rules documents
- 🔄 LangGraph agentic workflow
- 📚 Document retrieval from 15 internal rules documents
- 📖 Source citations for transparency
- 👨‍💼 Admin dashboard for managing users
- 📊 Progress tracking through 5 onboarding stages
- 🧠 Dual-layer memory system (short-term + long-term)

The interface will show:
- 💬 Interactive chat with the AI assistant
- 🎯 Progress tracking through 5 onboarding stages
- 📊 Session statistics and metrics
- 📚 Source citations (RAG version)
- 🎨 Beautiful purple gradient UI

### Try These Questions

Once the app is running, try asking questions about internal company policies:

**IT Administrator Questions:**
- "What is IT Administrator's Responsibilities?"
- "What are IT Administrator KPIs?"
- "Explain IT onboarding credentials"

**Work Policy Questions:**
- "What are remote and hybrid work guidelines?"
- "Explain work environment requirements"
- "What is the employee code of conduct?"

**Security Questions:**
- "What is endpoint security baseline?"
- "How do I report a security incident?"
- "What are data classification standards?"

**HR & Benefits Questions:**
- "What are leave and time off policies?"
- "Explain travel and expense reimbursement"
- "What workplace safety rules apply?"

The assistant will:
- Retrieve relevant documentation from internal rules
- Provide accurate, cited responses from company documents
- Remember your conversation history
- Track your progress through the onboarding stages
- Save important preferences to long-term memory
- Show sources for transparency with document names and relevance scores

---

## 🔧 Technical Implementation

### RAG System (Internal Rules Documents)

The RAG system automatically loads 15 internal rules documents from the `../Internal rules/` folder:

```python
# Documents are loaded during initialisation
from the backend. rag. initialiser import load_internal_rules_documents

docs = load_internal_rules_documents()
# Returns 15 Document objects with metadata:
# - origin: "internal_rules"
# - source: filename
# - category: "internal_rules"
```

**Key Features:**
- Automatic document discovery from the Internal rules folder
- Semantic search with ChromaDB vector store
- Keyword matching fallback for better retrieval
- Source citations with relevance scores
- Filters to return only internal rules documents (excludes sample docs)

### Memory Integration

#### Short-Term Memory (Session Context)
```python
# Save conversation
short_term_memory.save_message(session_id, "user", message)
short_term_memory.save_context(session_id, {"intent": "help"})

# Retrieve recent context
messages = short_term_memory.get_messages(session_id, limit=5)
context = short_term_memory.get_context(session_id)
```

#### Long-Term Memory (User Preferences)
```python
# Save important information
long_term_memory.save_memory(
    user_id=1,
    memory_type="onboarding",
    key="welcome.role",
    value="IT Administrator",
    importance=5
)

# Retrieve important memories
memories = long_term_memory.get_important_memories(user_id, min_importance=3)
```

### Error Handling

- **Redis Connection Failures**: Automatic fallback to in-memory storage
- **LLM API Errors**: Displays user-friendly error messages
- **RAG Retrieval Failures**: Falls back to contact information
- **Database Errors**: Logged with helpful context
- **Invalid Input**: Validation with clear feedback

### Configuration

Settings are managed through `.env` file:

```env
# Required - Get from https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Google OAuth (Required for authentication)
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret

# Database (SQLite by default)
DATABASE_URL=sqlite:///./onboarding.db

# Redis (optional - falls back to in-memory if unavailable)
REDIS_URL=redis://localhost:6379/0

# Admin emails (comma-separated)
ADMIN_EMAILS=admin@company.com,manager@company.com
```

**Configuration Details:**

- **GOOGLE_API_KEY**: Required for Gemini AI. Get yours at https://aistudio.google.com/app/apikey
- **GOOGLE_OAUTH_CLIENT_ID/SECRET**: Required for Google OAuth. Set up at https://console.cloud.google.com/
- **DATABASE_URL**: SQLite database path (auto-created on first run)
- **REDIS_URL**: Redis connection URL (optional, uses in-memory fallback if unavailable)
- **ADMIN_EMAILS**: Comma-separated list of admin user emails

Configuration is loaded via `backend/config.py` using Pydantic Settings with automatic validation.

---

## 📚 Documentation

### Database Schema

**users**
- id, email, full_name, hashed_password, is_active, role, created_at

**onboarding_profiles**
- id, user_id, current_stage, preferences, progress, completed_steps

**conversations**
- id, user_id, session_id, created_at, updated_at

**messages**
- id, conversation_id, role, content, message_metadata, timestamp

**long_term_memories**
- id, user_id, memory_type, key, value, importance, access_count

**documents**
- id, title, content, source, doc_metadata, created_at

### Architecture Decisions

#### Why Dual-Layer Memory?
- **Performance**: Redis provides fast session access
- **Persistence**: SQL ensures important data isn't lost
- **Flexibility**: Different storage for different use cases
- **Scalability**: Can scale each layer independently

---

## ✅ Task Requirements Coverage

### 1. Agent Purpose ✅
- ✅ Clear purpose defined: Onboarding assistance for new users
- ✅ Usefulness explained: Reduces support load, improves retention
- ✅ Target users identified: New users, product teams, support teams

### 2. Core Functionality ✅
- ✅ Main features implemented: Conversational AI, memory systems, stage management
- ✅ Primary tasks effective: Answers questions, guides onboarding
- ✅ User interactions included: Chat interface, progress tracking

### 3. User Interface ✅
- ✅ User-friendly interface: Streamlit chat app with clean design
- ✅ Intuitive and easy to use: Clear conversation flow, visual progress
- ✅ All functionalities accessible: Chat, sources, progress, settings

### 4. Technical Implementation ✅
- ✅ Appropriate tools: Google Gemini, Streamlit, SQLAlchemy, Redis
- ✅ Error handling: Redis fallback, API error handling, validation
- ✅ Real-world usage: Session management, persistence, scalability

### 5. Documentation ✅
- ✅ Clear usage documentation: Installation, usage, examples
- ✅ Common use cases included
- ✅ Technical decisions: Architecture rationale explained

### Implementation Status

#### ✅ Completed Features
- **Conversational AI Interface**: Beautiful Streamlit chat with purple gradient UI
- **Memory Systems**: Dual-layer (Redis + SQL) with fallback support
- **Onboarding Flow**: 5-stage progression with tracking
- **Session Management**: Unique session IDs and context preservation
- **Error Handling**: Graceful degradation and user-friendly messages
- **Progress Visualization**: Real-time metrics and stage indicators

---

## 🧪 Testing

### Manual Testing

**Streamlit Chat Interface:**

1. Start the chat application:
```bash
streamlit run chat_app.py
```

2. **Test Google OAuth Login:**
   - Click "Sign in with Google"
   - Complete Google authentication
   - Verify you're logged in

3. **Test Onboarding Flow:**
   - Complete the Welcome stage (name, role, department, etc.)
   - Progress through Department Info, Key Responsibilities, Tools & Systems, Training Needs
   - View progress in the sidebar

4. **Test RAG Document Retrieval:**
   - Ask: "What is IT Administrator's Responsibilities?"
   - Ask: "Explain work environment"
   - Ask: "What are remote and hybrid work guidelines?"
   - Verify sources are shown with document names and relevance scores

5. **Test Admin Dashboard (if admin user):**
   - View system overview and statistics
   - Check newcomers and onboarding progress
   - Upload documentation
   - View system configuration

6. **Test Memory Systems:**
   - Ask follow-up questions to verify the conversation history is remembered
   - Complete a stage and revisit it to see saved progress
   - Check that user preferences are preserved across sessions

7. **Test Session Management:**
   - Use the "🔄 New Session" button to start fresh
   - Verify old conversation history is cleared
   - Confirm onboarding progress is maintained

---

## 📊 Project Structure

```
Onboarding_agent/
├── backend/
│   ├── agent/               # LangGraph agentic workflow
│   │   ├── __init__.py
│   │   ├── state.py         # Agent state definition
│   │   ├── nodes.py         # Agent nodes (analyse, load memory, retrieve, respond, save)
│   │   └── graph.py         # LangGraph workflow orchestration
│   ├── auth/                # Google OAuth authentication
│   │   ├── __init__.py
│   │   └── oauth.py         # Google OAuth handler
│   ├── admin/               # Admin dashboard
│   │   ├── __init__.py
│   │   ├── dashboard.py     # Admin UI components
│   │   ├── queries.py       # Admin database queries
│   │   └── utils.py         # Admin utilities (document upload, user management)
│   ├── rag/                 # RAG system components
│   │   ├── __init__.py
│   │   ├── vector_store.py       # ChromaDB integration
│   │   ├── document_processor.py # Text chunking & processing
│   │   ├── query_planner.py      # Query analysis & planning
│   │   ├── reranker.py           # Result reranking
│   │   ├── agentic_rag.py        # Main RAG engine
│   │   └── initializer.py        # RAG initialisation (loads internal rules docs)
│   ├── memory/              # Dual-layer memory system
│   │   ├── __init__.py
│   │   ├── short_term.py    # Redis/in-memory session storage
│   │   └── long_term.py     # SQL persistent storage
│   ├── database/            # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py    # SQLAlchemy connection & session
│   │   └── models.py        # Database models (6 tables)
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic schemas (domain models)
│   ├── __init__.py
│   └── config.py            # Configuration management (Pydantic Settings)
├── Internal rules/          # Uploaded documents via admin panel (user-uploaded)
├── uploaded_profile_pics/   # User profile pictures
├── chroma_db/               # ChromaDB vector store data
├── chat_app.py              # Main Streamlit chat with RAG + Agent + Admin Dashboard
├── run_chat.sh              # Convenience script to start chat UI
├── requirements.txt         # Python dependencies
├── onboarding.db            # SQLite database (auto-created)
├── README.md                # This file - comprehensive documentation
├── QUICKSTART.md            # Quick start guide
├── GMAIL_OAUTH_SETUP.md     # Google OAuth setup guide
├── ADMIN_PANEL_GUIDE.md     # Admin dashboard documentation
├── .env.example             # Environment template
├── .env                     # Your configuration (gitignored)
└── .gitignore               # Git ignore patterns
```

**Internal Rules Documents (15 files in `../Internal rules/` - project root):**
- IT Administrator Responsibilities.md
- IT Administrator – Yearly KPIs.md
- IT Onboarding Credentials Guide.md
- Remote and Hybrid Work Guidelines.md
- Endpoint Security Baseline.md
- Access Request and Provisioning Standard.md
- Acceptable Use of Company Systems.md
- Data Classification and Handling Standard.md
- Employee Code of Conduct.md
- Leave, Time Off, and Absence Reporting.md
- Travel and Expense Reimbursement Policy.md
- Security Incident Reporting and Response (Employee Guide).md
- Workplace Safety and Facilities Rules.md
- Google Workspace Setup Guide.md
- Organisation Structure.md

---

## 🤝 Contributing

This is a student project for the Turing College AI Engineering course. 

---

## 📄 License

Educational project - Turing College

---

## 🙏 Acknowledgments

- **LangChain**: LLM integration framework
- **Google Gemini**: LLM capabilities
- **Streamlit**: Rapid UI development
- **SQLAlchemy**: Database ORM

---
