from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.models.schemas import APIChatRequest, APIChatResponse, UserCreate, User, Token
from backend.agent.graph import run_agent
from backend.database.connection import init_db, get_db
from backend.database.models import UserDB
from backend.auth.service import AuthService
from backend.auth.dependencies import get_current_active_user
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Onboarding Assistant API",
    description="REST API for the AI Onboarding Assistant with RAG and LangGraph agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and RAG system on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("API server started successfully")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Onboarding Assistant API",
        "version": "1.0.0"
    }


@app.post("/auth/register", response_model=User, status_code=201)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_data: User registration data (email, password, full_name)
        db: Database session
    
    Returns:
        Created user object
    """
    return AuthService.register_user(user_data, db)


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login endpoint to get access token.
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session
    
    Returns:
        Token object with access_token and token_type
    """
    from backend.models.schemas import UserLogin
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    return AuthService.login_user(login_data, db)


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: UserDB = Depends(get_current_active_user)):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from JWT token
    
    Returns:
        User object with user information
    """
    return User.model_validate(current_user)


@app.post("/chat", response_model=APIChatResponse)
async def chat(
    request: APIChatRequest,
    current_user: UserDB = Depends(get_current_active_user)
):
    """
    Chat endpoint for conversational AI with RAG (Protected - requires authentication).
    
    Args:
        request: APIChatRequest containing message and optional session_id
        current_user: Current authenticated user from JWT token
    
    Returns:
        APIChatResponse with response, session_id, sources, and current_stage
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Processing chat request for user {current_user.id}, session {session_id}")
        
        result = run_agent(
            user_input=request.message,
            user_id=current_user.id,
            session_id=session_id,
            current_stage="welcome"
        )
        
        return APIChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            sources=result.get("sources", []),
            current_stage=result.get("stage", "welcome")
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "components": {
            "api": "operational",
            "database": "operational",
            "agent": "operational"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
