from sqlalchemy.orm import Session
from backend.database.models import UserDB, OnboardingProfileDB
from datetime import datetime
from typing import List, Dict, Any


class AdminQueries:
    """Database queries for admin operations."""
    
    @staticmethod
    def get_all_onboarded_users(db: Session) -> List[Dict[str, Any]]:
        """Get all users who have completed onboarding."""
        profiles = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.current_stage == "completed"
        ).all()
        
        result = []
        for profile in profiles:
            user = db.query(UserDB).filter(UserDB.id == profile.user_id).first()
            if user:
                facts = profile.progress.get("facts", {}) if profile.progress else {}
                result.append({
                    "user_id": user.id,
                    "name": facts.get("welcome.name", "N/A"),
                    "email": user.email,
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                    "created_at": user.created_at,
                })
        
        return sorted(result, key=lambda x: x["completed_at"], reverse=True)
    
    @staticmethod
    def get_onboarding_stats(db: Session) -> Dict[str, Any]:
        """Get onboarding completion statistics."""
        total_users = db.query(UserDB).count()
        completed_users = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.current_stage == "completed"
        ).count()
        in_progress_users = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.current_stage != "completed"
        ).count()
        
        completion_rate = (completed_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "completed_users": completed_users,
            "in_progress_users": in_progress_users,
            "completion_rate": round(completion_rate, 2),
        }
    
    @staticmethod
    def get_user_by_email(email: str, db: Session) -> Dict[str, Any]:
        """Get user details by email."""
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            return None
        
        profile = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.user_id == user.id
        ).first()
        
        facts = profile.progress.get("facts", {}) if profile and profile.progress else {}
        
        return {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "onboarding_stage": profile.current_stage if profile else "N/A",
            "onboarding_name": facts.get("welcome.name", "N/A"),
            "onboarding_role": facts.get("welcome.role", "N/A"),
            "onboarding_department": facts.get("welcome.department", "N/A"),
        }
    
    @staticmethod
    def get_recent_onboarded_users(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently onboarded users."""
        profiles = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.current_stage == "completed"
        ).order_by(OnboardingProfileDB.updated_at.desc()).limit(limit).all()
        
        result = []
        for profile in profiles:
            user = db.query(UserDB).filter(UserDB.id == profile.user_id).first()
            if user:
                facts = profile.progress.get("facts", {}) if profile.progress else {}
                result.append({
                    "user_id": user.id,
                    "name": facts.get("welcome.name", "N/A"),
                    "email": user.email,
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                })
        
        return result
