# 🤖 AI Onboarding Assistant

An intelligent onboarding assistant powered by Google Gemini AI with dual-layer memory systems. This agent helps new users get started with your platform through conversational guidance, context-aware responses, and personalized onboarding experiences.

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

- 🤖 **Google Gemini 2.0 Flash** - Advanced LLM for natural conversations
- 🔐 **JWT Authentication** - Secure user registration and login
- 🧠 **Dual-Layer Memory** - Redis (short-term) + SQL (long-term)
- 📚 **RAG System** - ChromaDB vector store with 10 onboarding documents
- 🔄 **LangGraph Agent** - 5-node agentic workflow for intelligent responses
- 🎨 **Two UIs** - Simple chat + Advanced chat with RAG
- 🚀 **REST API** - FastAPI with protected endpoints
- 📊 **Stage-Based Flow** - 5 onboarding stages with progress tracking

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

**Authentication & Security:**
- **python-jose** - JWT token handling
- **passlib** - Password hashing with bcrypt
- **python-multipart** - Form data parsing

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

#### Option 1: Simple Chat (No RAG)

```bash
streamlit run simple_chat_app.py
```

**Features:**
- Fast and lightweight
- General conversational AI
- Memory systems
- Good for basic onboarding

#### Option 2: Advanced Chat with RAG + Agent

```bash
streamlit run chat_app.py
```

**Features:**
- Full RAG (Retrieval-Augmented Generation)
- LangGraph agentic workflow
- Document retrieval from knowledge base
- Source citations
- More accurate, grounded responses

Open your browser to `http://localhost:8501`

#### Option 3: REST API Server with Authentication 🔐

```bash
# Start the API server
uvicorn api:app --reload --port 8000

# Or use the convenience script
chmod +x run_api.sh
./run_api.sh
```

**Features:**
- RESTful API for integration with other applications
- JWT-based authentication for secure access
- Protected chat endpoint requiring authentication
- User registration and login
- Automatic session management
- CORS enabled for web applications
- Interactive API documentation at `http://localhost:8000/docs`

**Authentication Flow:**

1. **Register a new user:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

2. **Login to get access token:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. **Use the token to access protected endpoints:**
```bash
# Send a chat message (requires authentication)
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "message": "How do I create a project?",
    "session_id": "my-session-123"
  }'
```

**Response:**
```json
{
  "response": "To create a project...",
  "session_id": "my-session-123",
  "sources": [
    {
      "content": "...",
      "metadata": {"source": "projects_guide.md"}
    }
  ],
  "current_stage": "welcome"
}
```

4. **Get current user information:**
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

The interface will show:
- 💬 Interactive chat with the AI assistant
- 🎯 Progress tracking through 5 onboarding stages
- 📊 Session statistics and metrics
- 📚 Source citations (RAG version)
- 🎨 Beautiful purple gradient UI

### Try These Questions

Once the app is running, try asking:

**General Questions:**
- "How do I create a new project?"
- "What features are available?"
- "Tell me about getting started"

**Specific Questions (RAG excels here):**
- "What integrations are available?"
- "How do I set up two-factor authentication?"
- "What are the keyboard shortcuts?"
- "What's included in the Pro plan?"
- "How do I use the mobile app?"

The assistant will:
- Retrieve relevant documentation from the knowledge base
- Provide accurate, cited responses
- Remember your conversation history
- Track your progress through onboarding stages
- Save important preferences to long-term memory
- Show sources for transparency (RAG version)

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
# Required - Get from https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Database (SQLite by default)
DATABASE_URL=sqlite:///./onboarding.db

# Redis (optional - falls back to in-memory if unavailable)
REDIS_URL=redis://localhost:6379/0

# Authentication (Required for API)
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Configuration Details:**

