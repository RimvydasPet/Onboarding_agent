from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OnboardingStage(str, Enum):
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    LEARNING_PREFERENCES = "learning_preferences"
    FIRST_STEPS = "first_steps"
    COMPLETED = "completed"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    is_active: bool = True
    role: UserRole = UserRole.USER
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class OnboardingProfile(BaseModel):
    user_id: int
    current_stage: OnboardingStage = OnboardingStage.WELCOME
    preferences: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[str]] = None


class AgentState(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    user_id: int
    session_id: str
    current_stage: OnboardingStage = OnboardingStage.WELCOME
    context: Dict[str, Any] = Field(default_factory=dict)
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    next_action: Optional[str] = None


class APIChatRequest(BaseModel):
    """Request model for POST /chat endpoint"""
    message: str
    session_id: Optional[str] = None


class APIChatResponse(BaseModel):
    """Response model for POST /chat endpoint"""
    response: str
    session_id: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    current_stage: str
