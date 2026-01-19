# 🤖 AI Onboarding Assistant

An intelligent onboarding assistant powered by LangGraph, Agentic RAG, and dual-layer memory systems. This agent helps new users get started with your platform through conversational guidance, context-aware responses, and personalized onboarding experiences.

## 📋 Table of Contents

- [Agent Purpose](#agent-purpose)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Technical Implementation](#technical-implementation)
- [Documentation](#documentation)
- [Task Requirements Coverage](#task-requirements-coverage)

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

#### 1. **Agentic RAG System** (HARD Task ✅)
- **Intelligent Query Planning**: Analyzes user intent and determines optimal retrieval strategy
- **Multi-Strategy Retrieval**: Uses similarity search and Maximum Marginal Relevance (MMR)
- **Document Reranking**: Prioritizes most relevant information
- **Source Validation**: Ensures quality and relevance of retrieved content
- **Citation Generation**: Provides sources for transparency

#### 2. **Dual-Layer Memory System** (MEDIUM Task 1 ✅)
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

#### 3. **LangGraph Conversation Agent**
- **State Management**: Tracks conversation state across multiple turns
- **5-Node Processing Pipeline**:
  1. Analyze Input - Determine user intent and retrieval needs
  2. Load Memory - Retrieve relevant context from both memory layers
  3. Retrieve Context - Fetch documentation using RAG
  4. Generate Response - Create contextual, helpful responses
  5. Save Memory - Persist conversation for future reference

#### 4. **Onboarding Flow Management**
- **5 Structured Stages**:
  - Welcome - Initial greeting and introduction
  - Profile Setup - User profile configuration
  - Learning Preferences - Understanding user needs
  - First Steps - Guided first actions
  - Completed - Ongoing support

- **Progress Tracking**: Monitors completed steps and current stage
- **Adaptive Guidance**: Adjusts responses based on user's stage

#### 5. **Interactive Chat Interface**
- Beautiful Streamlit-based UI
- Real-time conversation
- Source citation display
- Progress visualization
- Session management

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (Streamlit)               │
│  - Chat Interface  - Progress Tracking  - Source Display    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   LangGraph Agent                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Analyze  │→ │  Load    │→ │ Retrieve │→ │ Generate │   │
│  │  Input   │  │  Memory  │  │ Context  │  │ Response │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐ ┌───▼────────┐ ┌───▼──────────┐
│  Agentic RAG    │ │  Memory    │ │  Database    │
│                 │ │  Systems   │ │              │
│ - Query Plan    │ │            │ │ - Users      │
│ - Vector Store  │ │ Short-term │ │ - Profiles   │
│ - Reranking     │ │ (Redis)    │ │ - Messages   │
│ - Citations     │ │            │ │ - Memories   │
│                 │ │ Long-term  │ │ - Documents  │
│                 │ │ (SQL)      │ │              │
└─────────────────┘ └────────────┘ └──────────────┘
```

### Technology Stack

- **LangGraph**: State machine for conversation flow
- **LangChain**: LLM orchestration and RAG components
- **Google Gemini**: LLM for response generation and query analysis
- **ChromaDB**: Vector database for document embeddings
- **SQLAlchemy**: ORM for persistent storage
- **Redis**: In-memory cache for session data
- **FastAPI**: REST API backend
- **Streamlit**: Interactive web interface
- **Pydantic**: Data validation and settings management

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
pip install -r requirements_new.txt
```

### Step 3: Configure Environment

```bash
cp .env.new .env
```

Edit `.env` and add your Google API key:

```env
GOOGLE_API_KEY=your_google_api_key_here
SECRET_KEY=your-secret-key-change-in-production
```

### Step 4: Initialize Database

```bash
python test_setup.py
```

### Step 5: (Optional) Install Redis

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

#### Option 1: Interactive Chat Interface (Recommended)

```bash
streamlit run chat_app.py
```

Open your browser to `http://localhost:8501`

#### Option 2: Demo UI (System Overview)

```bash
streamlit run demo_app.py
```

#### Option 3: FastAPI Backend

```bash
uvicorn backend.main:app --reload
```

API docs at `http://localhost:8000/docs`

### Common Use Cases

#### Example 1: Getting Started

**User:** "How do I create a new project?"

**Agent:** 
- Analyzes query intent (question about features)
- Retrieves relevant documentation from RAG
- Provides step-by-step instructions
- Cites sources from documentation
- Offers to help with next steps

#### Example 2: Troubleshooting

**User:** "I can't log in to my account"

**Agent:**
- Identifies troubleshooting intent
- Retrieves common login issues
- Provides solutions in order of likelihood
- Remembers issue for future reference
- Escalates to support if needed

#### Example 3: Learning Preferences

**User:** "I prefer video tutorials over text"

**Agent:**
- Saves preference to long-term memory
- Adjusts future recommendations
- Suggests video resources
- Tracks preference for personalization

### Programmatic Usage

```python
from backend.agent.graph import run_agent

# Run agent with user input
result = run_agent(
    user_input="How do I get started?",
    user_id=1,
    session_id="unique-session-id",
    current_stage="welcome"
)

print(result["response"])
print(result["retrieved_docs"])  # Source citations
```

### Testing RAG System

```bash
python backend/rag/initializer.py
```

This will:
- Initialize the RAG system
- Load sample documents
- Run test queries
- Display retrieval results

---

## 🔧 Technical Implementation

### Agentic RAG Pipeline

#### 1. Query Analysis
```python
# Analyzes user intent, topic, and complexity
analysis = query_planner.analyze_query(query, context)
# Returns: intent, topic, complexity, requires_retrieval, keywords
```

#### 2. Retrieval Strategy Planning
```python
# Determines optimal retrieval approach
strategy = query_planner.plan_retrieval_strategy(analysis)
# Simple queries: similarity search (k=3)
# Complex queries: MMR with reranking (k=7, fetch_k=20)
```

#### 3. Multi-Query Retrieval
```python
# Generates multiple search queries for better coverage
search_queries = query_planner.generate_search_queries(query, analysis)
# Combines original query with topic-specific and keyword variations
```

#### 4. Document Reranking
```python
# Scores and reranks documents by relevance
reranked_docs = reranker.rerank_documents(query, documents, top_k=5)
# Uses keyword overlap, exact matches, and metadata signals
```

#### 5. Source Validation & Citation
```python
# Validates quality and generates citations
validated = reranker.validate_sources(documents)
citations = reranker.add_citations(validated)
# Includes source, relevance score, and chunk information
```

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

The system includes comprehensive error handling:

- **Redis Connection Failures**: Automatic fallback to in-memory storage
- **LLM API Errors**: Graceful degradation with error messages
- **RAG Retrieval Failures**: Returns empty results with explanation
- **Database Errors**: Logged with user-friendly messages
- **Invalid Input**: Validation with helpful error messages

### Configuration

All settings managed through `backend/config.py`:

```python
class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    DATABASE_URL: str = "sqlite:///./onboarding.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    # ... more settings
```

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

#### Why LangGraph?
- **State Management**: Built-in state persistence across conversation turns
- **Flexibility**: Easy to add/modify nodes in the processing pipeline
- **Debugging**: Clear visualization of conversation flow
- **Scalability**: Handles complex multi-step reasoning

#### Why Agentic RAG?
- **Better Accuracy**: Query planning improves retrieval relevance
- **Transparency**: Citations build user trust
- **Adaptability**: Different strategies for different query types
- **Quality**: Reranking ensures best results surface first

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
- ✅ Main features implemented: RAG, conversation agent, memory systems
- ✅ Primary tasks effective: Answers questions, guides onboarding
- ✅ User interactions included: Chat interface, progress tracking

### 3. User Interface ✅
- ✅ User-friendly interface: Streamlit chat app with clean design
- ✅ Intuitive and easy to use: Clear conversation flow, visual progress
- ✅ All functionalities accessible: Chat, sources, progress, settings

### 4. Technical Implementation ✅
- ✅ Appropriate tools: LangGraph, LangChain, Gemini, ChromaDB, Redis, SQL
- ✅ Error handling: Redis fallback, API error handling, validation
- ✅ Real-world usage: Session management, persistence, scalability

### 5. Documentation ✅
- ✅ Clear usage documentation: Installation, usage, examples
- ✅ Common use cases: Getting started, troubleshooting, preferences
- ✅ Technical decisions: Architecture rationale explained

### Bonus Tasks

#### MEDIUM Task 1: Memory Systems ✅
- ✅ Short-term memory with Redis (with fallback)
- ✅ Long-term memory with SQL
- ✅ Importance scoring and access tracking
- ✅ Integration with LangGraph agent

#### MEDIUM Task 2: Authentication ⏳
- ⚠️ JWT token generation (implemented but not integrated)
- ⚠️ User registration/login (pending)
- ⚠️ Protected endpoints (pending)

#### HARD Task: Agentic RAG ✅
- ✅ Document processing and chunking
- ✅ Vector embeddings with ChromaDB
- ✅ Query planning with intent analysis
- ✅ Multi-strategy retrieval (similarity + MMR)
- ✅ Document reranking
- ✅ Source validation and citations

---

## 🧪 Testing

### Run All Tests

```bash
# Test basic setup
python test_setup.py

# Test RAG system
python backend/rag/initializer.py

# Test agent
python -c "from backend.agent.graph import run_agent; print(run_agent('How do I get started?'))"
```

### Manual Testing

1. Start chat interface: `streamlit run chat_app.py`
2. Try these queries:
   - "How do I create a new project?"
   - "What are the keyboard shortcuts?"
   - "I can't log in"
   - "Tell me about the mobile app"
   - "I prefer video tutorials"

---

## 📊 Project Status

**Overall Completion: ~85%**

- ✅ Memory Systems (MEDIUM Task 1) - 100%
- ✅ Agentic RAG (HARD Task) - 100%
- ✅ LangGraph Agent - 100%
- ✅ Chat Interface - 100%
- ✅ Documentation - 100%
- ⏳ Authentication (MEDIUM Task 2) - 30%
- ✅ Error Handling - 80%

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
