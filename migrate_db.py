"""
Database migration script to add onboarding_tasks table.
Run this after updating models.py to create the new table.
"""

from backend.database.connection import engine, Base
from backend.database.models import OnboardingTaskDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """Create new tables if they don't exist."""
    logger.info("Starting database migration...")
    
    try:
        # Create all tables defined in Base metadata
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database migration completed successfully!")
        logger.info("New table 'onboarding_tasks' created (if it didn't exist)")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_database()
