"""
Simple test script for the REST API
Run this after starting the API server with: uvicorn api:app --reload --port 8000
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_detailed_health():
    """Test the detailed health endpoint"""
    print("\n=== Testing Detailed Health ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_chat_endpoint():
    """Test the chat endpoint"""
    print("\n=== Testing Chat Endpoint ===")
    
    test_messages = [
        "How do I create a new project?",
        "What features are available?",
        "Tell me about integrations"
    ]
    
    session_id = "test-session-123"
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i}: {message} ---")
        
        payload = {
            "message": message,
            "session_id": session_id,
            "user_id": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Session ID: {data['session_id']}")
            print(f"Current Stage: {data['current_stage']}")
            print(f"Response: {data['response'][:200]}...")  # First 200 chars
            print(f"Number of Sources: {len(data.get('sources', []))}")
            
            if data.get('sources'):
                print("\nSources:")
                for idx, source in enumerate(data['sources'][:2], 1):  # Show first 2 sources
                    print(f"  {idx}. {source.get('metadata', {}).get('source', 'Unknown')}")
        else:
            print(f"Error: {response.text}")
        
        print("-" * 60)
    
    return True

def test_chat_without_session():
    """Test chat endpoint without providing session_id (should auto-generate)"""
    print("\n=== Testing Chat Without Session ID ===")
    
    payload = {
        "message": "Hello, I'm new here!",
        "user_id": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Auto-generated Session ID: {data['session_id']}")
        print(f"Response: {data['response'][:150]}...")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("REST API Test Suite")
    print("=" * 60)
    print("\nMake sure the API server is running:")
    print("  uvicorn api:app --reload --port 8000\n")
    
    try:
        # Run tests
        results = {
            "Health Check": test_health_check(),
            "Detailed Health": test_detailed_health(),
            "Chat Endpoint": test_chat_endpoint(),
            "Chat Without Session": test_chat_without_session()
        }
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        all_passed = all(results.values())
        print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️  Some tests failed"))
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print("Please start the server first:")
        print("  uvicorn api:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
