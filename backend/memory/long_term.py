from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database.models import LongTermMemoryDB, OnboardingProfileDB


class LongTermMemory:
    def __init__(self, db: Session):
        self.db = db
    
    def save_memory(
        self,
        user_id: int,
        memory_type: str,
        key: str,
        value: Any,
        importance: int = 1
    ):
        existing = self.db.query(LongTermMemoryDB).filter(
            LongTermMemoryDB.user_id == user_id,
            LongTermMemoryDB.memory_type == memory_type,
            LongTermMemoryDB.key == key
        ).first()
        
        if existing:
            existing.value = value
            existing.importance = importance
            existing.accessed_at = datetime.utcnow()
            existing.access_count += 1
        else:
            memory = LongTermMemoryDB(
                user_id=user_id,
                memory_type=memory_type,
                key=key,
                value=value,
                importance=importance
            )
            self.db.add(memory)
        
        self.db.commit()
    
    def get_memory(self, user_id: int, memory_type: str, key: str) -> Optional[Any]:
        memory = self.db.query(LongTermMemoryDB).filter(
            LongTermMemoryDB.user_id == user_id,
            LongTermMemoryDB.memory_type == memory_type,
            LongTermMemoryDB.key == key
        ).first()
        
        if memory:
            memory.accessed_at = datetime.utcnow()
            memory.access_count += 1
            self.db.commit()
            return memory.value
        return None
    
    def get_memories_by_type(self, user_id: int, memory_type: str) -> List[Dict[str, Any]]:
        memories = self.db.query(LongTermMemoryDB).filter(
            LongTermMemoryDB.user_id == user_id,
            LongTermMemoryDB.memory_type == memory_type
        ).order_by(LongTermMemoryDB.importance.desc()).all()
        
        return [
            {
                "key": m.key,
                "value": m.value,
                "importance": m.importance,
                "access_count": m.access_count
            }
            for m in memories
        ]
    
    def get_important_memories(self, user_id: int, min_importance: int = 3, limit: int = 10) -> List[Dict[str, Any]]:
        memories = self.db.query(LongTermMemoryDB).filter(
            LongTermMemoryDB.user_id == user_id,
            LongTermMemoryDB.importance >= min_importance
        ).order_by(
            LongTermMemoryDB.importance.desc(),
            LongTermMemoryDB.access_count.desc()
        ).limit(limit).all()
        
        return [
            {
                "type": m.memory_type,
                "key": m.key,
                "value": m.value,
                "importance": m.importance
            }
            for m in memories
        ]
    
    def update_onboarding_progress(self, user_id: int, stage: str, completed_step: str):
        profile = self.db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.user_id == user_id
        ).first()
        
        if not profile:
            profile = OnboardingProfileDB(
                user_id=user_id,
                current_stage=stage,
                completed_steps=[completed_step]
            )
            self.db.add(profile)
        else:
            profile.current_stage = stage
            if completed_step not in profile.completed_steps:
                profile.completed_steps.append(completed_step)
        
        self.db.commit()
    
    def get_onboarding_progress(self, user_id: int) -> Dict[str, Any]:
        profile = self.db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.user_id == user_id
        ).first()
        
        if not profile:
            return {
                "current_stage": "welcome",
                "completed_steps": [],
                "preferences": {},
                "progress": {}
            }
        
        return {
            "current_stage": profile.current_stage,
            "completed_steps": profile.completed_steps,
            "preferences": profile.preferences,
            "progress": profile.progress
        }
    
    def save_user_preference(self, user_id: int, preference_key: str, preference_value: Any):
        profile = self.db.query(OnboardingProfileDB).filter(
            OnboardingProfileDB.user_id == user_id
        ).first()
        
        if profile:
            if profile.preferences is None:
                profile.preferences = {}
            profile.preferences[preference_key] = preference_value
            self.db.commit()
