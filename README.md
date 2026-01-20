# 🤖 AI Onboarding Assistant

An intelligent onboarding assistant powered by Google Gemini AI with dual-layer memory systems. This agent helps new users get started with your platform through conversational guidance, context-aware responses, and personalized onboarding experiences.

## 📋 Table of Contents

- [Agent Purpose](#agent-purpose)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

---

## 🎯 Agent Purpose

### What is this agent?

The AI Onboarding Assistant is a conversational AI agent designed to guide new users through the onboarding process of a platform or product. It combines advanced retrieval-augmented generation (RAG) with stateful conversation management to provide personalized, context-aware assistance.

### Why is this agent useful?

**For Users:**
- **Instant Help**: Get answers to onboarding questions 24/7 without waiting for support
- **Personalized Guidance**: Receives tailored recommendations based on progress and preferences
- **Self-Paced Learning**: Move through onboarding at your own speed
- **Contextual Assistance**: Agent remembers your conversation and preferences

**For Organizations:**
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
- Progress tracking and visualization
- Session management

#### 2. **Dual-Layer Memory System**
- **Short-Term Memory**: Redis-based session storage for conversation context
  - Message history with TTL expiration
  - Session context tracking
  - Recent topics extraction
  - Fallback to in-memory storage when Redis unavailable
  
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
- **Adaptive Guidance**: Adjusts responses based on user's stage

#### 4. **Context-Aware Responses**
- Stage-specific prompts and guidance
- Conversation history integration
- User preference tracking
- Personalized recommendations

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

- **Google Gemini Pro**: LLM for conversational responses
- **Streamlit**: Interactive web interface
- **SQLAlchemy**: ORM for persistent storage
- **Redis**: In-memory cache for session data (optional, with fallback)
- **Pydantic**: Data validation and settings management
- **Python 3.11+**: Core programming language

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

#### Run the Chat Interface

```bash
streamlit run simple_chat_app.py
```

Open your browser to `http://localhost:8501`

The interface will show:
- 💬 Interactive chat with the AI assistant
- 🎯 Progress tracking through 5 onboarding stages
- 📊 Session statistics and metrics
- 🎨 Beautiful purple gradient UI

### Try These Questions

Once the app is running, try asking:

- "How do I create a new project?"
- "What features are available?"
- "Tell me about getting started"
- "I need help with my account"
- "What are the keyboard shortcuts?"

The assistant will:
- Provide helpful, context-aware responses
- Remember your conversation history
- Track your progress through onboarding stages
- Save important preferences to long-term memory

---

## 🔧 Technical Implementation

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
    memory_type="preference",
    key="learning_style",
    value="visual",
    importance=5
)

# Retrieve important memories
memories = long_term_memory.get_important_memories(user_id, min_importance=3)
```

### Error Handling

- **Redis Connection Failures**: Automatic fallback to in-memory storage
- **LLM API Errors**: Displays user-friendly error messages
- **Database Errors**: Logged with helpful context
- **Invalid Input**: Validation with clear feedback

### Configuration

Settings are managed through `.env` file:

```env
GOOGLE_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./onboarding.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

Configuration is loaded via `backend/config.py` using Pydantic Settings

---

## 📚 Documentation

### API Reference

#### Agent Endpoints

**POST /chat**
```json
{
  "message": "How do I create a project?",
  "session_id": "optional-session-id",
  "user_id": 1
}
```

Response:
```json
{
  "response": "To create a project...",
  "session_id": "session-123",
  "sources": [...],
  "current_stage": "first_steps"
}
```

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

1. Start chat interface: `streamlit run simple_chat_app.py`
2. Try these queries:
   - "How do I create a new project?"
   - "What features are available?"
   - "Tell me about getting started"
   - "I need help with my account"
3. Test stage progression by changing stages in the sidebar
4. Verify memory by asking follow-up questions
5. Check session management with "New Session" button

---

## 📊 Project Structure

```
Onboarding_agent/
├── backend/
│   ├── agent/           # Agent implementation (advanced features)
│   ├── rag/             # RAG system (advanced features)
│   ├── memory/          # Memory systems (active)
│   ├── database/        # SQLAlchemy models (active)
│   ├── models/          # Pydantic schemas (active)
│   ├── auth/            # Authentication (foundation)
│   └── config.py        # Configuration management
├── simple_chat_app.py   # Main chat interface ⭐
├── requirements.txt     # Dependencies
├── README.md            # This file
├── .env.example         # Environment template
└── .env                 # Your configuration (gitignored)
```

---

## 🤝 Contributing

This is a student project for Turing College AI Engineering course. 

---

## 📄 License

Educational project - Turing College

---

## 🙏 Acknowledgments

- **LangChain & LangGraph**: Conversation orchestration
- **Google Gemini**: LLM capabilities
- **ChromaDB**: Vector storage
- **Streamlit**: Rapid UI development

---

**Built with ❤️ for better user onboarding experiences**
