from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import uuid

from backend.database.connection import get_db
from backend.database.models import UserDB, OnboardingProfileDB
from backend.models.schemas import User, OnboardingProfile, ChatMessage
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory

router = APIRouter(prefix="/demo", tags=["demo"])

short_term_memory = ShortTermMemory()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "connected",
            "redis": "connected",
            "memory_systems": "operational"
        }
    }


@router.get("/database/stats")
async def database_stats(db: Session = Depends(get_db)):
    users_count = db.query(UserDB).count()
    profiles_count = db.query(OnboardingProfileDB).count()
    
    return {
        "total_users": users_count,
        "total_profiles": profiles_count,
        "tables": [
            "users",
            "onboarding_profiles",
            "conversations",
            "messages",
            "long_term_memories",
            "documents"
        ]
    }


@router.post("/memory/short-term/test")
async def test_short_term_memory(message: str):
    session_id = str(uuid.uuid4())
    
    short_term_memory.save_message(session_id, "user", message)
    short_term_memory.save_message(session_id, "assistant", f"Echo: {message}")
    
    short_term_memory.save_context(session_id, {
        "user_intent": "testing",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    messages = short_term_memory.get_messages(session_id)
    context = short_term_memory.get_context(session_id)
    
    return {
        "session_id": session_id,
        "messages": messages,
        "context": context,
        "message_count": len(messages)
    }


@router.post("/memory/long-term/test")
async def test_long_term_memory(
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    ltm = LongTermMemory(db)
    
    ltm.save_memory(
        user_id=user_id,
        memory_type="preference",
        key="favorite_topic",
        value="Python programming",
        importance=5
    )
    
    ltm.save_memory(
        user_id=user_id,
        memory_type="skill",
        key="experience_level",
        value="intermediate",
        importance=4
    )
    
    memories = ltm.get_memories_by_type(user_id, "preference")
    important = ltm.get_important_memories(user_id, min_importance=3)
    
    return {
        "user_id": user_id,
        "preferences": memories,
        "important_memories": important,
        "total_saved": 2
    }


@router.get("/onboarding/stages")
async def get_onboarding_stages():
    from backend.models.schemas import OnboardingStage
    
    return {
        "stages": [stage.value for stage in OnboardingStage],
        "total_stages": len(OnboardingStage),
        "description": {
            "welcome": "Initial greeting and introduction",
            "profile_setup": "User profile configuration",
            "learning_preferences": "Learning style and preferences",
            "first_steps": "Getting started guide",
            "completed": "Onboarding finished"
        }
    }


@router.get("/models/info")
async def get_models_info():
    return {
        "pydantic_models": [
            "UserCreate", "UserLogin", "User",
            "Token", "TokenData",
            "ChatMessage", "ChatRequest", "ChatResponse",
            "AgentState", "OnboardingProfile"
        ],
        "database_models": [
            "UserDB", "OnboardingProfileDB",
            "ConversationDB", "MessageDB",
            "LongTermMemoryDB", "DocumentDB"
        ],
        "enums": [
            "OnboardingStage", "UserRole"
        ]
    }