- **GOOGLE_API_KEY**: Required for Gemini AI. Get yours at https://aistudio.google.com/app/apikey
- **DATABASE_URL**: SQLite database path (auto-created on first run)
- **REDIS_URL**: Redis connection URL (optional, uses in-memory fallback if unavailable)
- **SECRET_KEY**: JWT signing key (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- **ALGORITHM**: JWT algorithm (HS256 recommended)
- **ACCESS_TOKEN_EXPIRE_MINUTES**: Token validity duration (default: 30 minutes)

Configuration is loaded via `backend/config.py` using Pydantic Settings with automatic validation.

---

## 📚 Documentation

### API Reference

The REST API is implemented using FastAPI and available at `http://localhost:8000` when running `uvicorn api:app --reload --port 8000`.

#### Endpoints

**Public Endpoints:**

**GET /** - Health check
```json
{
  "status": "healthy",
  "service": "AI Onboarding Assistant API",
  "version": "1.0.0"
}
```

**GET /health** - Detailed health check
```json
{
  "status": "healthy",
  "components": {
    "api": "operational",
    "database": "operational",
    "agent": "operational"
  }
}
```

**Authentication Endpoints:**

**POST /auth/register** - Register a new user

Request:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "role": "user",
  "created_at": "2024-01-25T12:00:00"
}
```

**POST /auth/login** - Login and get access token

Request (form-data):
```
username: user@example.com
password: securepassword123
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**GET /auth/me** - Get current user information (Protected)

Headers:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "role": "user",
  "created_at": "2024-01-25T12:00:00"
}
```

**Protected Endpoints:**

**POST /chat** - Conversational AI endpoint (Requires Authentication)

Headers:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

Request:
```json
{
  "message": "How do I create a project?",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "response": "To create a project...",
  "session_id": "session-123",
  "sources": [
    {
      "content": "Project creation guide...",
      "metadata": {"source": "projects_guide.md", "stage": "first_steps"}
    }
  ],
  "current_stage": "welcome"
}
```

**Interactive Documentation:**
Visit `http://localhost:8000/docs` for Swagger UI with interactive API testing.

**Security Notes:**
- Access tokens expire after 30 minutes (configurable)
- Passwords are hashed using bcrypt
- JWT tokens are signed with HS256 algorithm
- All protected endpoints require valid authentication

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

### Automated Tests

The project includes several test scripts to verify functionality:

**1. Authentication System Tests**
```bash
python test_auth.py
```
Tests user registration, login, token validation, and protected endpoints.

**2. API Endpoint Tests**
```bash
python test_api.py
```
Tests the REST API endpoints including chat functionality.

**3. cURL-based API Tests**
```bash
chmod +x test_api_curl.sh
./test_api_curl.sh
```
Shell script with cURL commands for API testing.

**4. Memory Fallback Tests**
```bash
python test_memory_fallback.py
```
Tests the memory system's fallback mechanism when Redis is unavailable.

### Manual Testing

**Streamlit Chat Interface:**
1. Start chat interface: `streamlit run simple_chat_app.py` or `streamlit run chat_app.py`
2. Try these queries:
   - "How do I create a new project?"
   - "What features are available?"
   - "Tell me about getting started"
   - "I need help with my account"
   - "What integrations are available?"
3. Test stage progression by changing stages in the sidebar
4. Verify memory by asking follow-up questions
5. Check session management with "New Session" button
6. View sources in the advanced chat app

**REST API Testing:**
1. Start API server: `uvicorn api:app --reload --port 8000`
2. Visit interactive docs: `http://localhost:8000/docs`
3. Test authentication flow:
   - Register a new user
   - Login to get access token
   - Use token to access protected endpoints
4. Test chat endpoint with various queries

### Utility Scripts

**Clear Memory Storage**
```bash
python clear_memories.py
```
Clears all stored memories (useful for testing fresh starts).

---

## 📊 Project Structure

```
Onboarding_agent/
├── backend/
│   ├── agent/           # LangGraph agentic workflow
│   │   ├── __init__.py
│   │   ├── state.py     # Agent state definition
│   │   ├── nodes.py     # Agent nodes (analyze, load memory, retrieve, respond, save)
│   │   └── graph.py     # LangGraph workflow orchestration
│   ├── auth/            # Authentication system
│   │   ├── __init__.py
│   │   ├── utils.py     # JWT & password hashing utilities
│   │   ├── dependencies.py  # FastAPI auth dependencies
│   │   └── service.py   # Authentication service layer
│   ├── rag/             # RAG system components
│   │   ├── __init__.py
│   │   ├── vector_store.py      # ChromaDB integration
│   │   ├── document_processor.py # Text chunking & processing
│   │   ├── query_planner.py     # Query analysis & planning
│   │   ├── reranker.py          # Result reranking
│   │   ├── agentic_rag.py       # Main RAG engine
│   │   ├── sample_documents.py  # Knowledge base (10 documents)
│   │   └── initializer.py       # RAG initialization
│   ├── memory/          # Dual-layer memory system
│   │   ├── __init__.py
│   │   ├── short_term.py    # Redis/in-memory session storage
│   │   └── long_term.py     # SQL persistent storage
│   ├── database/        # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py    # SQLAlchemy connection & session
│   │   └── models.py        # Database models (6 tables)
│   ├── models/          # Data models
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic schemas (API & domain models)
│   ├── __init__.py
│   └── config.py        # Configuration management (Pydantic Settings)
├── venv311/             # Python virtual environment
├── api.py               # FastAPI REST API server with authentication ⭐
├── simple_chat_app.py   # Simple Streamlit chat (no RAG)
├── chat_app.py          # Advanced Streamlit chat with RAG + Agent
├── run_api.sh           # Convenience script to start API
├── run_chat.sh          # Convenience script to start chat UI
├── test_auth.py         # Authentication system tests
├── test_api.py          # API endpoint tests
├── test_api_curl.sh     # cURL-based API tests
├── test_memory_fallback.py  # Memory fallback tests
├── clear_memories.py    # Utility to clear memory storage
├── requirements.txt     # Python dependencies
├── onboarding.db        # SQLite database (auto-created)
├── README.md            # This file - comprehensive documentation
├── AUTHENTICATION_GUIDE.md      # Detailed authentication guide
├── AUTHENTICATION_SUMMARY.md    # Auth implementation summary
├── IMPLEMENTATION_STATUS.md     # Current project status
├── FALLBACK_IMPROVEMENTS.md     # Memory fallback documentation
├── .env.example         # Environment template
├── .env                 # Your configuration (gitignored)
└── .gitignore           # Git ignore patterns
```

---

## 🤝 Contributing

This is a student project for Turing College AI Engineering course. 

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

**Built with ❤️ for better user onboarding experiences**
