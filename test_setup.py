import sys
import os

print("Testing basic imports and setup...\n")

try:
    from backend.config import settings
    print("✓ Config module loaded successfully")
    print(f"  - App Name: {settings.APP_NAME}")
    print(f"  - Database URL: {settings.DATABASE_URL}")
except Exception as e:
    print(f"✗ Config module failed: {e}")
    sys.exit(1)

try:
    from backend.models.schemas import (
        OnboardingStage, UserCreate, ChatMessage, AgentState
    )
    print("✓ Schema models loaded successfully")
    
    test_user = UserCreate(email="test@example.com", password="test123")
    print(f"  - Created test user: {test_user.email}")
    
    test_message = ChatMessage(role="user", content="Hello")
    print(f"  - Created test message: {test_message.content}")
except Exception as e:
    print(f"✗ Schema models failed: {e}")
    sys.exit(1)

try:
    from backend.database.models import Base, UserDB, OnboardingProfileDB
    print("✓ Database models loaded successfully")
    print(f"  - Tables defined: {len(Base.metadata.tables)}")
except Exception as e:
    print(f"✗ Database models failed: {e}")
    sys.exit(1)

try:
    from backend.database.connection import engine, init_db
    print("✓ Database connection module loaded")
    
    init_db()
    print("✓ Database initialized successfully")
    print(f"  - Tables created: {list(Base.metadata.tables.keys())}")
except Exception as e:
    print(f"✗ Database initialization failed: {e}")
    sys.exit(1)

try:
    from backend.memory.long_term import LongTermMemory
    print("✓ Long-term memory module loaded")
except Exception as e:
    print(f"✗ Long-term memory failed: {e}")
    sys.exit(1)

try:
    from backend.memory.short_term import ShortTermMemory
    print("✓ Short-term memory module loaded")
    print("  - Note: Redis connection will be tested when server starts")
except Exception as e:
    print(f"✗ Short-term memory failed: {e}")

print("\n" + "="*50)
print("All basic components loaded successfully!")
print("="*50)
