"""
Script to clear old memories and reset the database for a fresh start.
"""
from backend.database.connection import get_db
from backend.database.models import LongTermMemoryDB, ConversationDB, MessageDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_memories():
    """Clear all memories from the database."""
    db = next(get_db())
    
    try:
        # Delete all long-term memories
        memory_count = db.query(LongTermMemoryDB).count()
        db.query(LongTermMemoryDB).delete()
        
        # Delete all messages
        message_count = db.query(MessageDB).count()
        db.query(MessageDB).delete()
        
        # Delete all conversations
        conversation_count = db.query(ConversationDB).count()
        db.query(ConversationDB).delete()
        
        db.commit()
        
        logger.info(f"✅ Cleared {memory_count} memories")
        logger.info(f"✅ Cleared {message_count} messages")
        logger.info(f"✅ Cleared {conversation_count} conversations")
        logger.info("Database reset complete! You can now start fresh.")
        
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Clearing Database Memories")
    print("="*60 + "\n")
    
    response = input("This will delete all memories and conversations. Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        clear_all_memories()
        print("\n✅ Database cleared successfully!")
        print("You can now restart the chat app for a fresh onboarding experience.\n")
    else:
        print("\n❌ Operation cancelled.\n")
