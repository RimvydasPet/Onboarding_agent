# 🔐 Authentication Guide

## Overview

The AI Onboarding Assistant now includes a comprehensive JWT-based authentication system to secure API access and manage user sessions. This guide explains how to use the authentication features.

## Features

- **JWT Token Authentication**: Secure token-based authentication using JSON Web Tokens
- **Password Security**: Passwords are hashed using bcrypt before storage
- **User Registration**: Create new user accounts with email and password
- **User Login**: Authenticate and receive access tokens
- **Protected Endpoints**: Chat endpoint requires valid authentication
- **Token Expiration**: Tokens expire after 30 minutes (configurable)
- **Role-Based Access**: Support for user roles (user, admin)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Application                    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              POST /auth/register (Public)                │
│              POST /auth/login (Public)                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼ (Returns JWT Token)
┌─────────────────────────────────────────────────────────┐
│         Authorization: Bearer <token>                    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              GET /auth/me (Protected)                    │
│              POST /chat (Protected)                      │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The authentication system requires:
- `python-jose[cryptography]` - JWT token handling
- `passlib[bcrypt]` - Password hashing
- `python-multipart` - Form data parsing

### 2. Configure Environment

Ensure your `.env` file has the following settings:

```env
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important**: Change `SECRET_KEY` to a secure random string in production. Generate one using:

```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Start the API Server

```bash
uvicorn api:app --reload --port 8000
```

## API Endpoints

### Public Endpoints

#### 1. Register a New User

**Endpoint**: `POST /auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "role": "user",
  "created_at": "2024-01-25T12:00:00"
}
```

**Error Responses**:
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Invalid email format or missing fields

**Example (curl)**:
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "email": "user@example.com",
        "password": "securepassword123",
        "full_name": "John Doe"
    }
)
print(response.json())
```

#### 2. Login

**Endpoint**: `POST /auth/login`

**Request Body** (form-data):
```
username: user@example.com
password: securepassword123
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401 Unauthorized`: Incorrect email or password
- `403 Forbidden`: User account is inactive

**Example (curl)**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"
```

**Example (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/auth/login",
    data={
        "username": "user@example.com",
        "password": "securepassword123"
    }
)
token_data = response.json()
access_token = token_data["access_token"]
```

### Protected Endpoints

All protected endpoints require the `Authorization` header with a valid JWT token:

```
Authorization: Bearer <your_access_token>
```

#### 3. Get Current User

**Endpoint**: `GET /auth/me`

**Headers**:
```
Authorization: Bearer <your_access_token>
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "role": "user",
  "created_at": "2024-01-25T12:00:00"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: User account is inactive

**Example (curl)**:
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Example (Python)**:
```python
import requests

headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/auth/me", headers=headers)
print(response.json())
```

#### 4. Chat (Protected)

**Endpoint**: `POST /chat`

**Headers**:
```
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "message": "How do I create a project?",
  "session_id": "optional-session-id"
}
```

**Response** (200 OK):
```json
{
  "response": "To create a project...",
  "session_id": "session-123",
  "sources": [
    {
      "content": "...",
      "metadata": {"source": "projects_guide.md"}
    }
  ],
  "current_stage": "welcome"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or expired token
- `500 Internal Server Error`: Server error during processing

**Example (curl)**:
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I create a project?",
    "session_id": "my-session-123"
  }'
```

**Example (Python)**:
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "How do I create a project?",
        "session_id": "my-session-123"
    },
    headers=headers
)
print(response.json())
```

## Complete Authentication Flow Example

Here's a complete Python example showing the full authentication flow:

```python
import requests

BASE_URL = "http://localhost:8000"

# Step 1: Register a new user
register_response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "full_name": "New User"
    }
)
print("Registration:", register_response.json())

# Step 2: Login to get access token
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "newuser@example.com",
        "password": "securepass123"
    }
)
token_data = login_response.json()
access_token = token_data["access_token"]
print("Login successful, token received")

# Step 3: Get user information
headers = {"Authorization": f"Bearer {access_token}"}
user_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print("User info:", user_response.json())

# Step 4: Use the chat endpoint
chat_response = requests.post(
    f"{BASE_URL}/chat",
    json={"message": "How do I get started?"},
    headers={**headers, "Content-Type": "application/json"}
)
print("Chat response:", chat_response.json()["response"])
```

## Testing

A test script is provided to verify the authentication system:

```bash
python test_auth.py
```

This script will:
1. Register a test user
2. Login and receive a token
3. Get current user information
4. Send a chat message (authenticated)
5. Verify unauthenticated requests are rejected
6. Verify invalid tokens are rejected

## Security Best Practices

### For Development

1. **Use Strong Passwords**: Minimum 8 characters with mixed case, numbers, and symbols
2. **Keep Tokens Secure**: Never commit tokens to version control
3. **Use HTTPS**: In production, always use HTTPS to encrypt token transmission
4. **Rotate Secrets**: Change `SECRET_KEY` regularly in production

### For Production

1. **Environment Variables**: Store `SECRET_KEY` in environment variables, not in code
2. **Token Expiration**: Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` based on security requirements
3. **Rate Limiting**: Implement rate limiting on authentication endpoints
4. **CORS Configuration**: Restrict `ALLOWED_ORIGINS` to trusted domains only
5. **Database Security**: Use PostgreSQL or MySQL instead of SQLite
6. **Password Policy**: Enforce strong password requirements
7. **Account Lockout**: Implement account lockout after failed login attempts
8. **Audit Logging**: Log all authentication events

## Token Management

### Token Structure

JWT tokens contain:
- **Header**: Algorithm and token type
- **Payload**: User email (sub), expiration time (exp)
- **Signature**: Cryptographic signature

### Token Expiration

Tokens expire after 30 minutes by default. Configure in `.env`:

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

When a token expires, clients must login again to get a new token.

### Handling Token Expiration

```python
import requests

def make_authenticated_request(url, token, data=None):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 401:
        # Token expired, need to re-authenticate
        print("Token expired, please login again")
        return None
    
    return response.json()
```

## Troubleshooting

### Common Issues

**1. "Could not validate credentials"**
- Token is invalid or expired
- Token format is incorrect (should be "Bearer <token>")
- SECRET_KEY mismatch between token creation and validation

**2. "Email already registered"**
- User with this email already exists
- Use a different email or login with existing credentials

**3. "Incorrect email or password"**
- Check email and password are correct
- Passwords are case-sensitive

**4. "Inactive user"**
- User account has been deactivated
- Contact administrator to reactivate

**5. Connection refused**
- API server is not running
- Start server: `uvicorn api:app --reload --port 8000`

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration Examples

### JavaScript/TypeScript

```typescript
const BASE_URL = 'http://localhost:8000';

// Register
const register = async (email: string, password: string, fullName: string) => {
  const response = await fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName })
  });
  return response.json();
};

// Login
const login = async (email: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData
  });
  return response.json();
};

// Chat
const chat = async (token: string, message: string) => {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  return response.json();
};
```

### React Hook Example

```typescript
import { useState, useEffect } from 'react';

export const useAuth = () => {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });
    
    const data = await response.json();
    if (response.ok) {
      setToken(data.access_token);
      localStorage.setItem('access_token', data.access_token);
    }
    return data;
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('access_token');
  };

  return { token, login, logout };
};
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- View all endpoints and their parameters
- Test endpoints directly from the browser
- See request/response schemas
- Authenticate and test protected endpoints

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Check server logs for error messages
4. Ensure all dependencies are installed correctly

---

**Built with security in mind for the AI Onboarding Assistant** 🔐
