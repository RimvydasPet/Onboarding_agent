from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schemas import APIChatRequest, APIChatResponse
from backend.agent.graph import run_agent
from backend.database.connection import init_db
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


@app.post("/chat", response_model=APIChatResponse)
async def chat(request: APIChatRequest):
    """
    Chat endpoint for conversational AI with RAG.
    
    Args:
        request: APIChatRequest containing message, optional session_id, and user_id
    
    Returns:
        APIChatResponse with response, session_id, sources, and current_stage
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Processing chat request for user {request.user_id}, session {session_id}")
        
        result = run_agent(
            user_input=request.message,
            user_id=request.user_id,
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
