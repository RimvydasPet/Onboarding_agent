"""
Test script for authentication endpoints.
Run the API server first: uvicorn api:app --reload --port 8000
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_authentication_flow():
    """Test the complete authentication flow."""
    
    print("=" * 60)
    print("Testing Authentication System")
    print("=" * 60)
    
    # Test 1: Register a new user
    print("\n1. Testing User Registration...")
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ User registered successfully!")
            print(f"   User: {response.json()}")
        elif response.status_code == 400:
            print("⚠️  User already exists (expected if running multiple times)")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return
    
    # Test 2: Login to get access token
    print("\n2. Testing User Login...")
    login_data = {
        "username": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print("✅ Login successful!")
            print(f"   Token type: {token_data['token_type']}")
            print(f"   Access token: {access_token[:50]}...")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return
    
    # Test 3: Get current user info
    print("\n3. Testing Get Current User...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print("✅ Retrieved user information!")
            print(f"   Email: {user_data['email']}")
            print(f"   Name: {user_data['full_name']}")
            print(f"   Role: {user_data['role']}")
            print(f"   Active: {user_data['is_active']}")
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
    
    # Test 4: Send a chat message (protected endpoint)
    print("\n4. Testing Protected Chat Endpoint...")
    chat_data = {
        "message": "How do I create a project?",
        "session_id": "test-session-123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=chat_data,
            headers={**headers, "Content-Type": "application/json"}
        )
        if response.status_code == 200:
            chat_response = response.json()
            print("✅ Chat request successful!")
            print(f"   Response: {chat_response['response'][:100]}...")
            print(f"   Session ID: {chat_response['session_id']}")
            print(f"   Sources: {len(chat_response.get('sources', []))} documents")
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during chat: {e}")
    
    # Test 5: Try chat without authentication (should fail)
    print("\n5. Testing Chat Without Authentication...")
    try:
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        if response.status_code == 401:
            print("✅ Correctly rejected unauthenticated request!")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Try with invalid token (should fail)
    print("\n6. Testing Chat With Invalid Token...")
    invalid_headers = {"Authorization": "Bearer invalid_token_here"}
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=chat_data,
            headers={**invalid_headers, "Content-Type": "application/json"}
        )
        if response.status_code == 401:
            print("✅ Correctly rejected invalid token!")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Authentication Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n⚠️  Make sure the API server is running:")
    print("   uvicorn api:app --reload --port 8000\n")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API server is running!\n")
            test_authentication_flow()
        else:
            print("❌ API server responded but with unexpected status")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Please start it first.")
        print("   Run: uvicorn api:app --reload --port 8000")
