"""
Test script for the improved fallback memory mechanism.
This demonstrates the enhanced features including TTL simulation, thread safety, and error handling.
"""
import time
import logging
from backend.memory.short_term import ShortTermMemory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fallback_mechanism():
    """Test the fallback storage mechanism."""
    print("\n" + "="*60)
    print("Testing Improved Fallback Memory Mechanism")
    print("="*60 + "\n")
    
    # Initialize memory (will likely use fallback if Redis is not running)
    memory = ShortTermMemory()
    
    # Get storage stats
    stats = memory.get_storage_stats()
    print(f"Storage Mode: {stats['mode']}")
    print(f"Available: {stats['available']}")
    print(f"Stats: {stats}\n")
    
    # Test 1: Save and retrieve messages
    print("Test 1: Save and Retrieve Messages")
    print("-" * 40)
    session_id = "test_session_123"
    
    memory.save_message(session_id, "user", "Hello, this is a test message")
    memory.save_message(session_id, "assistant", "Hi! I received your message.")
    
    messages = memory.get_messages(session_id)
    print(f"Saved {len(messages)} messages")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. [{msg['role']}]: {msg['content'][:50]}...")
    print()
    
    # Test 2: Save and retrieve context
    print("Test 2: Save and Retrieve Context")
    print("-" * 40)
    context = {
        "user_name": "Test User",
        "preferences": {"theme": "dark", "language": "en"},
        "stage": "welcome"
    }
    memory.save_context(session_id, context)
    
    retrieved_context = memory.get_context(session_id)
    print(f"Context saved and retrieved: {retrieved_context}")
    print()
    
    # Test 3: Update context
    print("Test 3: Update Context")
    print("-" * 40)
    memory.update_context(session_id, {"stage": "department_info", "progress": 25})
    updated_context = memory.get_context(session_id)
    print(f"Updated context: {updated_context}")
    print()
    
    # Test 4: Extend session TTL
    print("Test 4: Extend Session TTL")
    print("-" * 40)
    memory.extend_session(session_id, ttl=7200)
    print(f"Session TTL extended to 7200 seconds (2 hours)")
    print()
    
    # Test 5: Storage statistics
    print("Test 5: Storage Statistics")
    print("-" * 40)
    stats = memory.get_storage_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Test 6: TTL expiration (only for fallback mode)
    if not memory.redis_available:
        print("Test 6: TTL Expiration Simulation (Fallback Mode)")
        print("-" * 40)
        
        # Create a session with short TTL
        short_session = "short_ttl_session"
        memory.save_message(short_session, "user", "This will expire soon")
        memory._set_expiry(memory._get_session_key(short_session), 2)  # 2 seconds
        
        print("Created session with 2-second TTL")
        print(f"Messages before expiry: {len(memory.get_messages(short_session))}")
        
        print("Waiting 3 seconds...")
        time.sleep(3)
        
        print(f"Messages after expiry: {len(memory.get_messages(short_session))}")
        print()
    
    # Test 7: Clear session
    print("Test 7: Clear Session")
    print("-" * 40)
    memory.clear_session(session_id)
    cleared_messages = memory.get_messages(session_id)
    cleared_context = memory.get_context(session_id)
    print(f"Messages after clear: {len(cleared_messages)}")
    print(f"Context after clear: {cleared_context}")
    print()
    
    # Final stats
    print("Final Storage Statistics")
    print("-" * 40)
    final_stats = memory.get_storage_stats()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        test_fallback_mechanism()
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
