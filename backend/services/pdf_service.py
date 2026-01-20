from typing import Optional, Dict
from sqlalchemy.orm import Session
from backend.database.models import UserDB, OnboardingProfileDB
from backend.services.task_manager import TaskManager
from backend.utils.pdf_generator import OnboardingPDFGenerator
import logging
import os

logger = logging.getLogger(__name__)


class PDFService:
    """Service to handle automatic PDF generation for onboarding."""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_manager = TaskManager(db)
        self.pdf_generator = OnboardingPDFGenerator()
    
    def should_generate_pdf(self, user_id: int, stage: str) -> bool:
        """
        Check if PDF should be generated for this stage completion.
        
        Args:
            user_id: User ID
            stage: Onboarding stage
        
        Returns:
            True if PDF should be generated
        """
        if stage == "welcome":
            return self.task_manager.is_stage_complete(user_id, stage)
        return False
    
    def generate_welcome_summary(self, user_id: int) -> Optional[bytes]:
        """
        Generate PDF summary after welcome stage completion.
        
        Args:
            user_id: User ID
        
        Returns:
            PDF bytes or None if generation fails
        """
        try:
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            profile = self.db.query(OnboardingProfileDB).filter(
                OnboardingProfileDB.user_id == user_id
            ).first()
            
            # Get welcome stage tasks with completion data
            welcome_tasks = self.task_manager.get_stage_tasks(user_id, "welcome")
            
            # Extract user data from completed tasks
            user_data = self._extract_user_data_from_tasks(user, profile, welcome_tasks)
            
            # Generate PDF
            tasks_data = {"welcome": welcome_tasks}
            pdf_bytes = self.pdf_generator.generate_onboarding_summary(
                user_data=user_data,
                tasks_data=tasks_data
            )
            
            # Optionally save to disk
            pdf_dir = "generated_pdfs"
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = os.path.join(pdf_dir, f"onboarding_summary_{user_id}.pdf")
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info(f"PDF generated for user {user_id} at {pdf_path}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF for user {user_id}: {e}")
            return None
    
    def _extract_user_data_from_tasks(
        self, 
        user: UserDB, 
        profile: Optional[OnboardingProfileDB],
        tasks: list
    ) -> Dict:
        """Extract user data from completed tasks."""
        user_data = {
            "name": user.username,
            "email": user.email,
            "role": "New Employee"
        }
        
        # Extract role from tasks if provided
        for task in tasks:
            if task.get('task_id') == 'role_shared' and task.get('completion_data'):
                role = task['completion_data'].get('response', '')
                if role:
                    user_data['role'] = role
                break
        
        return user_data
    
    def get_pdf_path(self, user_id: int) -> Optional[str]:
        """
        Get the path to generated PDF for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Path to PDF or None if not found
        """
        pdf_path = f"generated_pdfs/onboarding_summary_{user_id}.pdf"
        if os.path.exists(pdf_path):
            return pdf_path
        return None
    
    def get_pdf_download_url(self, user_id: int) -> str:
        """
        Get the download URL for user's PDF.
        
        Args:
            user_id: User ID
        
        Returns:
            Download URL
        """
        return f"/demo/onboarding/summary/pdf/{user_id}"
