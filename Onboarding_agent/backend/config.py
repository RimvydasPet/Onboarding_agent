from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path

# Resolve .env relative to this file's directory (backend/) -> parent is Onboarding_agent/
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    DATABASE_URL: str = "sqlite:///./onboarding.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    GEMINI_MODEL: str = "gemini-1.5-flash-latest"

    @property
    def gemini_model_id(self) -> str:
        model = str(self.GEMINI_MODEL or "").strip()
        if model.startswith("models/"):
            return model[len("models/"):]
        return model

    WEB_SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: str = ""
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    APP_NAME: str = "Onboarding Agent"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    DOCUMENTS_PUBLIC_BASE_URL: str = ""
    
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    ADMIN_EMAILS: str = ""
    
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8501"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def admin_emails_list(self) -> List[str]:
        admin_emails = str(self.ADMIN_EMAILS or "").strip()
        if not admin_emails:
            return []
        return [email.strip().lower() for email in admin_emails.split(",")]
    
    def is_admin_email(self, email: str) -> bool:
        return email.strip().lower() in self.admin_emails_list
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
