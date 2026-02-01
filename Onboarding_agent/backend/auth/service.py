from datetime import timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.database.models import UserDB, OnboardingProfileDB
from backend.models.schemas import UserCreate, UserLogin, Token, User
from backend.auth.utils import verify_password, get_password_hash, create_access_token
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations."""
    
    @staticmethod
    def register_user(user_data: UserCreate, db: Session) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            db: Database session
        
        Returns:
            Created user object
        
        Raises:
            HTTPException: If email already exists
        """
        existing_user = db.query(UserDB).filter(UserDB.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        
        db_user = UserDB(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=True,
            role="user"
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        onboarding_profile = OnboardingProfileDB(
            user_id=db_user.id,
            current_stage="welcome",
            preferences={},
            progress={},
            completed_steps=[]
        )
        db.add(onboarding_profile)
        db.commit()
        
        logger.info(f"New user registered: {user_data.email}")
        
        return User.model_validate(db_user)
    
    @staticmethod
    def authenticate_user(login_data: UserLogin, db: Session) -> Optional[UserDB]:
        """
        Authenticate a user with email and password.
        
        Args:
            login_data: User login credentials
            db: Database session
        
        Returns:
            UserDB object if authentication successful, None otherwise
        """
        user = db.query(UserDB).filter(UserDB.email == login_data.email).first()
        
        if not user:
            return None
        
        if not verify_password(login_data.password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    def login_user(login_data: UserLogin, db: Session) -> Token:
        """
        Login a user and generate access token.
        
        Args:
            login_data: User login credentials
            db: Database session
        
        Returns:
            Token object with access token
        
        Raises:
            HTTPException: If authentication fails
        """
        user = AuthService.authenticate_user(login_data, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return Token(access_token=access_token, token_type="bearer")
    
    @staticmethod
    def get_user_by_email(email: str, db: Session) -> Optional[UserDB]:
        """
        Get a user by email.
        
        Args:
            email: User email
            db: Database session
        
        Returns:
            UserDB object or None if not found
        """
        return db.query(UserDB).filter(UserDB.email == email).first()
    
    @staticmethod
    def get_user_by_id(user_id: int, db: Session) -> Optional[UserDB]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            db: Database session
        
        Returns:
            UserDB object or None if not found
        """
        return db.query(UserDB).filter(UserDB.id == user_id).first()
