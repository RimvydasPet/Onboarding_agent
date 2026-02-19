from sqlalchemy.orm import Session
from backend.database.models import UserDB, OnboardingProfileDB, LongTermMemoryDB
from datetime import datetime
from typing import List, Dict, Any


class AdminQueries:
    """Database queries for admin operations."""
    
    @staticmethod
    def _get_facts_for_user(user_id: int, profile: OnboardingProfileDB, db: Session) -> Dict[str, Any]:
        """Get facts from profile progress or fallback to LongTermMemory."""
        facts = {}
        
        if profile and profile.progress:
            facts = profile.progress.get("facts", {})
        
        if not facts:
            memories = db.query(LongTermMemoryDB).filter(
                LongTermMemoryDB.user_id == user_id,
                LongTermMemoryDB.memory_type == "onboarding"
            ).all()
            for memory in memories:
                facts[str(memory.key)] = memory.value
        
        return facts
    
    @staticmethod
    def get_all_onboarded_users(db: Session) -> List[Dict[str, Any]]:
        """Get all users with onboarding profiles."""
        profiles = db.query(OnboardingProfileDB).all()
        
        result = []
        for profile in profiles:
            user = db.query(UserDB).filter(UserDB.id == profile.user_id).first()
            facts = AdminQueries._get_facts_for_user(profile.user_id, profile, db)
            
            if user:
                result.append({
                    "user_id": user.id,
                    "name": facts.get("welcome.name", user.full_name or "N/A"),
                    "email": user.email,
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                    "created_at": user.created_at,
                })
            else:
                result.append({
                    "user_id": profile.user_id,
                    "name": facts.get("welcome.name", "N/A"),
                    "email": facts.get("welcome.email_preference", f"user_{profile.user_id}"),
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                    "created_at": profile.updated_at,
                })
        
        return sorted(result, key=lambda x: x["completed_at"] or x["created_at"], reverse=True)
    
    @staticmethod
    def get_onboarding_stats(db: Session) -> Dict[str, Any]:
        """Get onboarding completion statistics."""
        total_users = db.query(OnboardingProfileDB).count()
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
        """Get recently active onboarding users."""
        profiles = db.query(OnboardingProfileDB).order_by(OnboardingProfileDB.updated_at.desc()).limit(limit).all()
        
        result = []
        for profile in profiles:
            user = db.query(UserDB).filter(UserDB.id == profile.user_id).first()
            facts = AdminQueries._get_facts_for_user(profile.user_id, profile, db)
            
            if user:
                result.append({
                    "user_id": user.id,
                    "name": facts.get("welcome.name", user.full_name or "N/A"),
                    "email": user.email,
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                })
            else:
                result.append({
                    "user_id": profile.user_id,
                    "name": facts.get("welcome.name", "N/A"),
                    "email": facts.get("welcome.email_preference", f"user_{profile.user_id}"),
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "completed_at": profile.updated_at,
                })
        
        return result
    
    @staticmethod
    def get_newcomers_in_progress(db: Session, limit: int = 15) -> List[Dict[str, Any]]:
        """Get newcomers currently in onboarding (in-progress)."""
        profiles = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.current_stage != "completed"
        ).order_by(OnboardingProfileDB.updated_at.desc()).limit(limit).all()
        
        result = []
        for profile in profiles:
            user = db.query(UserDB).filter(UserDB.id == profile.user_id).first()
            facts = AdminQueries._get_facts_for_user(profile.user_id, profile, db)
            
            if user:
                result.append({
                    "user_id": user.id,
                    "name": facts.get("welcome.name", user.full_name or "N/A"),
                    "email": user.email,
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "current_stage": profile.current_stage,
                    "updated_at": profile.updated_at,
                    "created_at": user.created_at,
                })
            else:
                result.append({
                    "user_id": profile.user_id,
                    "name": facts.get("welcome.name", "N/A"),
                    "email": facts.get("welcome.email_preference", f"user_{profile.user_id}"),
                    "role": facts.get("welcome.role", "N/A"),
                    "department": facts.get("welcome.department", "N/A"),
                    "current_stage": profile.current_stage,
                    "updated_at": profile.updated_at,
                    "created_at": profile.updated_at,
                })
        
        return result
    
    @staticmethod
    def get_full_onboarding_details(user_id: int, db: Session) -> Dict[str, Any]:
        """Get complete onboarding details for a user including all stages and Q&A."""
        profile = db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.user_id == user_id
        ).first()
        
        if not profile:
            return None
        
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        facts = AdminQueries._get_facts_for_user(user_id, profile, db)
        preferences = profile.preferences if profile.preferences else {}
        progress = profile.progress if profile.progress else {}
        
        if user:
            return {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name or facts.get("welcome.name", "N/A"),
                "created_at": user.created_at,
                "current_stage": profile.current_stage,
                "completed_steps": profile.completed_steps if profile.completed_steps else [],
                "facts": facts,
                "preferences": preferences,
                "progress": progress,
                "updated_at": profile.updated_at,
            }
        else:
            return {
                "user_id": user_id,
                "email": facts.get("welcome.email_preference", f"user_{user_id}"),
                "full_name": facts.get("welcome.name", "N/A"),
                "created_at": profile.updated_at,
                "current_stage": profile.current_stage,
                "completed_steps": profile.completed_steps if profile.completed_steps else [],
                "facts": facts,
                "preferences": preferences,
                "progress": progress,
                "updated_at": profile.updated_at,
            }
