from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from backend.database.models import OnboardingTaskDB
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskManager:
    """Manage onboarding tasks for users."""
    
    # Define tasks for each stage
    STAGE_TASKS = {
        "welcome": [
            {"task_id": "intro_read", "description": "Read welcome message", "optional": False},
            {"task_id": "name_provided", "description": "Provide your name", "optional": False},
            {"task_id": "role_shared", "description": "Share your role/position", "optional": False},
            {"task_id": "office_location", "description": "Share preferred office location or remote work preference", "optional": False},
            {"task_id": "work_schedule", "description": "Discuss preferred work schedule/hours", "optional": False},
            {"task_id": "perks_interest", "description": "Share interest in company perks (gym, parking, meal plans, etc.)", "optional": False},
            {"task_id": "equipment_needs", "description": "Specify equipment needs (laptop, monitor, accessories)", "optional": False},
            {"task_id": "goals_discussed", "description": "Discuss your goals", "optional": True},
        ],
        "profile_setup": [
            {"task_id": "full_name", "description": "Enter your full name", "optional": False},
            {"task_id": "email_verified", "description": "Verify your email address", "optional": False},
            {"task_id": "role_selected", "description": "Select your role", "optional": False},
            {"task_id": "department_chosen", "description": "Choose your department", "optional": True},
            {"task_id": "avatar_uploaded", "description": "Upload profile picture", "optional": True},
        ],
        "learning_preferences": [
            {"task_id": "learning_style", "description": "Select learning style (visual/hands-on/reading)", "optional": False},
            {"task_id": "notification_prefs", "description": "Set notification preferences", "optional": False},
            {"task_id": "tutorial_pace", "description": "Choose tutorial pace", "optional": False},
            {"task_id": "language_pref", "description": "Set language preference", "optional": True},
        ],
        "first_steps": [
            {"task_id": "dashboard_explored", "description": "Explore the dashboard", "optional": False},
            {"task_id": "first_project", "description": "Create your first project", "optional": False},
            {"task_id": "tutorial_completed", "description": "Complete quick tutorial", "optional": False},
            {"task_id": "team_invited", "description": "Invite a team member", "optional": True},
            {"task_id": "settings_reviewed", "description": "Review account settings", "optional": True},
        ],
        "completed": [
            {"task_id": "feedback_provided", "description": "Provide onboarding feedback", "optional": True},
            {"task_id": "resources_bookmarked", "description": "Bookmark helpful resources", "optional": True},
        ]
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_stage_tasks(self, user_id: int, stage: str) -> List[OnboardingTaskDB]:
        """
        Initialize tasks for a specific stage.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            List of created tasks
        """
        if stage not in self.STAGE_TASKS:
            logger.warning(f"Unknown stage: {stage}")
            return []
        
        # Check if tasks already exist for this stage
        existing_tasks = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id,
            OnboardingTaskDB.stage == stage
        ).all()
        
        if existing_tasks:
            logger.info(f"Tasks already exist for user {user_id} in stage {stage}")
            return existing_tasks
        
        # Create new tasks
        tasks = []
        for task_def in self.STAGE_TASKS[stage]:
            task = OnboardingTaskDB(
                user_id=user_id,
                stage=stage,
                task_id=task_def["task_id"],
                description=task_def["description"],
                optional=task_def["optional"],
                completed=False
            )
            self.db.add(task)
            tasks.append(task)
        
        self.db.commit()
        logger.info(f"Initialized {len(tasks)} tasks for user {user_id} in stage {stage}")
        return tasks
    
    def get_stage_tasks(self, user_id: int, stage: str) -> List[Dict]:
        """
        Get all tasks for a specific stage.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            List of task dictionaries
        """
        tasks = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id,
            OnboardingTaskDB.stage == stage
        ).order_by(OnboardingTaskDB.id).all()
        
        return [self._task_to_dict(task) for task in tasks]
    
    def complete_task(self, user_id: int, stage: str, task_id: str, completion_data: Optional[Dict] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
            task_id: Task identifier
            completion_data: Optional data about task completion
        
        Returns:
            True if task was completed, False otherwise
        """
        task = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id,
            OnboardingTaskDB.stage == stage,
            OnboardingTaskDB.task_id == task_id
        ).first()
        
        if not task:
            logger.warning(f"Task not found: {task_id} for user {user_id} in stage {stage}")
            return False
        
        if task.completed:
            logger.info(f"Task {task_id} already completed")
            return True
        
        task.completed = True
        task.completed_at = datetime.utcnow()
        if completion_data:
            task.completion_data = completion_data
        
        self.db.commit()
        logger.info(f"Task {task_id} completed for user {user_id}")
        return True
    
    def get_stage_progress(self, user_id: int, stage: str) -> Dict:
        """
        Get progress statistics for a stage.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            Dictionary with progress statistics
        """
        tasks = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id,
            OnboardingTaskDB.stage == stage
        ).all()
        
        if not tasks:
            return {
                "total": 0,
                "completed": 0,
                "required_completed": 0,
                "required_total": 0,
                "optional_completed": 0,
                "optional_total": 0,
                "percentage": 0,
                "stage_complete": False
            }
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.completed)
        required_tasks = [t for t in tasks if not t.optional]
        optional_tasks = [t for t in tasks if t.optional]
        
        required_total = len(required_tasks)
        required_completed = sum(1 for t in required_tasks if t.completed)
        optional_total = len(optional_tasks)
        optional_completed = sum(1 for t in optional_tasks if t.completed)
        
        # Stage is complete when all required tasks are done
        stage_complete = required_completed == required_total and required_total > 0
        
        percentage = (completed / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "completed": completed,
            "required_completed": required_completed,
            "required_total": required_total,
            "optional_completed": optional_completed,
            "optional_total": optional_total,
            "percentage": round(percentage, 1),
            "stage_complete": stage_complete
        }
    
    def is_stage_complete(self, user_id: int, stage: str) -> bool:
        """
        Check if all required tasks in a stage are complete.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            True if stage is complete, False otherwise
        """
        progress = self.get_stage_progress(user_id, stage)
        return progress["stage_complete"]
    
    def get_next_incomplete_task(self, user_id: int, stage: str) -> Optional[Dict]:
        """
        Get the next incomplete task for a stage.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            Next incomplete task or None
        """
        task = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id,
            OnboardingTaskDB.stage == stage,
            OnboardingTaskDB.completed == False
        ).order_by(
            OnboardingTaskDB.optional.asc(),  # Required tasks first
            OnboardingTaskDB.id.asc()
        ).first()
        
        return self._task_to_dict(task) if task else None
    
    def _task_to_dict(self, task: OnboardingTaskDB) -> Dict:
        """Convert task model to dictionary."""
        return {
            "id": task.id,
            "task_id": task.task_id,
            "description": task.description,
            "completed": task.completed,
            "optional": task.optional,
            "completion_data": task.completion_data,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    
    def get_all_user_tasks(self, user_id: int) -> Dict[str, List[Dict]]:
        """
        Get all tasks for a user across all stages.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary mapping stages to task lists
        """
        tasks = self.db.query(OnboardingTaskDB).filter(
            OnboardingTaskDB.user_id == user_id
        ).order_by(OnboardingTaskDB.stage, OnboardingTaskDB.id).all()
        
        result = {}
        for task in tasks:
            if task.stage not in result:
                result[task.stage] = []
            result[task.stage].append(self._task_to_dict(task))
        
        return result
